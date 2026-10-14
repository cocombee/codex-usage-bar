"""Per-user update/launch manager. Never stops a desktop instance."""
import argparse
import json
import subprocess
import time
from pathlib import Path

import windows_setup as setup
from windows_versions import ADAPTERS


def refresh_needed(receipt, source_version, engine_fingerprint):
    if source_version not in ADAPTERS:
        return 'unsupported-update'
    if receipt['package_version'] != source_version or receipt.get('engine_fingerprint') != engine_fingerprint:
        return 'rebuild'
    return 'ready'


def process_kind(processes, installed_executable):
    if not processes:
        return 'closed'
    paths = [p.get('ExecutablePath') for p in processes]
    if all(path and setup.normal_path(path) == setup.normal_path(installed_executable) for path in paths):
        return 'mod'
    return 'other'


def next_action(kind, requested, update_pending=False):
    if update_pending and kind != 'closed':
        return 'wait'
    if kind == 'other':
        return 'wait' if requested else 'observe'
    if kind == 'mod':
        return 'activate' if requested else 'observe'
    return 'launch' if requested else 'observe'


def monitor(root):
    import windows_persistence as persistence
    root = setup.validate_install_root(root)
    status_path = root / 'manager-status.json'
    last_state = None
    def status(state, message, **details):
        nonlocal last_state
        value = (state, message, json.dumps(details, sort_keys=True))
        if value != last_state:
            setup.atomic_json(status_path, {'state': state, 'message': message, 'at': setup.now(), **details})
            last_state = value
    with setup.exclusive(root / 'manager-lock'):
        fingerprint = persistence.engine_fingerprint(setup.ROOT)
        requested = False
        last_request = None
        checked_at = -60
        blocked_version = None
        rebuild_pending = False
        failed_request = None
        failed_update = None
        while not (root / 'manager-stop.request').exists():
            action = None
            try:
                request_path = root / 'launch-request.json'
                if request_path.exists():
                    request = setup.read_json(request_path).get('id')
                    if request and request != last_request:
                        last_request = request
                        requested = True
                        failed_request = None
                        failed_update = None
                        checked_at = -60
                pointer = setup.read_json(root / 'current.json')
                build = setup.current_build(root, pointer['current'])
                receipt = setup.read_json(build / 'receipt.json')
                exe = build / 'app/ChatGPT.exe'
                processes = setup.app_processes()
                kind = process_kind(processes, exe)
                if time.monotonic() - checked_at >= 60:
                    package = setup.registered_package()
                    decision = refresh_needed(receipt, package['Version'], fingerprint)
                    blocked_version = package['Version'] if decision == 'unsupported-update' else None
                    rebuild_pending = decision == 'rebuild' and failed_update != (package['Version'], fingerprint)
                    if rebuild_pending:
                        requested = True
                        failed_request = None
                    checked_at = time.monotonic()
                if blocked_version:
                    status('unsupported-update', 'Codex ' + blocked_version + ' needs a tested adapter. Keeping the last verified mod.', version=blocked_version)
                if rebuild_pending and kind == 'closed':
                    status('building-update', 'Building and verifying the supported Codex update.')
                    candidate = setup.build()
                    setup.install(candidate)
                    rebuild_pending = False
                    # A refreshed engine will be selected on the next native
                    # launcher start. This manager never downloads executable code.
                    continue
                action = next_action(kind, requested and (failed_request is None or last_request != failed_request), rebuild_pending)
                if action == 'wait':
                    if not blocked_version:
                        status('waiting-for-quit', 'Quit Codex normally; the verified mod will open afterward.')
                elif action == 'activate':
                    # Electron's singleton routes this invocation to its current
                    # window. It does not create another app-server owner.
                    subprocess.Popen([str(exe)], cwd=exe.parent, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, creationflags=setup.CREATE_NO_WINDOW)
                    requested = False
                    if not blocked_version:
                        status('running', 'Codex Usage is running.', build=build.name)
                elif action == 'launch':
                    if pointer.get('state') == 'launch-failed':
                        raise ValueError('This candidate previously failed. Select a verified rollback or install a repaired build.')
                    status('launching', 'Verifying and opening Codex Usage.')
                    setup.launch()
                    requested = False
                    if blocked_version:
                        status('unsupported-update', 'Codex ' + blocked_version + ' needs a tested adapter. The last verified mod is running.', version=blocked_version)
                    else:
                        status('running', 'Codex Usage is running.', build=build.name)
                elif kind == 'closed' and not blocked_version and not rebuild_pending and failed_update is None:
                    status('idle', 'Launcher is ready. Open Codex Usage from its taskbar icon.')
                elif kind == 'mod' and not blocked_version and not rebuild_pending and failed_update is None:
                    status('running', 'Codex Usage is running.', build=build.name)
            except setup.DesktopInstanceRunning:
                # A Store shortcut can reopen the app during full verification.
                # Retain the request; a competing instance is not a bad build.
                requested = True
                failed_request = None
                checked_at = time.monotonic()
                status('waiting-for-quit', 'The standard Codex app reopened. Quit it normally and wait for Codex Usage (local mod); do not reopen the Store shortcut.')
            except Exception as error:
                if rebuild_pending or action == 'launch':
                    failed_update = (package['Version'], fingerprint)
                    rebuild_pending = False
                failed_request = last_request
                requested = False
                checked_at = time.monotonic()
                status('failed', str(error))
            time.sleep(2)
        status('stopped', 'Launcher stopped. The desktop app was left running.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    monitor(Path(parser.parse_args().root))
