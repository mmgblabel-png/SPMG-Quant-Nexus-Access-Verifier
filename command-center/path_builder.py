"""Bounded, local-only first-path-stone pilot for SPMG Game Maker.

Requires the user to have the AI Build Backup open and maximized. It performs
ONE left click, never presses Alt/Ctrl to place, never saves or publishes.
It does not claim OCR or authoritative confirmation of the selected material.
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
PROOF_DIR = DATA / 'path-pilot'
ATTEMPT = DATA / 'path-pilot-attempt.json'


def terrain_green(pixel):
    r, g, b = pixel[:3]
    return g > 80 and g > r * 1.22 and g > b * 1.14 and r < 190


def stone_grey(pixel):
    r, g, b = pixel[:3]
    return 65 <= max(r, g, b) <= 228 and max(r, g, b) - min(r, g, b) <= 32


def pixels(image, x, y, radius=15):
    w, h = image.size
    x0, x1 = max(0, x - radius), min(w, x + radius)
    y0, y1 = max(0, y - radius), min(h, y + radius)
    return [image.getpixel((u, v)) for v in range(y0, y1)
            for u in range(x0, x1)]


def choose_green_target(image):
    """Pick only from a bounded center-right grass zone, never a random GUI area."""
    w, h = image.size
    candidates = ((.585, .630), (.595, .645), (.57, .645), (.61, .62))
    for rx, ry in candidates:
        x, y = round(w * rx), round(h * ry)
        sample = pixels(image, x, y, 18)
        if sample and sum(terrain_green(c) for c in sample) / len(sample) >= .87:
            return x, y
    raise RuntimeError('Geen veilig, egaal grasgebied gevonden in de bekende bouwzone.')


def stone_preview_visible(image):
    """Heuristic for cube-shaped grey material preview in Game Maker properties.

    A neutral-colour preview is not authoritative proof that Stone_Grey is selected.
    """
    w, h = image.size
    x0, x1 = round(w * .90), round(w * .973)
    y0, y1 = round(h * .24), round(h * .55)
    points = [image.getpixel((x, y)) for y in range(y0, y1, 3)
              for x in range(x0, x1, 3)]
    return bool(points) and sum(stone_grey(p) for p in points) >= max(65, len(points) // 9)


def new_stone_pixels(before, after, center, radius=60):
    x, y = center
    w, h = before.size
    changed = 0
    for yy in range(max(0, y - radius), min(h, y + radius)):
        for xx in range(max(0, x - radius), min(w, x + radius)):
            b = before.getpixel((xx, yy))
            a = after.getpixel((xx, yy))
            if terrain_green(b) and stone_grey(a):
                changed += 1
    return changed


def actor_sidebar_preserved(before, after):
    """Protect the hierarchy area from accidental changes, without claiming OCR."""
    w, h = before.size
    x1 = int(w * .105)
    y0, y1 = int(h * .20), int(h * .355)
    total = modified = 0
    for yy in range(y0, y1, 2):
        for xx in range(4, x1, 2):
            total += 1
            p, q = before.getpixel((xx, yy)), after.getpixel((xx, yy))
            if max(abs(p[z] - q[z]) for z in range(3)) > 18:
                modified += 1
    return total > 0 and modified / total < .008


def run_pilot():
    if os.name != 'nt':
        raise RuntimeError('Deze bouwfunctie draait uitsluitend lokaal op Windows.')
    if ATTEMPT.exists():
        raise RuntimeError('De padsteenproef is al gestart. Controleer eerst het vorige resultaat; geen dubbele klik.')
    if (Path.home() / 'Documents' / 'SPMG-Sandbox' / 'AI-Agent-Work' /
            'SPMG-Desktop-Agent' / 'STOP').exists():
        raise RuntimeError('Agent STOP is actief.')
    try:
        import pyautogui as pg
        import pygetwindow as gw
    except ImportError as exc:
        raise RuntimeError('Benodigde lokale GUI-module ontbreekt: ' + str(exc))
    active = gw.getActiveWindow()
    if not active or 'game maker' not in (active.title or '').lower():
        raise RuntimeError('Activeer eerst het Game Maker-venster met AI Build Backup.')
    if not active.isMaximized:
        raise RuntimeError('Maximaliseer Game Maker voordat de agent gaat bouwen.')
    pg.FAILSAFE = True
    pg.PAUSE = .18
    w, h = pg.size()
    if w < 1500 or h < 700:
        raise RuntimeError('Beeldschermindeling te klein of niet herkend; geen klik uitgevoerd.')
    if abs(active.left) > 3 or abs(active.top) > 35 or abs(active.width - w) > 35:
        raise RuntimeError('Game Maker vult niet het verwachte scherm; geen klik uitgevoerd.')
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    # Move out of terrain; key 3 re-selects the known Stone_Grey quickbar slot.
    pg.moveTo(int(w * .53), int(h * .065), duration=.2)
    pg.press('3')
    time.sleep(.7)
    before = pg.screenshot().convert('RGB')
    if not stone_preview_visible(before):
        raise RuntimeError('Stone_Grey-materiaalvoorbeeld niet overtuigend zichtbaar; geen klik.')
    target = choose_green_target(before)
    # Durable attempt marker is written BEFORE the physical action.
    marker = {
        'started': datetime.now(timezone.utc).isoformat(),
        'operation': 'one_plain_left_click',
        'target': list(target),
        'save': False,
        'publish': False,
        'state': 'started',
    }
    ATTEMPT.write_text(json.dumps(marker, indent=2), encoding='utf-8')
    before.save(PROOF_DIR / 'before.png')
    try:
        pg.moveTo(target[0], target[1], duration=.4)
        time.sleep(.25)
        pg.click(button='left', clicks=1, interval=.0)
        time.sleep(.6)
        pg.moveTo(int(w * .53), int(h * .065), duration=.3)
        time.sleep(.75)
        after = pg.screenshot().convert('RGB')
        after.save(PROOF_DIR / 'after.png')
        count = new_stone_pixels(before, after, target)
        same_sidebar = actor_sidebar_preserved(before, after)
        evidence = {
            **marker,
            'state': 'needs_review',
            'new_neutral_stone_pixels': count,
            'actor_sidebar_unchanged': same_sidebar,
            'visual_proof_indication': bool(count >= 16 and same_sidebar),
            'screenshots': [str(PROOF_DIR / 'before.png'), str(PROOF_DIR / 'after.png')],
            'note': 'Lokale pixelschatting, geen onafhankelijk bewijs van correcte 3D-plaatsing. Niet opgeslagen.',
        }
        (PROOF_DIR / 'result.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        ATTEMPT.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps(evidence, ensure_ascii=False))
        return 0
    except BaseException:
        # Never clear the marker after uncertain GUI input.
        raise


if __name__ == '__main__':
    try:
        if sys.argv[1:] != ['--pilot']:
            raise ValueError('Alleen het begrensde commando --pilot is toegestaan.')
        sys.exit(run_pilot())
    except Exception as exc:
        print('PADBOUW GEBLOKKEERD: ' + str(exc), file=sys.stderr)
        sys.exit(2)
