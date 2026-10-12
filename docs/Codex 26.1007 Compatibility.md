# Codex 26.1007 Compatibility

Reviewed 12 October 2026.

## Changes

- Pin the macOS adapter to desktop **26.1007.30912** and its inspected source archive.
- Update four renderer chunk paths, unique integration anchors and minified bindings. The seven shared UI/metrics modules are unchanged.
- Remove the new vendor-only notification entitlement during local signing; retain the framework-library entitlement handling and existing integrity checks.
- Add a finite helper for installing a verified candidate after a manual quit, preserving the previous app for rollback.
- Update preview fixtures for current macOS bindings while retaining the Windows adapter and fixture bindings.

## Known limitation

The app archive is covered by the vendor signature. This modification replaces that signature with local ad-hoc signing. The current native desktop tool bridge verifies OpenAI signing identities across its process chain, including the outer app. Keeping the nested CLI vendor-signed does not satisfy that requirement.

Native desktop tools, including chat discovery and chat-to-chat messaging, therefore do not authorize under the modified app. Ordinary typing and replies continued after the observed installation. This is a required installation tradeoff, not a repaired native-tool integration. No peer checks, integrity fuses or vendor identities are bypassed.

Supported [plugin extensions](https://developers.openai.com/plugins/build/extensions) provide other UI surfaces; no documented extension was found for this exact row above the composer and its native context/speed hooks.

## Verification and remaining acceptance

- Source, ASAR contents, native digest, module syntax and unchanged integrity fuses passed the existing builder checks.
- Local deep/strict signatures and scoped entitlements passed.
- The installed app matches the verified candidate, and its running executable/framework match that bundle.
- The original vendor app remains in the rollback slot.
- The user confirmed the bar is visible, and this chat continued afterward.
- A further normal quit/reopen of this installed candidate, live metric accuracy and native diff interaction remain pending. The receipt remains `installed_pending_live_check`; no full acceptance is inferred.

Automated source, signing, installer and fixture tests complement these observations; they do not replace live acceptance.

## Recovery

Keep the receipt and retained previous app until acceptance. If necessary, quit Codex normally and run `python3 -B scripts/mod.py rollback` from an independent Terminal, then reopen the original app. The rollback verifies the recorded bundles before replacing anything.

Older-version build slots and receipts must be reviewed and preserved before preparing a new version. Do not relabel an older receipt as accepted or erase an unverified recovery copy. Local recovery archives, app bundles, operational receipts and logs are excluded from Git.
