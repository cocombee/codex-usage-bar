"""Launch/update decisions must preserve active work and unknown-version guards."""
from pathlib import Path
from contextlib import nullcontext
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import windows_manager as manager
import windows_persistence as persistence
from windows_versions import adapter_for


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.receipt = {'package_version': '26.1002.7124.0', 'engine_fingerprint': 'checked-engine'}

    def test_identical_engine_and_source_reuse_installed_build(self):
        self.assertEqual(manager.refresh_needed(self.receipt, '26.1002.7124.0', 'checked-engine'), 'ready')

    def test_code_change_requires_new_verified_build(self):
        self.assertEqual(manager.refresh_needed(self.receipt, '26.1002.7124.0', 'updated-engine'), 'rebuild')

    def test_supported_package_update_requires_new_build(self):
        with patch.dict(manager.ADAPTERS, {'99.0': 'test-only-adapter'}):
            self.assertEqual(manager.refresh_needed(self.receipt, '99.0', 'checked-engine'), 'rebuild')

    def test_unknown_package_cannot_become_a_rebuild(self):
        self.assertEqual(manager.refresh_needed(self.receipt, '99.0', 'updated-engine'), 'unsupported-update')
        with self.assertRaisesRegex(ValueError, 'Uninspected'):
            adapter_for('99.0')

    def test_running_store_copy_waits_without_stopping_it(self):
        self.assertEqual(manager.next_action('other', True), 'wait')
        self.assertEqual(manager.next_action('other', False), 'observe')

    def test_normal_quit_is_not_an_endless_relaunch_loop(self):
        self.assertEqual(manager.next_action('closed', False), 'observe')
        self.assertEqual(manager.next_action('closed', True), 'launch')

    def test_mod_request_activates_its_existing_instance(self):
        self.assertEqual(manager.next_action('mod', True), 'activate')
        self.assertEqual(manager.next_action('mod', False), 'observe')

    def test_pending_update_waits_for_normal_quit_without_consuming_launch_request(self):
        self.assertEqual(manager.next_action('mod', True, update_pending=True), 'wait')
        self.assertEqual(manager.next_action('other', True, update_pending=True), 'wait')
        self.assertEqual(manager.next_action('closed', True), 'launch')

    def test_mixed_or_unreadable_processes_cannot_allow_duplicate_launch(self):
        exe = str(Path('installed/ChatGPT.exe').resolve())
        self.assertEqual(manager.process_kind([], exe), 'closed')
        self.assertEqual(manager.process_kind([{'ExecutablePath': exe}, {'ExecutablePath': exe}], exe), 'mod')
        self.assertEqual(manager.process_kind([{'ExecutablePath': exe}, {'ExecutablePath': None}], exe), 'other')
        self.assertEqual(manager.process_kind([{'ExecutablePath': exe}, {'ExecutablePath': 'other/ChatGPT.exe'}], exe), 'other')

    def test_store_reopen_during_verification_keeps_request_for_normal_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'launch-request.json').write_text('{}')
            states, ticks, launches = [], [0], [0]
            def read(path):
                return ({'id': 'one-request'} if path.name == 'launch-request.json' else
                        {'current': 'candidate'} if path.name == 'current.json' else
                        {'package_version': '26.1007.9446.0', 'engine_fingerprint': 'checked-engine'})
            def launch():
                launches[0] += 1
                if launches[0] == 1:
                    raise manager.setup.DesktopInstanceRunning('Store reopened during verification')
            def clock():
                ticks[0] += 1
                return ticks[0]
            def sleep(_):
                if launches[0] >= 2:
                    (root / 'manager-stop.request').write_text('stop')
                self.assertLess(ticks[0], 30, 'Manager lost the pending launch request')
            with patch.object(manager.setup, 'exclusive', return_value=nullcontext()), \
                 patch.object(manager.setup, 'validate_install_root', return_value=root), \
                 patch.object(persistence, 'engine_fingerprint', return_value='checked-engine'), \
                 patch.object(manager.setup, 'read_json', side_effect=read), \
                 patch.object(manager.setup, 'current_build', return_value=root / 'candidate'), \
                 patch.object(manager.setup, 'app_processes', return_value=[]), \
                 patch.object(manager.setup, 'registered_package', return_value={'Version': '26.1007.9446.0'}), \
                 patch.object(manager.setup, 'launch', side_effect=launch), \
                 patch.object(manager.setup, 'build') as build, \
                 patch.object(manager.setup, 'atomic_json', side_effect=lambda path,value: states.append(value['state'])), \
                 patch.object(manager.time, 'monotonic', side_effect=clock), \
                 patch.object(manager.time, 'sleep', side_effect=sleep):
                manager.monitor(root)
            self.assertEqual(launches[0], 2)
            build.assert_not_called()
            self.assertEqual(states, ['launching', 'waiting-for-quit', 'launching', 'running', 'stopped'])

    def test_failed_startup_does_not_rebuild_rolled_back_candidate_every_minute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'launch-request.json').write_text('{}')
            receipt = {'package_version': '26.1007.2314.0', 'engine_fingerprint': 'checked-engine'}
            states, ticks = [], [0]
            def read(path):
                return ({'id': 'one-request'} if path.name == 'launch-request.json' else
                        {'current': 'candidate'} if path.name == 'current.json' else dict(receipt))
            def fail():
                receipt['package_version'] = '26.1002.7124.0'
                raise ValueError('Candidate exited during startup: 1')
            def clock():
                ticks[0] += 61
                return ticks[0]
            def sleep(_):
                if ticks[0] >= 300:
                    (root / 'manager-stop.request').write_text('stop')
            with patch.object(manager.setup, 'exclusive', return_value=nullcontext()), \
                 patch.object(manager.setup, 'validate_install_root', return_value=root), \
                 patch.object(persistence, 'engine_fingerprint', return_value='checked-engine'), \
                 patch.object(manager.setup, 'read_json', side_effect=read), \
                 patch.object(manager.setup, 'current_build', return_value=root / 'candidate'), \
                 patch.object(manager.setup, 'app_processes', return_value=[]), \
                 patch.object(manager.setup, 'registered_package', return_value={'Version':'26.1007.2314.0'}), \
                 patch.object(manager.setup, 'launch', side_effect=fail) as launch, \
                 patch.object(manager.setup, 'build') as build, \
                 patch.object(manager.setup, 'atomic_json', side_effect=lambda path,value: states.append(value['state'])), \
                 patch.object(manager.time, 'monotonic', side_effect=clock), \
                 patch.object(manager.time, 'sleep', side_effect=sleep):
                manager.monitor(root)
            launch.assert_called_once()
            build.assert_not_called()
            self.assertEqual(states, ['launching', 'failed', 'stopped'])


if __name__ == '__main__':
    unittest.main()
