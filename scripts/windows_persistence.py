"""Install the stable native launcher and an immutable, local engine snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import windows_setup as setup


def engine_files(source):
    source = Path(source)
    scripts = ['scripts/' + name for name in setup.SCRIPT_NAMES]
    return scripts + ['src/' + path.name for path in sorted((source / 'src').glob('*.mjs'))] + ['src/windows-launcher.cs']


def engine_fingerprint(source):
    return hashlib.sha256(json.dumps({name: setup.sha(Path(source) / name) for name in engine_files(source)}, sort_keys=True).encode()).hexdigest()


def install(root=None):
    setup.platform_guard()
    root = setup.validate_install_root(root or setup.default_install_root())
    pointer = setup.read_json(root / 'current.json')
    build = setup.current_build(root, pointer['current'])
    setup.verify_build(build)
    identity = engine_fingerprint(setup.ROOT)
    release = root / 'engines' / identity
    if not release.exists():
        pending = release.with_name(identity + '.pending-' + uuid.uuid4().hex)
        for name in engine_files(setup.ROOT):
            destination = pending / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(setup.ROOT / name, destination)
        setup.require(engine_fingerprint(pending) == identity, 'Engine changed during installation')
        pending.rename(release)
    setup.require(engine_fingerprint(release) == identity, 'Installed engine differs from its source')
    exe = root / 'CodexUsage.exe'
    icon = root / 'CodexUsage.ico'
    source_icon = build / 'app/resources/icon-chatgpt.ico'
    setup.require(source_icon.is_file(), 'Verified application icon is missing')
    setup.atomic_file(icon, source_icon.read_bytes())
    icon_hash = setup.sha(icon)
    source_hash = setup.sha(setup.ROOT / 'src/windows-launcher.cs')
    config_path = root / 'launcher-config.json'
    old = setup.read_json(config_path) if config_path.exists() else {}
    if not exe.exists() or old.get('launcher_source_sha256') != source_hash or old.get('launcher_icon_sha256') != icon_hash or old.get('launcher_sha256') != setup.sha(exe):
        compiler = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
        setup.require(compiler.is_file(), 'The Windows .NET Framework 4 compiler is required for the native launcher')
        temporary = root / ('CodexUsage.pending-' + uuid.uuid4().hex + '.exe')
        result = subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu',
            '/win32icon:' + str(icon),
            '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Runtime.Serialization.dll',
            '/out:' + str(temporary), str(setup.ROOT / 'src/windows-launcher.cs')], capture_output=True, text=True,
            creationflags=setup.CREATE_NO_WINDOW)
        setup.require(result.returncode == 0, 'Native launcher compilation failed: ' + result.stdout + result.stderr)
        try:
            os.replace(temporary, exe)
        except PermissionError:
            temporary.unlink(missing_ok=True)
            raise ValueError('Exit the Codex Usage tray launcher before upgrading its native executable. The desktop app need not be stopped.')
    setup.atomic_json(config_path, {'schema': 1, 'python': sys.executable, 'engine': str(release.relative_to(root)),
        'engine_fingerprint': identity, 'launcher_source_sha256': source_hash, 'launcher_icon_sha256': icon_hash, 'launcher_sha256': setup.sha(exe), 'autostart': True})
    links = setup.powershell('''
$shell = New-Object -ComObject WScript.Shell
$programs = Join-Path ([Environment]::GetFolderPath('Programs')) 'Codex Usage'
New-Item -ItemType Directory -Path $programs -Force | Out-Null
$paths = @((Join-Path $programs 'Codex Usage (local mod).lnk'), (Join-Path ([Environment]::GetFolderPath('Startup')) 'Codex Usage.lnk'))
foreach ($path in $paths) {
 $link=$shell.CreateShortcut($path)
 $link.TargetPath=$args[0]; $link.Arguments=''; $link.WorkingDirectory=$args[1]
 $link.IconLocation=$args[2] + ',0'; $link.Description='Codex Usage persistent local launcher'
 $link.Save()
}
$paths | ConvertTo-Json -Compress
''', exe, root, icon)
    for link in links:
        result = subprocess.run([str(exe), '--stamp-shortcut', str(link)], timeout=15, creationflags=setup.CREATE_NO_WINDOW)
        setup.require(result.returncode == 0, 'Could not assign the mod shortcut its taskbar identity')
    result = subprocess.run([str(exe), '--self-test'], timeout=15, creationflags=setup.CREATE_NO_WINDOW)
    setup.require(result.returncode == 0 and setup.read_json(root / 'launcher-self-test.json').get('passed'), 'Native launcher self-test failed')
    return {'launcher': str(exe), 'engine': str(release), 'shortcuts': links, 'autostart': True}
