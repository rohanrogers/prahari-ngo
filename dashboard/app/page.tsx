"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import IngestorGlyph from "../components/glyphs/IngestorGlyph";
import WatcherGlyph from "../components/glyphs/WatcherGlyph";
import CoordinatorGlyph from "../components/glyphs/CoordinatorGlyph";
import DispatchGlyph from "../components/glyphs/DispatchGlyph";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* HERO */}
      <section className="hero-section min-h-[92vh] flex flex-col justify-between relative overflow-hidden" style={{ paddingTop: "128px", paddingBottom: "64px" }}>
        <div className="container relative">
          {/* Date stamp */}
          <div className="absolute top-0 right-0 type-mono text-right" style={{ fontSize: "12px", color: "var(--ink-400)" }}>
            <div>Kerala, India</div>
            <div>15 August 2018</div>
            <div className="mt-1" style={{ color: "var(--ember-500)" }}>06:12 AM IST</div>
          </div>

          {/* Ember glow */}
          <div className="absolute pointer-events-none" style={{
            bottom: "-160px", left: "-160px", width: "600px", height: "600px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(200,126,87,0.1) 0%, transparent 70%)", filter: "blur(60px)",
          }} />

          <div style={{ maxWidth: "720px" }}>
            <motion.h1
              initial={{ y: 20 }}
              animate={{ y: 0 }}
              transition={{ duration: 1 }}
              className="type-display"
              style={{ fontSize: "clamp(3rem, 8vw, 5.5rem)" }}
            >
              The sentinel<br />
              that{" "}
              <span style={{
                background: "linear-gradient(135deg, var(--ember-500), var(--ember-300))",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}>
                watches
              </span>{" "}
              for you.
            </motion.h1>

            <motion.p
              initial={{ y: 12 }}
              animate={{ y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="mt-8"
              style={{ maxWidth: "560px", fontSize: "17px", color: "var(--ink-200)", lineHeight: 1.7 }}
            >
              In August 2018, the worst flood in a century killed 483 people in Kerala.
              Hundreds of NGOs, thousands of volunteers, coordinated through WhatsApp and paper registers.
              Prahari is what should have existed that morning.
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              className="mt-10 flex gap-3"
            >
              <Link href="/replay" className="btn btn-primary">
                <span>Watch August 15, 2018</span>
                <ArrowUpRight className="w-4 h-4" strokeWidth={1.5} />
              </Link>
              <Link href="/ingest" className="btn btn-ghost">Try ingestion</Link>
            </motion.div>
          </div>
        </div>

        {/* Live Ticker */}
        <div className="container mt-16">
          <LiveTicker />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section-pad" style={{ paddingTop: "128px", paddingBottom: "128px", borderTop: "1px solid var(--glass-stroke)" }}>
        <div className="container">
          <div className="mb-16">
            <div className="flex items-baseline gap-3 mb-4">
              <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--ember-500)" }}>01</span>
              <h2 style={{ fontSize: "32px", fontWeight: 600, letterSpacing: "-0.02em" }}>How it works</h2>
            </div>
            <p style={{ fontSize: "17px", color: "var(--ink-200)", maxWidth: "560px", lineHeight: 1.6 }}>
              Three agents, each with one job, connected in a loop that runs continuously.
            </p>
          </div>

          <div className="agent-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "20px" }}>
            <AgentCase
              number="01"
              glyph={<IngestorGlyph className="w-6 h-6" />}
              color="var(--signal-ocean)"
              name="Ingestor"
              summary="Reads what NGOs already have."
              body="WhatsApp exports, PDF signup forms, photographs of handwritten registers, Excel sheets with inconsistent columns. The Ingestor extracts volunteer records, normalizes skills, tags languages, geo-codes locations, and deduplicates across sources."
            />
            <AgentCase
              number="02"
              glyph={<WatcherGlyph className="w-6 h-6" />}
              color="var(--signal-sand)"
              name="Watcher"
              summary="Sees crises before the news does."
              body="Every five minutes, it scans OpenWeather across twelve Indian metros, five news RSS feeds, and eight Indian subreddits. A threat is only emitted when two independent sources agree. It grounds its confidence with Google Search."
            />
            <AgentCase
              number="03"
              glyph={<CoordinatorGlyph className="w-6 h-6" />}
              color="var(--signal-moss)"
              name="Coordinator"
              summary="Stages response before confirmation."
              body="When threat confidence crosses 65%, the Coordinator searches the volunteer graph by skill, geography, and language. It drafts outreach messages in Malayalam, Hindi, or Tamil — ready to send the moment a human confirms."
            />
            <AgentCase
              number="04"
              glyph={<DispatchGlyph className="w-6 h-6" />}
              color="#a855f7"
              name="Dispatch Optimizer"
              summary="Learns optimal assignment under chaos."
              body="A PPO reinforcement learning agent trained through 15 curriculum stages on Kerala flood scenarios. It balances skill matching, travel time, volunteer fatigue, and weather-conditional road closures to maximize lives reached per hour."
            />
          </div>
        </div>
      </section>

      {/* THE CLAIM */}
      <section className="section-pad" style={{ paddingTop: "128px", paddingBottom: "128px", borderTop: "1px solid var(--glass-stroke)" }}>
        <div className="container-narrow" style={{ textAlign: "center" }}>
          <div className="flex items-baseline gap-3 justify-center mb-8">
            <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--ember-500)" }}>02</span>
            <h2 style={{ fontSize: "24px", fontWeight: 600, letterSpacing: "-0.01em" }}>The claim we&apos;re making</h2>
          </div>
          <p className="type-display" style={{ fontSize: "2.25rem", lineHeight: 1.25 }}>
            Prahari would have alerted about Alappuzha flooding{" "}
            <span style={{ color: "var(--ember-500)" }}>33 minutes</span>
            {" "}before the first news article,
            and{" "}
            <span style={{ color: "var(--ember-500)" }}>two hours</span>
            {" "}before the first government advisory.
          </p>
          <p className="mt-8" style={{ fontSize: "14px", color: "var(--ink-400)" }}>
            Everything above is verifiable. We&apos;ll show you the replay.
          </p>
          <Link href="/replay" className="btn btn-primary mt-8 inline-flex">
            View the replay
            <ArrowUpRight className="w-4 h-4" strokeWidth={1.5} />
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="container footer-inner flex justify-between items-center" style={{
        paddingTop: "32px", paddingBottom: "32px",
        borderTop: "1px solid var(--glass-stroke)", fontSize: "13px", color: "var(--ink-400)",
      }}>
        <div>Built solo for GDG India &middot; Open source &middot; 2026</div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full pulse-breathe" style={{ background: "var(--signal-moss)" }} />
          <span className="type-mono" style={{ fontSize: "12px", letterSpacing: "0.05em" }}>LIVE</span>
        </div>
      </footer>
    </div>
  );
}

function AgentCase({ number, glyph, color, name, summary, body }: {
  number: string; glyph: React.ReactNode; color: string; name: string; summary: string; body: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.6 }}
      className="surface rounded-lg p-6 transition-colors"
    >
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center justify-center rounded-lg"
          style={{ width: "48px", height: "48px", background: `${color}14`, color }}>
          {glyph}
        </div>
        <div>
          <div style={{ fontSize: "12px", color: "var(--ink-400)", fontWeight: 500 }}>Agent {number}</div>
          <div style={{ fontSize: "17px", fontWeight: 600 }}>{name}</div>
        </div>
      </div>
      <h3 style={{ fontSize: "20px", fontWeight: 600, lineHeight: 1.3, marginBottom: "12px" }}>{summary}</h3>
      <p style={{ color: "var(--ink-200)", lineHeight: 1.65, fontSize: "14px" }}>{body}</p>
    </motion.div>
  );
}

function LiveTicker() {
  const messages = [
    { agent: "watcher", text: "scanning openweather \u00b7 12 cities" },
    { agent: "ingestor", text: "processing whatsapp_export.txt \u00b7 142 messages" },
    { agent: "watcher", text: "correlation found \u00b7 kozhikode \u00b7 confidence rising" },
    { agent: "coordinator", text: "ranking 47 volunteers \u00b7 ernakulam radius 15km" },
    { agent: "watcher", text: "threat dismissed \u00b7 insufficient source diversity" },
    { agent: "ingestor", text: "deduplicated 3 records \u00b7 phone match" },
  ];

  const agentColor = (a: string) =>
    a === "watcher" ? "var(--signal-sand)" : a === "ingestor" ? "var(--signal-ocean)" : "var(--signal-moss)";

  return (
    <div className="surface-glass rounded-lg py-3 px-4 overflow-hidden relative">
      <div className="type-mono absolute left-4 top-1/2 z-10 pr-6"
           style={{ fontSize: "12px", color: "var(--ink-400)", transform: "translateY(-50%)",
                    background: "linear-gradient(90deg, var(--ink-900), transparent)" }}>
        LIVE &middot;
      </div>
      <div className="ticker-track flex gap-12 whitespace-nowrap" style={{ paddingLeft: "60px", animation: "ticker-scroll 40s linear infinite" }}>
        {[...messages, ...messages].map((msg, i) => (
          <span key={i} className="type-mono" style={{ fontSize: "12px", color: "var(--ink-200)" }}>
            <span style={{ color: agentColor(msg.agent) }}>{"\u25b8"} {msg.agent}</span>
            <span className="ml-3" style={{ color: "var(--ink-400)" }}>{msg.text}</span>
          </span>
        ))}
      </div>
      <style>{`@keyframes ticker-scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }`}</style>
    </div>
  );
}
