#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""A tiny waveform editor in the browser. The human cuts the audio with clicks, presses Done, the page
closes itself, and this script exits having written the result to --out for the agent to read.

    uv run cut_ui.py take.mp3 --mode cuts --script elevenlabs.md --out vo/cuts.json
    uv run cut_ui.py track.wav --mode marks --beats audio/beats.json --labels stab,drop --out audio/marks.json

  --mode cuts   (voice) the take is one long recording of N lines. The page shows the script line by line;
                the human plays it and CLICKS where one line ends and the next begins (or presses C while it
                plays). N-1 cuts. Speech and pauses (the <break>s) are drawn differently so the gaps are easy
                to see. --script gives the lines: a text file with one line per row, or the markdown table
                of an elevenlabs.md ("| 01 | Imagine being ... | ... |").
  --mode marks  (music) click to drop a named marker (drop, stab, ...); --beats draws the grid and snaps.
Output JSON: {"file","duration","mode","cuts":[t...],"items":[{"n","start","end","label","text"}]}
  cuts mode: items are the pieces between cuts (start/end are WINDOWS that contain a line plus its pauses;
  vo_cut.py --regions trims each to its speech); marks mode: start == end.
Exit code 0 = Done pressed, 2 = Cancel button. No dependencies: Python standard library only.
Run it in the background (the agent is notified when it exits) and tell the human a tab has opened;
if no browser opens, give them the printed URL.
"""
import argparse
import http.server
import json
import mimetypes
import threading
import webbrowser
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--mode", choices=["cuts", "regions", "marks"], default="cuts")
ap.add_argument("--script", help="cuts: the lines of the take, one per row (or an elevenlabs.md table)")
ap.add_argument("--lines", type=int, default=0, help="cuts: number of lines if there is no --script")
ap.add_argument("--labels", default="", help="marks: comma-separated suggested names, offered in order")
ap.add_argument("--beats", help="beats.json from music_analyze.py: draws the grid, snaps to it")
ap.add_argument("--init", help="a previous output json to continue editing")
ap.add_argument("--out", default="cuts.json")
ap.add_argument("--port", type=int, default=0)
ap.add_argument("--no-open", action="store_true")
a = ap.parse_args()

audio = Path(a.audio).resolve()
import re


def read_script(path):
    if not path: return []
    text = Path(path).read_text()
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", text, re.M)
    if rows: return [t.strip() for _, t in rows]
    return [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]


if a.mode == "regions": a.mode = "cuts"
SCRIPT = read_script(a.script)
config = {"file": audio.name, "mode": a.mode, "script": SCRIPT, "lines": len(SCRIPT) or a.lines, "labels": [x for x in a.labels.split(",") if x],
          "beats": json.load(open(a.beats))["beats"] if a.beats else [],
          "init": json.load(open(a.init))["items"] if a.init and Path(a.init).exists() else []}
result = {"status": None}
done = threading.Event()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path == "/": self.send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/config": self.send(200, json.dumps(config).encode())
        elif self.path == "/audio": self.send(200, audio.read_bytes(), mimetypes.guess_type(audio.name)[0] or "application/octet-stream")
        else: self.send(404, b"")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/done":
            data = json.loads(body)
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(data, indent=1, ensure_ascii=False))
            result["status"] = "done"; self.send(200, b"{}"); done.set()
        elif self.path == "/cancel":
            if result["status"] is None: result["status"] = "cancel"  # a tab closing after Done must not undo it
            self.send(200, b"{}"); done.set()
        else: self.send(404, b"")


PAGE = r"""<!doctype html><meta charset=utf-8><title>Cut the audio</title>
<style>
:root{--bg:#14161a;--panel:#1d2026;--line:#2c313a;--fg:#e8eaee;--dim:#8b93a1;--acc:#ff9f43;--wave:#5aa9ff;--cut:#ff5d5d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}
header{display:flex;gap:8px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:14px;margin:0 12px 0 0;font-weight:600}.sp{flex:1}
button{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px 11px;cursor:pointer;font:inherit}
button:hover{border-color:#4a5160}button:disabled{opacity:.35;cursor:default}button.pri{background:var(--acc);color:#1a1000;border-color:var(--acc);font-weight:600}
label{color:var(--dim);display:flex;gap:5px;align-items:center}
#help{margin:10px 14px 0;padding:10px 14px;border:1px solid var(--line);border-radius:8px;background:var(--panel);line-height:1.55;position:relative}
#help b{color:var(--acc)}#help .x{position:absolute;right:6px;top:4px;background:none;border:0;color:var(--dim)}
.k{display:inline-block;padding:0 6px;border:1px solid #4a5160;border-radius:4px;font-size:12px;background:#101216}
.leg{display:inline-block;width:22px;height:11px;vertical-align:-1px;border-radius:2px;margin-right:4px}
main{flex:1;display:flex;min-height:0}#stage{flex:1;display:flex;flex-direction:column;min-width:0;padding:10px 14px;gap:8px}
canvas{width:100%;display:block;border-radius:6px;background:#101216;touch-action:none}#wave{flex:1;min-height:200px}#mini{height:46px;cursor:pointer}
aside{width:340px;border-left:1px solid var(--line);overflow:auto;padding:10px}
aside h2{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin:2px 4px 8px;display:flex;justify-content:space-between}
.row{display:grid;grid-template-columns:26px 1fr;gap:2px 8px;padding:8px;border:1px solid var(--line);border-radius:6px;margin-bottom:6px;background:var(--panel);cursor:pointer}
.row.now{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}.row .n{color:var(--acc);font-weight:700;grid-row:1/3}
.row .t{line-height:1.35}.row small{color:var(--dim)}.row.miss{opacity:.55}.row.ok small::before{content:"✓ ";color:#58d68d}
.row input{background:#101216;color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:3px 5px;width:100%;font:inherit}
footer{padding:8px 14px;border-top:1px solid var(--line);color:var(--dim);display:flex;justify-content:space-between;font-size:12px;gap:12px;flex-wrap:wrap}
#msg{position:fixed;inset:0;background:#000c;display:none;align-items:center;justify-content:center;font-size:18px}
</style>
<header><h1 id=title>Cut the audio</h1>
<button id=play>▶ Play</button><button id=cutnow class=pri>✂ Cut here (C)</button>
<button id=undo disabled>↶ Undo</button><button id=redo disabled>↷ Redo</button>
<button id=zin>＋</button><button id=zout>－</button><button id=fit>Fit</button>
<label id=snaplab style=display:none><input type=checkbox id=snap checked>snap to beats</label><button id=auto>Suggest cuts</button>
<span class=sp></span><span id=count style=color:var(--dim)></span><button id=cancel>Cancel</button><button id=done class=pri>Done</button></header>
<div id=help></div>
<main><div id=stage><canvas id=wave></canvas><canvas id=mini></canvas></div><aside><h2 id=ah></h2><div id=list></div></aside></main>
<footer><span id=status></span><span><span class=k>Space</span> play · <span class=k>C</span> cut at the playhead · click = cut there · drag a red line to move · <span class=k>Del</span> remove · <span class=k>⌘Z</span> undo · scroll = pan · <span class=k>⌘</span>+scroll = zoom</span></footer>
<div id=msg>Saved. You can close this tab.</div>
<script>
const $=id=>document.getElementById(id);
let cfg, buf, dur=0, ch, sr, speech=[];   // speech: [[a,b],...] stretches with sound
let pts=[], sel=-1, past=[], future=[];   // pts: {t,label}  (cuts or markers), kept sorted
let view={start:0,span:10}, playhead=0, playing=false, src=null, t0=0, p0=0, playEnd=null, ctx=null, drag=null;
const wave=$('wave'), mini=$('mini'), W=()=>wave.clientWidth, dpr=Math.min(2,devicePixelRatio||1);
const fmt=t=>{const m=Math.floor(t/60);return m+':'+(t%60).toFixed(2).padStart(5,'0')};
const marks=()=>cfg.mode==='marks', N=()=>cfg.script.length||cfg.lines||0;
const x2t=x=>view.start+x/W()*view.span, t2x=t=>(t-view.start)/view.span*W();
const lineText=i=>cfg.script[i]||('Piece '+(i+1));

function pieces(){const c=[0,...pts.map(p=>p.t),dur];return c.slice(0,-1).map((a,i)=>({a,b:c[i+1],i}))}
function pieceAt(t){return pieces().find(p=>t>=p.a&&t<p.b)||null}
function commit(){past.push(JSON.stringify(pts));if(past.length>300)past.shift();future=[]}
function restore(s){pts=JSON.parse(s);sel=-1;ui()}
$('undo').onclick=()=>{if(past.length){future.push(JSON.stringify(pts));restore(past.pop())}};
$('redo').onclick=()=>{if(future.length){past.push(JSON.stringify(pts));restore(future.pop())}};
function snapT(t,px=8){ if(!cfg.beats.length||!$('snap').checked)return t; let b=null,d=1e9; for(const x of cfg.beats){const dd=Math.abs(x-t);if(dd<d){d=dd;b=x}} return d*W()/view.span<=px?b:t }
function clampView(){view.span=Math.max(0.05,Math.min(dur,view.span));view.start=Math.max(0,Math.min(dur-view.span,view.start))}
function zoom(f,at=playhead){const k=(at-view.start)/view.span;view.span*=f;clampView();view.start=at-k*view.span;clampView();draw()}
function addPt(t){t=Math.max(.02,Math.min(dur-.02,t));if(pts.some(p=>Math.abs(p.t-t)<.03))return;commit();pts.push({t,label:marks()?(cfg.labels[pts.length]||''):''});pts.sort((x,y)=>x.t-y.t);sel=pts.findIndex(p=>p.t===t);ui()}

function draw(){
  size(wave);size(mini);const c=wave.getContext('2d'),w=wave.width,h=wave.height,rulerH=22*dpr,top=rulerH+(marks()?0:26*dpr);
  c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,w,h);const mid=(h+top)/2,amp=(h-top)/2*0.92;
  // pauses (silence between speech): hatched, so the <break>s are obvious
  if(!marks()){let prev=0;const gaps=[];for(const [a,b] of speech){if(a>prev)gaps.push([prev,a]);prev=b}if(prev<dur)gaps.push([prev,dur]);
    for(const [a,b] of gaps){if(b-a<.2)continue;const x0=t2x(a)*dpr,x1=t2x(b)*dpr;c.fillStyle='#ffffff0c';c.fillRect(x0,top,x1-x0,h-top);
      c.fillStyle='#ffffff10';c.fillRect(x0,h-4*dpr,x1-x0,4*dpr);
      if(x1-x0>40*dpr){c.fillStyle='#8b93a1';c.font=`${11*dpr}px system-ui`;c.fillText('pause '+(b-a).toFixed(1)+'s',x0+6*dpr,h-8*dpr)}}}
  if(cfg.beats.length){c.strokeStyle='#ffffff14';c.lineWidth=dpr;for(const b of cfg.beats){if(b<view.start||b>view.start+view.span)continue;const x=t2x(b)*dpr;c.beginPath();c.moveTo(x,top);c.lineTo(x,h);c.stroke()}}
  // pieces: a coloured band with the script text, the active one (under the playhead) brighter
  if(!marks()){const now=pieceAt(playhead);for(const p of pieces()){const x0=t2x(p.a)*dpr,x1=t2x(p.b)*dpr,act=now&&now.i===p.i;if(x1<0||x0>w)continue;
    c.fillStyle=act?'#ff9f4316':(p.i%2?'#5aa9ff10':'#58d68d10');c.fillRect(x0,top,x1-x0,h-top);
    c.fillStyle=act?'#ff9f43':(p.i%2?'#5aa9ff':'#58d68d');c.fillRect(x0,rulerH,x1-x0,24*dpr-2*dpr);c.fillStyle='#10131a';c.font=`bold ${12*dpr}px system-ui`;
    c.save();c.beginPath();c.rect(x0,rulerH,x1-x0,24*dpr);c.clip();c.fillText((p.i+1)+'  '+lineText(p.i),Math.max(x0,0)+6*dpr,rulerH+16*dpr);c.restore()}}
  const spp=view.span*sr/w,step=Math.max(1,Math.floor(spp/48));c.fillStyle='#5aa9ff';
  for(let x=0;x<w;x++){const s0=Math.floor((view.start+x/w*view.span)*sr),s1=Math.min(ch.length,Math.floor(s0+spp));let lo=1,hi=-1;for(let s=Math.max(0,s0);s<s1;s+=step){const v=ch[s];if(v<lo)lo=v;if(v>hi)hi=v}
    if(hi>=lo)c.fillRect(x,mid-hi*amp,1,Math.max(1,(hi-lo)*amp))}
  pts.forEach((p,i)=>{const x=t2x(p.t)*dpr;if(x<-20||x>w+20)return;const s=i===sel;c.strokeStyle=marks()?(s?'#ff9f43':'#ffd166'):(s?'#fff':'#ff5d5d');c.lineWidth=(s?3:2)*dpr;c.beginPath();c.moveTo(x,rulerH);c.lineTo(x,h);c.stroke();
    c.fillStyle=c.strokeStyle;c.font=`${13*dpr}px system-ui`;c.fillText(marks()?(p.label||('#'+(i+1))):'✂',x+5*dpr,h-10*dpr)});
  c.fillStyle='#171a1f';c.fillRect(0,0,w,rulerH);c.fillStyle='#8b93a1';c.strokeStyle='#3a404b';c.lineWidth=dpr;c.font=`${11*dpr}px system-ui`;
  const nice=[.01,.02,.05,.1,.2,.5,1,2,5,10,30,60];const stepT=nice.find(n=>n*w/view.span/dpr>=70)||60;
  for(let t=Math.ceil(view.start/stepT)*stepT;t<view.start+view.span;t+=stepT){const x=t2x(t)*dpr;c.beginPath();c.moveTo(x,rulerH-6*dpr);c.lineTo(x,rulerH);c.stroke();c.fillText(fmt(t),x+3*dpr,13*dpr)}
  const px=t2x(playhead)*dpr;c.strokeStyle='#fff';c.lineWidth=dpr;c.beginPath();c.moveTo(px,0);c.lineTo(px,h);c.stroke();
  drawMini();$('status').textContent=`${fmt(playhead)} / ${fmt(dur)}   ·   view ${view.span.toFixed(2)} s`;
}
function size(c){c.width=c.clientWidth*dpr;c.height=c.clientHeight*dpr}
function drawMini(){const c=mini.getContext('2d'),w=mini.width,h=mini.height;c.clearRect(0,0,w,h);const spp=dur*sr/w,step=Math.max(1,Math.floor(spp/24));c.fillStyle='#3d5a80';
  for(let x=0;x<w;x++){const s0=Math.floor(x/w*dur*sr),s1=Math.floor(s0+spp);let m=0;for(let s=s0;s<s1&&s<ch.length;s+=step){const v=Math.abs(ch[s]);if(v>m)m=v}c.fillRect(x,h/2-m*h/2,1,Math.max(1,m*h))}
  c.fillStyle='#ff5d5d';for(const p of pts)c.fillRect(p.t/dur*w-1,0,2,h);
  c.strokeStyle='#fff';c.lineWidth=2;c.strokeRect(view.start/dur*w,1,view.span/dur*w,h-2);c.fillStyle='#fff';c.fillRect(playhead/dur*w,0,2,h)}

function ui(){
  $('undo').disabled=!past.length;$('redo').disabled=!future.length;draw();const L=$('list');L.innerHTML='';
  if(marks()){$('ah').innerHTML='<span>Markers</span><span>'+pts.length+' placed</span>';
    pts.forEach((p,i)=>{const r=document.createElement('div');r.className='row'+(i===sel?' now':'');r.innerHTML=`<span class=n>${i+1}</span><div><input value="${(p.label||'').replace(/"/g,'&quot;')}" placeholder="name (drop, stab, ...)"><small>${fmt(p.t)} · <a href=# class=del>delete</a></small></div>`;
      r.onclick=e=>{if(e.target.className==='del'){e.preventDefault();commit();pts.splice(i,1);sel=-1;ui();return}sel=i;seek(p.t);ui()};r.querySelector('input').onchange=e=>{commit();p.label=e.target.value;ui()};L.appendChild(r)});
    $('count').textContent='';return}
  const ps=pieces(),now=pieceAt(playhead),n=N();
  $('ah').innerHTML=`<span>The script (${n} lines)</span><span>${pts.length} / ${Math.max(0,n-1)} cuts</span>`;
  const rows=Math.max(n,ps.length);
  for(let i=0;i<rows;i++){const p=ps[i];const r=document.createElement('div');r.className='row'+(p?' ok':' miss')+(now&&now.i===i?' now':'');
    r.innerHTML=`<span class=n>${i+1}</span><span class=t>${lineText(i)}</span><small>${p?fmt(p.a)+' → '+fmt(p.b)+' ('+(p.b-p.a).toFixed(1)+' s)':'not cut yet'}</small>`;
    r.onclick=()=>{if(p){view.start=Math.max(0,p.a-.3);clampView();start(p.a,p.b)}};L.appendChild(r)}
  $('count').textContent=pts.length===Math.max(0,n-1)?'✓ all lines cut':(pts.length<n-1?`${n-1-pts.length} more cut(s) needed`:`${pts.length-(n-1)} cut(s) too many`);
  $('count').style.color=pts.length===Math.max(0,n-1)?'#58d68d':'var(--dim)';
}
function help(){ $('help').innerHTML=marks()?
 `<button class=x onclick="this.parentNode.remove()">✕</button><b>Mark the music.</b> Play it, and <b>click on the waveform where something happens</b> (the drop, a stab, a breakdown…) — a marker drops there${cfg.beats.length?', snapped to the beat grid (faint lines)':''}. Name each marker in the list on the right. Drag a marker to move it.`:
 `<button class=x onclick="this.parentNode.remove()">✕</button><b>Cut the recording into its lines.</b> This is one take with every line of the script read in a row. <b>Press <span class=k>Space</span> and listen; each time one line ends, click in the pause after it</b> (or press <span class=k>C</span> as it plays) — a red ✂ line appears. You do not need to be exact: anywhere inside the pause is fine, the speech is trimmed afterwards.<br>
 <span class=leg style="background:#58d68d33"></span><span class=leg style="background:#5aa9ff33"></span>= the piece for each script line (its text on top; the one you are hearing is orange, and lit in the list on the right) &nbsp; <span class=leg style="background:#ffffff22"></span>= <b>pause</b> (a break, no speech). Press <b>Suggest cuts</b> for a first guess, then fix by ear.`}

function seek(t){playhead=Math.max(0,Math.min(dur,t));if(playing)start(playhead,playEnd);draw()}
function stop(){if(src){src.onended=null;try{src.stop()}catch(e){}src=null}playing=false;$('play').textContent='▶ Play'}
function start(from,to=null){stop();ctx=ctx||new AudioContext();src=ctx.createBufferSource();src.buffer=buf;src.connect(ctx.destination);src.start(0,from);t0=ctx.currentTime;p0=from;playEnd=to;playing=true;$('play').textContent='❚❚ Pause';src.onended=()=>{stop()};requestAnimationFrame(tick)}
let lastPiece=-1;
function tick(){if(!playing)return;playhead=p0+(ctx.currentTime-t0);if(playEnd!==null&&playhead>=playEnd){stop();playhead=playEnd;ui();return}
  if(playhead>view.start+view.span*0.92||playhead<view.start){view.start=Math.max(0,Math.min(dur-view.span,playhead-view.span*0.1))}
  const p=pieceAt(playhead);if(!marks()&&p&&p.i!==lastPiece){lastPiece=p.i;ui()}else draw();requestAnimationFrame(tick)}
$('play').onclick=()=>playing?stop():start(playhead);
$('cutnow').onclick=()=>{if(marks()){commit();pts.push({t:playhead,label:cfg.labels[pts.length]||''});pts.sort((x,y)=>x.t-y.t);ui()}else addPt(playhead)};
$('zin').onclick=()=>zoom(.5);$('zout').onclick=()=>zoom(2);$('fit').onclick=()=>{view={start:0,span:dur};draw()};
wave.addEventListener('wheel',e=>{e.preventDefault();if(e.ctrlKey||e.metaKey){zoom(Math.exp(e.deltaY*.01),x2t(e.offsetX))}else{view.start+=(Math.abs(e.deltaX)>Math.abs(e.deltaY)?e.deltaX:e.deltaY)/W()*view.span;clampView();draw()}},{passive:false});
const hit=x=>{for(let i=pts.length-1;i>=0;i--)if(Math.abs(t2x(pts[i].t)-x)<7)return i;return -1};
wave.onpointerdown=e=>{wave.setPointerCapture(e.pointerId);const x=e.offsetX;if(e.offsetY<22){drag={kind:'seek'};seek(x2t(x));return}
  const h=hit(x);if(h>=0){sel=h;drag={kind:'move',i:h,snap:JSON.stringify(pts),moved:false};ui()}else drag={kind:'click',x0:x}};
wave.onpointermove=e=>{const x=e.offsetX;if(!drag){wave.style.cursor=hit(x)>=0?'ew-resize':'crosshair';return}
  if(drag.kind==='seek')seek(x2t(x));
  else if(drag.kind==='move'){if(!drag.moved){past.push(drag.snap);future=[];drag.moved=true}pts[drag.i].t=Math.max(.02,Math.min(dur-.02,snapT(x2t(x))));draw()}};
wave.onpointerup=e=>{if(!drag)return;const d=drag;drag=null;
  if(d.kind==='click'&&Math.abs(e.offsetX-d.x0)<4){const t=snapT(x2t(e.offsetX));seek(t);marks()?(commit(),pts.push({t,label:cfg.labels[pts.length]||''}),pts.sort((x,y)=>x.t-y.t),sel=pts.findIndex(p=>p.t===t),ui()):addPt(t)}
  else if(d.kind==='move'){const cur=pts[d.i];pts.sort((x,y)=>x.t-y.t);sel=pts.indexOf(cur);ui()}};
mini.onpointerdown=e=>{const mv=ev=>{view.start=ev.offsetX/mini.clientWidth*dur-view.span/2;clampView();draw()};mini.setPointerCapture(e.pointerId);mv(e);mini.onpointermove=mv;mini.onpointerup=()=>{mini.onpointermove=null}};
addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;const k=e.key.toLowerCase();
  if(e.code==='Space'){e.preventDefault();$('play').click()}
  else if((e.metaKey||e.ctrlKey)&&k==='z'){e.preventDefault();(e.shiftKey?$('redo'):$('undo')).click()}
  else if((e.metaKey||e.ctrlKey)&&k==='y'){e.preventDefault();$('redo').click()}
  else if(k==='c'||k==='m'||k==='x'){$('cutnow').click()}
  else if(e.key==='Delete'||e.key==='Backspace'){if(sel>=0){commit();pts.splice(sel,1);sel=-1;ui()}}
  else if(e.key==='='||e.key==='+')zoom(.5);else if(e.key==='-')zoom(2);
  else if(e.key==='ArrowLeft'){e.preventDefault();sel>=0&&e.altKey?(commit(),pts[sel].t-=.02,ui()):seek(playhead-(e.shiftKey?1:.1))}
  else if(e.key==='ArrowRight'){e.preventDefault();sel>=0&&e.altKey?(commit(),pts[sel].t+=.02,ui()):seek(playhead+(e.shiftKey?1:.1))}});
addEventListener('resize',draw);

function analyse(){const f=Math.floor(sr*.01),n=Math.floor(ch.length/f),env=new Float32Array(n);let mx=0;for(let i=0;i<n;i++){let s=0;for(let j=0;j<f;j++){const v=ch[i*f+j];s+=v*v}env[i]=Math.sqrt(s/f);if(env[i]>mx)mx=env[i]}
  const th=mx*Math.pow(10,-38/20);let segs=[],st=null;for(let i=0;i<n;i++){const on=env[i]>th;if(on&&st===null)st=i;if(!on&&st!==null){segs.push([st,i]);st=null}}if(st!==null)segs.push([st,n]);
  const m=[];for(const s of segs){if(m.length&&s[0]-m[m.length-1][1]<15)m[m.length-1][1]=s[1];else m.push(s)}
  speech=m.map(s=>[s[0]/100,s[1]/100]);return speech}
$('auto').onclick=()=>{let m=speech.map(s=>[...s]);const n=N();if(n)while(m.length>n){let k=0,g=1e9;for(let i=0;i<m.length-1;i++){const d=m[i+1][0]-m[i][1];if(d<g){g=d;k=i}}m[k][1]=m[k+1][1];m.splice(k+1,1)}
  commit();pts=m.slice(0,-1).map((s,i)=>({t:(s[1]+m[i+1][0])/2,label:''}));sel=-1;ui()}; // a cut in the middle of each pause
$('done').onclick=async()=>{const n=N();if(!marks()&&n&&pts.length!==n-1&&!confirm(`You have ${pts.length+1} pieces but the script has ${n} lines. Save anyway?`))return;
  const ps=pieces();await fetch('/done',{method:'POST',body:JSON.stringify({file:cfg.file,duration:dur,mode:cfg.mode,cuts:pts.map(p=>+p.t.toFixed(3)),
    items:marks()?pts.map((p,i)=>({n:i+1,start:+p.t.toFixed(3),end:+p.t.toFixed(3),label:p.label||'',text:''})):ps.map(p=>({n:p.i+1,start:+p.a.toFixed(3),end:+p.b.toFixed(3),label:'',text:cfg.script[p.i]||''}))})});
  stop();$('msg').style.display='flex';setTimeout(()=>close(),600)};
$('cancel').onclick=async()=>{await fetch('/cancel',{method:'POST',body:'{}'});$('msg').textContent='Cancelled. You can close this tab.';$('msg').style.display='flex';setTimeout(()=>close(),600)};

(async()=>{cfg=await (await fetch('/config')).json();$('title').textContent=cfg.file;
  $('snaplab').style.display=cfg.beats.length?'flex':'none';$('auto').style.display=marks()?'none':'';help();
  const data=await (await fetch('/audio')).arrayBuffer();buf=await new AudioContext().decodeAudioData(data);dur=buf.duration;sr=buf.sampleRate;
  if(buf.numberOfChannels>1){const m=new Float32Array(buf.length),a=buf.getChannelData(0),b=buf.getChannelData(1);for(let i=0;i<m.length;i++)m[i]=(a[i]+b[i])/2;ch=m}else ch=buf.getChannelData(0);
  analyse();view={start:0,span:Math.min(dur,marks()?Math.max(20,dur/3):Math.min(dur,14))};
  pts=(cfg.init||[]).map(i=>({t:i.start,label:i.label||''})).filter(p=>marks()||p.t>0);ui()})();
</script>"""


def main():
    global server
    server = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"cut_ui: open {url}  (editing {audio.name}, mode {a.mode})", flush=True)
    if not a.no_open: webbrowser.open(url)
    done.wait()
    import time
    time.sleep(0.4)  # let the browser receive the reply
    server.shutdown()
    if result["status"] == "done":
        n = len(json.load(open(a.out))["items"]); print(f"cut_ui: DONE, {n} items -> {a.out}"); raise SystemExit(0)
    print("cut_ui: cancelled"); raise SystemExit(2)



main()
