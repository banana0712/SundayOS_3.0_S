"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Plus, MessageSquare, Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme-context";

type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

type Conversation = {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

const API_BASE = "http://localhost:8000";

export default function ChatInterface() {
  const { theme } = useTheme();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);

  const messageIdRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch conversations list
  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/conversations`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations || []);
      }
    } catch (error) {
      console.error("Failed to fetch conversations:", error);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Load conversation
  const loadConversation = useCallback(async (convId: string) => {
    setCurrentConvId(convId);
    try {
      const res = await fetch(`${API_BASE}/api/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        const loaded: Message[] = (data.messages || []).map((m: any, i: number) => ({
          id: i,
          role: m.role as "user" | "assistant",
          content: m.content as string,
        }));
        setMessages(loaded);
        messageIdRef.current = loaded.length;
      }
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  }, []);

  // New conversation
  const newConversation = useCallback(() => {
    setCurrentConvId(null);
    setMessages([]);
    messageIdRef.current = 0;
  }, []);

  // Delete conversation
  const deleteConversation = useCallback(async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/conversations/${convId}`, { method: "DELETE" });
      if (currentConvId === convId) {
        newConversation();
      }
      fetchConversations();
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  }, [currentConvId, newConversation, fetchConversations]);

  // Auto-scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // Send message
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: Message = {
      id: messageIdRef.current++,
      role: "user",
      content: text
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const body: any = { message: text };
      if (currentConvId) body.conversation_id = currentConvId;

      const res = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error("API request failed");
      }

      // Handle SSE streaming
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      const assistantMsgId = messageIdRef.current++;
      setMessages((prev) => [...prev, { id: assistantMsgId, role: "assistant", content: "" }]);

      let buffer = "";
      let accumulatedText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === "text") {
              accumulatedText += data.content;
              setMessages((prev) => {
                const updated = [...prev];
                const idx = updated.findIndex((m) => m.id === assistantMsgId);
                if (idx >= 0) {
                  updated[idx] = { ...updated[idx], content: accumulatedText };
                }
                return updated;
              });
            } else if (data.type === "done") {
              if (data.conversation_id && !currentConvId) {
                setCurrentConvId(data.conversation_id);
              }
              fetchConversations();
            }
          } catch (err) {
            // Skip invalid JSON
          }
        }
      }
    } catch (error) {
      console.error("Send message failed:", error);
      setMessages((prev) => [
        ...prev,
        { id: messageIdRef.current++, role: "assistant", content: "抱歉，发送消息失败。" }
      ]);
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden">
      {/* 背景层 */}
      {theme.backgroundType === "image" && theme.backgroundImage && (
        <div
          className="absolute inset-0 z-0"
          style={{
            backgroundImage: `url(${theme.backgroundImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            filter: `blur(${theme.backgroundBlur}px)`,
          }}
        />
      )}
      {theme.backgroundType === "solid" && (
        <div
          className="absolute inset-0 z-0"
          style={{ backgroundColor: theme.backgroundSolid }}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className="relative z-20 flex shrink-0 flex-col border-r shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)] backdrop-saturate-[180%] glass-surface"
        style={{
          width: `${theme.sidebarWidth}px`,
          borderColor: `rgba(255, 255, 255, ${theme.glassBorder})`,
          backgroundColor: `rgba(255, 255, 255, ${theme.sidebarOpacity})`,
          backdropFilter: `blur(${theme.glassBlur}px)`,
        }}
      >
        <div className="border-b border-white/[0.08] px-4 py-4 shadow-[0_1px_0_0_rgba(255,255,255,0.05)]">
          <button
            onClick={newConversation}
            className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-[14px] border border-white/20 bg-gradient-to-b from-white/[0.15] to-white/[0.08] px-4 py-3 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.2),inset_0_1px_0_rgba(255,255,255,0.15)] transition-all active:scale-[0.97] hover:border-white/30 hover:from-white/[0.18] hover:to-white/[0.1]"
          >
            <Plus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
            新对话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-3">
          {conversations.length === 0 && (
            <div className="px-3 py-12 text-center text-[12px] text-white/40">
              暂无对话
            </div>
          )}
          <div className="space-y-1.5">
            {conversations.map((conv) => (
              <motion.button
                key={conv.id}
                onClick={() => loadConversation(conv.id)}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                className={cn(
                  "group relative flex w-full items-center gap-3 overflow-hidden rounded-xl px-3 py-3 text-left transition-all duration-200",
                  currentConvId === conv.id
                    ? "border border-[#0a84ff]/40 bg-gradient-to-br from-[#0a84ff]/[0.15] to-[#0a84ff]/[0.08] shadow-[0_2px_8px_rgba(10,132,255,0.15),inset_0_1px_0_rgba(10,132,255,0.3)] backdrop-blur-xl"
                    : "border border-transparent hover:border-white/10 hover:bg-white/[0.05] hover:shadow-[0_1px_4px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.05)]"
                )}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-all",
                    currentConvId === conv.id
                      ? "bg-gradient-to-br from-[#0a84ff]/30 to-[#0a84ff]/20 shadow-[0_2px_8px_rgba(10,132,255,0.3),inset_0_1px_0_rgba(255,255,255,0.2)]"
                      : "bg-white/[0.06]"
                  )}
                >
                  <MessageSquare
                    className={cn(
                      "h-4 w-4 transition-colors",
                      currentConvId === conv.id
                        ? "text-[#0a84ff] drop-shadow-[0_0_8px_rgba(10,132,255,0.8)]"
                        : "text-white/50"
                    )}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium text-white">
                    {conv.title}
                  </div>
                  <div className="text-[11px] text-white/40">
                    {conv.message_count} 条消息
                  </div>
                </div>
                <button
                  onClick={(e) => deleteConversation(conv.id, e)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg border border-[#ff453a]/30 bg-[#ff453a]/10 p-1.5 text-[#ff453a] opacity-0 shadow-[inset_0_1px_0_rgba(255,69,58,0.2)] backdrop-blur-sm transition-all hover:bg-[#ff453a]/20 group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </motion.button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <div className="relative border-b border-white/[0.08] bg-white/[0.02] shadow-[0_1px_0_0_rgba(255,255,255,0.05),0_1px_3px_rgba(0,0,0,0.1)] backdrop-blur-[80px] backdrop-saturate-[180%]">
          <div className="flex items-center gap-4 px-6 py-3.5">
            <motion.div
              className="relative flex h-10 w-10 items-center justify-center"
              whileHover={{ scale: 1.08, rotate: 5 }}
              transition={{ type: "spring", stiffness: 400, damping: 15 }}
            >
              <div className="absolute inset-0 animate-pulse rounded-[12px] bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] opacity-90 blur-xl" />
              <div className="absolute inset-0 rounded-[12px] bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] shadow-[0_4px_16px_rgba(10,132,255,0.4)]" />
              <div className="absolute inset-[1.5px] rounded-[10.5px] bg-[#1a1a1e]/90 backdrop-blur-sm" />
              <Sparkles className="relative h-5 w-5 text-[#0a84ff] drop-shadow-[0_0_8px_rgba(10,132,255,1)]" />
            </motion.div>
            <div className="min-w-0 flex-1">
              <h1 className="text-[15px] font-semibold leading-tight text-white">
                Sunday AI
              </h1>
              <p className="text-[12px] text-white/50">智能对话助手</p>
            </div>
          </div>
        </div>

        {/* Messages container - flex: 1 to fill space */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {messages.length === 0 && (
              <motion.div
                className="flex h-full flex-col items-center justify-center text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <motion.div
                  className="relative mb-6 flex h-24 w-24 items-center justify-center"
                  animate={{
                    scale: [1, 1.05, 1],
                    rotate: [0, 3, -3, 0],
                  }}
                  transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                >
                  <div className="absolute inset-0 animate-pulse rounded-[24px] bg-gradient-to-br from-[#0a84ff]/40 to-[#bf5af2]/30 blur-2xl" />
                  <div className="relative flex h-full w-full items-center justify-center rounded-[24px] border border-white/20 bg-gradient-to-br from-white/[0.15] to-white/[0.08] shadow-[0_8px_32px_rgba(10,132,255,0.2),inset_0_2px_0_rgba(255,255,255,0.2)] backdrop-blur-xl">
                    <Sparkles className="h-10 w-10 text-[#0a84ff] drop-shadow-[0_0_16px_rgba(10,132,255,0.8)]" />
                  </div>
                </motion.div>
                <h2 className="text-[22px] font-semibold text-white">开始新的对话</h2>
                <p className="mt-3 max-w-sm text-[14px] leading-relaxed text-white/60">
                  在下方输入框输入消息，开始与 AI 对话
                </p>
              </motion.div>
            )}

            <div className="mx-auto max-w-3xl space-y-6">
              <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 20, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  className={cn(
                    "flex gap-4",
                    msg.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {msg.role === "assistant" && (
                    <motion.div
                      className="relative mt-1 flex h-9 w-9 shrink-0 items-center justify-center"
                      initial={{ scale: 0, rotate: -90 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
                    >
                      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] opacity-90 blur-lg" />
                      <div className="relative flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] shadow-[0_2px_12px_rgba(10,132,255,0.4),inset_0_1px_0_rgba(255,255,255,0.3)]">
                        <Sparkles className="h-4 w-4 text-white drop-shadow-sm" />
                      </div>
                    </motion.div>
                  )}
                  <div
                    className={cn(
                      "flex max-w-[75%] flex-col",
                      msg.role === "user" && "items-end"
                    )}
                  >
                    <motion.div
                      whileHover={theme.enableAnimations ? { scale: 1.005, y: -1 } : {}}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                      className={cn(
                        "group relative overflow-hidden transition-all duration-200",
                        msg.role === "user"
                          ? "border shadow-[0_4px_16px_rgba(10,132,255,0.3),inset_0_1px_0_rgba(255,255,255,0.25)]"
                          : "border shadow-[0_4px_16px_rgba(0,0,0,0.15),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl"
                      )}
                      style={{
                        borderRadius: `${theme.bubbleRadius}px`,
                        ...(msg.role === "user" ? {
                          backgroundColor: theme.bubbleUserColor,
                          borderColor: `${theme.bubbleUserColor}40`,
                        } : {
                          backgroundColor: `rgba(255, 255, 255, ${theme.glassOpacity})`,
                          borderColor: `rgba(255, 255, 255, ${theme.glassBorder})`,
                          backdropFilter: `blur(${theme.glassBlur}px)`,
                        })
                      }}
                    >
                      {msg.role === "user" && theme.glassReflection && (
                        <div className="absolute inset-0 bg-gradient-to-br from-white/30 via-transparent to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100" />
                      )}
                      <div className="relative px-5 py-3.5">
                        <p
                          className={cn(
                            "whitespace-pre-wrap",
                            msg.role === "user" ? "font-medium text-white" : "text-white/90"
                          )}
                          style={{
                            fontSize: `${theme.fontSize}px`,
                            lineHeight: theme.lineHeight,
                          }}
                        >
                          {msg.content}
                        </p>
                      </div>
                    </motion.div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {sending && (
              <motion.div
                className="flex gap-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="relative mt-1 flex h-9 w-9 shrink-0 items-center justify-center">
                  <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] blur-lg" />
                  <div className="relative flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] shadow-[0_2px_12px_rgba(10,132,255,0.4)]">
                    <Sparkles className="h-4 w-4 animate-pulse text-white" />
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-[18px] border border-white/[0.15] bg-gradient-to-br from-white/[0.12] to-white/[0.06] px-5 py-4 shadow-[0_4px_16px_rgba(0,0,0,0.15),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl">
                  <LoadingDot delay={0} />
                  <LoadingDot delay={0.15} />
                  <LoadingDot delay={0.3} />
                </div>
              </motion.div>
            )}
            <div ref={endRef} />
          </div>
        </div>

          {/* Input - flex-shrink: 0 to prevent compression */}
          <div className={cn(
            "flex-shrink-0 border-t border-white/[0.08] bg-white/[0.02] backdrop-blur-[80px] backdrop-saturate-[180%] px-6 py-6",
            messages.length === 0 && "mt-auto" // Push to bottom when empty
          )}>
            <div className="w-full max-w-3xl">
              <div
                className={cn(
                  "relative w-full rounded-[20px] border backdrop-blur-[60px] transition-all duration-300 glass-surface",
                  input.trim()
                    ? "border-[#0a84ff]/30 bg-white/[0.12] shadow-[0_8px_32px_rgba(10,132,255,0.2)]"
                    : "border-white/[0.15] bg-white/[0.08] shadow-[0_4px_16px_rgba(0,0,0,0.1)]"
                )}
                style={{ boxSizing: 'border-box' }}
              >
                <div className="flex items-center gap-4 p-4">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入消息..."
                    className="flex-1 resize-none bg-transparent text-[15px] text-white outline-none placeholder:text-white/40"
                    style={{
                      lineHeight: '24px',
                      padding: '10px 0',
                      minHeight: '44px',
                      maxHeight: '120px',
                    }}
                  />
                  <motion.button
                    onClick={sendMessage}
                    disabled={!input.trim() || sending}
                    aria-label="发送"
                    whileHover={input.trim() && !sending ? { scale: 1.05 } : {}}
                    whileTap={input.trim() && !sending ? { scale: 0.95 } : {}}
                    className={cn(
                      "relative flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-[12px] transition-all duration-200 ripple-effect",
                      input.trim() && !sending
                        ? "bg-[#0a84ff] text-white shadow-[0_4px_16px_rgba(10,132,255,0.5)]"
                        : "border border-white/10 bg-white/[0.05] text-white/30"
                    )}
                  >
                    <Send className="relative h-5 w-5" />
                  </motion.button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingDot({ delay = 0 }: { delay?: number }) {
  return (
    <motion.span
      className="h-2 w-2 rounded-full bg-white/60"
      animate={{ opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1.2, repeat: Infinity, delay, ease: "easeInOut" }}
    />
  );
}
