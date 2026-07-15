"use client";

import { useEffect, useState } from "react";
import { Users, TrendingUp, Activity, Shield } from "lucide-react";
import { apiFetch } from "@/lib/api-key";

type AdminTab = "users" | "usage" | "health";

type UserInfo = {
  id: string; username: string; has_token: boolean;
  created_at: string; memory_count: number; conv_count: number;
};

type UsageInfo = {
  users: number; total_memories: number; total_conversations: number;
  engines: { id: string; quality: number; calls: number; primary: boolean }[];
  runtime: {
    messages_today: number; calls_today: number; tokens_today: number;
    cost_today: number; avg_latency_ms: number;
  };
};

type HealthInfo = {
  server: { version: string; python: string };
  db: { type: string; users: number; memories: number; conversations: number };
  engines: { id: string; quality: number; healthy: boolean; calls: number }[];
  embedder: string; embedding_dim: number;
};

export function AdminPanel() {
  const [tab, setTab] = useState<AdminTab>("users");
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData(tab);
  }, [tab]);

  async function fetchData(t: AdminTab) {
    setLoading(true); setError("");
    try {
      if (t === "users") {
        const r = await apiFetch("/api/admin/users");
        if (!r.ok) throw new Error((await r.json()).detail || "Forbidden");
        const d = await r.json();
        setUsers(d.users || []);
      } else if (t === "usage") {
        const r = await apiFetch("/api/admin/usage");
        if (!r.ok) throw new Error((await r.json()).detail || "Forbidden");
        setUsage(await r.json());
      } else {
        const r = await apiFetch("/api/admin/health");
        if (!r.ok) throw new Error((await r.json()).detail || "Forbidden");
        setHealth(await r.json());
      }
    } catch (e: any) {
      setError(e.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  const tabs: { id: AdminTab; label: string; icon: React.ReactNode }[] = [
    { id: "users", label: "用户管理", icon: <Users className="h-4 w-4" /> },
    { id: "usage", label: "用量概览", icon: <TrendingUp className="h-4 w-4" /> },
    { id: "health", label: "系统健康", icon: <Activity className="h-4 w-4" /> },
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-border px-4 py-3">
        <Shield className="h-4 w-4 text-accent mr-2" />
        <span className="text-[13px] font-semibold text-primary mr-4">管理控制台</span>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] transition-colors ${
              tab === t.id
                ? "bg-[var(--surface-2)] text-primary"
                : "text-tertiary hover:text-secondary"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && <div className="text-center text-tertiary py-12">Loading...</div>}
        {error && (
          <div className="rounded-[12px] border border-[color:var(--danger)]/30 bg-[color:var(--danger)]/10 p-4 text-[13px] text-danger">
            {error}
            <p className="mt-2 text-[11px] text-tertiary">
              需要管理员权限才能访问此页面。请使用 API Key 登录 Console。
            </p>
          </div>
        )}

        {!loading && !error && tab === "users" && <UsersTab users={users} />}
        {!loading && !error && tab === "usage" && usage && <UsageTab usage={usage} />}
        {!loading && !error && tab === "health" && health && <HealthTab health={health} />}
      </div>
    </div>
  );
}

// ── Users Tab ──────────────────────────────────────────────────────

function UsersTab({ users }: { users: UserInfo[] }) {
  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <div className="rounded-[10px] border border-border bg-[var(--surface)] px-4 py-3">
          <div className="text-[11px] text-tertiary uppercase tracking-wider">注册用户</div>
          <div className="text-[24px] font-semibold text-accent">{users.length}</div>
        </div>
        <div className="rounded-[10px] border border-border bg-[var(--surface)] px-4 py-3">
          <div className="text-[11px] text-tertiary uppercase tracking-wider">已登录</div>
          <div className="text-[24px] font-semibold text-success">
            {users.filter((u) => u.has_token).length}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-[12px] border border-border">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border bg-[var(--surface-2)] text-left text-[11px] text-tertiary uppercase">
              <th className="px-4 py-2.5">用户名</th>
              <th className="px-4 py-2.5">User ID</th>
              <th className="px-4 py-2.5">状态</th>
              <th className="px-4 py-2.5">记忆数</th>
              <th className="px-4 py-2.5">注册时间</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-border hover:bg-[var(--surface-2)]/50">
                <td className="px-4 py-2.5 font-medium text-primary">{u.username}</td>
                <td className="px-4 py-2.5 font-mono text-[11px] text-tertiary">
                  {u.id.substring(0, 12)}...
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] ${
                      u.has_token
                        ? "bg-[color:var(--success)]/15 text-success"
                        : "bg-[color:var(--tertiary)]/10 text-tertiary"
                    }`}
                  >
                    {u.has_token ? "在线" : "离线"}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-secondary">{u.memory_count}</td>
                <td className="px-4 py-2.5 text-[12px] text-tertiary">{u.created_at}</td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-tertiary">
                  暂无注册用户
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Usage Tab ──────────────────────────────────────────────────────

function UsageTab({ usage }: { usage: UsageInfo }) {
  return (
    <div className="space-y-5">
      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="用户数" value={usage.users} color="var(--accent)" />
        <MetricCard label="总记忆" value={usage.total_memories} color="#64d2ff" />
        <MetricCard label="总对话" value={usage.total_conversations} color="var(--success)" />
        <MetricCard
          label="今日调用"
          value={usage.runtime.calls_today}
          color="#bf5af2"
        />
      </div>

      {/* Runtime stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="今日消息" value={usage.runtime.messages_today} color="var(--warning)" />
        <MetricCard label="今日 Token" value={usage.runtime.tokens_today.toLocaleString()} color="var(--warning)" />
        <MetricCard label="今日费用" value={`$${usage.runtime.cost_today.toFixed(4)}`} color="var(--danger)" />
        <MetricCard label="平均延迟" value={`${usage.runtime.avg_latency_ms}ms`} color="var(--accent)" />
      </div>

      {/* Engine usage */}
      <div>
        <h3 className="mb-3 text-[13px] font-semibold text-primary">引擎调用分布</h3>
        <div className="overflow-x-auto rounded-[12px] border border-border">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border bg-[var(--surface-2)] text-left text-[11px] text-tertiary uppercase">
                <th className="px-4 py-2.5">引擎</th>
                <th className="px-4 py-2.5">质量分</th>
                <th className="px-4 py-2.5">调用次数</th>
                <th className="px-4 py-2.5">主力</th>
              </tr>
            </thead>
            <tbody>
              {usage.engines.map((e) => (
                <tr key={e.id} className="border-b border-border">
                  <td className="px-4 py-2.5 font-medium text-primary">{e.id}</td>
                  <td className="px-4 py-2.5 text-secondary">{(e.quality * 100).toFixed(0)}%</td>
                  <td className="px-4 py-2.5 text-secondary">{e.calls}</td>
                  <td className="px-4 py-2.5">
                    {e.primary && (
                      <span className="rounded-full bg-[color:var(--accent)]/15 px-2 py-0.5 text-[10px] text-accent">
                        Primary
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Health Tab ─────────────────────────────────────────────────────

function HealthTab({ health }: { health: HealthInfo }) {
  return (
    <div className="space-y-5">
      {/* Server */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="版本" value={`v${health.server.version}`} color="var(--accent)" />
        <MetricCard label="数据库" value={health.db.type} color="#64d2ff" />
        <MetricCard label="嵌入器" value={health.embedder} color="var(--success)" />
        <MetricCard label="嵌入维度" value={health.embedding_dim} color="#bf5af2" />
      </div>

      {/* Engine health */}
      <div>
        <h3 className="mb-3 text-[13px] font-semibold text-primary">引擎状态</h3>
        <div className="overflow-x-auto rounded-[12px] border border-border">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border bg-[var(--surface-2)] text-left text-[11px] text-tertiary uppercase">
                <th className="px-4 py-2.5">引擎 ID</th>
                <th className="px-4 py-2.5">质量分</th>
                <th className="px-4 py-2.5">状态</th>
                <th className="px-4 py-2.5">调用次数</th>
              </tr>
            </thead>
            <tbody>
              {health.engines.map((e) => (
                <tr key={e.id} className="border-b border-border">
                  <td className="px-4 py-2.5 font-medium text-primary">{e.id}</td>
                  <td className="px-4 py-2.5 text-secondary">{(e.quality * 100).toFixed(0)}%</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] ${
                        e.healthy
                          ? "bg-[color:var(--success)]/15 text-success"
                          : "bg-[color:var(--danger)]/15 text-danger"
                      }`}
                    >
                      {e.healthy ? "正常" : "异常"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-secondary">{e.calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-[10px] border border-border bg-[var(--surface)] px-4 py-3">
      <div className="text-[10px] text-tertiary uppercase tracking-wider">{label}</div>
      <div className="mt-1 text-[20px] font-semibold" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
