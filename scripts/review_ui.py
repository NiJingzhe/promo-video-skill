#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""Review a rendered film in the browser: a monitor on top, a timeline strip underneath, notes on the picture.

    uv run review_ui.py out/promo.mp4 --out review/review.json [--overlay overlay.json]

The human plays or scrubs the film, presses M (or the button) to leave a note at that moment, drags on the
Notes track to mark a range, writes what is wrong, and finishes with Approved / Needs changes. Each note
carries the exact FRAME the human was looking at (saved as a png), so the agent sees what they saw.
Timeline (bottom): filmstrip of the picture, the finished mix's waveform (the audio is already in the film),
and - if --overlay is given - the beat grid, the music marks and the voice-over lines, so "this cut is
off the beat" is visible.

--overlay overlay.json: {"beats":[s...], "marks":[{"t":s,"label":"drop"}...], "vo":[{"start":s,"end":s,"text":"..."}...]}
Output (--out): {"file","duration","fps","verdict":"approved"|"changes","summary",
                 "notes":[{"id","t","end","timecode","text","frame"}]}   frames next to it in frames/
Exit code 0 = finished, 2 = Cancel. Python standard library + ffmpeg only.
"""
import argparse
import array
import http.server
import json
import math
import re
import subprocess
import tempfile
import threading
import webbrowser
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--out", default="review/review.json")
ap.add_argument("--overlay")
ap.add_argument("--port", type=int, default=0)
ap.add_argument("--no-open", action="store_true")
a = ap.parse_args()

video = Path(a.video).resolve()
out = Path(a.out).resolve()
frames_dir = out.parent / "frames"
work = Path(tempfile.mkdtemp(prefix="review-"))

probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)], capture_output=True, check=True, text=True).stdout)
vs = next(s for s in probe["streams"] if s["codec_type"] == "video")
num, den = (int(x) for x in vs["r_frame_rate"].split("/"))
FPS = num / den
DUR = float(probe["format"]["duration"])
TH_H, TH_W = 72, round(72 * int(vs["width"]) / int(vs["height"]))
IV = max(0.5, math.ceil(DUR / 120 * 2) / 2)         # one thumbnail every IV seconds, at most 120
NT = math.ceil(DUR / IV)

print("review_ui: preparing the timeline (thumbnails, waveform)...", flush=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"fps=1/{IV},scale={TH_W}:{TH_H},tile={NT}x1", "-frames:v", "1", "-q:v", "5", str(work / "sprite.jpg")], check=True)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout
samples = array.array("f"); samples.frombytes(raw[: len(raw) // 4 * 4])
peaks = [round(max(abs(x) for x in samples[i:i + 80]), 3) for i in range(0, len(samples), 80)] if len(samples) else []  # 100 per second

config = {"file": video.name, "duration": DUR, "fps": FPS, "thumb": {"w": TH_W, "h": TH_H, "iv": IV, "n": NT}, "peaks": peaks,
          "overlay": json.loads(Path(a.overlay).read_text()) if a.overlay else {}}
result = {"status": None}
done = threading.Event()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send(self, code, body: bytes, ctype="application/json", extra=None):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        try:
            self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser abandoned a range request while seeking

    def do_GET(self):
        if self.path == "/": self.send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/config": self.send(200, json.dumps(config).encode())
        elif self.path == "/sprite.jpg": self.send(200, (work / "sprite.jpg").read_bytes(), "image/jpeg")
        elif self.path == "/video": self.serve_video()
        else: self.send(404, b"")

    def serve_video(self):  # Range support: the <video> element seeks with it
        size = video.stat().st_size
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        lo, hi = (int(m.group(1) or 0), int(m.group(2)) if m and m.group(2) else size - 1) if m else (0, size - 1)
        hi = min(hi, size - 1)
        with open(video, "rb") as f:
            f.seek(lo); body = f.read(hi - lo + 1)
        self.send(206 if m else 200, body, "video/mp4", {"Accept-Ranges": "bytes", "Content-Range": f"bytes {lo}-{hi}/{size}"})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/frame/"):
            frames_dir.mkdir(parents=True, exist_ok=True)
            (frames_dir / f"{re.sub(r'[^0-9A-Za-z_-]', '', self.path[7:])}.png").write_bytes(body); self.send(200, b"{}")
        elif self.path == "/done":
            data = json.loads(body)
            for n in data["notes"]:
                f = frames_dir / f"{n['id']}.png"
                n["frame"] = str(f) if f.exists() else None
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
            result["status"] = "done"; self.send(200, b"{}"); done.set()
        elif self.path == "/cancel":
            if result["status"] is None: result["status"] = "cancel"
            self.send(200, b"{}"); done.set()
        else: self.send(404, b"")


PAGE = r"""<!doctype html><meta charset=utf-8><title>Review</title>
<style>
:root{--bg:#121418;--panel:#1c1f25;--line:#2b303a;--fg:#e8eaee;--dim:#8b93a1;--acc:#ff9f43;--note:#ff5d5d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{display:flex;gap:8px;align-items:center;padding:8px 14px;border-bottom:1px solid var(--line)}h1{font-size:14px;margin:0 auto 0 0;font-weight:600}
button,select{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px 11px;cursor:pointer;font:inherit}
button:hover{border-color:#4a5160}button.pri{background:var(--acc);color:#1a1000;border-color:var(--acc);font-weight:600}button:disabled{opacity:.35}
#top{flex:1;display:flex;min-height:0}#mon{flex:1;display:flex;flex-direction:column;min-width:0;padding:10px 14px 6px}
#screen{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;background:#000;border-radius:8px;position:relative}
video{max-width:100%;max-height:100%;display:block}
#bar{display:flex;gap:8px;align-items:center;padding:8px 0 0;flex-wrap:wrap}#tc{font:600 15px ui-monospace,Menlo,monospace;min-width:112px}.dim{color:var(--dim)}
#notes{width:340px;border-left:1px solid var(--line);padding:10px;overflow:auto}
#notes h2{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin:2px 2px 8px;display:flex;justify-content:space-between}
.note{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:8px;margin-bottom:8px}.note.sel{border-color:var(--acc)}
.note .h{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;cursor:pointer}.note .h b{color:var(--note);font-family:ui-monospace,Menlo,monospace;font-size:13px}
.note img{width:100%;border-radius:4px;display:block;margin-bottom:6px;background:#000}.note textarea{width:100%;min-height:54px;resize:vertical;background:#101216;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px;font:inherit}
.note .x{background:none;border:0;color:var(--dim);padding:0 4px}
#empty{color:var(--dim);line-height:1.6;padding:8px}.k{display:inline-block;padding:0 6px;border:1px solid #4a5160;border-radius:4px;font-size:12px;background:#101216}
#tl{height:268px;border-top:1px solid var(--line);padding:6px 14px 10px;background:#0f1115}#tl canvas{width:100%;height:100%;display:block;touch-action:none}
#modal{position:fixed;inset:0;background:#000b;display:none;align-items:center;justify-content:center}#modal>div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;width:440px}
#modal textarea{width:100%;height:80px;background:#101216;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:8px;font:inherit;margin:10px 0}
.verd{display:flex;gap:8px}.verd button{flex:1;padding:12px}.verd button.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}
#msg{position:fixed;inset:0;background:#000c;display:none;align-items:center;justify-content:center;font-size:18px}
</style>
<header><h1 id=title>Review</h1><span class=dim id=hint></span><button id=cancel>Cancel</button><button id=finish class=pri>Finish review…</button></header>
<div id=top><div id=mon><div id=screen><video id=v playsinline></video></div>
 <div id=bar><button id=prev title="back 1 frame (←)">◀︎</button><button id=play style=min-width:84px>▶ Play</button><button id=next title="forward 1 frame (→)">▶︎</button>
  <span id=tc>0:00:00</span><span class=dim id=tot></span>
  <select id=rate><option value=.25>0.25×</option><option value=.5>0.5×</option><option value=1 selected>1×</option><option value=2>2×</option></select>
  <label class=dim><input type=checkbox id=loop> loop the selected range</label><span style=flex:1></span>
  <button id=add class=pri>✎ Note here (M)</button></div></div>
 <div id=notes><h2><span>Notes</span><span id=ncount>0</span></h2><div id=list></div></div></div>
<div id=tl><canvas id=c></canvas></div>
<div id=modal><div><b>Finish the review</b><div class=verd style=margin-top:12px><button id=vok>✓ Approved</button><button id=vch>✎ Needs changes</button></div>
 <textarea id=sum placeholder="Overall comment (optional)"></textarea><div style="display:flex;gap:8px;justify-content:flex-end"><button id=back>Back</button><button id=send class=pri>Send review</button></div></div></div>
<div id=msg>Sent. You can close this tab.</div>
<script>
const $=id=>document.getElementById(id), v=$('v'), cv=$('c'), ctx=cv.getContext('2d'), dpr=Math.min(2,devicePixelRatio||1);
let cfg, spr=new Image(), notes=[], sel=null, past=[], future=[], view={start:0,span:10}, drag=null, rangeSel=null, verdict='changes', seq=1;
const GUT=74, TR={ruler:[0,22],pic:[24,96],aud:[100,160],beat:[164,184],vo:[186,210],note:[212,250]};
const fps=()=>cfg.fps, T=()=>cfg.duration;
const tcode=t=>{const f=Math.round(t*fps()),s=Math.floor(f/fps());return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')+':'+String(f%Math.round(fps())).padStart(2,'0')};
const x2t=x=>view.start+(x-GUT)/(cv.clientWidth-GUT)*view.span, t2x=t=>GUT+(t-view.start)/view.span*(cv.clientWidth-GUT);
const clampView=()=>{view.span=Math.max(.5,Math.min(T(),view.span));view.start=Math.max(0,Math.min(T()-view.span,view.start))};
const snapshot=()=>{past.push(JSON.stringify(notes));if(past.length>200)past.shift();future=[]};
function undo(){if(past.length){future.push(JSON.stringify(notes));notes=JSON.parse(past.pop());sel=null;ui()}}
function redo(){if(future.length){past.push(JSON.stringify(notes));notes=JSON.parse(future.pop());sel=null;ui()}}

function draw(){
  cv.width=cv.clientWidth*dpr;cv.height=cv.clientHeight*dpr;const w=cv.clientWidth,h=cv.clientHeight;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  ctx.font='11px system-ui';ctx.textBaseline='middle';
  const lab=(k,t)=>{const [a,b]=TR[k];ctx.fillStyle='#8b93a1';ctx.fillText(t,6,(a+b)/2)};
  lab('pic','Picture');lab('aud','Audio');if(cfg.overlay.beats)lab('beat','Beats / marks');if(cfg.overlay.vo)lab('vo','Voice-over');lab('note','Notes');
  ctx.save();ctx.beginPath();ctx.rect(GUT,0,w-GUT,h);ctx.clip();
  // ruler
  ctx.fillStyle='#171a20';ctx.fillRect(GUT,0,w-GUT,22);const nice=[.5,1,2,5,10,15,30,60];const st=nice.find(n=>n*(w-GUT)/view.span>=70)||60;ctx.fillStyle='#8b93a1';ctx.strokeStyle='#3a404b';ctx.textBaseline='middle';
  for(let t=Math.ceil(view.start/st)*st;t<view.start+view.span;t+=st){const x=t2x(t);ctx.beginPath();ctx.moveTo(x,16);ctx.lineTo(x,22);ctx.stroke();ctx.fillText(Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')+(st<1?'.'+String(Math.round(t%1*10)):''),x+3,10)}
  // filmstrip
  const [pa,pb]=TR.pic,ph=pb-pa,th=cfg.thumb;if(spr.complete&&spr.naturalWidth){for(let i=Math.floor(view.start/th.iv);i<th.n;i++){const t=i*th.iv;if(t>view.start+view.span)break;const x0=t2x(t),x1=t2x(Math.min(T(),t+th.iv)),sw=x1-x0,nat=ph*th.w/th.h;
    const srcW=sw<nat?th.w*sw/nat:th.w;ctx.drawImage(spr,i*th.w,0,srcW,th.h,x0,pa,sw,ph)}}
  // audio waveform (the finished mix)
  const [aa,ab]=TR.aud,mid=(aa+ab)/2,amp=(ab-aa)/2*.92;ctx.fillStyle='#1b1f27';ctx.fillRect(GUT,aa,w-GUT,ab-aa);ctx.fillStyle='#5aa9ff';
  for(let x=GUT;x<w;x+=1){const t0=x2t(x),t1=x2t(x+1);let m=0;for(let i=Math.floor(t0*100);i<=Math.max(Math.floor(t0*100),Math.floor(t1*100))&&i<cfg.peaks.length;i++)if(cfg.peaks[i]>m)m=cfg.peaks[i];ctx.fillRect(x,mid-m*amp,1,Math.max(1,m*amp*2))}
  // beats / marks
  const o=cfg.overlay;if(o.beats){const [ba,bb]=TR.beat;ctx.fillStyle='#141720';ctx.fillRect(GUT,ba,w-GUT,bb-ba);o.beats.forEach((b,i)=>{if(b<view.start||b>view.start+view.span)return;const x=t2x(b);ctx.fillStyle=i%4===0?'#c9ced8':'#59606e';ctx.fillRect(x,ba+(i%4===0?2:8),1,i%4===0?bb-ba-4:bb-ba-14)});
    (o.marks||[]).forEach(m=>{const x=t2x(m.t);if(x<GUT-60||x>w)return;ctx.strokeStyle='#ffd166';ctx.beginPath();ctx.moveTo(x,24);ctx.lineTo(x,TR.note[0]-2);ctx.stroke();ctx.fillStyle='#ffd166';ctx.fillText(m.label||'',x+4,ba+10)})}
  if(o.vo){const [va,vb]=TR.vo;ctx.fillStyle='#141720';ctx.fillRect(GUT,va,w-GUT,vb-va);o.vo.forEach(l=>{const x0=t2x(l.start),x1=t2x(l.end);if(x1<GUT||x0>w)return;ctx.fillStyle='#3b8f6a';ctx.fillRect(x0,va+2,x1-x0,vb-va-4);ctx.fillStyle='#0b1a12';ctx.save();ctx.beginPath();ctx.rect(x0,va,x1-x0,vb-va);ctx.clip();ctx.fillText(l.text||'',x0+4,(va+vb)/2);ctx.restore()})}
  // notes track
  const [na,nb]=TR.note;ctx.fillStyle='#141720';ctx.fillRect(GUT,na,w-GUT,nb-na);if(!notes.length&&!rangeSel){ctx.fillStyle='#4b5260';ctx.fillText('click = scrub · drag here to mark a range · M = note at the playhead',GUT+8,(na+nb)/2)}
  const R=n=>n.end&&n.end>n.t;[...notes,...(rangeSel?[{t:rangeSel.a,end:rangeSel.b,id:'~',tmp:1}]:[])].forEach(n=>{const x0=t2x(n.t),x1=R(n)?t2x(n.end):x0,s=sel===n.id;
    if(R(n)){ctx.fillStyle=s?'#ff9f4366':'#ff5d5d44';ctx.fillRect(x0,na+4,x1-x0,nb-na-8);ctx.fillRect(x0,24,x1-x0,2)}ctx.fillStyle=s?'#ff9f43':'#ff5d5d';ctx.fillRect(x0-1,24,2,nb-24);
    ctx.beginPath();ctx.arc(x0,na+12,6,0,7);ctx.fill();ctx.fillStyle='#fff';ctx.fillText(String(notes.findIndex(q=>q.id===n.id)+1||''),x0+9,na+12)});
  // playhead
  const px=t2x(v.currentTime||0);ctx.strokeStyle='#fff';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(px,0);ctx.lineTo(px,h);ctx.stroke();ctx.lineWidth=1;ctx.fillStyle='#fff';ctx.beginPath();ctx.moveTo(px-6,0);ctx.lineTo(px+6,0);ctx.lineTo(px,9);ctx.fill();
  ctx.restore();
  $('tc').textContent=tcode(v.currentTime||0);
}
function ui(){
  draw();$('ncount').textContent=notes.length;const L=$('list');L.innerHTML='';
  if(!notes.length){L.innerHTML='<div id=empty><b>How to review</b><br>1. Play the film or drag along the strip below.<br>2. When something is wrong or great, press <span class=k>M</span> (or ✎ Note here): the frame you are looking at is attached.<br>3. Type what to change. To cover a stretch, drag on the red <b>Notes</b> track first.<br>4. <b>Finish review</b> when done — the agent reads your notes.</div>';return}
  notes.forEach((n,i)=>{const d=document.createElement('div');d.className='note'+(sel===n.id?' sel':'');d.dataset.id=n.id;
    d.innerHTML=`<div class=h><b>${i+1} · ${tcode(n.t)}${n.end&&n.end>n.t?' → '+tcode(n.end):''}</b><button class=x title=delete>✕</button></div><img src="${n.thumb||''}" ${n.thumb?'':'hidden'}><textarea placeholder="What should change here?">${n.text||''}</textarea>`;
    d.querySelector('.h').onclick=e=>{if(e.target.className==='x'){snapshot();notes.splice(i,1);sel=null;ui();return}sel=n.id;seekTo(n.t);ui()};
    const ta=d.querySelector('textarea');ta.onfocus=()=>{sel=n.id;draw()};ta.oninput=()=>{n.text=ta.value};ta.onchange=()=>{snapshot()};
    d.querySelector('img').onclick=()=>seekTo(n.t);L.appendChild(d)})}
function seekTo(t){v.currentTime=Math.max(0,Math.min(T(),t));draw()}
async function addNote(t0=v.currentTime,t1=null){snapshot();v.pause();const id='n'+String(seq++).padStart(2,'0')+'_'+Math.round(t0*1000);const n={id,t:+t0.toFixed(3),end:t1?+t1.toFixed(3):null,text:''};
  // freeze the exact frame at t0 (wait for the seek, or the canvas would hold the previous picture) and upload it
  if(Math.abs(v.currentTime-t0)>.001||v.seeking)await new Promise(r=>{v.addEventListener('seeked',r,{once:true});v.currentTime=t0});
  const cvs=document.createElement('canvas');cvs.width=v.videoWidth;cvs.height=v.videoHeight;cvs.getContext('2d').drawImage(v,0,0);
  n.thumb=cvs.toDataURL('image/jpeg',.6);cvs.toBlob(b=>fetch('/frame/'+id,{method:'POST',body:b}),'image/png');
  notes.push(n);notes.sort((a,b)=>a.t-b.t);sel=id;ui();const ta=document.querySelector(`.note[data-id="${id}"] textarea`);ta&&ta.focus()}
$('add').onclick=()=>addNote();
$('play').onclick=()=>v.paused?v.play():v.pause();
v.onplay=()=>{$('play').textContent='❚❚ Pause';loop()};v.onpause=()=>{$('play').textContent='▶ Play';draw()};
function loop(){if(v.paused)return;const n=notes.find(q=>q.id===sel&&q.end&&q.end>q.t);if($('loop').checked&&n&&v.currentTime>=n.end)v.currentTime=n.t;
  if(v.currentTime>view.start+view.span*.95||v.currentTime<view.start){view.start=Math.max(0,Math.min(T()-view.span,v.currentTime-view.span*.1))}draw();requestAnimationFrame(loop)}
v.onseeked=draw;v.ontimeupdate=()=>{if(v.paused)draw()};
$('prev').onclick=()=>{v.pause();seekTo(v.currentTime-1/fps())};$('next').onclick=()=>{v.pause();seekTo(v.currentTime+1/fps())};
$('rate').onchange=e=>v.playbackRate=+e.target.value;
// timeline interaction
const track=y=>y>=TR.note[0]?'note':'scrub';
const near=x=>{for(const n of notes)if(Math.abs(t2x(n.t)-x)<8)return n;return null};
cv.onpointerdown=e=>{cv.setPointerCapture(e.pointerId);const x=e.offsetX,y=e.offsetY;if(x<GUT)return;
  if(track(y)==='note'){const n=near(x);if(n){sel=n.id;seekTo(n.t);ui();drag={k:'none'};return}drag={k:'range',a:x2t(x),x0:x};rangeSel=null}
  else{drag={k:'scrub'};v.pause&&0;seekTo(x2t(x))}};
cv.onpointermove=e=>{if(!drag)return;const t=Math.max(0,Math.min(T(),x2t(e.offsetX)));if(drag.k==='scrub')seekTo(t);else if(drag.k==='range'&&Math.abs(e.offsetX-drag.x0)>4){rangeSel={a:Math.min(drag.a,t),b:Math.max(drag.a,t)};draw()}};
cv.onpointerup=e=>{if(!drag)return;const d=drag;drag=null;if(d.k==='range'){if(rangeSel&&rangeSel.b-rangeSel.a>.1){const r=rangeSel;rangeSel=null;seekTo(r.a);addNote(r.a,r.b)}else{rangeSel=null;seekTo(x2t(e.offsetX))}}};
cv.addEventListener('wheel',e=>{e.preventDefault();if(e.ctrlKey||e.metaKey){const t=x2t(e.offsetX),k=(t-view.start)/view.span;view.span*=Math.exp(e.deltaY*.01);clampView();view.start=t-k*view.span;clampView()}else{view.start+=(Math.abs(e.deltaX)>Math.abs(e.deltaY)?e.deltaX:e.deltaY)/cv.clientWidth*view.span;clampView()}draw()},{passive:false});
addEventListener('resize',draw);
addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;const k=e.key.toLowerCase();
  if(e.code==='Space'){e.preventDefault();$('play').click()}else if(k==='m'){addNote()}
  else if((e.metaKey||e.ctrlKey)&&k==='z'){e.preventDefault();e.shiftKey?redo():undo()}
  else if(e.key==='ArrowLeft'){e.preventDefault();v.pause();seekTo(v.currentTime-(e.shiftKey?1:1/fps()))}else if(e.key==='ArrowRight'){e.preventDefault();v.pause();seekTo(v.currentTime+(e.shiftKey?1:1/fps()))}
  else if(e.key==='Home')seekTo(0);else if(e.key==='End')seekTo(T());
  else if((e.key==='Delete'||e.key==='Backspace')&&sel){snapshot();notes=notes.filter(n=>n.id!==sel);sel=null;ui()}
  else if(e.key==='='||e.key==='+'){view.span/=2;clampView();draw()}else if(e.key==='-'){view.span*=2;clampView();draw()}});
// finish
$('finish').onclick=()=>{verdict=notes.length?'changes':'approved';mark();$('modal').style.display='flex'};
const mark=()=>{$('vok').classList.toggle('on',verdict==='approved');$('vch').classList.toggle('on',verdict==='changes')};
$('vok').onclick=()=>{verdict='approved';mark()};$('vch').onclick=()=>{verdict='changes';mark()};$('back').onclick=()=>$('modal').style.display='none';
$('send').onclick=async()=>{v.pause();await fetch('/done',{method:'POST',body:JSON.stringify({file:cfg.file,duration:cfg.duration,fps:cfg.fps,verdict,summary:$('sum').value,
  notes:notes.map(n=>({id:n.id,t:n.t,end:n.end,timecode:tcode(n.t)+(n.end?' -> '+tcode(n.end):''),text:n.text||''}))})});$('modal').style.display='none';$('msg').style.display='flex';setTimeout(()=>close(),600)};
$('cancel').onclick=async()=>{await fetch('/cancel',{method:'POST',body:'{}'});$('msg').textContent='Cancelled. You can close this tab.';$('msg').style.display='flex';setTimeout(()=>close(),600)};
(async()=>{cfg=await (await fetch('/config')).json();$('title').textContent=cfg.file;$('tot').textContent='/ '+tcode(cfg.duration)+' · '+cfg.fps.toFixed(0)+' fps';
  view={start:0,span:Math.min(cfg.duration,30)};spr.onload=draw;spr.src='/sprite.jpg';v.src='/video';v.onloadedmetadata=()=>{ui()};ui()})();
</script>"""


def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"review_ui: open {url}  ({video.name}, {DUR:.1f}s, {FPS:g} fps)", flush=True)
    if not a.no_open: webbrowser.open(url)
    done.wait()
    import time
    time.sleep(0.4)
    server.shutdown()
    if result["status"] == "done":
        d = json.loads(out.read_text()); print(f"review_ui: DONE, verdict {d['verdict']}, {len(d['notes'])} notes -> {out}"); raise SystemExit(0)
    print("review_ui: cancelled"); raise SystemExit(2)


main()
