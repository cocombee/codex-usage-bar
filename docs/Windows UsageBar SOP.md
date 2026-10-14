# Windows UsageBar install, restart and recovery SOP

Use this procedure whenever a Store update hides the bar or a mod build is replaced. A verified build, installed files, a healthy process and a working rendered bar are separate results. Do not report installation as fully accepted until the last step succeeds.

## 1. Identify the app and preserve recovery

Read `AGENTS.md` and `Startup And Signing Prevention.md`. Check the registered Store package, `%LOCALAPPDATA%\OpenAI\CodexUsage\current.json`, and `manager-status.json`. Inspect the running executable path:

```powershell
Get-AppxPackage -Name OpenAI.Codex | Select-Object Version,InstallLocation
Get-CimInstance Win32_Process -Filter "Name = 'ChatGPT.exe'" |
  Select-Object ProcessId,ParentProcessId,ExecutablePath
Get-Content "$env:LOCALAPPDATA\OpenAI\CodexUsage\current.json"
Get-Content "$env:LOCALAPPDATA\OpenAI\CodexUsage\manager-status.json"
```

`WindowsApps\OpenAI.Codex_...\app\ChatGPT.exe` is the standard Store app. The mod runs from `OpenAI\CodexUsage\builds\<selected-build>\app\ChatGPT.exe`. Opening the standard Codex shortcut does not activate the mod. Keep the previous verified build and all account/profile data.

## 2. Validate and build the exact source

Use a clean copy of the intended Git commit. Run the shared JavaScript, Windows deployment, manager, native launcher, shared-adapter and signing-policy tests described in `CONTRIBUTING.md`. Run the rendered fixture against the new candidate.

```powershell
python -B scripts/windows_setup.py --check
python -B scripts/windows_setup.py --build
```

A new Store version requires an independently inspected adapter: exact archive/executable/runtime hashes, renderer version, unique anchors and React/usage/context/native-control bindings. Never bypass the registry or hashes. Keep ASAR validation and runtime fuses enabled. Record the Git commit and local build receipt privately; do not commit vendor files, profiles, logs or credentials.

## 3. Install without interrupting work

Before upgrading the native launcher, choose **Exit launcher** from the UsageBar tray menu, or run `CodexUsage.exe --exit` from its installation directory. Confirm the tray process exits normally. The Codex desktop window can remain open. Windows locks a running launcher executable; leaving the tray process running can make an otherwise verified installation fail when replacing it.

```powershell
$usageBuild = (Get-Content -Raw .local-windows/latest.json | ConvertFrom-Json).build
python -B scripts/windows_setup.py --install "$usageBuild"
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; inspect the reported error.' }
python -B scripts/windows_setup.py --enable-persistence
if ($LASTEXITCODE -ne 0) { throw 'Persistent launcher installation failed.' }
```

Confirm `current.json` selects the verified candidate, retains a previous build, and the native launcher's self-test passes. An `installed-awaiting-launch` receipt does not prove the bar is running.

If installation was interrupted after copying a candidate, retain that unselected attempt for diagnosis. Verify the active pointer before preserving the unselected directory under a distinct name, then rerun installation from the verified source build. Never move a selected or running build, select a partial copy by hand, or delete the previous recovery build.

## 4. Switch to the mod in this order

1. Open **Codex Usage (local mod)** from Start, or run the command below. This requests the mod and leaves an existing Store app running.
2. Quit all standard Codex windows normally. Leave the UsageBar tray launcher running.
3. Let UsageBar verify and open the selected build. **Do not reopen the standard Codex shortcut while it is verifying.** Watch `manager-status.json` for `running`, or inspect the reported error. Repeatedly opening the standard shortcut can win the launch race and keep the bar absent.

```powershell
Start-Process -FilePath "$env:LOCALAPPDATA\OpenAI\CodexUsage\CodexUsage.exe" -WindowStyle Hidden
```

The manager never forces an app to close. If the Store app reopens during verification, the manager must retain the launch request and return to `waiting-for-quit`, rather than classify the candidate as failed. Quit the Store app normally again and let the mod open. A real startup crash remains a failure requiring diagnosis.

## 5. Verify success before recording acceptance

Check that the running executable matches the selected build and `current.json` records `process-healthy`. Then inspect the actual window: the bar must appear above the composer; Weekly must match the native account usage; Context and estimated token speed must behave correctly; Files changed must open the native diff. Normally quit the mod and reopen it using **Codex Usage (local mod)**. Verify the same installed build and bar again.

Only after all observations pass:

```powershell
python -B "$env:LOCALAPPDATA\OpenAI\CodexUsage\windows_setup.py" --accept --confirm-rendered-ui --confirm-live-metrics --confirm-diff-interaction --confirm-quit-reopen
```

Record the successful Git commit, Store/renderer versions, build identity, automated results, exact-process verification and both normal-launch observations in the local receipt. Add a sanitized acceptance note to the repository only after the observations exist. Never infer UI success from fixture tests, a tray icon or a process remaining alive.

## Recovery by reported state

| State or symptom | Next action |
| --- | --- |
| Bar absent; executable is under WindowsApps | Follow step 4; use the mod shortcut. |
| `waiting-for-quit` | Quit the standard app normally; leave the mod tray launcher running. |
| `launching` or `building-update` | Read the status and build receipt; allow verification to finish. Do not open a competing instance. |
| `unsupported-update` | Inspect the exact new package and add a tested adapter; retain the previous verified mod. |
| `failed` after a competing Store launch | Open **Codex Usage (local mod)** again to submit a fresh request, then follow step 4. Updated managers retain this request automatically. |
| `launch-failed`, `needs-attention` or a real crash | Inspect the exact executable, current receipt and fresh crash evidence. Do not loop candidate launches or alter live files. |
| No tray launcher | Run the native executable in step 4; inspect `launcher-error.log` if it exits. |

To select the retained build, first quit Codex normally, then run:

```powershell
python -B "$env:LOCALAPPDATA\OpenAI\CodexUsage\windows_setup.py" --rollback
```

Launch and verify that build through the same mod shortcut. Do not delete user data, reset credentials, disable security checks, or treat reopening the original Store app as successful mod recovery.
