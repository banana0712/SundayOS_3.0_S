"""Self-contained chat web page served at `/` by the backend.

Dual-column layout: conversation history sidebar + chat area.
Bilingual (中/EN) with browser language detection.
API key is stored in browser localStorage — never baked into the HTML.
"""
from __future__ import annotations

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
    --accent:#0A84FF; --success:#30D158; --warning:#FFD60A; --danger:#FF453A;
    --font:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
    --sidebar-w: 268px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{background:var(--bg);color:var(--text);font-family:var(--font);
    -webkit-font-smoothing:antialiased;display:flex;height:100dvh;overflow:hidden}
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
    background:radial-gradient(1100px 600px at 78% -8%,rgba(10,132,255,.09),transparent 60%),
      radial-gradient(900px 500px at 8% 108%,rgba(48,209,88,.05),transparent 55%)}

  /* ── sidebar ─────────────────────────────── */
  #sidebar{position:relative;z-index:2;width:var(--sidebar-w);flex-shrink:0;
    display:flex;flex-direction:column;border-right:1px solid var(--border);
    background:rgba(21,21,24,.5);backdrop-filter:blur(24px);transition:margin .25s cubic-bezier(.22,1,.36,1)}
  #sidebar.collapsed{margin-left:calc(-1*var(--sidebar-w))}
  .sb-header{display:flex;align-items:center;gap:8px;padding:14px 14px 10px}
  .sb-header .new-btn{flex:1;display:flex;align-items:center;gap:6px;
    border:1px solid var(--border2);border-radius:10px;padding:8px 12px;
    background:var(--surface);color:var(--text);font-size:13px;font-family:var(--font);
    cursor:pointer;transition:.2s}
  .sb-header .new-btn:hover{border-color:var(--accent);color:var(--accent)}
  .sb-header .collapse-btn{width:30px;height:30px;border-radius:8px;border:1px solid var(--border);
    background:var(--surface);color:var(--ter);cursor:pointer;font-size:15px;display:flex;
    align-items:center;justify-content:center;transition:.2s}
  .sb-header .collapse-btn:hover{color:var(--text);border-color:var(--border2)}
  #conv-list{flex:1;overflow-y:auto;padding:4px 10px}
  .conv-item{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:10px;
    cursor:pointer;transition:.15s;margin-bottom:2px;position:relative}
  .conv-item:hover{background:var(--surface2)}
  .conv-item.active{background:var(--surface2);border:1px solid var(--border)}
  .conv-item .c-info{flex:1;min-width:0}
  .conv-item .c-title{font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .conv-item .c-meta{font-size:11px;color:var(--ter);margin-top:2px}
  .conv-item .c-del{opacity:0;width:24px;height:24px;border-radius:6px;border:none;
    background:transparent;color:var(--danger);cursor:pointer;font-size:13px;
    transition:.15s;flex-shrink:0}
  .conv-item:hover .c-del{opacity:1}
  .conv-item .c-del:hover{background:rgba(255,69,58,.15)}
  .sb-empty{text-align:center;color:var(--ter);font-size:12px;padding:24px 16px}

  /* ── main chat ───────────────────────────── */
  #main-col{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;min-width:0}
  header{display:flex;align-items:center;gap:12px;padding:10px 18px;
    border-bottom:1px solid var(--border);flex-shrink:0;
    background:rgba(21,21,24,.6);backdrop-filter:blur(24px)}
  .mark{width:34px;height:34px;border-radius:11px;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#0a84ff,#5e5ce6,#30d158);position:relative;flex-shrink:0}
  .mark span{position:absolute;inset:2px;border-radius:9px;background:var(--surface);
    display:flex;align-items:center;justify-content:center;font-size:16px}
  .htxt b{font-size:15px;font-weight:600;letter-spacing:-.01em}
  .htxt div{font-size:12px;color:var(--ter)}
  .spacer{flex:1}
  .hbtn{background:none;border:1px solid var(--border);color:var(--sec);
    border-radius:999px;padding:5px 10px;font-size:12px;cursor:pointer;transition:.2s;font-family:var(--font)}
  .hbtn:hover{border-color:var(--border2);color:var(--text)}
  .hbtn.on{background:var(--accent);border-color:var(--accent);color:#fff}
  .lang-group{display:flex;gap:0;border-radius:999px;overflow:hidden;border:1px solid var(--border)}
  .lang-group button{border:none;border-radius:0;padding:5px 9px;font-size:12px;cursor:pointer;
    background:transparent;color:var(--ter);font-family:var(--font);transition:.15s}
  .lang-group button:first-child{border-right:1px solid var(--border)}
  .lang-group button.on{background:var(--surface2);color:var(--text);font-weight:600}
  .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
  .dot.on{background:var(--success)} .dot.off{background:var(--danger)}
  .conn{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ter)}
  main{flex:1;overflow-y:auto;padding:20px 16px}
  .wrap{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
  .empty{text-align:center;color:var(--sec);margin-top:18vh}
  .empty .big{width:56px;height:56px;border-radius:16px;border:1px solid var(--border);
    display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;color:var(--accent)}
  .empty h2{font-size:22px;color:var(--text);font-weight:600}
  .empty p{margin-top:8px;font-size:14px}
  .row{display:flex;gap:10px}
  .row.me{justify-content:flex-end}
  .av{width:28px;height:28px;border-radius:50%;flex-shrink:0;margin-top:2px;
    background:linear-gradient(135deg,#0a84ff,#5e5ce6);display:flex;align-items:center;justify-content:center;font-size:14px}
  .bubble{max-width:80%;padding:10px 14px;border-radius:18px;font-size:15px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
  .me .bubble{background:var(--accent);color:#fff}
  .ai .bubble{background:var(--surface);border:1px solid var(--border)}
  .meta{font-size:11px;color:var(--ter);margin-top:4px;padding:0 4px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .tag{border:1px solid var(--border);border-radius:999px;padding:1px 7px}
  .tag.err{border-color:rgba(255,69,58,.4);color:var(--danger)}
  .err-detail{font-size:10px;color:var(--ter);margin-top:2px;padding:0 4px;max-width:80%}
  footer{position:relative;z-index:1;padding:12px 16px 20px;border-top:1px solid var(--border);flex-shrink:0;
    background:rgba(21,21,24,.6);backdrop-filter:blur(24px)}
  .composer{max-width:760px;margin:0 auto;display:flex;gap:8px;align-items:flex-end;
    border:1px solid var(--border);background:var(--surface);border-radius:20px;padding:8px 8px 8px 16px;transition:.2s}
  .composer:focus-within{border-color:var(--border2)}
  textarea{flex:1;background:none;border:none;outline:none;color:var(--text);font-family:var(--font);
    font-size:15px;resize:none;max-height:160px;line-height:1.5;padding:6px 0}
  .send{width:36px;height:36px;border-radius:50%;border:none;flex-shrink:0;cursor:pointer;
    background:var(--surface2);color:var(--ter);font-size:16px;transition:.2s;display:flex;align-items:center;justify-content:center}
  .send.on{background:var(--accent);color:#fff}
  .typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--ter);margin:0 2px;animation:b 1s infinite}
  .typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}
  @keyframes b{0%,100%{opacity:.3}50%{opacity:1}}
  .status-bar{display:flex;align-items:center;gap:12px;max-width:760px;margin:0 auto 6px;font-size:10px;color:var(--ter)}
  .status-bar span{display:flex;align-items:center;gap:3px}

  /* ── console / dashboard ──────────────────── */
  .dash-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;padding:16px}
  .dash-card{border:1px solid var(--border);border-radius:14px;padding:16px;background:var(--surface);transition:.2s}
  .dash-card:hover{border-color:var(--border2)}
  .dash-card .d-val{font-size:28px;font-weight:600;letter-spacing:-.01em;margin-top:4px}
  .dash-card .d-label{font-size:11px;color:var(--ter);text-transform:uppercase;letter-spacing:.08em}
  .dash-card .d-sub{font-size:10px;color:var(--ter);margin-top:4px}
  .dash-section{margin:8px 16px}
  .dash-section h3{font-size:13px;font-weight:600;color:var(--sec);margin-bottom:8px}
  .dash-table{width:100%;font-size:12px;border-collapse:collapse}
  .dash-table th,.dash-table td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--border)}
  .dash-table th{font-size:10px;color:var(--ter);text-transform:uppercase}
  .dash-table td{color:var(--text)}
  .dash-badge{padding:2px 8px;border-radius:999px;font-size:10px}
  .dash-badge.ok{background:rgba(48,209,88,.15);color:var(--success)}
  .dash-badge.warn{background:rgba(255,214,10,.15);color:var(--warning)}
  .dash-badge.err{background:rgba(255,69,58,.15);color:var(--danger)}
  .dash-badge.info{background:rgba(10,132,255,.15);color:var(--accent)}

  /* ── responsive ──────────────────────────── */
  @media (max-width:640px){
    #sidebar{position:fixed;left:0;top:0;bottom:0;z-index:10;box-shadow:0 0 40px rgba(0,0,0,.5)}
    #sidebar.collapsed{display:none}
    .bubble{max-width:90%}
  }
</style>
</head>
<body>
<!-- ── Sidebar ───────────────────────────────── -->
<div id="sidebar">
  <div class="sb-header">
    <button class="new-btn" id="newConvBtn">＋ <span id="newConvLabel">新对话</span></button>
    <button class="collapse-btn" id="collapseBtn" title="折叠侧栏">☰</button>
  </div>
  <div id="conv-list"></div>
</div>

<!-- ── Main chat ─────────────────────────────── -->
<div id="main-col">
<header>
  <button class="collapse-btn" id="expandBtn" title="展开侧栏" style="display:none">☰</button>
  <div class="mark"><span>☀️</span></div>
  <div class="htxt"><b>Sunday</b><div id="subtitle">一个心智，服务你的一切</div></div>
  <div class="spacer"></div>
  <div class="lang-group">
    <button id="langZh" onclick="setLang('zh')">中文</button>
    <button id="langEn" onclick="setLang('en')">EN</button>
  </div>
  <button class="hbtn" id="consoleBtn" onclick="toggleConsole()">📊</button>
  <div class="conn"><span class="dot" id="dot"></span><span id="conntxt">…</span></div>
  <button class="hbtn" id="keyBtn">🔑</button>
</header>
<main id="main">
  <div class="wrap" id="wrap"></div>
  <div id="consoleView" style="display:none"></div>
</main>
<footer id="chatFooter">
  <div class="status-bar" id="statusBar"></div>
  <div class="composer">
    <textarea id="input" rows="1" placeholder="对 Sunday 说点什么…"></textarea>
    <button class="send" id="send">↑</button>
  </div>
</footer>
</div>

<script>
// ── i18n ───────────────────────────────────────
const T = {
  zh:{subtitle:"一个心智，服务你的一切",placeholder:"对 Sunday 说点什么…",
    on:"已连接",off:"连不上后端",empty_h:"开始和 Sunday 聊天",
    empty_p:"问它任何事——写代码、记事、规划、或只是聊聊。",
    thinking:"Sunday 正在思考…",errNet:"连不上服务，请稍后再试。",
    err401:"密码不对。点右上角 🔑 重新输入 API Key。",
    askKey:"请输入你的 API Key（SUNDAY_API_KEY）：",
    fast:"快思考",deep:"慢思考",newConv:"新对话",noConv:"暂无对话",
    engines:"引擎",memories:"记忆",convs:"会话",
    errEngine:"引擎调用失败"},
  en:{subtitle:"One mind for every task",placeholder:"Say something to Sunday…",
    on:"Connected",off:"Backend offline",empty_h:"Start a conversation",
    empty_p:"Ask anything — code, notes, plans, or just chat.",
    thinking:"Sunday is thinking…",errNet:"Can't reach the service. Try again.",
    err401:"Wrong key. Click 🔑 to re-enter your API Key.",
    askKey:"Enter your API Key (SUNDAY_API_KEY):",
    fast:"fast",deep:"deep",newConv:"New Chat",noConv:"No conversations",
    engines:"Engines",memories:"Memories",convs:"Chats",
    errEngine:"Engine Error"}
};

// ── state ──────────────────────────────────────
let lang = localStorage.getItem("sunday.lang") ||
  (navigator.language.startsWith("zh") ? "zh" : "en");
let apiKey = localStorage.getItem("sunday.key") || "";
let convId = null;          // current conversation id
let convList = [];          // cached conversation list
let sidebarOpen = true;

const $ = id => document.getElementById(id);
const wrap=$("wrap"), main=$("main"), input=$("input"), sendBtn=$("send");

function t(k){return T[lang][k]}
function fmtTime(iso){const d=new Date(iso);const now=new Date();const diff=now-d;
  if(diff<6e4)return "刚刚";if(diff<36e5)return Math.floor(diff/6e4)+"分钟前";
  if(diff<864e5)return Math.floor(diff/36e5)+"小时前";
  return d.toLocaleDateString(lang==="zh"?"zh-CN":"en-US",{month:"short",day:"numeric"})}

// ── lang ───────────────────────────────────────
function setLang(l){
  lang=l;localStorage.setItem("sunday.lang",l);applyLang();refreshConvList();}
function applyLang(){
  document.documentElement.lang=lang;
  $("subtitle").textContent=t("subtitle");
  input.placeholder=t("placeholder");
  $("newConvLabel").textContent=t("newConv");
  $("langZh").className=lang==="zh"?"on":"";
  $("langEn").className=lang==="en"?"on":"";
  if(!wrap.children.length||wrap.querySelector(".empty")) renderEmpty();
  updateStatusBar();
}
$("langZh").className=lang==="zh"?"on":"";
$("langEn").className=lang==="en"?"on":"";

function renderEmpty(){
  wrap.innerHTML=`<div class="empty"><div class="big">☀️</div><h2>${t("empty_h")}</h2><p>${t("empty_p")}</p></div>`;
}

// ── key ────────────────────────────────────────
function ensureKey(force){
  if(force||!apiKey){const v=prompt(t("askKey"),apiKey||"");if(v!==null){apiKey=v.trim();localStorage.setItem("sunday.key",apiKey);}}
  return apiKey;}

// ── sidebar ────────────────────────────────────
function toggleSidebar(){
  sidebarOpen=!sidebarOpen;
  $("sidebar").className=sidebarOpen?"":"collapsed";
  $("expandBtn").style.display=sidebarOpen?"none":"";
}
$("collapseBtn").onclick=toggleSidebar;
$("expandBtn").onclick=toggleSidebar;

async function refreshConvList(){
  if(!apiKey){$("conv-list").innerHTML=`<div class="sb-empty">${t("noConv")}</div>`;return}
  try{
    const r=await fetch("/api/conversations?user_id=web",{headers:{"X-API-Key":apiKey}});
    if(!r.ok){convList=[];renderConvList();return}
    const d=await r.json();convList=d.conversations||[];renderConvList();
  }catch(e){convList=[];renderConvList()}
}

function renderConvList(){
  const el=$("conv-list");
  if(!convList.length){el.innerHTML=`<div class="sb-empty">${t("noConv")}</div>`;return}
  el.innerHTML=convList.map(c=>`
    <div class="conv-item${c.id===convId?' active':''}" data-cid="${c.id}" onclick="selectConv('${c.id}')">
      <div class="c-info">
        <div class="c-title">${esc(c.title)}</div>
        <div class="c-meta">${c.message_count||0} 条 · ${fmtTime(c.updated_at)}</div>
      </div>
      <button class="c-del" onclick="event.stopPropagation();deleteConv('${c.id}')" title="删除">✕</button>
    </div>
  `).join("")
}

function esc(s){const d=document.createElement("div");d.textContent=s;return d.innerHTML}

async function selectConv(id){
  if(!apiKey)return;
  convId=id;wrap.innerHTML="";renderEmpty();
  try{
    const r=await fetch("/api/conversations/"+id,{headers:{"X-API-Key":apiKey}});
    if(!r.ok)return;
    const d=await r.json();
    wrap.innerHTML="";
    (d.messages||[]).forEach(m=>{
      const role=m.role==="user"?"me":"ai";
      const meta=m.role==="assistant"?buildMeta(m.engine,m.system,m.trace):"";
      addMsg(role,m.content,meta,hasError(m.trace));
    });
  }catch(e){}
  renderConvList()
}

function hasError(trace){return trace&&trace.errors&&Object.keys(trace.errors).length>0}
function buildMeta(engine,system,trace){
  let s="";
  if(engine)s+=engine+" ";
  if(system){const tag=system==="reasoner"?t("deep"):t("fast");s+=`<span class="tag">${tag}</span> `}
  if(hasError(trace))s+=`<span class="tag err">⚠ ${t("errEngine")}</span>`;
  return s}

async function newConversation(){
  convId=null;wrap.innerHTML="";renderEmpty();renderConvList();input.focus()}
$("newConvBtn").onclick=newConversation;

async function deleteConv(id){
  if(!confirm("删除这条对话？"))return;
  try{
    await fetch("/api/conversations/"+id,{method:"DELETE",headers:{"X-API-Key":apiKey}});
    if(convId===id){convId=null;wrap.innerHTML="";renderEmpty()}
    await refreshConvList();
  }catch(e){}
}

// ── messages ───────────────────────────────────
function addMsg(role,text,meta,isErr){
  if(wrap.querySelector(".empty"))wrap.innerHTML="";
  const row=document.createElement("div");
  row.className="row "+(role==="me"?"me":(isErr?"ai err":"ai"));
  const inner=role==="me"
    ?`<div><div class="bubble"></div></div>`
    :`<div class="av">☀️</div><div><div class="bubble"></div>${meta?`<div class="meta">${meta}</div>`:""}</div>`;
  row.innerHTML=inner;
  row.querySelector(".bubble").textContent=text;
  if(isErr){
    const errDiv=document.createElement("div");
    errDiv.className="err-detail";errDiv.textContent="⚠ "+t("errEngine");
    row.querySelector(".meta")?.after(errDiv)}
  wrap.appendChild(row);
  main.scrollTop=main.scrollHeight;
  return row}

// ── chat ───────────────────────────────────────
let sending=false;
async function send(){
  const text=input.value.trim();if(!text||sending)return;
  if(!ensureKey())return;
  addMsg("me",text);input.value="";input.style.height="auto";
  sending=true;sendBtn.classList.remove("on");
  const typing=addMsg("ai","");
  typing.querySelector(".bubble").innerHTML='<span class="typing"><span></span><span></span><span></span></span>';
  try{
    const body={message:text,user_id:"web"};
    if(convId)body.conversation_id=convId;
    const r=await fetch("/api/chat",{method:"POST",
      headers:{"Content-Type":"application/json","X-API-Key":apiKey},
      body:JSON.stringify(body)});
    typing.remove();
    if(r.status===401){addMsg("ai",t("err401"),"",true);return}
    const d=await r.json();
    // remember conversation id
    if(d.conversation_id&&!convId){convId=d.conversation_id}
    const sysTag=d.system?`<span class="tag">${d.system==="reasoner"?t("deep"):t("fast")}</span>`:"";
    const eng=d.engine?d.engine+" ":"";
    const hasErr=d.trace&&d.trace.errors&&Object.keys(d.trace.errors).length>0;
    const errTag=hasErr?`<span class="tag err">⚠ ${t("errEngine")}</span>`:"";
    addMsg("ai",d.reply||t("errNet"),eng+sysTag+errTag,hasErr);
    if(hasErr&&d.trace&&d.trace.errors){
      // render per-engine error
      const row=wrap.lastElementChild;
      const errs=Object.entries(d.trace.errors).map(([eid,msg])=>`${eid}: ${msg}`).join(" · ");
      const errDiv=document.createElement("div");
      errDiv.className="err-detail";errDiv.textContent=errs;
      row.appendChild(errDiv)}
    // refresh sidebar
    if(convId)await refreshConvList();
  }catch(e){typing.remove();addMsg("ai",t("errNet"),"",true)}
  finally{sending=false}
}

// ── health / status ────────────────────────────
async function ping(){
  try{
    const r=await fetch("/health");const d=await r.json();
    const ok=r.ok&&(d.engines||[]).length>0;
    $("dot").className="dot "+(ok?"on":"off");
    $("conntxt").textContent=ok?t("on"):t("off");
    updateStatusBar(d);
  }catch(e){$("dot").className="dot off";$("conntxt").textContent=t("off")}
}

function updateStatusBar(d){
  if(!d){$("statusBar").innerHTML="";return}
  const engCount=(d.engines||[]).length;
  const memCount=d.memory_nodes||0;
  const convCount=d.conversation_count||0;
  $("statusBar").innerHTML=
    `<span>⚙ ${t("engines")}: ${engCount}</span>`+
    `<span>🧠 ${t("memories")}: ${memCount}</span>`+
    `<span>💬 ${t("convs")}: ${convCount}</span>`;
  // also refresh console view if visible
  if(consoleMode) refreshConsole();
}

// ── console / dashboard toggle ──────────────────
let consoleMode = false;
let healthCache = null;

function toggleConsole(){
  consoleMode = !consoleMode;
  $("consoleBtn").className = "hbtn" + (consoleMode ? " on" : "");
  $("wrap").style.display = consoleMode ? "none" : "";
  $("chatFooter").style.display = consoleMode ? "none" : "";
  $("consoleView").style.display = consoleMode ? "" : "none";
  $("subtitle").textContent = consoleMode ? "Console" : t("subtitle");
  if(consoleMode) refreshConsole();
}

async function refreshConsole(){
  try{
    const r = await fetch("/health");
    healthCache = await r.json();
  }catch(e){ healthCache = null }
  const engR = await fetch("/api/engines").then(r=>r.json()).catch(()=>({engines:[]}));
  const d = healthCache || {};

  const engCount = (d.engines||[]).length;
  const memCount = d.memory_nodes||0;
  const convCount = d.conversation_count||0;
  const engNames = (d.engines||[]).join(", ");

  // count status
  const isMock = engNames.includes("mock");
  const statusColor = isMock ? "warn" : "ok";
  const statusLabel = isMock ? "Mock Mode" : "Live";

  $("consoleView").innerHTML = `
    <div class="dash-grid">
      <div class="dash-card">
        <div class="d-label">${t("engines")}</div>
        <div class="d-val" style="color:var(--accent)">${engCount}</div>
        <div class="d-sub"><span class="dash-badge ${statusColor}">${statusLabel}</span> ${engNames}</div>
      </div>
      <div class="dash-card">
        <div class="d-label">${t("memories")}</div>
        <div class="d-val" style="color:#64d2ff">${memCount}</div>
        <div class="d-sub">会话内记忆条数</div>
      </div>
      <div class="dash-card">
        <div class="d-label">${t("convs")}</div>
        <div class="d-val" style="color:var(--success)">${convCount}</div>
        <div class="d-sub">多轮对话会话</div>
      </div>
      <div class="dash-card">
        <div class="d-label">Endpoint</div>
        <div class="d-val" style="color:#bf5af2;font-size:14px">/api/chat</div>
        <div class="d-sub">认知引擎路由 + 双系统 + 护栏</div>
      </div>
    </div>
    <div class="dash-section">
      <h3>引擎详情</h3>
      <table class="dash-table">
        <tr><th>ID</th><th>推理能力</th><th>工具调用</th><th>价格(输入)</th><th>价格(输出)</th></tr>
        ${(engR.engines||[]).map(e=>`
          <tr>
            <td style="color:var(--accent)">${e.id}</td>
            <td><span class="dash-badge ${e.strong_reasoning?'ok':'warn'}">${e.strong_reasoning?'Strong':'Light'}</span></td>
            <td><span class="dash-badge ${e.function_calling?'ok':'err'}">${e.function_calling?'Yes':'No'}</span></td>
            <td>$${e.price_in}/1M</td>
            <td>$${e.price_out}/1M</td>
          </tr>`).join("")}
      </table>
    </div>
    <div class="dash-section">
      <h3>架构模块开发状态</h3>
      <table class="dash-table">
        <tr><th>模块</th><th>状态</th><th>Phase</th></tr>
        <tr><td>L1.5 引擎抽象层</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>L2 记忆系统 (Storage)</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>L3 双系统判据</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>L6 护栏系统</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>会话管理</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>记忆持久化 (SQLite)</td><td><span class="dash-badge warn">TODO</span></td><td>1</td></tr>
        <tr><td>Reasoner ReAct 循环</td><td><span class="dash-badge warn">TODO</span></td><td>1→2</td></tr>
        <tr><td>L2 Reflection 反思</td><td><span class="dash-badge err">Not Started</span></td><td>2</td></tr>
        <tr><td>L4 共情计算</td><td><span class="dash-badge err">Not Started</span></td><td>2</td></tr>
        <tr><td>L5 技能系统</td><td><span class="dash-badge err">Not Started</span></td><td>2</td></tr>
        <tr><td>SSE 流式端点</td><td><span class="dash-badge err">Not Started</span></td><td>1</td></tr>
      </table>
    </div>
  `;
}

// ── init ───────────────────────────────────────
input.addEventListener("input",()=>{input.style.height="auto";input.style.height=Math.min(input.scrollHeight,160)+"px";sendBtn.classList.toggle("on",!!input.value.trim())});
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
sendBtn.addEventListener("click",send);
$("keyBtn").addEventListener("click",()=>{ensureKey(true);refreshConvList()});

applyLang();renderEmpty();ping();setInterval(ping,8000);
if(!apiKey)setTimeout(()=>ensureKey(true),400);
refreshConvList();
</script>
</body>
</html>"""
