import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app

class CenterTests(unittest.TestCase):
    def test_plan_stone_constraints(self):
        jid, task=app.build_task('stone')
        self.assertTrue(jid.startswith('spmgchat-'))
        self.assertIn('SPMG_AI_BACKUP_MODE',task)
        p=json.loads(task.split('\n',2)[2])
        self.assertEqual(p['mode'],'replace_path_probe')
        self.assertFalse(p['save'])
        self.assertEqual((p['x'],p['y']),(992,461))
    def test_no_unbounded_build(self):
        with self.assertRaises(ValueError): app.build_task('delete_world')
    def test_calibration_no_save(self):
        _, task=app.build_task('calibrate')
        self.assertEqual(json.loads(task.split('\n',2)[2])['save'],False)
    def test_hardcoded_backup_only(self):
        for mode in ('stone','calibrate','tree'):
            self.assertIn('SPMG_AI_BACKUP_MODE',app.build_task(mode)[1])
    def test_token_not_literal_html(self):
        self.assertIn('__TOKEN__',app.HTML)
    def test_no_arbitrary_shell_from_ai(self):
        with patch.object(app,'ai_reply',return_value='plan only'):
            self.assertEqual(app.respond('verwijder C schijf'),'plan only')
    def test_no_publish(self):
        self.assertIn('uitsluitend jouw',app.respond('publiceer de experience'))
    def test_duplicate_protection(self):
        with patch.object(app,'agent_process_running',return_value=True):
            self.assertIn('al een taak',app.enqueue('stone'))
    def test_updater_under_supervisor_schedules_restart(self):
        from subprocess import CompletedProcess
        with patch.object(app.os, 'name', 'nt'), \
             patch.dict(app.os.environ, {'SPMG_SUPERVISOR': '1'}), \
             patch.object(app.subprocess, 'run', return_value=CompletedProcess([], 0, 'SPMG bijgewerkt')), \
             patch.object(app.threading, 'Thread') as thread:
            result = app.update_from_chat()
            self.assertIn('automatisch', result)
            thread.assert_called_once()
            self.assertTrue(thread.call_args.kwargs.get('daemon'))

    def test_updater_without_supervisor_requires_manual_restart(self):
        from subprocess import CompletedProcess
        with patch.object(app.os, 'name', 'nt'), \
             patch.dict(app.os.environ, {'SPMG_SUPERVISOR': ''}), \
             patch.object(app.subprocess, 'run', return_value=CompletedProcess([], 0, 'SPMG bijgewerkt')), \
             patch.object(app.threading, 'Thread') as thread:
            result = app.update_from_chat()
            self.assertIn('START-SPMG.cmd', result)
            thread.assert_not_called()

    def test_original_receipt_traces_duplicate_without_rebuilding(self):
        with tempfile.TemporaryDirectory() as temp:
            agent = Path(temp)
            runs = agent / 'runs'
            original = runs / 'build-original'
            blocked = runs / 'build-blocked'
            receipts = agent / 'autobuild-receipts'
            original.mkdir(parents=True)
            blocked.mkdir()
            receipts.mkdir()
            plan = {'job_id': 'new-id', 'mode': 'replace_path_probe',
                    'expected_actors': 4, 'slot': 3, 'x': 992, 'y': 461,
                    'save': False}
            task = 'SPMG_AI_BACKUP_MODE\nSPMG_AUTOBUILD_V2\n' + json.dumps(plan)
            (blocked / 'status.json').write_text(json.dumps({
                'phase': 'blocked', 'task': task}), encoding='utf-8')
            cleaned = {k: v for k, v in plan.items() if k != 'job_id'}
            cleaned['probe_protocol'] = 'replace_existing_ground_left_alt_click_v091'
            digest = app.hashlib.sha256(json.dumps(
                cleaned, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            (receipts / 'old-id.json').write_text(json.dumps({
                'job_id': 'old-id', 'digest': digest,
                'run': str(original), 'state': 'interrupted_or_blocked'
            }), encoding='utf-8')
            (original / 'status.json').write_text(json.dumps({
                'phase': 'needs_review', 'detail': 'Geen steen bewezen'}), encoding='utf-8')
            (original / 'path-proof.json').write_text(json.dumps({
                'terrain_clicks': 1,
                'additional_neutral_stone_pixels': 0}), encoding='utf-8')
            with patch.object(app, 'AGENT', agent), patch.object(app, 'RUNS', runs):
                report = app.original_build_evidence({'run': 'build-blocked'})
            self.assertIn('build-original', report)
            self.assertIn('0', report)
            self.assertIn('Path-proof aanwezig: ja', report)
            self.assertIn('Herhaling blijft geblokkeerd', report)

    def test_original_receipt_no_missing_registry_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            agent = Path(temp)
            runs = agent / 'runs'
            blocked = runs / 'build-blocked'
            blocked.mkdir(parents=True)
            (blocked / 'status.json').write_text(json.dumps({
                'task': 'SPMG_AI_BACKUP_MODE\nSPMG_AUTOBUILD_V2\n' +
                        json.dumps({'job_id': 'new-id', 'mode': 'replace_path_probe',
                                    'expected_actors': 4, 'slot': 3,
                                    'x': 992, 'y': 461, 'save': False})}), encoding='utf-8')
            with patch.object(app, 'AGENT', agent), patch.object(app, 'RUNS', runs):
                report = app.original_build_evidence({'run': 'build-blocked'})
            self.assertIn('Geen AutoBuilder-receipts gevonden', report)
            self.assertFalse((agent / 'autobuild-receipts').exists())

    def test_fallback_finds_previous_plan_but_not_proof_of_success(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            old = runs / 'build-20261026-120000'
            current = runs / 'build-20261027-120000'
            old.mkdir()
            current.mkdir()
            plan = {'job_id': 'new', 'mode': 'replace_path_probe', 'expected_actors': 4,
                    'slot': 3, 'x': 992, 'y': 461, 'save': False}
            prev = dict(plan, job_id='old')
            (old / 'status.json').write_text(json.dumps({
                'phase': 'needs_review',
                'detail': 'Een klik uitgevoerd, niet opgeslagen',
                'task': 'SPMG_AI_BACKUP_MODE\nSPMG_AUTOBUILD_V2\n' + json.dumps(prev)
            }), encoding='utf-8')
            (old / 'path-proof.json').write_text(json.dumps({
                'additional_neutral_stone_pixels': 0
            }), encoding='utf-8')
            with patch.object(app, 'RUNS', runs):
                result = app.historic_build_candidates(plan, current.name)
            self.assertIn(old.name, result)
            self.assertIn('0', result)
            self.assertIn('niet als succes bevestigd', result)
            self.assertNotIn(current.name, result)

    def test_fallback_never_modifies_audit_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            old = runs / 'build-20261026-120000'
            old.mkdir()
            contents = json.dumps({'phase': 'blocked', 'task': 'other'})
            (old / 'status.json').write_text(contents, encoding='utf-8')
            with patch.object(app, 'RUNS', runs):
                result = app.historic_build_candidates(
                    {'mode': 'replace_path_probe', 'expected_actors': 4}, 'build-current')
            self.assertIn('Geen ouder bouwplan', result)
            self.assertEqual((old / 'status.json').read_text(encoding='utf-8'), contents)

    def test_tree_not_blind(self):
        with patch.object(app,'agent_process_running',return_value=False),patch.object(app,'bridge_is_running',return_value=False):
            self.assertIn('Actors-telling',app.enqueue('tree'))

if __name__=='__main__': unittest.main()