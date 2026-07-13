"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Plus, Circle, Cpu, MessageSquare, Trash2 } from "lucide-react";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";

type Msg = {
  id: number;
  role: "user" | "assistant";
  text: string;
  engine?: string | null;
  system?: string;
  mock?: boolean;
};

type ConvInfo = {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export function ChatView() {
  const { t } = useI18n();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const idRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // connection indicator (uses /health, not /api/chat)
  useEffect(() => {
    let alive = true;
    const ping = async () => {
      try {
        const r = await fetch("/health");
        const d = await r.json();
        if (alive) setOnline(d.engines?.length > 0);
      } catch {
        if (alive) setOnline(false);
      }
    };
    ping();
    const id = setInterval(ping, 8000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  // ---- conversation state ----
  const [convs, setConvs] = useState<ConvInfo[]>([]);
  const [convId, setConvId] = useState<string | null>(null);

  const fetchConvs = useCallback(async () => {
    try {
      const r = await fetch("/api/conversations");
      if (r.ok) {
        const d = await r.json();
        setConvs(d.conversations || []);
      }
    } catch { /* backend may not have this endpoint yet */ }
  }, []);

  useEffect(() => { fetchConvs(); }, [fetchConvs]);

  const selectConv = useCallback(async (id: string) => {
    setConvId(id);
    try {
      const r = await fetch(`/api/conversations/${id}`);
      if (r.ok) {
        const d = await r.json();
        const loaded: Msg[] = (d.messages || []).map((m: Record<string, unknown>, i: number) => ({
          id: i,
          role: m.role as "user" | "assistant",
          text: m.content as string,
          engine: (m.engine as string) || undefined,
          system: (m.system as string) || undefined,
        }));
        setMsgs(loaded);
      }
    } catch { /* ignore */ }
  }, []);

  const newConv = useCallback(() => {
    setConvId(null);
    setMsgs([]);
  }, []);

  const deleteConv = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`/api/conversations/${id}`, { method: "DELETE" });
      if (convId === id) { setConvId(null); setMsgs([]); }
      fetchConvs();
    } catch { /* ignore */ }
  }, [convId, fetchConvs]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, sending]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    const userMsg: Msg = { id: idRef.current++, role: "user", text };
    setMsgs((m) => [...m, userMsg]);
    setInput("");
    setSending(true);
    try {
      const body: Record<string, unknown> = { message: text };
      if (convId) body.conversation_id = convId;
      const r = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (r.status === 502) {
        setMsgs((m) => [...m, { id: idRef.current++, role: "assistant", text: t("chat.err.offline") }]);
        setOnline(false);
        setSending(false);
        return;
      }

      // SSE streaming
      const contentType = r.headers.get("content-type") || "";
      if (r.ok && contentType.includes("text/event-stream")) {
        const reader = r.body?.getReader();
        if (!reader) throw new Error("no reader");
        const decoder = new TextDecoder();
        const msgId = idRef.current++;
        // Placeholder message that gets updated
        setMsgs((m) => [...m, { id: msgId, role: "assistant", text: "" }]);
        let buf = "";
        let streamedText = "";
        const updateMsg = (partial: Partial<Msg>) => {
          setMsgs((m) => m.map(msg => msg.id === msgId ? { ...msg, ...partial } : msg));
        };
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop() || "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const d = JSON.parse(line.slice(6));
              if (d.type === "done") {
                if (d.conversation_id && !convId) setConvId(d.conversation_id);
                updateMsg({ engine: d.engine, system: d.system });
                fetchConvs();
              } else if (d.type === "text") {
                streamedText += d.content;
                updateMsg({ text: streamedText });
              } else if (d.type === "finish") {
                streamedText = d.content || streamedText;
                updateMsg({ text: streamedText });
              } else if (d.type === "thought" || d.type === "action" || d.type === "observation") {
                // Append step marker to text
                const marker = d.type === "thought" ? "\n💭 "
                  : d.type === "action" ? "\n🔧 " : "\n📋 ";
                streamedText += marker + (d.content || "").substring(0, 80);
                updateMsg({ text: streamedText });
              } else if (d.type === "error") {
                streamedText += "\n⚠ " + d.content;
                updateMsg({ text: streamedText });
              }
            } catch { /* skip bad JSON */ }
          }
        }
        if (!streamedText) updateMsg({ text: t("chat.err.generic") });
      } else {
        // Fallback: regular JSON response
        const d = await r.json();
        const reply: string = d.reply ?? t("chat.err.generic");
        if (d.conversation_id && !convId) { setConvId(d.conversation_id); fetchConvs(); }
        else if (convId) { fetchConvs(); }
        const isMock = typeof d.engine === "string" && d.engine.startsWith("mock");
        setMsgs((m) => [...m, { id: idRef.current++, role: "assistant", text: reply, engine: d.engine, system: d.system, mock: isMock }]);
      }
    } catch {
      setMsgs((m) => [...m, { id: idRef.current++, role: "assistant", text: t("chat.err.generic") }]);
    } finally {
      setSending(false);
      taRef.current?.focus();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full">
      {/* Conversation sidebar */}
      <aside className="flex w-[260px] shrink-0 flex-col border-r border-border bg-[var(--surface)]/40 backdrop-blur-[var(--glass-blur)]">
        <div className="flex items-center gap-2 border-b border-border px-3 py-3">
          <button
            onClick={newConv}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-[10px] border border-border2 bg-[var(--surface)] py-2 text-[13px] text-primary transition-colors hover:border-accent hover:text-accent"
          >
            <Plus className="h-4 w-4" />
            {t("chat.newchat")}
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-1">
          {convs.length === 0 && (
            <div className="px-3 py-8 text-center text-[12px] text-tertiary">
              {t("chat.empty.title")}
            </div>
          )}
          {convs.map((c) => (
            <button
              key={c.id}
              onClick={() => selectConv(c.id)}
              className={cn(
                "group flex w-full items-center gap-2 rounded-[10px] px-3 py-2.5 text-left transition-colors",
                c.id === convId
                  ? "bg-[var(--surface-2)] border border-border"
                  : "hover:bg-[var(--surface-2)]"
              )}
            >
              <MessageSquare className={cn(
                "h-4 w-4 shrink-0",
                c.id === convId ? "text-accent" : "text-tertiary"
              )} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] text-primary">{c.title}</div>
                <div className="text-[10px] text-tertiary">{c.message_count} msg</div>
              </div>
              <button
                onClick={(e) => deleteConv(c.id, e)}
                className="ml-auto h-6 w-6 shrink-0 rounded-md text-tertiary opacity-0 transition-opacity hover:bg-[color:var(--danger)]/10 hover:text-danger group-hover:opacity-100"
              >
                <Trash2 className="h-3.5 w-3.5 mx-auto" />
              </button>
            </button>
          ))}
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex min-w-0 flex-1 flex-col px-4">
      {/* header */}
      <div className="flex items-center gap-3 py-4">
        <div className="relative flex h-9 w-9 items-center justify-center">
          <div className="absolute inset-0 rounded-[11px] bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] opacity-90" />
          <div className="absolute inset-[1.5px] rounded-[9.5px] bg-[var(--surface)]" />
          <Sparkles className="relative h-4 w-4 text-accent" />
        </div>
        <div className="min-w-0">
          <h1 className="text-subtitle leading-tight text-primary">{t("chat.title")}</h1>
          <p className="text-caption text-tertiary">{t("chat.subtitle")}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-[11px] text-tertiary">
            <Circle
              className={cn(
                "h-2 w-2",
                online === null ? "fill-tertiary text-tertiary"
                  : online ? "fill-success text-success" : "fill-danger text-danger"
              )}
            />
            {online === false ? t("chat.backend.down") : t("chat.backend.up")}
          </span>
          <button
            onClick={newConv}
            className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-[12px] text-secondary transition-colors hover:border-border-strong hover:text-primary"
          >
            <Plus className="h-3.5 w-3.5" />
            {t("chat.newchat")}
          </button>
        </div>
      </div>

      {/* messages */}
      <div className="flex-1 overflow-y-auto pb-4">
        {msgs.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-glass border border-border text-accent">
              <Sparkles className="h-6 w-6" />
            </div>
            <h2 className="text-title text-primary">{t("chat.empty.title")}</h2>
            <p className="mt-2 max-w-xs text-[14px] text-secondary">{t("chat.empty.hint")}</p>
          </div>
        )}

        <div className="space-y-4">
          <AnimatePresence initial={false}>
            {msgs.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}
              >
                {m.role === "assistant" && (
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#0a84ff] to-[#5e5ce6] text-white">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                )}
                <div className={cn("max-w-[78%]", m.role === "user" && "flex flex-col items-end")}>
                  <div
                    className={cn(
                      "rounded-[18px] px-4 py-2.5 text-[15px] leading-relaxed",
                      m.role === "user"
                        ? "bg-accent text-white"
                        : "border border-border bg-[var(--surface)] text-primary"
                    )}
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>
                  {m.role === "assistant" && m.engine && (
                    <div className="mt-1 flex items-center gap-2 px-1 text-[11px] text-tertiary">
                      <Cpu className="h-3 w-3" />
                      <span>{t("chat.engine")}: {m.engine}</span>
                      {m.system && (
                        <span className="rounded-full border border-border px-1.5 py-0.5">
                          {t(`chat.system.${m.system}`)}
                        </span>
                      )}
                      {m.mock && <span className="text-warning">· {t("chat.mock.note")}</span>}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {sending && (
            <div className="flex gap-3">
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#0a84ff] to-[#5e5ce6] text-white">
                <Sparkles className="h-3.5 w-3.5 animate-pulse" />
              </div>
              <div className="flex items-center gap-1 rounded-[18px] border border-border bg-[var(--surface)] px-4 py-3">
                <Dot /> <Dot delay={0.15} /> <Dot delay={0.3} />
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* composer */}
      <div className="pb-6">
        {online === false && (
          <div className="mb-2 rounded-[12px] border border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 px-3 py-2 text-[12px] text-warning">
            {t("chat.err.offline")} <span className="text-tertiary">{t("chat.backend.hint")}</span>
          </div>
        )}
        <div className="flex items-end gap-2 rounded-[20px] border border-border bg-[var(--surface)] p-2 pl-4 transition-colors focus-within:border-border-strong">
          <textarea
            ref={taRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={t("chat.placeholder")}
            className="max-h-40 flex-1 resize-none bg-transparent py-2 text-[15px] text-primary outline-none placeholder:text-tertiary"
          />
          <button
            onClick={send}
            disabled={!input.trim() || sending}
            aria-label={t("chat.send")}
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-all",
              input.trim() && !sending
                ? "bg-accent text-white hover:opacity-90"
                : "bg-[var(--surface-2)] text-tertiary"
            )}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
      </div>
    </div>
  );
}

function Dot({ delay = 0 }: { delay?: number }) {
  return (
    <motion.span
      className="h-1.5 w-1.5 rounded-full bg-tertiary"
      animate={{ opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1, repeat: Infinity, delay }}
    />
  );
}
