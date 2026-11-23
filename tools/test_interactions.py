#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用本机 Chrome 与 Node 22+ 验证真实 DOM；断言失败或空白截图均返回非零。"""
import functools
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOT = "/tmp/zdesc_shots/30-interactions.png"

# 独立固定基线；数据有意更新时需显式审查，不从当前 DOM 反推预期。
EXPECTED = {
    '01-初始卡片数': 58,
    '02-筛选后卡片数': 19,
    '03-全部属L3': 'yes',
    '04-高亮按钮': 'L3 中间件层 19',
    '05-结果提示': '匹配 19 / 58 个仓库 · L3 中间件层',
    '06-恢复全部': 58,
    '07-搜索vector': 'typed',
    '08-搜索命中数': 1,
    '09-命中仓库': 'z-vector',
    '10-搜不存在词': 'typed',
    '11-空结果卡片数': 0,
    '12-空态可见': 'VISIBLE',
    '13-重置后卡片数': 58,
    '14-打开抽屉': 'OPEN',
    '15-抽屉标题': 'z-vector Central',
    '15a-弹窗可访问名称': True,
    '15b-首焦点为关闭': True,
    '15c-ShiftTab在弹窗内循环': True,
    '15d-Tab回到关闭': True,
    '15e-斜杠不穿透弹窗': True,
    '15f-弹窗背景不可聚焦': True,
    '16-抽屉分区数': 5,
    '17-模块标签数': 7,
    '17b-无注记时不显示注记块': 'absent(正确)',
    '19-外链地址': 'https://github.com/z-opc-foundation/z-vector',
    '19b-语言条存在': 4,
    '19c-打开z-boot': 'OPEN',
    '18-注记文本': '据本仓 README「火车制重构」：原 fl',
    '20-Esc关闭': 'CLOSED',
    '20b-关闭恢复触发焦点': True,
    '21-斜杠聚焦': 'focused',
}

PROBE = r"""
(async function(){
var log=[];
function cards(){return document.querySelectorAll('.card').length;}
function step(n,fn){
  try{log.push({name:n,actual:fn()});}
  catch(e){log.push({name:n,error:e.message});}
}
async function waitFor(fn,label){
  var end=performance.now()+5000;
  while(!fn()){
    if(performance.now()>end) throw new Error('DOM timeout: '+label);
    await new Promise(resolve=>setTimeout(resolve,25));
  }
}
function fbtn(layer){
  return Array.prototype.find.call(document.querySelectorAll('.fbtn'),
    function(x){return x.dataset.layer===layer;});
}
function setQuery(v){
  var q=document.getElementById('q');
  q.value=v;
  q.dispatchEvent(new Event('input',{bubbles:true}));
}

await waitFor(()=>document.readyState==='complete' && window.ZDESC && cards()>0,'initial render');
  step('01-初始卡片数', function(){return cards();});

  // 1) 点击「L3 中间件层」筛选
  step('02-筛选后卡片数', function(){fbtn('l3').click(); return cards();});
  step('03-全部属L3', function(){
    return Array.prototype.every.call(document.querySelectorAll('.card'),
      function(c){return c.classList.contains('layer-l3');})?'yes':'no';});
  step('04-高亮按钮', function(){
    var o=document.querySelector('.fbtn.on'); return o?o.textContent.trim():'none';});
  step('05-结果提示', function(){
    return document.getElementById('resultLine').textContent.slice(0,30);});

  // 2) 回到全部
  step('06-恢复全部', function(){fbtn('all').click(); return cards();});

  // 3) 搜索（走 input 事件 + 防抖）
  step('07-搜索vector', function(){setQuery('vector'); return 'typed';});

  await waitFor(()=>document.getElementById('resultLine').textContent.includes('关键词「vector」'),'vector search');
    step('08-搜索命中数', function(){return cards();});
    step('09-命中仓库', function(){
      return Array.prototype.map.call(document.querySelectorAll('.card'),
        function(c){return c.dataset.repo;}).sort().join(',');});

    // 4) 空结果态
    step('10-搜不存在词', function(){setQuery('zzz-not-exist'); return 'typed';});

    await waitFor(()=>document.getElementById('resultLine').textContent.includes('关键词「zzz-not-exist」'),'empty search');
      step('11-空结果卡片数', function(){return cards();});
      step('12-空态可见', function(){
        return document.getElementById('empty').hidden?'hidden':'VISIBLE';});

      // 5) 重置
      step('13-重置后卡片数', function(){
        document.getElementById('resetBtn').click(); return cards();});

      // 6) 详情抽屉（z-vector 无注记，另开 z-boot 验证注记渲染路径）
      step('14-打开抽屉', function(){
        var c=document.querySelector('.card[data-repo="z-vector"]');
        if(!c) return 'no-card';
        c.click();
        return document.getElementById('drawer').hidden?'STILL-HIDDEN':'OPEN';});
      step('15-抽屉标题', function(){
        var h=document.querySelector('#dBody .dh h3');
        return h?h.textContent.trim():'none';});
      step('15a-弹窗可访问名称', function(){
        return !!document.getElementById(document.getElementById('drawer').getAttribute('aria-labelledby'));});
      step('15b-首焦点为关闭', function(){return document.activeElement.id==='dClose';});
      step('15c-ShiftTab在弹窗内循环', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));
        var links=document.querySelectorAll('#drawer a[href]');
        return document.activeElement===links[links.length-1];});
      step('15d-Tab回到关闭', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
        return document.activeElement.id==='dClose';});
      step('15e-斜杠不穿透弹窗', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true,cancelable:true}));
        return document.activeElement.id==='dClose';});
      step('15f-弹窗背景不可聚焦', function(){
        document.getElementById('q').focus();
        return document.activeElement.id==='dClose' && document.querySelector('main').inert;});
      step('16-抽屉分区数', function(){
        return document.querySelectorAll('#dBody .dsec').length;});
      step('17-模块标签数', function(){
        return document.querySelectorAll('#dBody .mod').length;});
      step('17b-无注记时不显示注记块', function(){
        return document.querySelector('#dBody .dnote')?'BLOCK-PRESENT':'absent(正确)';});
      step('19-外链地址', function(){
        var a=document.querySelector('#dBody .dlinks a');
        return a?a.getAttribute('href'):'none';});
      step('19b-语言条存在', function(){
        return document.querySelectorAll('#dBody .langs-bar i').length;});

      // 6b) 换一个带注记的仓库，验证注记块渲染
      step('19c-打开z-boot', function(){
        document.getElementById('dClose').click();
        var c=document.querySelector('.card[data-repo="z-boot"]');
        if(!c) return 'no-card';
        c.click();
        return document.getElementById('drawer').hidden?'STILL-HIDDEN':'OPEN';});
      step('18-注记文本', function(){
        var n=document.querySelector('#dBody .dnote');
        return n?n.textContent.slice(0,22):'none';});

      // 7) Esc 关闭
      step('20-Esc关闭', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
        return document.getElementById('drawer').hidden?'CLOSED':'STILL-OPEN';});

      step('20b-关闭恢复触发焦点', function(){
        return document.activeElement.dataset.repo==='z-boot' && !document.querySelector('main').inert;});

      // 8) 斜杠聚焦搜索
      step('21-斜杠聚焦', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true}));
        return document.activeElement.id==='q'?'focused':'not-focused';});

return log;
})()
"""


# Node 原生 WebSocket 只承担 CDP 传输和门禁，不复制完整 UI 验收脚本。
CDP_RUNNER = r"""
import {writeFile} from 'node:fs/promises';
let input='';
for await (const chunk of process.stdin) input+=chunk;
const config=JSON.parse(input), pending=new Map(), errors=[];
let socket, id=0;
function call(method,params={}){
  return new Promise((resolve,reject)=>{
    const n=++id;
    const timer=setTimeout(()=>{pending.delete(n);reject(new Error(method+' timeout'));},20000);
    pending.set(n,{resolve,reject,timer});
    socket.send(JSON.stringify({id:n,method,params}));
  });
}
function disconnect(message){
  for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error(message));}
  pending.clear();
}
async function evaluate(expression){
  const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});
  if(r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
try{
  if(typeof WebSocket==='undefined') throw new Error('需要 Node 22+ 原生 WebSocket');
  const response=await fetch(config.debug+'/json/list',{signal:AbortSignal.timeout(5000)});
  if(!response.ok) throw new Error('CDP discovery HTTP '+response.status);
  const tab=(await response.json()).find(t=>t.type==='page');
  if(!tab) throw new Error('CDP page target missing');
  socket=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('WebSocket open timeout')),5000);
    socket.onopen=()=>{clearTimeout(timer);resolve();};
    socket.onerror=()=>{clearTimeout(timer);reject(new Error('WebSocket open failed'));};
  });
  socket.onclose=()=>disconnect('CDP disconnected');
  socket.onerror=()=>disconnect('CDP socket error');
  socket.onmessage=({data})=>{
    const m=JSON.parse(data), p=m.params;
    if(pending.has(m.id)){
      const waiter=pending.get(m.id);pending.delete(m.id);clearTimeout(waiter.timer);
      m.error ? waiter.reject(new Error(JSON.stringify(m.error))) : waiter.resolve(m.result);
    }
    if(m.method==='Runtime.exceptionThrown') errors.push(p.exceptionDetails.exception?.description || p.exceptionDetails.text);
    if(m.method==='Runtime.consoleAPICalled' && ['error','assert'].includes(p.type))
      errors.push('console '+p.type+': '+p.args.map(a=>a.value ?? a.description).join(' '));
    if(m.method==='Log.entryAdded' && p.entry.level==='error') errors.push(p.entry.text);
    if(m.method==='Network.responseReceived' && p.response.status>=400)
      errors.push('HTTP '+p.response.status+' '+p.response.url);
    if(m.method==='Network.loadingFailed') errors.push('resource failed: '+p.errorText);
    if(m.method==='Fetch.requestPaused'){
      const local=new URL(p.request.url).origin===config.origin;
      if(!local) errors.push('blocked external request: '+p.request.url);
      call(local ? 'Fetch.continueRequest' : 'Fetch.failRequest',local ? {requestId:p.requestId} :
        {requestId:p.requestId,errorReason:'BlockedByClient'}).catch(e=>errors.push(e.message));
    }
  };
  await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Log.enable');
  await call('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
  await call('Emulation.setDeviceMetricsOverride',{width:1100,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  const navigation=await call('Page.navigate',{url:config.origin+'/'});
  if(navigation.errorText) throw new Error('navigation: '+navigation.errorText);
  // 用新文档的 load 状态就绪，不依赖虚拟时间或可能停滞的 rAF。
  for(const end=Date.now()+10000;;){
    if(await evaluate(`location.href===${JSON.stringify(config.origin+'/')} && document.readyState==='complete'`)) break;
    if(Date.now()>end) throw new Error('page load timeout');
    await new Promise(resolve=>setTimeout(resolve,50));
  }
  const checks=await evaluate(config.probe), names=Object.keys(config.expected);
  if(!Array.isArray(checks)) throw new Error('PROBEDOM missing result array');
  if(names.length!==31 || JSON.stringify(checks.map(c=>c.name))!==JSON.stringify(names))
    errors.push('PROBEDOM incomplete/duplicate/out-of-order: '+checks.length+'/31');
  let passed=0;
  for(const c of checks){
    const expected=config.expected[c.name];
    const ok=Object.hasOwn(config.expected,c.name) && !c.error && c.actual===expected;
    if(ok) passed++; else errors.push('assertion: '+c.name);
    console.log('PROBEDOM '+c.name+' = '+JSON.stringify(c.actual)+' ['+(ok?'PASS':'FAIL')+']'+
      (ok?'':' expected='+JSON.stringify(expected)+(c.error?' error='+c.error:'')));
  }
  // 不画测试日志覆盖层，截实际仓库目录；像素检查不能替代 DOM 断言。
  await call('Page.bringToFront');
  await evaluate(`document.getElementById('repos').scrollIntoView({block:'start',behavior:'instant'})`);
  await evaluate(`new Promise(resolve=>{
    const timer=setTimeout(resolve,200);
    requestAnimationFrame(()=>requestAnimationFrame(()=>{clearTimeout(timer);resolve();}));
  })`);
  const visible=await evaluate(`Array.from(document.querySelectorAll('.card')).some(c=>{
    const r=c.getBoundingClientRect();
    return c.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) && r.width>0 && r.height>0 &&
      r.top>=0 && r.bottom<=innerHeight && c.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));
  })`);
  if(!visible) errors.push('no visible, unobstructed repository card in screenshot viewport');
  const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});
  await writeFile(config.shot,Buffer.from(shot.data,'base64'));
  // 浏览器自身解码 PNG 到离屏 canvas，无 Pillow/图像依赖，也不改页面 DOM。
  const pixels=await evaluate(`(async()=>{
    const image=new Image();image.src='data:image/png;base64,${shot.data}';await image.decode();
    const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
    const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
    const data=ctx.getImageData(0,0,canvas.width,canvas.height).data, bins=new Map();
    let samples=0,dominant=0;
    for(let i=0;i<data.length;i+=64){
      const key=((data[i]>>4)<<8)|((data[i+1]>>4)<<4)|(data[i+2]>>4);
      const count=(bins.get(key)||0)+1;bins.set(key,count);dominant=Math.max(dominant,count);samples++;
    }
    return {width:image.width,height:image.height,colors:bins.size,nonDominant:1-dominant/samples};
  })()`);
  console.log('SCREENSHOT '+config.shot+' '+JSON.stringify(pixels));
  if(pixels.width!==1100 || pixels.height!==1000 || pixels.colors<16 || pixels.nonDominant<0.02)
    errors.push('blank/invalid screenshot');
  // CDP 往返也让截图期间的异步异常进入错误列表。
  await evaluate('0');
  console.log('DOM assertions: '+passed+'/31; gate: '+(errors.length?'FAIL':'PASS'));
  if(errors.length) throw new Error(errors.join('\n'));
}catch(e){
  console.error('[FAIL] '+e.message);process.exitCode=1;
}finally{
  disconnect('runner finished');
  if(socket) socket.close();
}
"""


class LocalHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            super().do_GET()


def main():
    server = browser = None
    try:
        # 先清旧证据，启动失败也不能留下上一轮的“成功截图”。
        Path(SHOT).parent.mkdir(parents=True, exist_ok=True)
        Path(SHOT).unlink(missing_ok=True)
        node = shutil.which('node')
        if not node:
            raise RuntimeError('需要 PATH 中的 Node 22+')
        with tempfile.TemporaryDirectory(prefix='zdint-') as temporary:
            handler = functools.partial(LocalHandler, directory=SITE)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            origin = 'http://127.0.0.1:' + str(server.server_port)
            profile = os.path.join(temporary, 'profile')
            with open(os.path.join(temporary, 'chrome.log'), 'w+b') as chrome_log:
                browser = subprocess.Popen([
                    CHROME, '--headless=new', '--no-first-run', '--no-default-browser-check',
                    '--disable-extensions', '--disable-background-networking', '--disable-sync',
                    '--disable-component-update', '--disable-default-apps', '--no-pings',
                    '--no-proxy-server', '--password-store=basic',
                    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost',
                    '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
                    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
                    '--user-data-dir=' + profile, 'about:blank',
                ], stdout=subprocess.DEVNULL, stderr=chrome_log, start_new_session=True)
                try:
                    port_file = Path(profile) / 'DevToolsActivePort'
                    deadline = time.monotonic() + 15
                    while True:
                        if browser.poll() is not None or time.monotonic() > deadline:
                            chrome_log.seek(0)
                            raise RuntimeError('Chrome startup failed/timeout: ' +
                                               chrome_log.read().decode(errors='replace')[-2000:])
                        try:
                            lines = port_file.read_text().splitlines()
                            if len(lines) >= 2 and lines[0].isdigit():
                                port = int(lines[0])
                                break
                        except FileNotFoundError:
                            pass
                        time.sleep(0.05)
                    config = dict(debug='http://127.0.0.1:' + str(port), origin=origin,
                                  probe=PROBE, expected=EXPECTED, shot=SHOT)
                    print('Real DOM runner: ' + origin + ' (isolated Chrome CDP, pid=' +
                          str(browser.pid) + ')', flush=True)
                    # 即使调用环境启用了 Node 代理，也只直连本次 loopback 服务。
                    env = dict(os.environ, NO_PROXY='*', no_proxy='*')
                    result = subprocess.run([node, '--input-type=module', '-e', CDP_RUNNER],
                                            input=json.dumps(config), text=True, timeout=60, env=env)
                    return 0 if result.returncode == 0 else 1
                finally:
                    # 只终止本次创建的独立进程组，不按进程名/端口清理其他浏览器。
                    try:
                        os.killpg(browser.pid, signal.SIGTERM)
                        browser.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                    finally:
                        try:
                            os.killpg(browser.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        browser.wait(timeout=5)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        print('[FAIL] ' + (str(exc) or 'interrupted'), file=sys.stderr)
        return 1
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    sys.exit(main())
