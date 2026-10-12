"""Manual-quit install boundaries without app, process, or filesystem changes."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install_after_quit as worker


class AfterQuitTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.args = SimpleNamespace(candidate_sha256='candidate', check=False)
        self.receipt = {
            'state': 'candidate_verified',
            'candidate_sha256': 'candidate',
            'preinstall_sha256': 'previous',
            'version': 'fixture',
        }
        self.original = [{'pid': 101, 'executable': str(worker.mod.APP / 'Contents/MacOS/ChatGPT')}]
        self.now = 0
        self.receipt_file = Mock()
        self.receipt_file.read_text.return_value = json.dumps(self.receipt)
        stack.enter_context(patch.object(worker.mod, 'RECEIPT', self.receipt_file))
        self.verify = stack.enter_context(patch.object(worker, 'verify_builds'))
        self.processes = stack.enter_context(patch.object(worker.mod, 'codex_instances', return_value=self.original))
        self.install = stack.enter_context(patch.object(worker.mod, 'install'))
        self.record = stack.enter_context(patch.object(worker, 'record'))
        self.lock = stack.enter_context(patch.object(worker, 'exclusive_install'))
        stack.enter_context(patch.object(worker.time, 'monotonic', side_effect=lambda: self.now))
        self.sleep = stack.enter_context(patch.object(worker.time, 'sleep', side_effect=self.advance))
        # These guards turn an accidental process operation into a test failure.
        stack.enter_context(patch.object(worker.subprocess, 'run', side_effect=AssertionError('Must not launch processes')))
        stack.enter_context(patch.object(worker.os, 'kill', side_effect=AssertionError('Must not signal apps')))
        stack.enter_context(patch.object(worker.os, 'killpg', side_effect=AssertionError('Must not signal process groups')))

    def advance(self, seconds):
        self.now += seconds

    def states(self):
        return [call.args[0] for call in self.record.call_args_list]

    def test_running_app_expires_without_replacement(self):
        def wait(seconds):
            self.assertEqual(seconds, 1)
            self.install.assert_not_called()
            self.advance(400)

        self.sleep.side_effect = wait
        worker.main(self.args)

        self.install.assert_not_called()
        self.assertEqual(self.states(), ['waiting_for_user_quit', 'expired_without_changes'])
        self.assertEqual(self.sleep.call_count, 3)
        self.verify.assert_called_once_with(self.receipt, 'previous')

    def test_changed_or_additional_instance_aborts_untouched(self):
        replacements = [
            [{'pid': 202, 'executable': self.original[0]['executable']}],
            [{'pid': 101, 'executable': '/fixture/Other.app/Contents/MacOS/ChatGPT'}],
            self.original + [{'pid': 202, 'executable': self.original[0]['executable']}],
        ]
        for observed in replacements:
            with self.subTest(observed=observed):
                self.processes.side_effect = [self.original, self.original, observed]
                with self.assertRaisesRegex(ValueError, 'instance changed'):
                    worker.main(self.args)
                self.install.assert_not_called()
        self.assertNotIn('installing', self.states())

    def test_expected_manual_quit_installs_once_after_final_absence_check(self):
        snapshots = iter([self.original, self.original, self.original, [], []])
        observations = []

        def observe():
            self.install.assert_not_called()
            observed = next(snapshots)
            observations.append(observed)
            return observed

        def install():
            self.assertEqual(observations[-2:], [[], []])
            self.assertEqual(self.verify.call_count, 2)

        self.processes.side_effect = observe
        self.install.side_effect = install
        worker.main(self.args)

        self.install.assert_called_once_with()
        self.assertEqual(self.processes.call_count, 5)
        self.assertEqual(self.sleep.call_count, 2)
        self.assertEqual(self.states(), ['waiting_for_user_quit', 'installing', 'installed_awaiting_reopen'])
        final = self.record.call_args.kwargs
        self.assertFalse(final['live_ui_verified'])
        self.assertFalse(final['ordinary_chat_verified'])
        self.lock.assert_called_once_with()
        self.lock.return_value.__exit__.assert_called_once()

    def test_quit_first_observed_at_deadline_expires_untouched(self):
        self.processes.side_effect = [self.original, self.original, [], []]
        self.sleep.side_effect = lambda seconds: self.advance(1200)

        worker.main(self.args)

        self.install.assert_not_called()
        self.assertEqual(self.states(), ['waiting_for_user_quit', 'expired_without_changes'])

    def test_reopened_app_before_replacement_aborts_untouched(self):
        reopened = [{'pid': 202, 'executable': self.original[0]['executable']}]
        self.processes.side_effect = [self.original, [], reopened]

        with self.assertRaisesRegex(ValueError, 'reopened before replacement'):
            worker.main(self.args)

        self.install.assert_not_called()
        self.assertNotIn('installing', self.states())

    def test_candidate_changed_while_waiting_aborts_untouched(self):
        changed = {**self.receipt, 'candidate_sha256': 'different'}
        self.receipt_file.read_text.side_effect = [json.dumps(self.receipt), json.dumps(changed)]
        self.processes.side_effect = [self.original, []]

        with self.assertRaisesRegex(ValueError, 'Verified candidate changed'):
            worker.main(self.args)

        self.install.assert_not_called()
        self.verify.assert_called_once_with(self.receipt, 'previous')
        self.assertNotIn('installing', self.states())

    def test_build_revalidation_failure_after_quit_aborts_untouched(self):
        self.processes.side_effect = [self.original, []]
        self.verify.side_effect = [None, ValueError('Installed app changed since preparation')]

        with self.assertRaisesRegex(ValueError, 'Installed app changed'):
            worker.main(self.args)

        self.install.assert_not_called()
        self.assertNotIn('installing', self.states())

    def test_initial_instance_must_be_exactly_the_installed_app(self):
        for observed in [[], self.original * 2, [{'pid': 101, 'executable': '/fixture/Other.app/Contents/MacOS/ChatGPT'}]]:
            with self.subTest(observed=observed):
                self.processes.return_value = observed
                with self.assertRaisesRegex(ValueError, 'exactly the current installed Codex instance'):
                    worker.main(self.args)
                self.install.assert_not_called()
                self.lock.assert_not_called()
                self.record.assert_not_called()

    def test_check_validates_without_waiting_or_installing(self):
        self.args.check = True
        output = io.StringIO()

        with patch('sys.stdout', output):
            worker.main(self.args)

        self.assertEqual(json.loads(output.getvalue()), {
            'ready': True, 'version': 'fixture', 'candidate_sha256': 'candidate', 'running_pid': 101,
        })
        self.install.assert_not_called()
        self.lock.assert_not_called()
        self.record.assert_not_called()
        self.sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
