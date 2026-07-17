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
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover,user-scalable=no" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="theme-color" content="#0B0B0C" />
<link rel="manifest" href="/manifest.json" />
<title>Sunday</title>
<style>
  :root{
    --bg:#0B0B0C; --surface:#151518; --surface2:#1b1b1f;
    --border:rgba(255,255,255,.08); --border2:rgba(255,255,255,.14);
    --text:#F5F5F7; --sec:rgba(245,245,247,.62); --ter:rgba(245,245,247,.38);
    --accent:#0A84FF; --success:#30D158; --warning:#FFD60A; --danger:#FF453A;
    --font:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
    --sidebar-w: 268px;
    --safe-top: env(safe-area-inset-top,0px);
    --safe-bottom: env(safe-area-inset-bottom,0px);
    --tap-min: 44px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{background:var(--bg);color:var(--text);font-family:var(--font);
    -webkit-font-smoothing:antialiased;display:flex;height:100dvh;overflow:hidden;
    -webkit-tap-highlight-color:transparent;-webkit-overflow-scrolling:touch}
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

  /* ── mobile-first responsive system ──────── */
  /* Industry standards 2025-2026: dvh, clamp(), safe-area, container queries */
  @media (max-width: 768px) {
    /* Hide desktop-only header elements on mobile (keep keyBtn for logout) */
    .lang-group, #consoleBtn, .conn, #collapseBtn, .htxt div, .spacer {display:none!important}
    /* Backdrop overlay (sibling element, not pseudo-element) */
    #backdrop{display:none;position:fixed;inset:0;z-index:48;
      background:rgba(0,0,0,.5);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px)}
    #backdrop.show{display:block}
    /* Sidebar → off-canvas overlay */
    #sidebar{
      position:fixed;left:0;top:0;bottom:0;z-index:50;width:280px;max-width:85vw;
      box-shadow:0 0 60px rgba(0,0,0,.6);
      background:rgba(21,21,24,.96);backdrop-filter:blur(32px);
      padding-top:calc(var(--safe-top) + 8px);
      transform:translateX(-100%);transition:transform .28s cubic-bezier(.22,1,.36,1);
      margin-left:0!important;
    }
    #sidebar.open{transform:translateX(0)}
    /* Hamburger menu button */
    #menuBtn{display:flex!important;min-width:44px;min-height:44px;font-size:20px}
    /* Full-width bubbles */
    .bubble{max-width:92%!important}
    /* Header — minimal bar */
    header{
      padding:6px 12px;padding-top:calc(var(--safe-top) + 6px);
      min-height:48px;gap:8px;justify-content:flex-start
    }
    .htxt b{font-size:15px}
    .mark{width:32px;height:32px;border-radius:9px;flex-shrink:0}
    /* Main scroll area — room for bottom nav */
    main{
      padding:10px 10px;padding-bottom:calc(var(--safe-bottom) + 104px);
      overscroll-behavior-y:contain;-webkit-overflow-scrolling:touch;
      scroll-behavior:smooth;
    }
    /* Footer / composer — sticky above bottom nav */
    footer{
      padding:8px 10px calc(var(--safe-bottom) + 64px);
      position:sticky;bottom:0;
    }
    .composer{padding:6px 6px 6px 14px;border-radius:18px}
    textarea{font-size:16px!important;line-height:1.4} /* 16px prevents iOS zoom */
    .send{width:44px;height:44px;min-width:44px;min-height:44px}
    .send:active{background:var(--accent);opacity:.7}
    /* Bottom navigation bar */
    #bottomNav{
      display:flex;position:fixed;bottom:0;left:0;right:0;z-index:40;
      height:calc(56px + var(--safe-bottom));
      padding-bottom:var(--safe-bottom);
      background:rgba(21,21,24,.92);backdrop-filter:blur(24px);
      -webkit-backdrop-filter:blur(24px);
      border-top:1px solid var(--border);
    }
    #bottomNav button{
      flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
      gap:2px;border:none;background:none;color:var(--ter);font-family:var(--font);
      font-size:10px;font-weight:500;cursor:pointer;transition:color .15s;
      min-height:48px;padding:4px 8px;
      -webkit-tap-highlight-color:transparent;
      -webkit-appearance:none;-webkit-user-select:none;user-select:none;
    }
    #bottomNav button:active{opacity:.6}
    #bottomNav button.on{color:var(--accent)}
    #bottomNav button .nav-icon{font-size:20px;line-height:1;margin-bottom:1px}
    /* All buttons — touch feedback */
    button{-webkit-user-select:none;user-select:none}
    button:active{opacity:.7}
    /* Console / dashboard mobile */
    .dash-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;padding:8px}
    .dash-card{padding:12px;border-radius:12px}
    .dash-card .d-val{font-size:22px}
    .dash-section{margin:4px 8px}
    .dash-table th,.dash-table td{padding:6px 8px;font-size:11px}
    .dash-table{overflow-x:auto;display:block;-webkit-overflow-scrolling:touch}
    /* Conversation sidebar items — larger touch targets */
    .conv-item{padding:10px 12px;min-height:44px}
    .conv-item .c-title{font-size:13px}
    .c-del{width:32px;height:32px;min-width:32px;min-height:32px}
    .sb-header .new-btn{min-height:44px;font-size:14px}
    /* Status bar */
    .status-bar{font-size:10px;gap:8px}
    /* Login / register card */
    .login-card{display:flex;flex-direction:column;align-items:center}
    .login-card input{-webkit-appearance:none;-moz-appearance:none;appearance:none}
    /* Feedback buttons — subtle, expand on hover */
    .feedback-row{display:flex;gap:4px;margin-top:6px;opacity:0.35;transition:opacity .2s}
    .bubble:hover .feedback-row,.feedback-row:hover{opacity:1}
    .fb-btn{background:none;border:1px solid var(--border);border-radius:14px;padding:2px 10px;
      font-size:12px;cursor:pointer;color:var(--sec);transition:.15s;min-height:28px;
      -webkit-user-select:none;user-select:none}
    .fb-btn:hover{background:var(--surface2);border-color:var(--border2);color:var(--text)}
    .fb-btn.active{background:var(--accent);border-color:var(--accent);color:#fff!important;opacity:1}
    .fb-note{display:flex;align-items:center;gap:6px;margin-top:4px;padding:4px 8px;
      border-radius:10px;background:var(--surface);border:1px solid var(--border);animation:fadeIn .2s}
    .fb-note textarea{flex:1;background:none;border:none;outline:none;color:var(--text);
      font-size:12px;font-family:var(--font);resize:none;min-height:24px;padding:2px 0}
    .fb-note button{background:var(--accent);border:none;color:#fff;border-radius:8px;
      padding:3px 10px;font-size:11px;cursor:pointer;min-height:28px}
    @keyframes fadeIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
    /* Reduce motion if user prefers */
    @media (prefers-reduced-motion:reduce){
      #sidebar,#backdrop{transition:none!important}
    }
  }

  /* ── tiny screens (< 400px) ───────────────── */
  @media (max-width: 400px) {
    .mark{width:28px;height:28px;border-radius:8px}
    .htxt b{font-size:14px}
    .dash-grid{grid-template-columns:1fr}
    .bubble{max-width:96%!important;padding:8px 12px;font-size:14px}
    textarea{font-size:16px!important}
    .send{width:40px;height:40px;min-width:40px;min-height:40px}
    #bottomNav button{font-size:9px}
    #bottomNav button .nav-icon{font-size:18px}
    #sidebar{width:280px;max-width:90vw}
    .dash-table{font-size:10px}
    .dash-table th,.dash-table td{padding:4px 6px;font-size:10px}
    header{padding:4px 8px;padding-top:calc(var(--safe-top) + 4px);min-height:44px}
    .dash-card{padding:10px;border-radius:10px}
    .dash-card .d-val{font-size:18px}
    footer{padding:6px 8px calc(var(--safe-bottom) + 60px)}
    .composer{padding:4px 4px 4px 10px}
    main{padding:8px 6px;padding-bottom:calc(var(--safe-bottom) + 100px)}
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

<!-- Backdrop for mobile sidebar overlay -->
<div id="backdrop" onclick="closeSidebar()"></div>

<!-- ── Main chat ─────────────────────────────── -->
<div id="main-col">
<header>
  <button class="collapse-btn" id="menuBtn" title="菜单" style="display:none" onclick="toggleSidebar()">☰</button>
  <div class="mark"><span>☀️</span></div>
  <div class="htxt"><b>Sunday</b><div id="subtitle">一个心智，服务你的一切</div></div>
  <div class="spacer"></div>
  <div class="lang-group">
    <button id="langZh" onclick="setLang('zh')">中文</button>
    <button id="langEn" onclick="setLang('en')">EN</button>
  </div>
  <button class="hbtn" id="consoleBtn" onclick="toggleConsole()" title="切换视图">📊</button>
  <div class="conn"><span class="dot" id="dot"></span><span id="conntxt">…</span></div>
  <button class="hbtn" id="keyBtn">🔑</button>
</header>
<main id="main">
  <div class="wrap" id="wrap"></div>
  <div id="consoleView" style="display:none"></div>
  <div id="memoryView" style="display:none"></div>
  <div id="debugView" style="display:none"></div>
</main>
<footer id="chatFooter">
  <div class="status-bar" id="statusBar"></div>
  <div class="composer">
    <textarea id="input" rows="1" placeholder="对 Sunday 说点什么…" enterkeyhint="send"></textarea>
    <button class="send" id="send">↑</button>
  </div>
</footer>
</div>

<!-- ── Bottom nav (mobile) ──────────────────── -->
<nav id="bottomNav">
  <button class="on" data-view="0" onclick="switchView(0)"><span class="nav-icon">💬</span>Chat</button>
  <button data-view="1" onclick="switchView(1)"><span class="nav-icon">📊</span>Console</button>
  <button data-view="2" onclick="switchView(2)"><span class="nav-icon">🧠</span>Memory</button>
</nav>

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
// Auth: prefer sunday.token (user login), fall back to sunday.key (legacy API key)
let sundayToken = localStorage.getItem("sunday.token") || "";
let apiKey = sundayToken || localStorage.getItem("sunday.key") || "";
// Validate stored token on startup: if it's an old API key (not a real token),
// clear it so the user sees the login/register card.
if (!sundayToken && apiKey) {
  // Has old-format key but no token — show login card
  // (Old API keys won't work with the new X-Sunday-Token header)
  sundayToken = ""; apiKey = "";
  localStorage.removeItem("sunday.key");
}
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
  if(sundayToken){
    wrap.innerHTML=`<div class="empty"><div class="big">☀️</div><h2>${t("empty_h")}</h2><p>${t("empty_p")}</p></div>`;
    return;
  }
  wrap.innerHTML=renderLoginCard();
}

// ── Login UI ────────────────────────────────────
function renderLoginCard(){
  return `
    <div class="big">☀️</div>
    <h2>Welcome to Sunday</h2>
    <p style="margin-bottom:16px">登录或注册以开始聊天</p>
    <div class="login-card" id="loginCard">
      <input id="loginUser" type="text" placeholder="用户名" autocomplete="username"
        style="width:240px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:15px;font-family:var(--font);outline:none;margin-bottom:8px"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border2)'">
      <input id="loginPass" type="password" placeholder="密码" autocomplete="current-password"
        style="width:240px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:15px;font-family:var(--font);outline:none;margin-bottom:4px"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border2)'"
        onkeydown="if(event.key==='Enter')doLogin()">
      <p id="loginErr" style="font-size:11px;color:var(--danger);display:none;margin:4px 0"></p>
      <button onclick="doLogin()"
        style="width:240px;padding:10px 0;border-radius:10px;border:none;background:var(--accent);color:#fff;
        font-size:14px;font-family:var(--font);cursor:pointer;min-height:44px;margin-top:8px">登录</button>
      <button onclick="showRegister()"
        style="background:none;border:none;color:var(--accent);font-size:12px;font-family:var(--font);cursor:pointer;margin-top:10px;text-decoration:underline">没有账号？注册</button>
    </div>
    <div class="login-card" id="regCard" style="display:none">
      <input id="regUser" type="text" placeholder="用户名 (2-30位)" autocomplete="username"
        style="width:240px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:15px;font-family:var(--font);outline:none;margin-bottom:8px"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border2)'">
      <input id="regPass" type="password" placeholder="密码 (4位以上)" autocomplete="new-password"
        style="width:240px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:15px;font-family:var(--font);outline:none;margin-bottom:8px"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border2)'">
      <input id="regPass2" type="password" placeholder="确认密码"
        style="width:240px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:15px;font-family:var(--font);outline:none;margin-bottom:4px"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border2)'"
        onkeydown="if(event.key==='Enter')doRegister()">
      <p id="regErr" style="font-size:11px;color:var(--danger);display:none;margin:4px 0"></p>
      <button onclick="doRegister()"
        style="width:240px;padding:10px 0;border-radius:10px;border:none;background:var(--accent);color:#fff;
        font-size:14px;font-family:var(--font);cursor:pointer;min-height:44px;margin-top:8px">注册</button>
      <button onclick="showLogin()"
        style="background:none;border:none;color:var(--accent);font-size:12px;font-family:var(--font);cursor:pointer;margin-top:10px;text-decoration:underline">已有账号？登录</button>
    </div>`;
}

function showRegister(){
  document.getElementById('loginCard').style.display='none';
  document.getElementById('regCard').style.display='';
}
function showLogin(){
  document.getElementById('regCard').style.display='none';
  document.getElementById('loginCard').style.display='';
}

async function doLogin(){
  const u=document.getElementById('loginUser').value.trim();
  const p=document.getElementById('loginPass').value.trim();
  const err=document.getElementById('loginErr');
  if(!u||!p){err.textContent='请输入用户名和密码';err.style.display='';return}
  try{
    const r=await fetch('/api/auth/login',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!r.ok){err.textContent=d.detail||'登录失败';err.style.display='';return}
    sundayToken=d.token;apiKey=sundayToken;
    localStorage.setItem('sunday.token',sundayToken);
    err.style.display='none';
    renderEmpty();refreshConvList();ping();
  }catch(e){err.textContent='网络错误';err.style.display=''}
}

async function doRegister(){
  const u=document.getElementById('regUser').value.trim();
  const p=document.getElementById('regPass').value.trim();
  const p2=document.getElementById('regPass2').value.trim();
  const err=document.getElementById('regErr');
  if(!u||!p){err.textContent='请输入用户名和密码';err.style.display='';return}
  if(p!==p2){err.textContent='两次密码不一致';err.style.display='';return}
  try{
    const r=await fetch('/api/auth/register',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(!r.ok){err.textContent=d.detail||'注册失败';err.style.display='';return}
    sundayToken=d.token;apiKey=sundayToken;
    localStorage.setItem('sunday.token',sundayToken);
    err.style.display='none';
    renderEmpty();refreshConvList();ping();
  }catch(e){err.textContent='网络错误';err.style.display=''}
}

// ── key (backward-compat) ───────────────────────
function ensureKey(force){
  if(force||!sundayToken){renderEmpty();return false;}
  return true;}

// ── sidebar ────────────────────────────────────
const isMobile = () => window.matchMedia("(max-width: 768px)").matches;

function toggleSidebar(){
  sidebarOpen=!sidebarOpen;
  applySidebarState();
}

function closeSidebar(){
  sidebarOpen=false;
  applySidebarState();
}

function applySidebarState(){
  const s=$("sidebar");
  if(isMobile()){
    if(sidebarOpen){s.classList.add("open");$("backdrop").classList.add("show");document.body.style.overflow="hidden"}
    else{s.classList.remove("open");$("backdrop").classList.remove("show");document.body.style.overflow=""}
  }else{
    s.className=sidebarOpen?"":"collapsed";
  }
}
$("collapseBtn").onclick=()=>{toggleSidebar();};

// ── swipe-to-close sidebar ────────────────────
let touchStartX=0,touchStartY=0;
document.addEventListener("touchstart",e=>{touchStartX=e.touches[0].clientX;touchStartY=e.touches[0].clientY},{passive:true});
document.addEventListener("touchend",e=>{
  const dx=e.changedTouches[0].clientX-touchStartX;
  const dy=e.changedTouches[0].clientY-touchStartY;
  // swipe left > 60px to close
  if(dx<-60&&Math.abs(dy)<Math.abs(dx)&&sidebarOpen){closeSidebar()}
  // swipe right from left edge to open
  if(dx>60&&Math.abs(dy)<Math.abs(dx)&&touchStartX<30&&!sidebarOpen){sidebarOpen=true;applySidebarState()}
});

// ── keyboard handling (iOS visualViewport) ─────
if(window.visualViewport){
  window.visualViewport.addEventListener("resize",()=>{
    const offset=window.innerHeight-window.visualViewport.height;
    if(offset>100){
      // keyboard open — push footer up
      $("chatFooter").style.transform=`translateY(-${offset-56}px)`;
      main.scrollTop=main.scrollHeight;
    }else{
      $("chatFooter").style.transform="";
    }
  });
}

async function refreshConvList(){
  if(!apiKey){$("conv-list").innerHTML=`<div class="sb-empty">${t("noConv")}</div>`;return}
  try{
    const r=await fetch("/api/conversations",{headers:{"X-Sunday-Token":sundayToken}});
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
    const r=await fetch("/api/conversations/"+id,{headers:{"X-Sunday-Token":sundayToken}});
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
    await fetch("/api/conversations/"+id,{method:"DELETE",headers:{"X-Sunday-Token":sundayToken}});
    if(convId===id){convId=null;wrap.innerHTML="";renderEmpty()}
    await refreshConvList();
  }catch(e){}
}

// ── messages ───────────────────────────────────
function addMsg(role,text,meta,isErr,engineId){
  if(wrap.querySelector(".empty"))wrap.innerHTML="";
  const row=document.createElement("div");
  row.className="row "+(role==="me"?"me":(isErr?"ai err":"ai"));
  // Store engine_id as data attr for feedback
  if(engineId) row.setAttribute("data-engine", engineId);
  const inner=role==="me"
    ?`<div><div class="bubble"></div></div>`
    :`<div class="av">☀️</div><div><div class="bubble"></div>${meta?`<div class="meta">${meta}</div>`:""}</div>`;
  row.innerHTML=inner;
  row.querySelector(".bubble").textContent=text;
  if(isErr){
    const errDiv=document.createElement("div");
    errDiv.className="err-detail";errDiv.textContent="⚠ "+t("errEngine");
    row.querySelector(".meta")?.after(errDiv)}
  // Auto-feedback: only for the single-bubble AI case, but NOT if
  // feedback will be added externally by burst rendering code.
  // Avoid double 👍👎 rows.
  const _hasFb=row.querySelector('.feedback-row');
  if(!_hasFb&&role==="ai"&&!isErr&&text&&!text.includes('[mock')&&!text.includes('[mock')){
    row.querySelector(".bubble")?.parentElement?.appendChild(makeFbRow(text,engineId||''));
  }
  wrap.appendChild(row);
  main.scrollTop=main.scrollHeight;
  return row}

function escAttr(s){return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;')}

// Helper: create feedback button row (reusable for multi-bubble)
function makeFbRow(text,engineId){
  const fbRow=document.createElement("div");
  fbRow.className="feedback-row";
  fbRow.innerHTML=
    `<button class="fb-btn" onclick="event.stopPropagation();rateReply(1,'${escAttr(text.substring(0,60))}','${escAttr(engineId||'')}',this)" title="有帮助">👍</button>`+
    `<button class="fb-btn fb-dislike" onclick="event.stopPropagation();rateReply(-1,'${escAttr(text.substring(0,60))}','${escAttr(engineId||'')}',this)" title="不太对">👎</button>`;
  return fbRow;
}

// ── chat ───────────────────────────────────────
let sending=false;
async function send(){
  const text=input.value.trim();if(!text||sending)return;
  if(!sundayToken){renderEmpty();return;}
  addMsg("me",text);input.value="";input.style.height="auto";
  sending=true;sendBtn.classList.remove("on");
  const typing=addMsg("ai","");
  typing.querySelector(".bubble").innerHTML='<span class="typing"><span></span><span></span><span></span></span>';
  try{
    const body={message:text};
    if(convId)body.conversation_id=convId;

    // Try SSE streaming first
    const r=await fetch("/api/chat/stream",{method:"POST",
      headers:{"Content-Type":"application/json","X-Sunday-Token":sundayToken},
      body:JSON.stringify(body)});

    if(r.status===401){typing.remove();addMsg("ai",t("err401"),"",true);sending=false;return}
    if(r.status===403){typing.remove();addMsg("ai","API Key 权限不足 (403 Forbidden)。请确认 Key 有正确的权限。","",true);sending=false;return}
    if(r.status===502||r.status===503){typing.remove();addMsg("ai",t("errNet")+" (后端服务未就绪)","",true);sending=false;return}

    if(!r.ok){
      // Try to read error body
      let errText=""; try{const ed=await r.json();errText=ed.detail||JSON.stringify(ed)}catch(ex){errText=await r.text().catch(()=>"")}
      typing.remove();addMsg("ai",`请求失败 (${r.status}): ${errText.substring(0,200)}`,"",true);sending=false;return
    }

    if(r.ok && r.headers.get("content-type")?.includes("text/event-stream")){
      // SSE streaming path — live streaming into one bubble,
      // then on "done" we burst the accumulated text into natural segments.
      typing.remove();
      const bubbleRow=addMsg("ai","");
      const bubble=bubbleRow.querySelector(".bubble");
      bubble.innerHTML="";
      let streamedText="",streamEngine="",streamSystem="";
      const reader=r.body.getReader();
      const decoder=new TextDecoder();
      let buf="";
      while(true){
        const{value,done}=await reader.read();
        if(done)break;
        buf+=decoder.decode(value,{stream:true});
        const lines=buf.split("\n");
        buf=lines.pop()||"";
        for(const line of lines){
          if(!line.startsWith("data: "))continue;
          try{
            const d=JSON.parse(line.slice(6));
            if(d.type==="done"){
              if(d.conversation_id&&!convId)convId=d.conversation_id;
              streamEngine=d.engine||"";streamSystem=d.system||"";
              if(d.bursts&&d.bursts.length>1){
                // Replace monolithic bubble with burst segments
                const bursts=d.bursts;
                const firstText=bursts[0];
                bubble.textContent=firstText.trim();
                // Build meta on first bubble
                const sysTag=streamSystem?`<span class="tag">${streamSystem==="reasoner"?t("deep"):t("fast")}</span>`:"";
                const eng=streamEngine?streamEngine+" ":"";
                const metaDiv=document.createElement("div");
                metaDiv.className="meta";
                metaDiv.innerHTML=eng+sysTag;
                if(firstText.trim()&&!firstText.includes('[mock')){
                  const fbRow=makeFbRow(firstText,streamEngine||'');
                  bubbleRow.querySelector(".bubble")?.parentElement?.appendChild(fbRow);
                }
                bubbleRow.appendChild(metaDiv);
                // Subsequent bursts
                let delay=600;
                for(let i=1;i<bursts.length;i++){
                  setTimeout(()=>{
                    const showTyping=addMsg("ai","");
                    showTyping.querySelector(".bubble").innerHTML='<span class="typing"><span></span><span></span><span></span></span>';
                    setTimeout(()=>{
                      showTyping.remove();
                      const segRow=addMsg("ai",bursts[i].trim(),"",false,streamEngine||'');
                      // Add feedback only to last segment
                      if(i===bursts.length-1&&bursts[i].trim()&&!bursts[i].includes('[mock')){
                        const fbRow2=makeFbRow(bursts[i],streamEngine||'');
                        segRow.querySelector(".bubble")?.parentElement?.appendChild(fbRow2);
                      }
                    },400+Math.random()*500);
                  },delay);
                  delay+=600+Math.random()*400;
                }
              }else{
                // Single bubble (no burst) — add meta + feedback
                bubble.textContent=streamedText||bubble.textContent||(d.reply||"");
                const sysTag=streamSystem?`<span class="tag">${streamSystem==="reasoner"?t("deep"):t("fast")}</span>`:"";
                const eng=streamEngine?streamEngine+" ":"";
                const metaDiv=document.createElement("div");
                metaDiv.className="meta";
                metaDiv.innerHTML=eng+sysTag;
                bubbleRow.appendChild(metaDiv);
                if(streamedText&&!streamedText.includes('[mock')){
                  const fbRow=makeFbRow(streamedText,streamEngine||'');
                  bubbleRow.querySelector(".bubble")?.parentElement?.appendChild(fbRow);
                }
              }
            }else if(d.type==="text"){
              streamedText+=d.content;
              bubble.textContent=streamedText;
            }else if(d.type==="thought"){
              bubble.innerHTML+=`<div style="font-size:11px;color:var(--ter);margin:4px 0">💭 ${esc(d.content).substring(0,100)}</div>`;
            }else if(d.type==="action"){
              bubble.innerHTML+=`<div style="font-size:11px;color:var(--accent);margin:4px 0">🔧 ${esc(d.tool_name||"")}: ${esc((d.tool_input||"").substring(0,60))}</div>`;
            }else if(d.type==="observation"){
              bubble.innerHTML+=`<div style="font-size:11px;color:var(--success);margin:4px 0">📋 ${esc((d.content||"").substring(0,100))}</div>`;
            }else if(d.type==="finish"){
              streamedText=d.content||streamedText;
              bubble.textContent=streamedText;
            }else if(d.type==="error"){
              bubble.textContent="Error: "+d.content;
            }
          }catch(e){/* skip bad JSON */}
        }
      }
    }else{
      // Fallback: non-streaming
      const d=await r.json();
      typing.remove();
      if(d.conversation_id&&!convId)convId=d.conversation_id;
      const hasErr=d.trace&&d.trace.errors&&Object.keys(d.trace.errors).length>0;
      const engineId=d.engine||"";

      // Multi-bubble burst rendering
      const bursts=d.bursts||[];
      if(bursts.length>1&&!hasErr){
        let delay=300;
        for(let i=0;i<bursts.length;i++){
          setTimeout(()=>{
            if(i===0){
              // Show typing indicator briefly before first bubble
              const tyRow=addMsg("ai","");
              tyRow.querySelector(".bubble").innerHTML='<span class="typing"><span></span><span></span><span></span></span>';
              setTimeout(()=>{
                tyRow.remove();
                const row=addMsg("ai",bursts[i].trim(),"",false,engineId);
                if(bursts[i].trim()&&!bursts[i].includes('[mock')){
                  const fbRow=makeFbRow(bursts[i],engineId);
                  row.querySelector(".bubble")?.parentElement?.appendChild(fbRow);
                }
              },350);
            }else{
              const row=addMsg("ai",bursts[i].trim(),"",false,engineId);
              if(i===bursts.length-1&&bursts[i].trim()&&!bursts[i].includes('[mock')){
                const fbRow=makeFbRow(bursts[i],engineId);
                row.querySelector(".bubble")?.parentElement?.appendChild(fbRow);
              }
            }
          },delay);
          delay+=450+Math.random()*400;
        }
      }else{
        // Single bubble (no burst or error)
        const sysTag=d.system?`<span class="tag">${d.system==="reasoner"?t("deep"):t("fast")}</span>`:"";
        const eng=d.engine?d.engine+" ":"";
        const errTag=hasErr?`<span class="tag err">⚠ ${t("errEngine")}</span>`:"";
        addMsg("ai",d.reply||t("errNet"),eng+sysTag+errTag,hasErr,d.engine);
        if(hasErr&&d.trace&&d.trace.errors){
          const row=wrap.lastElementChild;
          const errs=Object.entries(d.trace.errors).map(([eid,msg])=>`${eid}: ${msg}`).join(" · ");
          const errDiv=document.createElement("div");
          errDiv.className="err-detail";errDiv.textContent=errs;
          row.appendChild(errDiv)}
      }
    }
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
  if(viewMode === 1) refreshConsole();
  if(viewMode === 2) refreshMemory();
}

// ── console / dashboard / memory toggle ─────────
// 0 = chat, 1 = dashboard, 2 = memory, 3 = debug
let viewMode = 0;
let healthCache = null;

// Renders a key-entry prompt (inline HTML, not browser prompt())
function renderKeyPromptView(viewName){
  return `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:260px;text-align:center;padding:24px">
      <div style="font-size:40px;margin-bottom:12px">🔑</div>
      <h2 style="font-size:18px;color:var(--text);margin-bottom:8px">需要 API Key</h2>
      <p style="font-size:13px;color:var(--sec);margin-bottom:20px;max-width:280px">${viewName} 需要验证身份才能加载数据。请输入你的 API Key。</p>
      <input id="keyInputInline" type="password" placeholder="SUNDAY_API_KEY"
        style="width:100%;max-width:280px;padding:10px 14px;border-radius:10px;border:1px solid var(--border2);
        background:var(--surface);color:var(--text);font-size:14px;font-family:var(--font);text-align:center;
        outline:none;transition:border-color .2s"
        onfocus="this.style.borderColor='var(--accent)'"
        onblur="this.style.borderColor='var(--border2)'">
      <button onclick="saveInlineKey()"
        style="margin-top:12px;padding:10px 32px;border-radius:10px;border:none;background:var(--accent);color:#fff;
        font-size:14px;font-family:var(--font);cursor:pointer;min-height:44px">
        确认并加载
      </button>
      <p id="keyInlineErr" style="font-size:11px;color:var(--danger);margin-top:8px;display:none"></p>
    </div>`;
}

function saveInlineKey(){
  const inp = document.getElementById("keyInputInline");
  const err = document.getElementById("keyInlineErr");
  if(!inp) return;
  const v = inp.value.trim();
  if(!v){ err.textContent = "Key 不能为空"; err.style.display=""; return }
  apiKey = v;
  localStorage.setItem("sunday.token", sundayToken);
  err.style.display = "none";
  // Reload the current view
  if(viewMode === 1) refreshConsole();
  if(viewMode === 2) refreshMemory();
  if(viewMode === 3) refreshDebug();
}

function switchView(mode){
  viewMode = mode;
  $("wrap").style.display = mode === 0 ? "" : "none";
  $("chatFooter").style.display = mode === 0 ? "" : "none";
  $("consoleView").style.display = mode === 1 ? "" : "none";
  $("memoryView").style.display = mode === 2 ? "" : "none";
  $("debugView").style.display = mode === 3 ? "" : "none";
  // Update bottom nav active state
  document.querySelectorAll("#bottomNav button").forEach((b,i)=>{
    b.className = i === mode ? "on" : "";
  });
  if(mode === 1) refreshConsole();
  if(mode === 2) refreshMemory();
  if(mode === 3) refreshDebug();
}

function toggleConsole(){
  switchView((viewMode + 1) % 4);
}

async function refreshConsole(){
  if(!apiKey){ $("consoleView").innerHTML = renderKeyPromptView("Console 仪表盘"); return }
  try{
    const r = await fetch("/health");
    healthCache = await r.json();
  }catch(e){ healthCache = null }
  const engR = await fetch("/api/engines").then(r=>r.json()).catch(()=>({engines:[]}));
  const skillR = await fetch("/api/skills",{headers:{"X-Sunday-Token":sundayToken}}).then(r=>r.json()).catch(()=>({skills:{},by_category:{},total:0}));
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
        <div class="d-label">Skills</div>
        <div class="d-val" style="color:#bf5af2">${skillR.total||0}</div>
        <div class="d-sub">${Object.entries(skillR.by_category||{}).map(([k,v])=>k+": "+v).join(" · ")}</div>
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
        <tr><td>L5 技能系统</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
        <tr><td>SSE 流式端点</td><td><span class="dash-badge ok">Done</span></td><td>1</td></tr>
      </table>
    </div>
    <div class="dash-section">
      <h3>Skills (${skillR.total||0})</h3>
      <table class="dash-table">
        <tr><th>Skill</th><th>Category</th><th>Risk</th></tr>
        ${Object.entries(skillR.skills||{}).map(([name,s])=>`
          <tr>
            <td style="color:var(--accent)">${name}</td>
            <td><span class="dash-badge info">${s.category}</span></td>
            <td><span class="dash-badge ${s.risk==='low'?'ok':s.risk==='medium'?'warn':'err'}">${s.risk}</span></td>
          </tr>`).join("")}
      </table>
    </div>
  `;
}

// ── memory view ────────────────────────────────
async function refreshMemory(){
  if(!apiKey){ $("memoryView").innerHTML = renderKeyPromptView("Memory 记忆视图"); return }
  // fetch stats
  let stats = {};
  try{
    const r = await fetch("/api/memory/stats", {headers:{"X-Sunday-Token":sundayToken}});
    if(r.ok) stats = await r.json();
  }catch(e){}

  // fetch reflections
  let refs = [];
  try{
    const r = await fetch("/api/memory/reflections?limit=10", {headers:{"X-Sunday-Token":sundayToken}});
    if(r.ok){ const d = await r.json(); refs = d.reflections || []; }
  }catch(e){}

  // fetch recent memories
  let recents = [];
  try{
    const r = await fetch("/api/memory/search", {
      method:"POST",
      headers:{"Content-Type":"application/json","X-Sunday-Token":sundayToken},
      body:JSON.stringify({query:"*",k:15})
    });
    if(r.ok){ const d = await r.json(); recents = d.results || []; }
  }catch(e){}

  const totalNodes = stats.total_nodes || 0;
  const byType = stats.by_type || {};
  const embedder = stats.embedder || "hash";
  const dbType = stats.db_type || "memory";

  $("memoryView").innerHTML = `
    <div class="dash-grid">
      <div class="dash-card" style="cursor:pointer" onclick="doReflect()">
        <div class="d-label">Reflection (L2)</div>
        <div class="d-val" style="color:#bf5af2;font-size:22px">${refs.length} insights</div>
        <div class="d-sub">${refs.length ? 'Last: '+refs[0].content.substring(0,50)+'...' : 'Click to trigger reflection'}</div>
      </div>
      <div class="dash-card">
        <div class="d-label">Episodic</div>
        <div class="d-val" style="color:var(--accent)">${byType.episodic||0}</div>
        <div class="d-sub">情景记忆</div>
      </div>
      <div class="dash-card">
        <div class="d-label">Semantic</div>
        <div class="d-val" style="color:#64d2ff">${byType.semantic||0}</div>
        <div class="d-sub">语义/知识记忆</div>
      </div>
      <div class="dash-card">
        <div class="d-label">DB / Embedder</div>
        <div class="d-val" style="color:var(--success);font-size:14px">${dbType} + ${embedder}</div>
        <div class="d-sub">Total: ${totalNodes} nodes</div>
      </div>
    </div>
    <div class="dash-section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <h3>Recent Memories (${recents.length})</h3>
        <button class="hbtn" onclick="doReflect()" style="font-size:11px;padding:3px 8px">🔍 Reflect</button>
        <button class="hbtn" onclick="doConsolidate()" style="font-size:11px;padding:3px 8px">🗑 Consolidate</button>
      </div>
      ${recents.length === 0 ? '<p style="color:var(--ter);font-size:12px;padding:12px 0">No memories yet. Chat with Sunday to create some!</p>' : ''}
      <table class="dash-table">
        <tr><th>Content</th><th>Type</th><th>Importance</th><th>Score</th><th>Time</th></tr>
        ${recents.map(r=>`
          <tr>
            <td style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.content.substring(0,80))}</td>
            <td><span class="dash-badge info">${r.type}</span></td>
            <td>${r.components ? Math.round(r.components.importance*10) : '?'}/10</td>
            <td>${r.score ? r.score.toFixed(2) : '?'}</td>
            <td style="font-size:10px;color:var(--ter)">${r.id ? 'mem_'+r.id.substring(4,10) : ''}</td>
          </tr>`).join("")}
      </table>
    </div>
    ${refs.length > 0 ? `
    <div class="dash-section">
      <h3>Reflection Insights (${refs.length})</h3>
      ${refs.slice(0,5).map(r=>`
        <div class="dash-card" style="margin-bottom:8px">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span class="dash-badge ok">insight</span>
            <span style="font-size:10px;color:var(--ter)">${r.evidence_ids ? r.evidence_ids.length : 0} sources</span>
          </div>
          <p style="font-size:13px;color:var(--text);line-height:1.5">${esc(r.content)}</p>
        </div>`).join("")}
    </div>` : ''}
    <p style="font-size:10px;color:var(--ter);padding:12px 16px">
      L1 Storage (SQLite) ✅ &nbsp;|&nbsp; L2 Reflection (LLM) 🟡 &nbsp;|&nbsp; L3 Experience ❌
    </p>
  `;
}

async function doReflect(){
  try{
    $("memoryView").innerHTML = '<div class="dash-grid"><div class="dash-card"><div class="d-val" style="font-size:16px">Running reflection...</div></div></div>';
    const r = await fetch("/api/memory/reflect", {
      method:"POST",
      headers:{"Content-Type":"application/json","X-Sunday-Token":sundayToken},
      body:JSON.stringify({force:true})
    });
    const d = await r.json();
    refreshMemory();
  }catch(e){ refreshMemory(); }
}

async function doConsolidate(){
  try{
    const r = await fetch("/api/memory/consolidate", {
      method:"POST",
      headers:{"X-Sunday-Token":sundayToken}
    });
    refreshMemory();
  }catch(e){}
}

// ── debug view ─────────────────────────────────
async function refreshDebug(){
  if(!apiKey){ $("debugView").innerHTML = renderKeyPromptView("Debug 诊断视图"); return }
  let ov={};
  try{
    const r=await fetch("/api/debug/overview",{headers:{"X-Sunday-Token":sundayToken}});
    if(r.ok) ov=await r.json();
  }catch(e){}

  const checks=ov.checks||{};
  const ckIcon=v=>v?"✅":"❌";

  $("debugView").innerHTML=`
    <div class="dash-section"><h3>System Checks</h3>
      <table class="dash-table">
        <tr><td>DB Accessible</td><td>${ckIcon(checks.db_accessible)}</td></tr>
        <tr><td>Engines Available</td><td>${ckIcon(checks.engines_available)}</td></tr>
        <tr><td>Memory Working</td><td>${ckIcon(checks.memory_working)}</td></tr>
      </table>
    </div>
    <div class="dash-grid">
      <div class="dash-card"><div class="d-label">Python</div><div class="d-val" style="font-size:13px">${ov.server?.python?.split(" ")[0]||"?"}</div></div>
      <div class="dash-card"><div class="d-label">Engines</div><div class="d-val" style="color:var(--accent)">${ov.engines?.count||0}</div><div class="d-sub">${(ov.engines?.list||[]).join(", ")}</div></div>
      <div class="dash-card"><div class="d-label">Memory (${ov.memory?.db_type||"?"})</div><div class="d-val" style="color:#64d2ff">${ov.memory?.total_nodes||0}</div><div class="d-sub">${ov.memory?.embedder||"?"} embedder</div></div>
      <div class="dash-card"><div class="d-label">Tools</div><div class="d-val" style="color:#bf5af2">${ov.tools?.count||0}</div><div class="d-sub">${(ov.tools?.list||[]).map(t=>t.name+"("+t.risk+")").join(", ")}</div></div>
    </div>
    <div class="dash-section"><h3>Usage</h3>
      <table class="dash-table">
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Messages Today</td><td>${ov.usage?.messages_today||0}</td></tr>
        <tr><td>API Calls</td><td>${ov.usage?.calls_today||0}</td></tr>
        <tr><td>Tokens Used</td><td>${ov.usage?.tokens_today||0}</td></tr>
        <tr><td>Cost Today</td><td>$${ov.usage?.cost_today||0}</td></tr>
        <tr><td>Avg Latency</td><td>${ov.usage?.avg_latency_ms||0}ms</td></tr>
      </table>
    </div>
    <div class="dash-section"><h3>Memory by Type</h3>
      <table class="dash-table">
        <tr><th>Type</th><th>Count</th></tr>
        ${Object.entries(ov.memory?.by_type||{}).map(([k,v])=>`
          <tr><td>${k}</td><td>${v}</td></tr>`).join("")}
      </table>
    </div>
    <p style="font-size:10px;color:var(--ter);padding:12px 16px">
      🔧 Debug View — <a href="/docs" target="_blank" style="color:var(--accent)">Swagger UI /docs</a> · <a href="/api/debug/env" style="color:var(--accent)">Env Diagnostic</a>
    </p>
  `;
}

// ── feedback ────────────────────────────────────
function rateReply(rating, msgPreview, engineId, btnEl){
  if(!apiKey) return;
  // Mark button active
  if(btnEl){
    const row=btnEl.parentElement;
    row.querySelectorAll('.fb-btn').forEach(b=>b.classList.remove('active'));
    btnEl.classList.add('active');
  }
  const url=location.origin+'/api/feedback';
  if(rating<0){
    // 👎 — show a text input for explanation
    const existing=document.querySelector('.fb-note');
    if(existing) existing.remove();
    const note=document.createElement('div');
    note.className='fb-note';
    note.innerHTML=`
      <textarea rows="1" placeholder="哪里不满意？（可选，回车提交）" id="fbTextInput"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();submitFbNote('${escAttr(msgPreview)}','${engineId}')}"></textarea>
      <button onclick="submitFbNote('${escAttr(msgPreview)}','${engineId}')">提交</button>`;
    btnEl.parentElement?.after(note);
    document.getElementById('fbTextInput')?.focus();
  }else{
    // 👍 — submit immediately
    fetch(url,{method:'POST',
      headers:{'Content-Type':'application/json','X-API-Key':apiKey},
      body:JSON.stringify({rating:1,msg_preview:msgPreview,engine_id:engineId})
    }).catch(()=>{});
  }
}

function submitFbNote(msgPreview, engineId){
  const inp=document.getElementById('fbTextInput');
  const text=inp?.value.trim()||'';
  const note=document.querySelector('.fb-note');
  note?.remove();
  fetch(location.origin+'/api/feedback',{method:'POST',
    headers:{'Content-Type':'application/json','X-API-Key':apiKey},
    body:JSON.stringify({rating:-1,feedback_text:text,msg_preview:msgPreview,engine_id:engineId})
  }).catch(()=>{});
}

// ── init ───────────────────────────────────────
input.addEventListener("input",()=>{input.style.height="auto";input.style.height=Math.min(input.scrollHeight,160)+"px";sendBtn.classList.toggle("on",!!input.value.trim())});
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
sendBtn.addEventListener("click",send);
$("keyBtn").addEventListener("click",()=>{sundayToken="";apiKey="";localStorage.removeItem("sunday.token");localStorage.removeItem("sunday.key");renderEmpty();refreshConvList();location.reload()});

// Mobile: start with sidebar closed
if(isMobile()){sidebarOpen=false;applySidebarState();}

applyLang();renderEmpty();ping();setInterval(ping,8000);
// Login is handled by renderEmpty()'s login card. No prompt() needed.
refreshConvList();
</script>
</body>
</html>"""
