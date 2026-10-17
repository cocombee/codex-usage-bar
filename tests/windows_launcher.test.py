"""Exercise the compiled native launcher's quiet diagnostics and shell identity."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import windows_setup as setup


@unittest.skipUnless(os.name == 'nt', 'Native Windows launcher')
class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.exe = cls.root / 'CodexUsage.exe'
        compiler = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu',
            '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Runtime.Serialization.dll',
            '/out:' + str(cls.exe), str(setup.ROOT / 'src/windows-launcher.cs')], check=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_valid_configuration_passes_without_launching_a_desktop(self):
        script = self.root / 'engine/scripts/windows_manager.py'
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('raise RuntimeError("Must not execute")', encoding='utf-8')
        (self.root / 'launcher-config.json').write_text(json.dumps({'python': sys.executable, 'engine': 'engine'}), encoding='utf-8')
        result = subprocess.run([str(self.exe), '--self-test'], timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads((self.root / 'launcher-self-test.json').read_text()), {'app_id': 'Cocombee.CodexUsage', 'passed': True})

    def test_bad_command_fails_without_a_blocking_dialog(self):
        result = subprocess.run([str(self.exe), '--invalid'], timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown launcher arguments', (self.root / 'launcher-error.log').read_text())

    def test_shortcut_gets_the_same_identity_as_the_mod_window(self):
        link = self.root / 'Codex Usage.lnk'
        setup.powershell('$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]); $s.TargetPath=$args[1]; $s.Save()', link, self.exe)
        subprocess.run([str(self.exe), '--stamp-shortcut', str(link)], check=True, timeout=15)
        value = setup.powershell('''
$shell=New-Object -ComObject Shell.Application
$item=$shell.Namespace($args[0]).ParseName($args[1])
$item.ExtendedProperty('System.AppUserModel.ID') | ConvertTo-Json -Compress
''', self.root, link.name)
        self.assertEqual(value, 'Cocombee.CodexUsage')


if __name__ == '__main__':
    unittest.main()
