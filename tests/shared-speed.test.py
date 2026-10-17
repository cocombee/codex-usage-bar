"""Both adapters deliver the same speed lifecycle; no real app is read or built."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mod
import windows_patch
import windows_patch_26_1007
import windows_patch_26_1007_9446


class RendererFixture:
    def __init__(self, adapter):
        if adapter is mod:
            primary = '\n'.join([
                'ke=(0,LR.jsxs)(uR.Item,{children:[ue,Oe]})',
                'className:Sg(`flex w-full flex-col gap-2`,Pe&&`relative`),onPaste:Li?wl:void 0',
                '(0,QX.jsx)(Vm,{initial:!1,children:Gl&&o==null?',
            ])
            turn = 'function Go(e){return e}var Ko,qo,Jo,Yo,Xo,Zo;'
            initial = '(Kl.div,{"aria-hidden":u,className:f,inert:p,initial:m,animate:h,exit:g,transition:_,children:b})'
        elif adapter is windows_patch:
            primary = '\n'.join([
                'Oe=(0,jR.jsxs)(QL.Item,{children:[ce,De]})',
                'className:ld(`flex w-full flex-col gap-2`,Ue&&`relative`),onPaste:Yi?Ul:void 0',
                '(0,WX.jsx)(ae,{initial:!1,children:lu&&s==null?',
            ])
            turn = 'function Vo(e){return e}var Ho,Uo,Wo,Go,Ko,qo;'
            initial = '(gc.div,{"aria-hidden":u,className:f,inert:p,initial:m,animate:h,exit:g,transition:_,children:b})'
        else:
            primary = '\n'.join([
                'ke=(0,LR.jsxs)(uR.Item,{children:[ue,Oe]})',
                'className:Sg(`flex w-full flex-col gap-2`,Pe&&`relative`),onPaste:Li?wl:void 0',
                '(0,QX.jsx)(Vm,{initial:!1,children:Gl&&o==null?',
            ])
            turn = 'function Go(e){return e}var Ko,qo,Jo,Yo,Xo,Zo;'
            initial = '(Kl.div,{"aria-hidden":u,className:f,inert:p,initial:m,animate:h,exit:g,transition:_,children:b})'
            if adapter is windows_patch_26_1007_9446:
                initial = initial.replace('(Kl.div,', '(Gl.div,')
        self.files = {
            adapter.PRIMARY: primary,
            adapter.SHARED: 'onNotification(e,t,n=null,r,i=Date.now()){',
            adapter.TURN: turn,
            adapter.INITIAL: initial,
        }
        if adapter is windows_patch:
            self.files[adapter.BOOTSTRAP] = 'p.app.setAppUserModelId(NY(Q9))'
        elif adapter in (windows_patch_26_1007, windows_patch_26_1007_9446):
            self.files[adapter.BOOTSTRAP] = 'f.app.setAppUserModelId(rr(Hk))'

    def read(self, path):
        return self.files[path].encode('utf-8')


class SharedSpeedTests(unittest.TestCase):
    def test_windows_bootstrap_handles_owl_without_optional_app_details(self):
        for adapter, variable in ((windows_patch, 'p'), (windows_patch_26_1007, 'f'), (windows_patch_26_1007_9446, 'f')):
            bootstrap = adapter.patch_sources(RendererFixture(adapter))[adapter.BOOTSTRAP].decode('utf-8')
            with self.subTest(adapter=adapter.__name__), tempfile.TemporaryDirectory() as directory:
                script = Path(directory) / 'bootstrap.mjs'
                script.write_text("import assert from 'node:assert/strict';\n"
                    + "const calls=[],icons=[];process.resourcesPath='/verified/resources';\n"
                    + "const app={setAppUserModelId:id=>calls.push(id),on:(event,callback)=>{assert.equal(event,'browser-window-created');callback({},{});callback({},{setIcon:path=>icons.push(path)});}};\n"
                    + "new Function('" + variable + "'," + repr(bootstrap) + ")({app});\n"
                    + "assert.deepEqual(calls,['Cocombee.CodexUsage']);\n"
                    + "app.setAppDetails=details=>calls.push(details.appId);\n"
                    + "new Function('" + variable + "'," + repr(bootstrap) + ")({app});\n"
                    + "assert.deepEqual(calls,['Cocombee.CodexUsage','Cocombee.CodexUsage','Cocombee.CodexUsage']);\n", encoding='utf-8')
                script.write_text(script.read_text('utf-8') + "assert.deepEqual(icons,['/verified/resources/icon-chatgpt.ico','/verified/resources/icon-chatgpt.ico']);\n", encoding='utf-8')
                subprocess.run(['node', str(script)], check=True, timeout=15)

    def test_new_windows_composer_passes_core_snapshot_to_weekly_metric(self):
        adapter = windows_patch_26_1007_9446
        host = adapter.patch_sources(RendererFixture(adapter))[adapter.PRIMARY].decode('utf-8').split('let __cuBar;', 1)[1]
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'host.mjs'
            script.write_text('''
import assert from 'node:assert/strict';
const React={useRef:()=>({current:null})}, jsx={jsx:(type,props)=>({type,props})};
const weekly={windowDurationMins:10080,usedPercent:9,resetsAt:123456};
const entries=[{limitName:null,snapshot:{secondary:weekly}},
 {limitName:'other-model',snapshot:{secondary:{...weekly,usedPercent:99}}}];
const factory=new Function('Z','K','__cuLayout','__cuCreateBar','Q','ns','Rye',
''' + repr('let __cuBar;' + host + '\nreturn __cuHost;') + ''');
const host=factory(()=>React,()=>jsx,()=>{},()=>function Bar(){},()=>({last:{totalTokens:29},modelContextWindow:100}),{},()=>entries);
const bar=host({conversationId:'chat',hostId:'host',rateLimit:{}}).props.children;
assert.equal(bar.props.entries.length,1);
assert.deepEqual(bar.props.entries[0].snapshot.secondary,weekly);
assert.equal(bar.props.usage.last.totalTokens,29);
''', encoding='utf-8')
            subprocess.run(['node', str(script)], check=True, timeout=15)

    def test_packaged_speed_clears_on_completion_for_both_adapters(self):
        # Both adapters read text and normalize a Windows checkout's CRLF.
        expected = (mod.ROOT / 'src/speed.mjs').read_text(encoding='utf-8').encode('utf-8')
        for adapter in (mod, windows_patch, windows_patch_26_1007, windows_patch_26_1007_9446):
            with self.subTest(adapter=adapter.__name__):
                modules = adapter.patch_sources(RendererFixture(adapter))
                speed = modules['webview/assets/codex-usage-speed.mjs']
                self.assertEqual(speed, expected)
                self.assertIn(b'__cuObserve(this.hostId,e,t)', modules[adapter.SHARED])
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / 'speed.mjs').write_bytes(speed)
                    (root / 'check.mjs').write_text('''
import assert from 'node:assert/strict';
import {observeMetric, readSpeed, subscribeSpeed} from './speed.mjs';
const notices = [];
subscribeSpeed('host', 'chat', () => notices.push(readSpeed('host', 'chat')));
observeMetric('host', 'turn/started', {threadId:'chat', turn:{id:'turn'}}, 0);
observeMetric('host', 'thread/tokenUsage/updated', {
  threadId:'chat', tokenUsage:{last:{outputTokens:110},total:{outputTokens:110}}
}, 5000);
assert.equal(readSpeed('host', 'chat'), 22);
observeMetric('host', 'turn/completed', {threadId:'chat',turn:{id:'turn'}}, 5100);
assert.equal(readSpeed('host', 'chat'), null);
assert.deepEqual(notices, [22, null]);
''', encoding='utf-8')
                    subprocess.run(['node', str(root / 'check.mjs')], check=True, timeout=15)


if __name__ == '__main__':
    unittest.main()
