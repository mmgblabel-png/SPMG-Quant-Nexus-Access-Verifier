"""SPMG AI Command Center v1: one local chat, audited bounded Game Maker runner.

No remote shell, arbitrary file writes, publisher, wallet tools or unsafe model tools.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

VERSION = '1.0.4'
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'command-center.sqlite3'
AGENT = Path.home() / 'Documents' / 'SPMG-Sandbox' / 'AI-Agent-Work' / 'SPMG-Desktop-Agent'
RUNS = AGENT / 'runs'
PORT = int(os.environ.get('SPMG_COMMAND_CENTER_PORT', '8792'))
TOKEN = secrets.token_urlsafe(32)
JOB_LOCK = threading.Lock()
ACTIVE = {'id': None, 'kind': None}
BASE_REPO = 'https://github.com/mmgblabel-png/SPMG-Quant-Nexus-Access-Verifier/tree/main/command-center'
SERVER = None


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, at TEXT NOT NULL, who TEXT NOT NULL, text TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, phase TEXT NOT NULL, task TEXT NOT NULL, output TEXT DEFAULT "")')
    return db


def record(who, msg):
    with connect() as db:
        db.execute('INSERT INTO messages (at,who,text) VALUES (?,?,?)', (utc(), who, msg[:16000]))


def history():
    with connect() as db:
        return [{'who': x[0], 'text': x[1], 'at': x[2]} for x in db.execute('SELECT who,text,at FROM messages ORDER BY id DESC LIMIT 35')][::-1]


def recent_jobs():
    with connect() as db:
        return [{'id': x[0], 'kind': x[1], 'phase': x[2], 'at': x[3], 'output': x[4][-1100:]} for x in db.execute('SELECT id,kind,phase,at,output FROM jobs ORDER BY at DESC LIMIT 12')]


def last_run():
    if not RUNS.is_dir():
        return None
    recent = sorted((x for x in RUNS.iterdir() if x.is_dir() and x.name.startswith('build-')), key=lambda x: x.stat().st_mtime, reverse=True)
    for directory in recent[:5]:
        f = directory / 'status.json'
        if f.is_file():
            try:
                raw = json.loads(f.read_text(encoding='utf-8'))
                return {'run': directory.name, 'phase': raw.get('phase'), 'detail': raw.get('detail', ''), 'error': raw.get('error', ''), 'gui_actions': raw.get('gui_input_actions_executed'), 'save_sent': raw.get('save_shortcut_sent')}
            except (OSError, ValueError):
                continue
    return None


def status():
    return {'version': VERSION, 'installed_agent': (AGENT / 'agent.py').is_file(), 'game_maker_runs': RUNS.is_dir(), 'chat_ai': bool(os.environ.get('OPENAI_API_KEY')), 'current_job': dict(ACTIVE), 'latest_run': last_run(), 'repo': BASE_REPO, 'jobs': recent_jobs()}


def build_task(kind, actor_count=4):
    """Compile ONLY known narrow plans. Never let an LLM generate executable Python."""
    jid = 'spmgchat-' + uuid.uuid4().hex[:16]
    if kind == 'tree':
        plan = {'job_id': jid, 'mode': 'place_props', 'expected_actors': actor_count,
                'steps': [{'asset': 'tree', 'slot': 7, 'x': .58, 'y': .68}], 'save': True}
    elif kind == 'stone':
        plan = {'job_id': jid, 'mode': 'replace_path_probe', 'expected_actors': 4, 'slot': 3,
                'x': 992, 'y': 461, 'save': False}
    elif kind == 'calibrate':
        plan = {'job_id': jid, 'mode': 'calibrate_path', 'expected_actors': 4, 'slot': 3, 'save': False}
    else:
        raise ValueError('Niet-ondersteunde bouwactie')
    text = 'SPMG_AI_BACKUP_MODE\nSPMG_AUTOBUILD_V2\n' + json.dumps(plan, ensure_ascii=False, separators=(',', ':'))
    return jid, text


def bridge_is_running():
    # Prevent two independent desktop controllers from using the same Game Maker UI.
    if os.name != 'nt':
        return False
    ps = ("Get-CimInstance Win32_Process | Where-Object { "
          "$_.Name -match '^python(w)?\\.exe$' -and "
          "$_.CommandLine -match 'bridge_worker\\.py' } | Select-Object -First 1 -ExpandProperty ProcessId")
    try:
        p = subprocess.run(['powershell','-NoProfile','-Command',ps],stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL,text=True,timeout=7)
        return bool(p.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        # Cannot safely establish no competing controller.
        return True


def agent_process_running():
    return bool(ACTIVE['id'])


def worker(jid, kind, task):
    try:
        if not (AGENT / 'agent.py').is_file():
            raise RuntimeError('Agent niet gevonden in de bestaande SPMG-Desktop-Agent-map.')
        if (AGENT / 'STOP').exists():
            raise RuntimeError('STOP-bestand aanwezig. Eerst vrijgeven nadat je Game Maker hebt gecontroleerd.')
        with connect() as db:
            db.execute('UPDATE jobs SET phase=? WHERE id=?', ('running', jid))
        taskpath = DATA / ('task-' + jid + '.txt')
        taskpath.write_text(task, encoding='utf-8')
        # Run existing audited controller. No arbitrary shell or unbounded code.
        command = ['py', '-3', str(AGENT / 'agent.py'), '--run', '--task-file', str(taskpath)]
        result = subprocess.run(command, cwd=AGENT, text=True, errors='replace',
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=420, shell=False)
        output = result.stdout[-12000:]
        phase = 'review' if result.returncode == 0 else 'blocked'
    except subprocess.TimeoutExpired:
        phase, output = 'blocked', 'Bouwactie stopte na tijdslimiet; controleer de actuele scène voordat je opnieuw bouwt.'
    except Exception as exc:
        phase, output = 'blocked', type(exc).__name__ + ': ' + str(exc)
    finally:
        try:
            with connect() as db:
                db.execute('UPDATE jobs SET phase=?,output=? WHERE id=?', (phase, output, jid))
        finally:
            with JOB_LOCK:
                ACTIVE['id'] = None
                ACTIVE['kind'] = None


def enqueue(kind):
    with JOB_LOCK:
        if agent_process_running():
            return 'Er loopt al een taak. Ik start geen tweede bouwproces.'
        if bridge_is_running():
            return 'De oude Agent Bridge draait nog. Stop die eenmalig met Ctrl+C; gebruik voortaan dit Command Center voor opdrachten.'
        if kind == 'tree':
            # Hard baseline: new runs must not duplicate saved trees or guess counts.
            return ('Boomplaatsing is beschikbaar in de bestaande AutoBuilder, maar vereist eerst een '
                    'actuele bevestigde Actors-telling. Gebruik “controleer Game Maker” en het uitvoerlog; '
                    'ik start niet blind een vijfde Actor.')
        jid, task = build_task(kind)
        with connect() as db:
            db.execute('INSERT INTO jobs (id,at,kind,phase,task) VALUES (?,?,?,?,?)', (jid, utc(), kind, 'queued', task))
        ACTIVE['id'], ACTIVE['kind'] = jid, kind
    threading.Thread(target=worker, args=(jid, kind, task), daemon=True).start()
    return ('Opdracht ' + jid + ' gestart in de AI Build Backup. ' +
            ('Er wordt NIET automatisch opgeslagen.' if kind in ('stone','calibrate') else 'Opslag volgt alleen na bewijs.') +
            ' Bekijk het resultaat bij Status.')


def launch_probe():
    with JOB_LOCK:
        if agent_process_running():
            return 'Er loopt al een bouwtaak.'
        if bridge_is_running():
            return 'De oude Agent Bridge draait nog. Stop die eerst met Ctrl+C om dubbele besturing te voorkomen.'
        jid = 'probe-' + uuid.uuid4().hex[:12]
        with connect() as db:
            db.execute('INSERT INTO jobs (id,at,kind,phase,task) VALUES (?,?,?,?,?)', (jid, utc(), 'probe', 'queued', '--probe'))
        ACTIVE['id'], ACTIVE['kind'] = jid, 'probe'
    def go():
        try:
            with connect() as db: db.execute('UPDATE jobs SET phase=? WHERE id=?', ('running',jid))
            cp = subprocess.run(['py','-3',str(AGENT/'agent.py'),'--probe'],cwd=AGENT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90,text=True,errors='replace')
            phase,output=('review' if cp.returncode == 0 else 'blocked'),cp.stdout[-6000:]
        except Exception as exc:
            phase,output='blocked',str(exc)
        finally:
            with connect() as db: db.execute('UPDATE jobs SET phase=?,output=? WHERE id=?',(phase,output,jid))
            with JOB_LOCK: ACTIVE['id']=ACTIVE['kind']=None
    threading.Thread(target=go,daemon=True).start()
    return 'Game Maker-screenshotcontrole gestart. Geen bouwacties of API-kosten.'


def is_openai_ready():
    return bool(os.environ.get('OPENAI_API_KEY'))


def ai_reply(prompt):
    if not is_openai_ready():
        return ('Ik kan lokale SPMG-opdrachten verwerken, maar vrije AI-chat vereist een OPENAI_API_KEY. '
                'ChatGPT Plus bevat niet automatisch API-tegoed. Je sleutel blijft lokaal in Windows.')
    try:
        from openai import OpenAI
        messages = [{'role':'system', 'content': (
            'Je bent de Nederlandstalige SPMG Game Maker ontwikkelassistent. Je geeft concrete plannen en '
            'beperkt jezelf tot beschikbare mogelijkheden. Geen claims dat je Game Maker hebt aangepast. '
            'Geen shellcode, ongecontroleerde OS-acties, publicatie, betalingen of wallettransacties. '
            'Voor echt uitvoeren heeft de lokale gebruiker vaste en gecontroleerde opdrachten. '
            'Antwoord compact, technisch, in het Nederlands.')}]
        for item in history()[-10:]:
            messages.append({'role':'assistant' if item['who']=='agent' else 'user', 'content': item['text'][:3000]})
        client=OpenAI(timeout=40,max_retries=1)
        r=client.responses.create(model=os.environ.get('SPMG_CHAT_MODEL','gpt-4.1-mini'), input=messages, max_output_tokens=650, store=False)
        return r.output_text.strip() or 'Geen AI-antwoord ontvangen.'
    except Exception as exc:
        return 'AI-chat niet beschikbaar: ' + type(exc).__name__ + '. De lokale bouwfuncties blijven werken.'


def update_from_chat():
    """User-requested updater; fetch only manifest-hashed files from own repo."""
    if ACTIVE['id']:
        return 'Er loopt nog een taak. Bijwerken is geblokkeerd totdat die is afgelopen.'
    if os.name != 'nt':
        return 'Automatisch bijwerken in de chat is bedoeld voor Windows.'
    updater = ROOT / 'update.ps1'
    if not updater.is_file():
        return 'update.ps1 ontbreekt. Start eenmaal met START-SPMG.cmd.'
    try:
        result = subprocess.run(
            ['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(updater),'-Apply'],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors='replace', timeout=100, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 'Bijwerken niet gelukt: ' + str(exc)
    if result.returncode:
        return 'Bijwerken is veilig afgebroken: ' + result.stdout[-1200:]
    # The PowerShell launcher supervises the Python process. Exit with a
    # dedicated code AFTER the HTTP response; the launcher then reloads the
    # updated app. Never spawn an orphan Python process from a daemon thread.
    if os.environ.get('SPMG_SUPERVISOR') != '1':
        return ('Updatebestanden gecontroleerd en geïnstalleerd. Start het '
                'Command Center één keer opnieuw met START-SPMG.cmd; de huidige '
                'chatserver draait nog met de vorige code.')
    def request_restart():
        time.sleep(2.5)
        os._exit(23)
    threading.Thread(target=request_restart, daemon=True).start()
    return ('Update gecontroleerd. De Windows-starter herstart de AI-chat automatisch. '
            'Vernieuw daarna deze pagina met Ctrl+F5 om de nieuwe verbinding te gebruiken.')


def diagnose_latest():
    """Read-only explanation from the real most recent agent run."""
    run = last_run()
    if not run:
        return 'Er zijn nog geen bouwruns gevonden. Gebruik eerst Game Maker controleren.'
    p = RUNS / run['run']
    detail = str(run.get('detail') or '')
    error = str(run.get('error') or '')
    lines = [
        'Laatste bouwrun: ' + run['run'],
        'Status: ' + str(run.get('phase') or 'onbekend'),
        'Reden: ' + (error or detail or 'Geen exacte foutmelding opgeslagen.'),
    ]
    if error and detail:
        lines.append('Aanvullend: ' + detail)
    proof = p / 'path-proof.json'
    if proof.is_file():
        try:
            evidence = json.loads(proof.read_text(encoding='utf-8'))
            lines.append('Terreinbewijs: ' + str(evidence.get('additional_neutral_stone_pixels', 'niet gemeten')) + ' extra steenpixels.')
        except (OSError, ValueError):
            lines.append('Terreinbewijs kon niet gelezen worden.')
    else:
        lines.append('Geen path-proof.json in deze run: blokplaatsing is niet onafhankelijk bevestigd.')
    if run.get('phase') == 'blocked':
        if 'herhaling' in (detail + error).casefold():
            lines.append('De anti-herhalingsbeveiliging is geactiveerd. Dit is geen bewijs dat een blok is geplaatst.')
        lines.append('Veilige volgende stap: laat de AI Build Backup open, controleer of er een nieuwe steen of Actor aanwezig is en verstuur nog geen tweede steenproef.')
    elif run.get('phase') == 'needs_review':
        lines.append('Veilige volgende stap: vergelijk de screenshots voor/na en sla niet op bij onzekerheid.')
    else:
        lines.append('Controleer de opgeslagen scène voordat je een volgende bouwtaak start.')
    lines.append('De lokale AI-chat staat ' + ('aan.' if is_openai_ready() else 'uit; vaste controles werken zonder API-sleutel.'))
    return '\n'.join(lines)


def respond(message):
    msg = message.strip()
    if not msg or len(msg) > 4000:
        return 'Schrijf een opdracht van maximaal 4000 tekens.'
    lower = msg.casefold()
    record('user', msg)
    if any(word in lower for word in ('waarom', 'diagnose', 'geblokkeerd', 'bouwfout', 'bouwprobleem')):
        reply = diagnose_latest()
    elif any(word in lower for word in ('status','hoe staat','overzicht','voortgang','laatste run')):
        s = status()
        last = s['latest_run'] or {}
        reply = f"Agent: {'gevonden' if s['installed_agent'] else 'niet gevonden'}. Laatste bouwrun: {last.get('run','geen')}; status: {last.get('phase','onbekend')}. {last.get('detail','')} Actieve taak: {s['current_job']['id'] or 'geen'}."
    elif ('controleer' in lower or 'inspecteer' in lower or 'screenshot' in lower) and ('game' in lower or 'scene' in lower or 'scène' in lower):
        reply = launch_probe()
    elif ('kalibreer' in lower or 'kalibratie' in lower) and ('pad' in lower or 'steen' in lower or 'stone' in lower):
        reply = enqueue('calibrate')
    elif any(w in lower for w in ('steenproef','vloertest','test steen','eerste steen','test het pad','vervang één grasblok')):
        reply = enqueue('stone')
    elif ('boom' in lower or 'bomen' in lower) and any(w in lower for w in ('plaats','bouw','plant')):
        reply = enqueue('tree')
    elif ('update' in lower or 'bijwerken' in lower or 'bijwerkt' in lower) and any(w in lower for w in ('agent','jezelf','software','command','systeem')):
        # Update is a narrowly scoped signed-hash check implemented in update.ps1.
        # Manual restart of this running server is still needed on Windows.
        reply = update_from_chat()
    elif 'publiceer' in lower or 'publish' in lower:
        reply = 'Publicatie blijft uitsluitend jouw handeling. Ik kan wel een checklist en screenshots opleveren.'
    elif ('bouw' in lower or 'maak' in lower) and any(w in lower for w in ('plaza','nexus hub','hele game','volledige','wandelpad')):
        reply = ('Ik kan het bouwplan voorbereiden, maar het huidige v0.9.1 Game Maker-deel heeft '
                 'nog geen bewezen pad- of gebouwuitvoering. Ik ga geen ongeteste serie klikken doen. '
                 'De eerste steenproef en automatische objectopslag worden nog getest. ' +
                 (ai_reply(msg) if is_openai_ready() else 'Zeg “controleer Game Maker” om de huidige scène te inspecteren.'))
    else:
        reply = ai_reply(msg)
    record('agent',reply)
    return reply


HTML = r'''<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPMG AI Command Center</title><style>
:root{font:15px/1.5 system-ui,Segoe UI,Arial;background:#07111f;color:#e8f3ff}*{box-sizing:border-box}body{margin:0;display:flex;height:100vh}
nav{width:265px;background:#0b1a2d;border-right:1px solid #263d55;padding:24px;display:flex;flex-direction:column;gap:22px}
.brand{font-size:19px;font-weight:750;letter-spacing:.3px}.brand small{display:block;font-size:12px;color:#8eabc7;font-weight:400}
nav button{border:1px solid #284864;background:#132b43;color:#cce9fb;text-align:left;border-radius:10px;padding:11px 12px;cursor:pointer;font:inherit}
nav button:hover{background:#214565}main{flex:1;display:flex;flex-direction:column;min-width:0}.top{border-bottom:1px solid #263d55;padding:14px 25px;display:flex;align-items:center;justify-content:space-between;background:#09192b}
.top h1{font-size:19px;margin:0}.pill{border:1px solid #2a6073;background:#133b4a;border-radius:50px;padding:5px 13px;color:#a5eddb;font-size:12px}
#messages{flex:1;overflow:auto;padding:24px min(6vw,70px);display:flex;flex-direction:column;gap:15px}
.msg{max-width:820px;white-space:pre-wrap;border-radius:14px;padding:15px 19px;line-height:1.55;background:#10243a;border:1px solid #25415c}.msg.user{align-self:flex-end;background:#0d526b;border-color:#1688a3}.role{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:#8db1c8;margin-bottom:6px}
form{display:flex;gap:10px;background:#0b1a2d;padding:15px 25px 23px}textarea{flex:1;background:#071728;color:#eaf6ff;border:1px solid #375875;border-radius:12px;padding:12px 15px;font:inherit;resize:vertical;min-height:66px}button.submit{border:0;border-radius:12px;background:linear-gradient(90deg,#1378b8,#18b9d1);color:#fff;padding:0 22px;font-weight:700;cursor:pointer}
footer{color:#84a9bf;font-size:12px;padding:0 25px 15px;background:#0b1a2d}#details{display:none;margin:12px 25px;background:#0d2134;border:1px solid #234259;border-radius:12px;padding:12px 18px;max-height:270px;overflow:auto;white-space:pre-wrap;font:12px Consolas,monospace}
@media(max-width:700px){nav{width:70px;padding:12px}.brand{font-size:12px}.brand small{display:none}nav button{font-size:0}nav button:before{content:'●';font-size:15px}.top{padding:14px}#messages{padding:15px}form{padding:12px}}
</style></head><body><nav><div class="brand">◆ SPMG AI<br>COMMAND CENTER<small>Lokale Game Maker-agent</small></div>
<button onclick="ask('status')">◉ Agentstatus</button><button onclick="ask('controleer Game Maker')">▣ Game Maker controleren</button><button onclick="ask('kalibreer het stenen pad')">◈ Padkalibratie</button><button onclick="ask('test eerste steen')">▦ Steenproef</button><button onclick="ask('waarom is bouwen geblokkeerd?')">! Diagnose blokkade</button><button onclick="showStatus()">☷ Logs en resultaten</button><div style="flex:1"></div><small style="color:#7fa0b8">Alleen AI Build Backup. Geen aankopen, wallets of publicatie.</small></nav>
<main><div class="top"><h1>SPMG AI Developer <span style="font-size:12px;color:#80a0b6">v1.0.4</span></h1><span class="pill" id="state">● Lokaal</span></div>
<section id="details"></section><section id="messages"></section><form id="frm"><textarea id="input" placeholder="Bijv. 'Controleer Game Maker', 'Wat is de status?', 'Ontwerp de Welcome Plaza'..."></textarea><button class="submit" type="submit">Verstuur</button></form><footer>Jij geeft de opdracht · de lokale agent voert alleen ondersteunde acties uit · jij publiceert zelf</footer></main>
<script>
const KEY = '__TOKEN__';
const messages=document.getElementById('messages');const input=document.getElementById('input');
function bubble(who,text){const div=document.createElement('div');div.className='msg '+who;const label=document.createElement('div');label.className='role';label.textContent=who==='user'?'Jij':'SPMG AI';const body=document.createElement('div');body.textContent=text;div.append(label,body);messages.appendChild(div);messages.scrollTop=messages.scrollHeight}
async function api(endpoint,method='GET',data){let response=await fetch(endpoint,{method,headers:{'Content-Type':'application/json','X-SPMG-Token':KEY},body:data?JSON.stringify(data):undefined});if(!response.ok)throw Error('HTTP '+response.status);return response.json()}
async function ask(text){const msg=text||input.value.trim();if(!msg)return;input.value='';bubble('user',msg);try{let r=await api('/api/chat','POST',{message:msg});bubble('agent',r.reply);await updateState()}catch(e){bubble('agent','Fout: '+e.message)}}
async function showStatus(){try{let s=await api('/api/status');let area=document.getElementById('details');area.style.display='block';area.textContent=JSON.stringify(s,null,2)}catch(e){bubble('agent',e.message)}}
async function updateState(){try{let s=await api('/api/status');document.getElementById('state').textContent=(s.current_job.id?'● Bezig: '+s.current_job.kind:'● Lokaal · '+(s.installed_agent?'agent gevonden':'agent ontbreekt'))+(s.chat_ai?' · AI-chat aan':' · AI-chat uit')}catch(e){document.getElementById('state').textContent='Niet verbonden'}}
document.getElementById('frm').onsubmit=e=>{e.preventDefault();ask()};input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask()}});
(async()=>{try{const r=await api('/api/history');if(!r.messages.length)bubble('agent','Welkom bij SPMG AI Command Center. Je kunt met mij chatten, de Game Maker-agent controleren en ondersteunde bouwproeven uitvoeren. Publiceren doe jij zelf.');else r.messages.forEach(m=>bubble(m.who==='user'?'user':'agent',m.text))}catch(e){bubble('agent','Verbinden mislukt: '+e.message)}await updateState()})();setInterval(updateState,12000);
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, code=200):
        raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            raw=HTML.replace('__TOKEN__',TOKEN).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
        elif path=='/api/status': self.send_json(status())
        elif path=='/api/history': self.send_json({'messages':history()})
        else: self.send_json({'error':'Niet gevonden'},404)

    def do_POST(self):
        origin=self.headers.get('Origin','')
        allowed={'http://127.0.0.1:'+str(PORT),'http://localhost:'+str(PORT)}
        if (origin and origin not in allowed) or self.headers.get('X-SPMG-Token')!=TOKEN:
            return self.send_json({'error':'Ongeldige aanvraag'},403)
        if self.path!='/api/chat': return self.send_json({'error':'Onbekend'},404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>10000: raise ValueError('Ongeldige berichtlengte')
            payload=json.loads(self.rfile.read(length))
            message=payload.get('message','')
            if not isinstance(message,str): raise ValueError('Tekst verwacht')
            reply=respond(message)
            self.send_json({'reply':reply})
        except (ValueError,TypeError,KeyError) as exc:
            self.send_json({'error':str(exc)},400)
        except Exception as exc:
            self.send_json({'error':type(exc).__name__},500)


def main():
    with connect(): pass
    global SERVER
    httpd=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    SERVER=httpd
    print(f'SPMG AI Command Center v{VERSION} — http://127.0.0.1:{PORT}')
    print('Alleen lokaal. Publicatie en walletacties uitgeschakeld.')
    try: httpd.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: print('\nSPMG Command Center gestopt.')
    finally: httpd.server_close()


if __name__=='__main__': main()