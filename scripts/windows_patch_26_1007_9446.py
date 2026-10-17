"""Inspected x64 Windows adapter for Store 26.1007.9446.0."""
from mod import ROOT, unique_replace

VERSION = '26.1007.9446.0'
APP_VERSION = '26.1007.71326'
PINNED = {
    'resources/app.asar': '356c13dc715816436fa1cf31e9f77863f62ea7b7cacc465b397313246eb29325',
    'ChatGPT.exe': 'ee785aec9ff3058afb01069a8b455fb17e46f3c33611a867efd3db37de1f05f3',
    'chrome.dll': 'ce6d04cc948e034c5f18d116a76dbb2cdf84b068c85101e53d168fbb33dadd60',
}
PRIMARY = 'webview/assets/app-primary-cd52df2361eb.js'
SHARED = 'webview/assets/app-shared-30671c57ec82.js'
TURN = 'webview/assets/local-conversation-turn-82ba4623d196.js'
INITIAL = 'webview/assets/app-initial-102e45562729.js'
BOOTSTRAP = '.vite/build/bootstrap-iULMfRBf.js'
ASSETS = (PRIMARY, SHARED, TURN, INITIAL)
REACT = 'PCn'
JSX = 'Agn'
DOM = 'Dgn'
PORTAL = 'Ogn'


def patch_sources(archive):
    bootstrap = archive.read(BOOTSTRAP).decode('utf-8')
    bootstrap = unique_replace(bootstrap, 'f.app.setAppUserModelId(rr(Hk))',
        '(f.app.setAppUserModelId("Cocombee.CodexUsage"),typeof f.app.setAppDetails==="function"&&f.app.setAppDetails({appId:"Cocombee.CodexUsage",'
        'relaunchCommand:\'"\'+process.env.LOCALAPPDATA+\'\\\\OpenAI\\\\CodexUsage\\\\CodexUsage.exe"\','
        'relaunchDisplayName:"Codex Usage"}),f.app.on("browser-window-created",(_event,window)=>{'
        'if(typeof window.setIcon==="function")window.setIcon(process.resourcesPath+"/icon-chatgpt.ico")}))', 'Windows persistent taskbar identity')
    primary, shared, turn, initial = (archive.read(path).decode('utf-8') for path in ASSETS)
    primary = unique_replace(primary, 'ke=(0,LR.jsxs)(uR.Item,{children:[ue,Oe]})',
        'ke=(0,LR.jsxs)(uR.Item,{"data-cu-native-goal":true,children:[ue,Oe]})', 'Windows Goal marker')
    anchor = 'onNotification(e,t,n=null,r,i=Date.now()){'
    shared = unique_replace(shared, anchor, anchor + 'try{__cuObserve(this.hostId,e,t)}catch{}', 'Windows notification observer')
    shared = 'import{observeMetric as __cuObserve}from"./codex-usage-speed.mjs";\n' + shared
    anchor = 'className:Sg(`flex w-full flex-col gap-2`,Pe&&`relative`),onPaste:Li?wl:void 0'
    primary = unique_replace(primary, anchor, '"data-cu-composer-stack":true,' + anchor, 'Windows composer stack')
    anchor = '(0,QX.jsx)(Vm,{initial:!1,children:Gl&&o==null?'
    primary = unique_replace(primary, anchor,
        'jt!==`cloud`?(0,QX.jsx)(__cuHost,{conversationId:Ye,hostId:ct.hostId,rateLimit:Jt}):null,' + anchor,
        'Windows usage placement')
    primary = ('import{useNativeLayout as __cuLayout}from"./codex-usage-native-layout.mjs";\n'
               'import{createBar as __cuCreateBar}from"./codex-usage-bar.mjs";\n' + primary + '''
let __cuBar;
function __cuHost({conversationId,hostId,rateLimit}){
  __cuBar??=__cuCreateBar(Z(),K());
  const placementRef=Z().useRef(null);
  __cuLayout(Z(),placementRef);
  const usage=Q(ns,conversationId);
  const core=Rye(rateLimit).filter(entry=>entry.limitName==null);
  return K().jsx(`div`,{ref:placementRef,"data-cu-placement":true,children:K().jsx(__cuBar,{conversationId,hostId,usage,entries:core})});
}
''')
    start = turn.index('function Go(e){')
    end = turn.index('var Ko,qo,Jo,Yo,Xo,Zo;', start)
    turn = unique_replace(turn, turn[start:end], '''function Go(e){
      return __cuFixed(e,{React:__cuLoadReact(),jsx:Jo,DOM:qo,anchor:dr,
        useSelector:V,diffAtom:yn,cwdAtom:Ae,extraAtom:Gr,summarize:diff=>io(Kn(diff)),
        Diff:Ma,Motion:Qe,Presence:Lt,Todo:ha,Layout:oo,fade:Xo,layout:Zo,delay:Yo});
    }
    ''', 'Windows native fixed-content composition')
    turn = ('import{PCn as __cuLoadReact}from"./app-shared-30671c57ec82.js";\n'
            'import{renderNativeFixed as __cuFixed}from"./codex-usage-native-fixed.mjs";\n' + turn)
    anchor = '(Gl.div,{"aria-hidden":u,className:f,inert:p,initial:m,animate:h,exit:g,transition:_,children:b})'
    initial = unique_replace(initial, anchor, anchor.replace('{"aria-hidden":u', '{"data-cu-native-utility":true,"aria-hidden":u'), 'Windows utility marker')
    modules = {}
    for name in ['bar', 'metrics', 'speed', 'diff-slot', 'native-fixed', 'native-layout', 'responsive']:
        source = (ROOT / 'src' / (name + '.mjs')).read_text(encoding='utf-8')
        for dependency in ['metrics', 'speed', 'diff-slot', 'responsive']:
            source = source.replace("'./" + dependency + ".mjs'", "'./codex-usage-" + dependency + ".mjs'")
        modules['webview/assets/codex-usage-' + name + '.mjs'] = source.encode('utf-8')
    return {BOOTSTRAP: bootstrap.encode('utf-8'), PRIMARY: primary.encode('utf-8'), SHARED: shared.encode('utf-8'),
            TURN: turn.encode('utf-8'), INITIAL: initial.encode('utf-8'), **modules}
