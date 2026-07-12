import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/shell/app-shell";

export const metadata: Metadata = {
  title: "Sunday OS · Console",
  description:
    "The visual operating system of an intelligent cognitive architecture.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh" className="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
