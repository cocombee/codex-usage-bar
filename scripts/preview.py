#!/usr/bin/env python3
"""Loopback-only UI fixture, using the installed host React without copying it."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import argparse
import json
import sys
sys.dont_write_bytecode = True
from mod import Archive, ROOT, NEW, ASAR

HOST_FILES = {'app-shared-8bd9d0399038.js','rolldown-runtime-2d059c5e81f4.js',
              'codex-usage-speed.mjs','codex-usage-bar.mjs','codex-usage-metrics.mjs',
              'codex-usage-diff-slot.mjs','codex-usage-native-fixed.mjs'}
HOST_ARCHIVE = NEW / ASAR
WINDOWS = False
WINDOWS_ADAPTER = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        try:
            if path in ['/', '/tests/fixture.html']:
                html = (ROOT / 'tests/fixture.html').read_text(encoding='utf-8')
                if WINDOWS:
                    html = html.replace('PCn as loadReact, Agn as loadJSX, Dgn as loadDOM, Ogn as loadPortal',
                                        f'{WINDOWS_ADAPTER.REACT} as loadReact, {WINDOWS_ADAPTER.JSX} as loadJSX, {WINDOWS_ADAPTER.DOM} as loadDOM, {WINDOWS_ADAPTER.PORTAL} as loadPortal')
                    html = html.replace('app-shared-8bd9d0399038.js', Path(WINDOWS_ADAPTER.SHARED).name)
                data = html.encode('utf-8'); mime = 'text/html'
            elif path.startswith('/__host/') and path.rsplit('/',1)[1] in HOST_FILES:
                data = Archive(HOST_ARCHIVE).read('webview/assets/' + path.rsplit('/',1)[1]); mime = 'text/javascript'
            elif path in ['/src/bar.mjs','/src/metrics.mjs','/src/speed.mjs','/src/diff-slot.mjs','/src/native-fixed.mjs','/src/native-layout.mjs','/src/responsive.mjs']:
                data = (ROOT / path.lstrip('/')).read_bytes(); mime = 'text/javascript'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(data)
        except Exception:
            self.send_error(500)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows', action='store_true', help='Use the latest verified local Windows build')
    args = parser.parse_args()
    if args.windows:
        WINDOWS = True
        build = Path(json.loads((ROOT / '.local-windows/latest.json').read_text(encoding='utf-8'))['build'])
        HOST_ARCHIVE = build / 'app/resources/app.asar'
        from windows_versions import adapter_for
        receipt = json.loads((build / 'receipt.json').read_text(encoding='utf-8'))
        WINDOWS_ADAPTER = adapter_for(receipt['package_version'])
        HOST_FILES.add(Path(WINDOWS_ADAPTER.SHARED).name)
        for name in ['responsive', 'native-layout']:
            HOST_FILES.add('codex-usage-' + name + '.mjs')
    server = HTTPServer(('127.0.0.1', 0), Handler)
    print(f'http://127.0.0.1:{server.server_port}', flush=True)
    server.serve_forever()
