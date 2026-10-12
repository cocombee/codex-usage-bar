# Installation

In macOS Terminal, from the downloaded repository, run:

```sh
python3 scripts/setup.py
```

Requirements: Apple Silicon macOS, Python 3.9+, Node.js 20+, the inspected desktop version `26.1007.30912` at `/Applications/ChatGPT.app`, and a writable checkout on the same filesystem as `/Applications` with backup space. Other versions stop without replacement; the installer never guesses new patch anchors or disables validation.

## Native desktop tool limitation

The local ad-hoc signature prevents the native desktop tool bridge from authorizing on this version. Chat discovery, chat-to-chat messaging and other tools using that bridge are affected. Ordinary typing and replies worked after this installation. Accept this tradeoff before installing; no peer-authorization checks are disabled or spoofed. See [26.1007 compatibility](Codex%2026.1007%20Compatibility.md).

## Three steps

1. Check version, recognized archive, prerequisites, filesystem boundaries, free space and duplicate processes. Acquire an exclusive install lock.
2. Build while Codex stays open. Validate the source signature and native ASAR digest; create the protected original archive and complete candidate locally. Recompute archive/header/native integrity before scoped local signing. Verify signatures, entitlements, unchanged fuses, module syntax and unrelated archive contents. The entire build has a 15-minute limit; external commands have shorter limits.
3. Recheck the candidate and exact installed app, close the inspected main process if running, atomically exchange complete bundles, and normally open the installed app once. The app also installs correctly when initially closed. Wait for one healthy main process for ten seconds, prove its mapped main executable and framework inodes match the installed bundle, reject fresh main/helper crash reports, and repeat signature/integrity checks. A pathname alone cannot prove the running build after a bundle exchange. No data, Keychain, Gatekeeper or quarantine reset is involved.

Run `python3 scripts/setup.py --check` for compatibility checks without building, closing or installing. Keep Terminal open until the install result appears. Codex reopens automatically; do not open another copy while installation is in progress. The installer attaches to an already reopened, verified candidate instead of issuing a second launch, and refuses stale or duplicate instances. Run outside Codex so the worker survives the app closing.

## Install an already verified candidate after a manual quit

`python3 -B scripts/install_after_quit.py --candidate-sha256 <SHA256>` uses the candidate hash in `local-build.json`, verifies the recorded source and candidate, then waits up to 20 minutes for the current app to quit normally. Run it from an independent Terminal or a finite one-time worker so it survives Codex closing. Add `--check` for read-only verification.

This helper never quits or launches Codex. After quitting, wait for `installed_awaiting_reopen` in `local-install-after-quit-status.json`, then reopen the app. The same atomic installer retains the original app in `New Build`. An unexpected app instance, changed build or expired wait stops installation. Do not use a persistent or automatically restarting job.

## Recovery and errors

- Unsupported version, unknown archive or invalid signature: app stays untouched. Use a reviewed version; do not bypass the checks.
- Missing Node/Python, insufficient space, unwritable folders or a checkout on another disk: correct the stated prerequisite and rerun. No sudo is invoked.
- Build failure or timeout: Codex has not been closed or replaced. Details are in `local-setup.log`. Timeout cleanup terminates surviving build descendants even when their parent has already exited. A partial/unrecognized candidate is refused rather than overwritten silently.
- Codex refuses to close within 30 seconds: replacement is refused. Close Codex normally and rerun.
- Candidate fails normal startup: restore the complete previous verified app by atomic exchange and issue one recovery launch. Never repeatedly launch a failing candidate. A recovery that cannot prove a safe process boundary stops with a recorded error.
- Interrupted transaction: inspect `local-install-status.json` and `local-build.json` before retrying. Never discard the retained previous app while acceptance is pending.

All local logs, locks, receipts, command launchers and app bundles are excluded from Git. The protected original is `Safe Build`; the verified candidate or immediate previous app occupies `New Build`. Updating while installed acceptance remains pending first copies the recorded recovery app into `Protected Recovery`, verifies its exact archive, fingerprint and signing policy, and saves its provenance in `local-recovery.json`. Further pending updates reuse their exact linked protected copy and never replace it with an unaccepted predecessor. After a later build receives explicit acceptance, its next pending update chain preserves that newer accepted predecessor in a separate fingerprint-addressed verified slot with its own provenance; older verified copies remain intact. Unknown, incomplete or changed recovery copies stop the build before `New Build` is reused. No acceptance is inferred from requesting another update.

If a pending update fails startup, recovery copies the protected original into a unique temporary bundle on the same filesystem, verifies it, and atomically restores that copy. The protected original remains untouched. Space checks reserve the initial protected copy and a separate rollback staging copy. Interrupted staging folders are excluded from Git and never silently reused. Transactions whose installed app does not match the receipt stop for review.

## Acceptance

Automated checks distinguish compatibility, build validation, installed-bundle validation and process health. After the command completes, confirm the native usage row renders and normally quit/reopen the exact installed app once. Live metric correctness and native diff interactions require separate acceptance. A working process and synthetic tests do not prove these outcomes.

Once you have personally verified both rendered UI and normal quit/reopen, leave that installed app running and record those checks from this checkout:

```sh
python3 scripts/setup.py --accept --confirm-rendered-ui --confirm-quit-reopen
```

This optional command verifies the installed candidate, retained recovery bundles, signatures, fingerprints, and identity of the sole running app before saving your explicit attestation in `local-build.json`. It does not build, install, quit, launch, or delete the recovery app. Process health never grants acceptance automatically. You can update without recording acceptance: the installer preserves the known-working recovery copy first. If either check fails, preserve the receipts and recovery bundles; do not use the acceptance command to bypass a failed check.

The 26.1007 candidate was installed from the verified vendor app through the manual-quit path. Its exact running bundle and retained original were verified; the user confirmed the bar appears, and ordinary chat continued. A further normal quit/reopen of the installed candidate, live metric accuracy and native diff interaction remain pending. Recovery to an older build is not acceptance of this candidate. Source-signing policy, timeouts, locking and failure recovery have automated coverage. This pinned installer cannot guarantee every macOS environment will launch successfully, so refusal and recovery are part of its contract.
