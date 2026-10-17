# Windows Preview

## Status and installation

The experimental local x64 Windows port supports inspected Store packages `OpenAI.Codex` **26.1002.7124.0**, **26.1007.2314.0**, and **26.1007.9446.0**, with renderer versions **26.1002.52244**, **26.1007.21434**, and **26.1007.71326**, respectively. Requires Python 3.10+, one of those exact current-user Store packages and approximately 6 GB free space for build and installation. Unknown versions fail before copying.

From the repository in PowerShell:

```powershell
python scripts/windows_setup.py --check
python scripts/windows_setup.py --build
$build = (Get-Content -Raw .local-windows/latest.json | ConvertFrom-Json).build
python scripts/windows_setup.py --install "$build"
python scripts/windows_setup.py --enable-persistence
```

The separate copy installs under `%LOCALAPPDATA%\OpenAI\CodexUsage`, with a **Codex Usage (local mod)** Start menu shortcut. Quit all ChatGPT/Codex desktop windows normally, then open it. Installation does not stop the running app. The shortcut uses the Python executable that performed installation; keep it available.

Persistence installs a stable `CodexUsage.exe` launcher with the GPT icon, an immutable local engine snapshot and a per-user Startup shortcut. Pin **Codex Usage (local mod)** from the Start menu and replace the Store taskbar pin. The pin targets the stable launcher rather than a build-specific executable. The launcher must start through Explorer or the Start menu so it survives Codex quitting.

The independent tray manager checks Store updates every minute. Supported updates are copied and verified after a normal quit; unknown versions retain the last verified mod and report that a tested adapter is needed. It respects manual quits, and opening the pinned shortcut requests another launch. It does not download executable Git code. Exit the tray launcher and remove its Startup shortcut to disable login startup. `CodexUsage.exe --exit` closes only the launcher for maintenance.

The current Owl runtime lacks `app.setAppDetails`; Windows adapters guard that optional API. Window creation applies the verified GPT icon explicitly so the unpackaged app does not display a generic icon. Both the shortcuts and windows use `Cocombee.CodexUsage`. Startup failures retain their diagnostic and do not repeatedly rebuild the failed candidate until a new request. Local diagnostics are `manager-status.json`, `launcher-error.log`, and `current.json` in the installation root.

If the Store app reopens during full verification, the manager retains the pending launch and waits for a normal quit. It does not reject the candidate or launch a second desktop instance.

The normal launcher uses the usual profile without copying credentials or history. It verifies the whole installed tree, refuses concurrent desktop instances, and observes the exact launched executable for 12 seconds. Process health does not establish UI correctness. An unpackaged copy may not support every Store integration; sandbox setup, protocol activation, updating and account behavior need native acceptance.

The usage row also appears on local new-chat screens, above the native project/computer controls and Goal rail. Shared layout code preserves their width and reserves an 8 CSS px gap.

### Goal fails in one chat but works in another

When multiple desktop instances are open during development, a chat may be a follower of the window that started it. The pinned host's Goal setter requires the owner window and rejects follower requests before sending `thread/goal/set`; the UI hides that explanation behind "Failed to set goal". Set the Goal in the original owner window. A chat started in the mod can set its Goal there. Do not remove the ownership check. The normal launcher prevents this concurrent-instance setup.

For launcher diagnostics:

```powershell
python "$env:LOCALAPPDATA\OpenAI\CodexUsage\windows_setup.py" --launch
```

## Implementation and packaging

- `scripts/windows_versions.py` selects a version-specific adapter with exact source pins and renderer bindings. Each supported version has inspected hooks; compatibility is not inferred from its version number.
- `src/windows-launcher.cs`, `scripts/windows_manager.py`, and `scripts/windows_persistence.py` provide taskbar identity, GPT icons, per-user startup, and the supported-update manager.
- `scripts/windows_integrity.py` parses the launcher's PE resource directory with bounds/uniqueness checks and synchronizes its `INTEGRITY` / `ELECTRONASAR` header hash. The runtime DLL's integrity fuses remain enabled.
- `scripts/windows_setup.py` implements registered-package discovery, Authenticode checks, build verification, per-user deployment, locking, launch checks, rollback and acceptance receipts.

The supported source has valid OpenAI Authenticode signatures. Modifying the launcher invalidates its signature, so the candidate removes the stale certificate table and is explicitly an **unsigned local mod**. The runtime DLL and other copied files remain byte-identical. Only the launcher and ASAR change. The original Store app, WindowsApps ACLs, package registration, certificate trust and Windows security policy are unchanged.

This is an unpackaged local copy, not a signed MSIX update or redistributable Windows release. If Windows policy blocks unsigned local software, stop and use the Store app. Never disable the policy. Do not publish copied vendor binaries, extracted assets, profiles or diagnostic logs. `.local-windows/` is excluded from Git. Public distribution would require a separately authorized packaging/licensing/signing design.

References: [official Windows deployment](https://learn.chatgpt.com/docs/enterprise/windows-deployment), [Electron ASAR integrity](https://www.electronjs.org/docs/latest/tutorial/asar-integrity), [MSIX signing](https://learn.microsoft.com/en-us/windows/msix/package/sign-app-package-using-signtool), [MSIX integrity](https://learn.microsoft.com/en-us/windows/msix/desktop/tamper-protection).

## Recovery

Unique build directories retain prior copies and each build's matching installer scripts. The installed `windows_setup.py` is a stable dispatcher that selects the scripts for the verified current build. Installation switches `current.json` only after fully verifying the new copy. An OS byte-range lock rejects overlapping operations and releases on process death. An interrupted copy is never selected for launch. There is no recursive removal of existing installations.

If a candidate exits during startup, the previous build is verified and selected when available. The failed candidate is not repeatedly relaunched. A failed first launch is marked failed; the original Store app remains available. If startup verification is interrupted while the process is alive, the receipt records `needs-attention`; no files are replaced underneath it.

To select the previous mod after quitting normally:

```powershell
python "$env:LOCALAPPDATA\OpenAI\CodexUsage\windows_setup.py" --rollback
```

After interruption, inspect `%LOCALAPPDATA%\OpenAI\CodexUsage\current.json`. With no desktop instance running, rerun `--launch` or select `--rollback`. Never delete profile data as recovery. Updated Store builds require fresh inspection and new pins.

## Development checks

```powershell
node --test tests/*.test.mjs
python -B tests/windows.test.py
python -B tests/signing.test.py
$env:CODEX_USAGE_NODE_MODULES = 'C:\path\to\node_modules'
$env:CODEX_USAGE_PYTHON = 'C:\path\to\python.exe'
# Optional CODEX_USAGE_BROWSER selects a different Chrome executable.
node tests/render.mjs
```

The fixture uses the Windows build's React, fictional metrics and a loopback-only server. It never attaches to a running app. Node.js 20+, Playwright and Chrome are required for that test.

Recorded on Windows 11 build 26200:

- Source package metadata, exact file pins, original Authenticode signatures, native header equality and enabled fuses passed.
- The candidate changed exactly 11 intended archive entries; other archive entries and copied files were verified. Four patched host modules passed JavaScript syntax checks.
- 12 shared JavaScript tests, 15 Windows PE/locking/recovery tests and 4 signing-policy tests passed.
- 35 font/width and 60 zoom layouts passed, including fixture diff click/keyboard behavior.
- An isolated candidate process remained alive at its exact path after 18 seconds. Later native UI checks used a separate browser profile and the existing local account state without copying credentials.
- The actual chat row rendered with Weekly at 82% remaining, matching the core account quota, and a current Context value. Native Files changed was visible. Goal creation succeeded in a chat owned by the mod; a follower chat correctly failed the host's ownership check.
- The updated installed build rendered the row on the actual new-chat screen, aligned above the project/computer controls with a visible 8 px gap. Unknown Context and token speed remained `—`.
- The mod was quit normally and reopened during testing. Two launches through the normal shared-profile launcher, live token speed, native diff interaction and full native scaling acceptance remain pending.
- The macOS integrity tests were attempted on Windows but could not create their framework symlink fixtures because this account lacks Windows symlink privileges. They did not pass on Windows; macOS installation/process-group/atomic-exchange tests require a Mac.

## Native acceptance still required

For Store `26.1007.9446.0`, source signatures and pins, native digest/fuses, all 12 intended archive changes, and the installed engine were verified. The actual shared-profile chat rendered Weekly, token speed, and Context above Goal. The stable taskbar shortcut points to `CodexUsage.exe` and uses the GPT icon. Automated checks cover 22 Windows deployment cases, 11 manager cases, three compiled launcher checks, three packaged-renderer contracts, 19 shared JavaScript cases, and six signing-policy cases. A further normal quit/reopen of the exact installed candidate, live token-speed accuracy, native diff interaction, and full display scaling remain pending; the full acceptance receipt has not been marked accepted.

1. Compare the Weekly countdown with the native usage panel; the remaining percentage and core bucket have been checked.
2. Compare Context with the current chat and check token speed during a real response, across chats and hosts. Confirm speed clears to `—` on completion, interruption or idle status, and that a new turn waits for a fresh sample. Windows uses the same lifecycle observer as macOS.
3. Open the actual Files changed diff; check plans, Goal and other native controls.
4. Check narrow widths, font changes and Windows display scaling.
5. Normally quit and reopen the exact installed **Codex Usage (local mod)**. Confirm account and row behavior. Two normal healthy launches must be recorded.

Only after those observations, explicitly record acceptance:

```powershell
python "$env:LOCALAPPDATA\OpenAI\CodexUsage\windows_setup.py" --accept --confirm-rendered-ui --confirm-live-metrics --confirm-diff-interaction --confirm-quit-reopen
```

Acceptance never launches the app, checks that the exact installed build is running, and verifies its files. Keep native acceptance pending in contributions until the observations have actually been made.
