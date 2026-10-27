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

    def test_tree_not_blind(self):
        with patch.object(app,'agent_process_running',return_value=False),patch.object(app,'bridge_is_running',return_value=False):
            self.assertIn('Actors-telling',app.enqueue('tree'))

if __name__=='__main__': unittest.main()