"""Regression checks for the approved local-signing scope."""
from pathlib import Path
import sys
import plistlib
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from signing import local_entitlements,assert_local_entitlements,RESTRICTED_VENDOR_KEYS,LIBRARY_LOADING_KEY
import signing

class SigningPolicyTests(unittest.TestCase):
    def test_vendor_claims_removed_runtime_and_supported_caps_preserved(self):
        value={key:'synthetic-vendor-claim' for key in RESTRICTED_VENDOR_KEYS}
        value.update({'com.apple.security.cs.allow-jit':True,'com.apple.security.cs.allow-unsigned-executable-memory':True,'com.apple.security.network.client':True})
        result=local_entitlements(value)
        self.assertFalse(set(result)&RESTRICTED_VENDOR_KEYS)
        self.assertTrue(all(result[key] is True for key in result))
        self.assertIn('com.apple.application-identifier',value)
    def test_loading_exception_requires_explicit_verified_host(self):
        with self.assertRaises(ValueError):local_entitlements({},allow_library_loading=True)
        self.assertEqual(local_entitlements({}),{})
        self.assertEqual(local_entitlements({},allow_library_loading=True,verified_executable_host=True),{LIBRARY_LOADING_KEY:True})
    def test_current_notification_vendor_claim_removed(self):
        self.assertEqual(local_entitlements({'com.apple.developer.usernotifications.communication':True,
                                            'com.apple.security.cs.allow-jit':True}),
                         {'com.apple.security.cs.allow-jit':True})
    def test_unknown_vendor_claim_fails_closed(self):
        with self.assertRaises(ValueError):assert_local_entitlements({'com.apple.developer.unexpected':True})
    def test_boolean_scope_cannot_be_accidentally_enabled(self):
        with self.assertRaises(ValueError):local_entitlements({},allow_library_loading='false')

    def test_framework_seal_has_no_process_entitlements_and_hosts_keep_runtime_caps(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory).resolve()/'ChatGPT.app';app.mkdir()
            framework=app/signing.FRAMEWORK
            binary=framework/'Versions/Current/Codex Framework'
            binary.parent.mkdir(parents=True);binary.touch()
            helper=framework/'Versions/Current/Helpers/Codex (Renderer).app'
            helper.mkdir(parents=True)
            original={'com.apple.security.cs.allow-jit':True,
                      'com.apple.security.cs.allow-unsigned-executable-memory':True,
                      'com.apple.developer.team-identifier':'synthetic-vendor'}
            observed=[]
            def capture(argv,**kwargs):
                observed.append((argv[-1],plistlib.loads(Path(argv[argv.index('--entitlements')+1]).read_bytes())))
                self.assertNotIn('--force-library-entitlements',argv)
                self.assertEqual(argv[argv.index('--options')+1],'runtime')
            with patch.object(signing,'targets',return_value=[helper,framework,app]), \
                 patch.object(signing,'metadata',return_value={'entitlements':original}), \
                 patch.object(signing,'executable',side_effect=lambda target:target/'executable'), \
                 patch.object(signing,'verified_loader',return_value={}), \
                 patch.object(signing.subprocess,'run',side_effect=capture), \
                 patch.object(signing,'verify',side_effect=lambda app,expected:expected):
                expected=signing.sign(app)
            self.assertEqual([row[0] for row in observed],[str(helper),str(framework),str(app)])
            self.assertEqual(expected[str(signing.FRAMEWORK)],{})
            for target in [helper,app]:
                key=str(target.relative_to(app)) if target!=app else '.'
                self.assertEqual(expected[key],{
                    'com.apple.security.cs.allow-jit':True,
                    'com.apple.security.cs.allow-unsigned-executable-memory':True,
                    LIBRARY_LOADING_KEY:True})
            self.assertEqual([row[1] for row in observed],list(expected.values()))

unittest.main(verbosity=2)
