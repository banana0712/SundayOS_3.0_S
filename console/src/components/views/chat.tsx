"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Plus, Circle, Cpu } from "lucide-react";
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

export function ChatView() {
  const { t } = useI18n();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const idRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // connection indicator
  useEffect(() => {
    let alive = true;
    const ping = async () => {
      try {
        const r = await fetch("/api/chat", { method: "GET" });
        const d = await r.json();
        if (alive) setOnline(Boolean(d.ok));
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
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, user_id: "me" }),
      });
      if (r.status === 502) {
        setMsgs((m) => [...m, { id: idRef.current++, role: "assistant", text: t("chat.err.offline") }]);
        setOnline(false);
        return;
      }
      const d = await r.json();
      const reply: string = d.reply ?? t("chat.err.generic");
      const isMock = typeof d.engine === "string" && d.engine.startsWith("mock");
      setMsgs((m) => [
        ...m,
        { id: idRef.current++, role: "assistant", text: reply, engine: d.engine, system: d.system, mock: isMock },
      ]);
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
    <div className="mx-auto flex h-full max-w-[860px] flex-col px-4">
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
            onClick={() => setMsgs([])}
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
