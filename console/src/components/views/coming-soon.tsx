"use client";

import { NAV } from "@/config/nav";
import { useUI } from "@/store/ui";
import { useI18n } from "@/i18n";
import { ArrowUpRight } from "lucide-react";

export function ComingSoon({ title }: { title: string }) {
  const { view, setView } = useUI();
  const { t } = useI18n();
  const item = NAV.find((n) => n.slug === view) ?? NAV.find((n) => n.label === title);
  const Icon = item?.icon;

  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="glass max-w-md rounded-glass p-10 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-md border border-border text-accent">
          {Icon && <Icon className="h-6 w-6" />}
        </div>
        <h2 className="text-title text-primary">{item ? t(`nav.${item.slug}`) : title}</h2>
        <p className="mx-auto mt-2 max-w-xs text-[14px] leading-relaxed text-secondary">
          {t("soon.body")}
        </p>
        <button
          onClick={() => setView("")}
          className="mt-6 inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-2 text-[13px] text-secondary transition-colors hover:border-border-strong hover:text-primary"
        >
          {t("soon.back")}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
