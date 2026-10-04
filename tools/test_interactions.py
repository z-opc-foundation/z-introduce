#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""z-desc 交互回归：在真实浏览器里驱动搜索/筛选/详情抽屉，断言 DOM 实际变化。

为什么需要这个：Node 单测只覆盖了 match() 纯函数，验证不了事件委托、
防抖重渲染、抽屉开关在浏览器里是否真的接线成功。

实现说明：本机 Chrome 的 --dump-dom 会挂住（--screenshot 正常），
所以探针把断言结果画成覆盖整页的 <pre>，用截图读回。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

SITE = "/Users/zifang/workplace/ceo_workplace/z-opc-foundation/z-desc"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOT = "/tmp/zdesc_shots/30-interactions.png"

PROBE = r"""
<script>
var log=[];
function cards(){return document.querySelectorAll('.card').length;}
function step(n,fn){try{log.push(n+' = '+fn());}catch(e){log.push(n+' = ERR:'+e.message);}}
function fbtn(layer){
  return Array.prototype.find.call(document.querySelectorAll('.fbtn'),
    function(x){return x.dataset.layer===layer;});
}
function setQuery(v){
  var q=document.getElementById('q');
  q.value=v;
  q.dispatchEvent(new Event('input',{bubbles:true}));
}

setTimeout(function(){
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

  setTimeout(function(){
    step('08-搜索命中数', function(){return cards();});
    step('09-命中仓库', function(){
      return Array.prototype.map.call(document.querySelectorAll('.card'),
        function(c){return c.dataset.repo;}).sort().join(',');});

    // 4) 空结果态
    step('10-搜不存在词', function(){setQuery('zzz-not-exist'); return 'typed';});

    setTimeout(function(){
      step('11-空结果卡片数', function(){return cards();});
      step('12-空态可见', function(){
        return document.getElementById('empty').hidden?'hidden':'VISIBLE';});

      // 5) 重置
      step('13-重置后卡片数', function(){
        document.getElementById('resetBtn').click(); return cards();});

      // 6) 详情抽屉（z-vector 无注记，另开 z-graph 验证注记渲染路径）
      step('14-打开抽屉', function(){
        var c=document.querySelector('.card[data-repo="z-vector"]');
        if(!c) return 'no-card';
        c.click();
        return document.getElementById('drawer').hidden?'STILL-HIDDEN':'OPEN';});
      step('15-抽屉标题', function(){
        var h=document.querySelector('#dBody .dh h3');
        return h?h.textContent.trim():'none';});
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
      step('19c-打开z-graph', function(){
        document.getElementById('dClose').click();
        var c=document.querySelector('.card[data-repo="z-graph"]');
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

      // 8) 斜杠聚焦搜索
      step('21-斜杠聚焦', function(){
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true}));
        return document.activeElement.id==='q'?'focused':'not-focused';});

      var box=document.createElement('pre');
      box.style.cssText='position:fixed;inset:0;z-index:99999;background:#000;color:#4f4;'+
        'font:15px/1.7 monospace;padding:14px;margin:0;white-space:pre-wrap;';
      box.textContent=log.join('\n');
      document.body.appendChild(box);
    },320);
  },320);
},900);
</script>
"""


def main():
    stage = tempfile.mkdtemp(prefix="zdint-")
    shutil.copytree(os.path.join(SITE, "assets"),
                    os.path.join(stage, "assets"), dirs_exist_ok=True)
    html = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    probe_html = os.path.join(stage, "probe.html")
    open(probe_html, "w", encoding="utf-8").write(
        html.replace("</body>", PROBE + "</body>"))

    os.makedirs("/tmp/zdesc_shots", exist_ok=True)
    if os.path.exists(SHOT):
        os.remove(SHOT)

    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--disable-extensions", "--disable-background-networking",
         "--disable-sync", "--no-first-run", "--password-store=basic",
         "--user-data-dir=" + tempfile.mkdtemp(prefix="zdprof-"),
         "--virtual-time-budget=5000", "--window-size=1100,1000",
         "--screenshot=" + SHOT, "file://" + probe_html],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(2)
        if os.path.exists(SHOT) and os.path.getsize(SHOT) > 5000:
            break
    proc.kill()
    try:
        proc.wait(timeout=10)
    except Exception:
        pass

    if not os.path.exists(SHOT):
        print("[!] 截图未生成，无法读取探针结果")
        return 1
    print("探针截图:", SHOT, os.path.getsize(SHOT) // 1024, "KB")
    print("请查看该图片读取断言结果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
