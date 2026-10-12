#!/usr/bin/env python3
"""One finite app-only installation after the user manually quits Codex.

Does not quit/launch apps, re-sign bundles, or edit authorization, chats, or settings.
Uses the existing verified transaction and retains the original app for rollback.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import mod
from install_once import atomic_json, exclusive_install, verify_builds

REPORT = mod.ROOT / 'local-install-after-quit-status.json'


def record(state, **details):
    value = {'state': state, 'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'worker_pid': os.getpid(), **details}
    atomic_json(REPORT, value)
    print(json.dumps(value), flush=True)


def checked_receipt(expected):
    receipt = json.loads(mod.RECEIPT.read_text())
    if receipt.get('state') != 'candidate_verified' or receipt.get('candidate_sha256') != expected:
        raise ValueError('Verified candidate changed; installation refused')
    verify_builds(receipt, receipt['preinstall_sha256'])
    return receipt


def main(args):
    receipt = checked_receipt(args.candidate_sha256)
    instances = mod.codex_instances()
    expected = str(mod.APP / 'Contents/MacOS/ChatGPT')
    if len(instances) != 1 or instances[0]['executable'] != expected:
        raise ValueError('Expected exactly the current installed Codex instance')
    if args.check:
        print(json.dumps({'ready': True, 'version': receipt['version'],
                          'candidate_sha256': receipt['candidate_sha256'], 'running_pid': instances[0]['pid']}))
        return
    old_pid = instances[0]['pid']
    with exclusive_install():
        record('waiting_for_user_quit', version=receipt['version'], old_pid=old_pid,
               candidate_sha256=receipt['candidate_sha256'], timeout_seconds=1200)
        deadline = time.monotonic() + 1200
        while True:
            observed = mod.codex_instances()
            if time.monotonic() >= deadline:
                record('expired_without_changes')
                return
            if not observed:
                break
            if observed != instances:
                raise ValueError('Codex instance changed before the quit boundary; app untouched')
            time.sleep(1)
        checked_receipt(args.candidate_sha256)
        if mod.codex_instances():
            raise ValueError('Codex reopened before replacement; app untouched')
        record('installing', candidate_sha256=receipt['candidate_sha256'])
        mod.install()
        record('installed_awaiting_reopen', version=receipt['version'],
               candidate_sha256=receipt['candidate_sha256'], previous_app=str(mod.NEW),
               installed_app=str(mod.APP), live_ui_verified=False, ordinary_chat_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--job-label')
    args = parser.parse_args()
    try:
        main(args)
    except Exception as error:
        if not args.check:
            record('failed', error=str(error))
        else:
            print(str(error), file=sys.stderr)
        sys.exit(1)
    finally:
        if args.job_label and not args.check:
            subprocess.run(['/bin/launchctl', 'remove', args.job_label], check=False, capture_output=True)
