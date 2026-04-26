"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, Upload, Map, Rewind, Brain, Command } from "lucide-react";

export default function NavPill() {
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href;

  return (
    <nav
      className="fixed top-6 left-1/2 z-50 surface-glass flex items-center gap-1 px-2 py-2 rounded-full"
      style={{ transform: "translateX(-50%)", fontSize: "0.875rem" }}
    >
      <Link href="/" className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors"
            style={isActive("/") ? { background: "rgba(200,126,87,0.12)", color: "var(--ember-300)" } : { color: "var(--ink-0)" }}>
        <Shield className="w-4 h-4" strokeWidth={1.5} style={{ color: "var(--ember-500)" }} />
        <span className="type-display" style={{ fontSize: "1rem" }}>Prahari</span>
      </Link>

      <div className="w-px h-4" style={{ background: "var(--glass-stroke)" }} />

      <NavLink href="/ingest" active={isActive("/ingest")} icon={<Upload className="w-3.5 h-3.5" strokeWidth={1.5} />}>Ingest</NavLink>
      <NavLink href="/live" active={isActive("/live")} icon={<Map className="w-3.5 h-3.5" strokeWidth={1.5} />}>Live</NavLink>
      <NavLink href="/replay" active={isActive("/replay")} icon={<Rewind className="w-3.5 h-3.5" strokeWidth={1.5} />}>Replay</NavLink>
      <NavLink href="/dispatch" active={isActive("/dispatch")} icon={<Brain className="w-3.5 h-3.5" strokeWidth={1.5} />}>Dispatch</NavLink>

      <div className="w-px h-4" style={{ background: "var(--glass-stroke)" }} />

      <button
        className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors"
        style={{ color: "var(--ink-400)", background: "transparent", border: "none", cursor: "pointer", fontSize: "0.875rem" }}
      >
        <Command className="w-3.5 h-3.5" strokeWidth={1.5} />
        <span className="type-mono" style={{ fontSize: "0.75rem" }}>K</span>
      </button>
    </nav>
  );
}

function NavLink({ href, children, icon, active }: { href: string; children: React.ReactNode; icon: React.ReactNode; active: boolean }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors"
      style={active
        ? { background: "rgba(200,126,87,0.12)", color: "var(--ember-300)" }
        : { color: "var(--ink-200)" }
      }
    >
      {icon}
      <span>{children}</span>
    </Link>
  );
}
