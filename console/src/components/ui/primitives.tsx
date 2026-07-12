"use client";

import { cn } from "@/lib/cn";

/* ── Section header ─────────────────────────────────────── */
export function SectionTitle({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between">
      <div>
        <h2 className="text-subtitle text-primary">{title}</h2>
        {hint && <p className="mt-0.5 text-caption text-tertiary">{hint}</p>}
      </div>
      {action}
    </div>
  );
}

/* ── Card ───────────────────────────────────────────────── */
export function Card({
  className,
  children,
  glass,
}: {
  className?: string;
  children: React.ReactNode;
  glass?: boolean;
}) {
  return (
    <div className={cn(glass ? "glass rounded-lg" : "card", className)}>{children}</div>
  );
}

/* ── Sparkline (area) ───────────────────────────────────── */
export function Sparkline({
  data,
  color = "var(--accent)",
  height = 44,
  className,
}: {
  data: number[];
  color?: string;
  height?: number;
  className?: string;
}) {
  const w = 120;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1);
  const pts = data.map((d, i) => [i * step, height - ((d - min) / span) * (height - 6) - 3]);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${w},${height} L0,${height} Z`;
  const gid = `spark-${color.replace(/[^a-z0-9]/gi, "")}`;

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className={cn("w-full", className)} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ── Donut / radial percentage ──────────────────────────── */
export function Donut({
  value,
  size = 72,
  stroke = 7,
  color = "var(--accent)",
  label,
}: {
  value: number; // 0..1
  size?: number;
  stroke?: number;
  color?: string;
  label?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - value);
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 600ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[15px] font-semibold tabular-nums tnum">{Math.round(value * 100)}%</span>
        {label && <span className="text-[9px] text-tertiary">{label}</span>}
      </div>
    </div>
  );
}

/* ── Radar chart ────────────────────────────────────────── */
export function Radar({
  axes,
  values,
  size = 240,
  color = "var(--accent)",
}: {
  axes: string[];
  values: number[]; // 0..1 aligned with axes
  size?: number;
  color?: string;
}) {
  const cx = size / 2;
  const cy = size / 2;
  const R = size / 2 - 34;
  const n = axes.length;
  const angle = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (i: number, radius: number): [number, number] => [
    cx + Math.cos(angle(i)) * radius,
    cy + Math.sin(angle(i)) * radius,
  ];
  const rings = [0.25, 0.5, 0.75, 1];
  const poly = values.map((v, i) => point(i, R * v).join(",")).join(" ");

  return (
    <svg width={size} height={size} className="overflow-visible">
      {rings.map((rr) => (
        <polygon
          key={rr}
          points={axes.map((_, i) => point(i, R * rr).join(",")).join(" ")}
          fill="none"
          stroke="var(--border)"
          strokeWidth="1"
        />
      ))}
      {axes.map((_, i) => {
        const [x, y] = point(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--border)" strokeWidth="1" />;
      })}
      <polygon points={poly} fill={color} fillOpacity="0.16" stroke={color} strokeWidth="1.8" />
      {values.map((v, i) => {
        const [x, y] = point(i, R * v);
        return <circle key={i} cx={x} cy={y} r="2.6" fill={color} />;
      })}
      {axes.map((a, i) => {
        const [x, y] = point(i, R + 18);
        return (
          <text
            key={a}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-[color:var(--text-tertiary)] text-[10px]"
          >
            {a}
          </text>
        );
      })}
    </svg>
  );
}

/* ── Status badge ───────────────────────────────────────── */
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "ok" | "warn" | "danger" | "accent";
  children: React.ReactNode;
}) {
  const map = {
    neutral: "border-border text-secondary",
    ok: "border-[color:var(--success)]/30 bg-[color:var(--success)]/10 text-success",
    warn: "border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 text-warning",
    danger: "border-[color:var(--danger)]/30 bg-[color:var(--danger)]/10 text-danger",
    accent: "border-[color:var(--accent)]/30 bg-[var(--accent-soft)] text-accent",
  };
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium", map[tone])}>
      {children}
    </span>
  );
}
