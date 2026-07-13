"""Self-contained chat web page served at `/` by the backend.

Opening the Railway URL now shows a real, usable chat UI (no second deploy,
no CORS — same origin). Bilingual (中/EN). The API key is entered once by the
user and stored in their browser's localStorage — it is NOT baked into this
served HTML, so the page is safe to serve publicly.
"""

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
<title>Sunday</title>
<style>
  :root{
    --bg:#0B0B0C; --surface:#151518; --surface2:#1b1b1f;
    --border:rgba(255,255,255,.08); --border2:rgba(255,255,255,.14);
    --text:#F5F5F7; --sec:rgba(245,245,247,.62); --ter:rgba(245,245,247,.38);
    --accent:#0A84FF; --success:#30D158; --danger:#FF453A;
    --font:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{background:var(--bg);color:var(--text);font-family:var(--font);
    -webkit-font-smoothing:antialiased;display:flex;flex-direction:column;height:100dvh}
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
    background:radial-gradient(1100px 600px at 78% -8%,rgba(10,132,255,.10),transparent 60%),
      radial-gradient(900px 500px at 8% 108%,rgba(48,209,88,.05),transparent 55%)}
  header{position:relative;z-index:1;display:flex;align-items:center;gap:12px;
    padding:14px 18px;border-bottom:1px solid var(--border);
    background:rgba(21,21,24,.6);backdrop-filter:blur(24px)}
  .mark{width:34px;height:34px;border-radius:11px;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#0a84ff,#5e5ce6,#30d158);position:relative;flex:0 0 auto}
  .mark span{position:absolute;inset:2px;border-radius:9px;background:var(--surface);
    display:flex;align-items:center;justify-content:center;font-size:16px}
  .htxt b{font-size:15px;font-weight:600;letter-spacing:-.01em}
  .htxt div{font-size:12px;color:var(--ter)}
  .spacer{flex:1}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--ter)}
  .dot.on{background:var(--success)} .dot.off{background:var(--danger)}
  .conn{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ter)}
  button.ghost{background:none;border:1px solid var(--border);color:var(--sec);
    border-radius:999px;padding:6px 12px;font-size:12px;cursor:pointer;transition:.2s}
  button.ghost:hover{border-color:var(--border2);color:var(--text)}
  main{position:relative;z-index:1;flex:1;overflow-y:auto;padding:20px 16px}
  .wrap{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
  .empty{text-align:center;color:var(--sec);margin-top:18vh}
  .empty .big{width:56px;height:56px;border-radius:16px;border:1px solid var(--border);
    display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;color:var(--accent)}
  .empty h2{font-size:22px;color:var(--text);font-weight:600}
  .empty p{margin-top:8px;font-size:14px}
  .row{display:flex;gap:10px}
  .row.me{justify-content:flex-end}
  .av{width:28px;height:28px;border-radius:50%;flex:0 0 auto;margin-top:2px;
    background:linear-gradient(135deg,#0a84ff,#5e5ce6);display:flex;align-items:center;justify-content:center;font-size:14px}
  .bubble{max-width:80%;padding:10px 14px;border-radius:18px;font-size:15px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
  .me .bubble{background:var(--accent);color:#fff}
  .ai .bubble{background:var(--surface);border:1px solid var(--border)}
  .meta{font-size:11px;color:var(--ter);margin-top:4px;padding:0 4px;display:flex;gap:8px;align-items:center}
  .tag{border:1px solid var(--border);border-radius:999px;padding:1px 7px}
  .err .bubble{border-color:rgba(255,69,58,.4);background:rgba(255,69,58,.08)}
  footer{position:relative;z-index:1;padding:12px 16px 20px;border-top:1px solid var(--border);
    background:rgba(21,21,24,.6);backdrop-filter:blur(24px)}
  .composer{max-width:760px;margin:0 auto;display:flex;gap:8px;align-items:flex-end;
    border:1px solid var(--border);background:var(--surface);border-radius:20px;padding:8px 8px 8px 16px;transition:.2s}
  .composer:focus-within{border-color:var(--border2)}
  textarea{flex:1;background:none;border:none;outline:none;color:var(--text);font-family:var(--font);
    font-size:15px;resize:none;max-height:160px;line-height:1.5;padding:6px 0}
  .send{width:36px;height:36px;border-radius:50%;border:none;flex:0 0 auto;cursor:pointer;
    background:var(--surface2);color:var(--ter);font-size:16px;transition:.2s;display:flex;align-items:center;justify-content:center}
  .send.on{background:var(--accent);color:#fff}
  .typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--ter);margin:0 2px;animation:b 1s infinite}
  .typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}
  @keyframes b{0%,100%{opacity:.3}50%{opacity:1}}
  @media (max-width:520px){.bubble{max-width:88%}}
</style>
</head>
<body>
<header>
  <div class="mark"><span>☀️</span></div>
  <div class="htxt"><b>Sunday</b><div id="subtitle">一个心智，服务你的一切</div></div>
  <div class="spacer"></div>
  <div class="conn"><span class="dot" id="dot"></span><span id="conntxt">…</span></div>
  <button class="ghost" id="langBtn">EN</button>
  <button class="ghost" id="keyBtn">🔑</button>
  <button class="ghost" id="newBtn">＋</button>
</header>
<main id="main"><div class="wrap" id="wrap"></div></main>
<footer>
  <div class="composer">
    <textarea id="input" rows="1" placeholder="对 Sunday 说点什么…"></textarea>
    <button class="send" id="send">↑</button>
  </div>
</footer>
<script>
const T = {
  zh:{subtitle:"一个心智，服务你的一切",placeholder:"对 Sunday 说点什么…",
    on:"已连接",off:"连不上后端",empty_h:"开始和 Sunday 聊天",
    empty_p:"问它任何事——写代码、记事、规划、或只是聊聊。",
    thinking:"Sunday 正在思考…",errNet:"连不上服务，请稍后再试。",
    err401:"密码不对。点右上角 🔑 重新输入 API Key。",
    askKey:"请输入你的 API Key（就是 Railway 里设的 SUNDAY_API_KEY）：",
    fast:"快思考",deep:"慢思考",lang:"EN"},
  en:{subtitle:"One mind for every task",placeholder:"Say something to Sunday…",
    on:"Connected",off:"Backend offline",empty_h:"Start a conversation",
    empty_p:"Ask anything — code, notes, plans, or just chat.",
    thinking:"Sunday is thinking…",errNet:"Can't reach the service. Try again.",
    err401:"Wrong key. Click 🔑 to re-enter your API Key.",
    askKey:"Enter your API Key (the SUNDAY_API_KEY you set on Railway):",
    fast:"fast",deep:"deep",lang:"中"}
};
let lang = localStorage.getItem("sunday.lang") || "zh";
let apiKey = localStorage.getItem("sunday.key") || "";
const $ = id => document.getElementById(id);
const wrap=$("wrap"), main=$("main"), input=$("input"), sendBtn=$("send");

function t(k){return T[lang][k]}
function applyLang(){
  document.documentElement.lang=lang;
  $("subtitle").textContent=t("subtitle");
  input.placeholder=t("placeholder");
  $("langBtn").textContent=t("lang");
  if(!wrap.children.length||wrap.querySelector(".empty")) renderEmpty();
}
function renderEmpty(){
  wrap.innerHTML=`<div class="empty"><div class="big">☀️</div><h2>${t("empty_h")}</h2><p>${t("empty_p")}</p></div>`;
}
function ensureKey(force){
  if(force||!apiKey){
    const v=prompt(t("askKey"), apiKey||"");
    if(v!==null){apiKey=v.trim();localStorage.setItem("sunday.key",apiKey);}
  }
  return apiKey;
}
function addMsg(role,text,meta){
  if(wrap.querySelector(".empty")) wrap.innerHTML="";
  const row=document.createElement("div");
  row.className="row "+(role==="me"?"me":role==="err"?"ai err":"ai");
  const inner = role==="me"
    ? `<div><div class="bubble"></div></div>`
    : `<div class="av">☀️</div><div><div class="bubble"></div>${meta?`<div class="meta">${meta}</div>`:""}</div>`;
  row.innerHTML=inner;
  row.querySelector(".bubble").textContent=text;
  wrap.appendChild(row);
  main.scrollTop=main.scrollHeight;
  return row;
}
async function ping(){
  try{
    const r=await fetch("/health"); const d=await r.json();
    const ok=r.ok && (d.engines||[]).length>0;
    $("dot").className="dot "+(ok?"on":"off");
    $("conntxt").textContent=ok?t("on"):t("off");
  }catch(e){$("dot").className="dot off";$("conntxt").textContent=t("off");}
}
let sending=false;
async function send(){
  const text=input.value.trim(); if(!text||sending) return;
  if(!ensureKey()) return;
  addMsg("me",text); input.value=""; input.style.height="auto";
  sending=true; sendBtn.classList.remove("on");
  const typing=addMsg("ai","");
  typing.querySelector(".bubble").innerHTML='<span class="typing"><span></span><span></span><span></span></span>';
  try{
    const r=await fetch("/api/chat",{method:"POST",
      headers:{"Content-Type":"application/json","X-API-Key":apiKey},
      body:JSON.stringify({message:text,user_id:"web"})});
    typing.remove();
    if(r.status===401){addMsg("err",t("err401"));return;}
    const d=await r.json();
    const sysTag = d.system? `<span class="tag">${d.system==="reasoner"?t("deep"):t("fast")}</span>`:"";
    const eng = d.engine? `${d.engine} `:"";
    addMsg("ai", d.reply||t("errNet"), eng+sysTag);
  }catch(e){ typing.remove(); addMsg("err",t("errNet")); }
  finally{ sending=false; }
}
input.addEventListener("input",()=>{input.style.height="auto";input.style.height=Math.min(input.scrollHeight,160)+"px";sendBtn.classList.toggle("on",!!input.value.trim());});
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}});
sendBtn.addEventListener("click",send);
$("langBtn").addEventListener("click",()=>{lang=lang==="zh"?"en":"zh";localStorage.setItem("sunday.lang",lang);applyLang();});
$("keyBtn").addEventListener("click",()=>ensureKey(true));
$("newBtn").addEventListener("click",()=>{renderEmpty();});
applyLang(); renderEmpty(); ping(); setInterval(ping,8000);
if(!apiKey) setTimeout(()=>ensureKey(true),400);
</script>
</body>
</html>"""
