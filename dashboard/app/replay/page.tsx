"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Pause, Rewind } from "lucide-react";
import timelineData from "./timeline.json";
import SignalRibbon from "../../components/SignalRibbon";
import AgentTerminal from "../../components/AgentTerminal";
import Narrator from "../../components/Narrator";

const timeline = timelineData as any;

export default function ReplayPage() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [confidence, setConfidence] = useState(0);
  const [visibleSignals, setVisibleSignals] = useState<any[]>([]);
  const [terminalLines, setTerminalLines] = useState<any[]>([]);
  const [phase, setPhase] = useState<"idle" | "signals" | "thinking" | "emitted" | "coordinator" | "complete">("idle");
  const [flash, setFlash] = useState(false);

  // Space-to-play keyboard handler
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.code === "Space" && target.tagName !== "INPUT" && target.tagName !== "TEXTAREA" && target.tagName !== "BUTTON") {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const events = timeline.events;
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const advanceEvent = useCallback(() => {
    setCurrentIndex((prev) => {
      const next = prev + 1;
      if (next >= events.length) {
        setIsPlaying(false);
        setPhase("complete");
        return prev;
      }

      const event = events[next];

      if (event.source === "openweather" || event.source === "reddit" || event.source?.startsWith("rss") || event.source === "imd" || event.source === "cwc") {
        setVisibleSignals((prev) => [...prev, { ...event, _i: next }]);
        setPhase("signals");
      } else if (event.source === "prahari_watcher") {
        setPhase("thinking");
        if (event.data?.confidence_history) {
          event.data.confidence_history.forEach((val: number, i: number) => {
            setTimeout(() => setConfidence(val), i * 600);
          });
        }
        if (event.data?.action === "threat_emitted") {
          setFlash(true);
          setTimeout(() => setFlash(false), 200);
          setPhase("emitted");
          setTimeout(() => setPhase("coordinator"), 1200);
          setConfidence(event.data.confidence);
        }
      } else if (event.source === "prahari_coordinator") {
        if (event.data?.calls) {
          event.data.calls.forEach((call: string, i: number) => {
            setTimeout(() => {
              setTerminalLines((prev) => [...prev, { id: `call-${next}-${i}`, type: "fn" as const, text: call }]);
            }, i * 400);
          });
        }
        if (event.data?.matched_count) {
          setTimeout(() => {
            setTerminalLines((prev) => [...prev, {
              id: `result-${next}`, type: "result" as const,
              text: `Matched ${event.data.matched_count} volunteers in 2.3 seconds \u00b7 8 boats \u00b7 4 medical \u00b7 2 logistics`,
            }]);
          }, 2000);
        }
      } else if (event.source === "news_first_article" || event.source === "govt_advisory") {
        setPhase("complete");
      }

      return next;
    });
  }, [events]);

  useEffect(() => {
    if (isPlaying) {
      const interval = Math.max(400, 3500 / speed);
      timerRef.current = setInterval(advanceEvent, interval);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, speed, advanceEvent]);

  const reset = () => {
    setIsPlaying(false);
    setCurrentIndex(-1);
    setVisibleSignals([]);
    setTerminalLines([]);
    setConfidence(0);
    setPhase("idle");
  };

  const currentTime = currentIndex >= 0
    ? new Date(events[currentIndex].time).toLocaleTimeString("en-IN", {
        hour: "2-digit", minute: "2-digit", hour12: true, timeZone: "Asia/Kolkata",
      })
    : "06:00 AM";

  return (
    <div className="min-h-screen relative overflow-hidden transition-colors" style={{
      paddingTop: "96px",
      background: phase === "emitted" || phase === "coordinator" || phase === "complete"
        ? "linear-gradient(180deg, #121210, rgba(61,36,24,0.06))"
        : "var(--ink-900)",
      transitionDuration: "1000ms",
    }}>
      {/* Flash */}
      <AnimatePresence>
        {flash && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.3 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 pointer-events-none z-40"
            style={{ background: "var(--ember-500)" }} />
        )}
      </AnimatePresence>

      {/* Signal Ribbon */}
      <div className="container" style={{ marginBottom: "32px" }}>
        <SignalRibbon signals={visibleSignals} confidence={confidence} phase={phase} />
      </div>

      {/* Date / Time */}
      <div className="container" style={{ marginBottom: "8px" }}>
        <div className="flex justify-between items-start">
          <div>
            <div style={{ fontSize: "13px", color: "var(--ink-400)" }}>Kerala Floods &middot; 15 August 2018</div>
            <div className="type-mono mt-2" style={{ fontSize: "3rem", fontWeight: 500, lineHeight: 1, letterSpacing: "-0.02em" }}>
              {currentTime} <span style={{ color: "var(--ink-500)", fontSize: "1.25rem", fontWeight: 400 }}>IST</span>
            </div>
          </div>
          <div className="type-mono text-right" style={{ fontSize: "12px", color: "var(--ink-400)" }}>
            <div>Alappuzha District</div>
            <div>9.4981&deg;N &middot; 76.3388&deg;E</div>
          </div>
        </div>
      </div>

      {/* Narrator */}
      <div className="container" style={{ marginBottom: "32px" }}>
        <Narrator phase={phase} />
      </div>

      {/* Main focal area */}
      <div className="container-narrow" style={{ minHeight: "50vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <AnimatePresence mode="wait">
          {phase === "idle" && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center">
              <p style={{ fontSize: "22px", fontWeight: 500, color: "var(--ink-200)" }}>
                Press play. We&apos;ll walk you through the morning of August 15, 2018.
              </p>
              <p className="mt-4" style={{ fontSize: "14px", color: "var(--ink-500)" }}>
                Prahari will process only the public data that existed at each moment.
              </p>
              <p className="mt-12 mx-auto" style={{ fontSize: "13px", color: "var(--ink-500)", maxWidth: "550px", fontStyle: "italic", borderTop: "1px solid var(--glass-stroke)", paddingTop: "24px" }}>
                *Sources marked IMD and CWC are historically verified facts, reconstructed from government press releases and archived news reporting.
              </p>
            </motion.div>
          )}

          {phase === "signals" && (
            <motion.div key="signals" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ width: "100%" }}>
              <h2 className="mb-12 text-center" style={{ fontSize: "28px", fontWeight: 600 }}>
                Signals are starting to arrive
              </h2>
              <div className="space-y-4">
                <AnimatePresence>
                  {visibleSignals.slice(-4).map((s: any) => (
                    <SignalRow key={s._i} signal={s} />
                  ))}
                </AnimatePresence>
              </div>
            </motion.div>
          )}

          {phase === "thinking" && (
            <motion.div key="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center" style={{ width: "100%" }}>
              <div className="mb-12">
                <p style={{ fontSize: "28px", fontWeight: 600, lineHeight: 1.3 }}>Five sources now agree.</p>
                <p style={{ fontSize: "22px", fontWeight: 400, color: "var(--ember-500)", marginTop: "8px" }}>
                  The Watcher is weighing them.
                </p>
              </div>
              <ConfidenceMeter value={confidence} />
            </motion.div>
          )}

          {phase === "emitted" && (
            <motion.div key="emitted" initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ opacity: 0 }} className="text-center">
              <motion.p className="type-display" style={{ fontSize: "3.5rem", color: "var(--ember-500)" }}
                animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                The Watcher has alerted.
              </motion.p>
              <p className="mt-4" style={{ fontSize: "14px", color: "var(--ink-400)" }}>
                Confidence 78% &middot; Flood &middot; Alappuzha
              </p>
            </motion.div>
          )}

          {(phase === "coordinator" || phase === "complete") && (
            <motion.div key="coord" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} style={{ width: "100%" }}>
              <h2 className="mb-8 text-center" style={{ fontSize: "24px", fontWeight: 600 }}>
                Now the Coordinator takes over.
              </h2>
              <AgentTerminal lines={terminalLines} agent="coordinator" />
              {phase === "complete" && <GroundTruthReveal />}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Playback */}
      <div className="fixed bottom-6 left-1/2 surface-glass rounded-full flex items-center gap-1 px-3 py-2 z-30"
           style={{ transform: "translateX(-50%)" }}>
        <button onClick={reset} className="btn btn-ghost" style={{ height: "36px", padding: "0 14px" }}>
          <Rewind className="w-4 h-4" strokeWidth={1.5} />
        </button>
        <button onClick={() => setIsPlaying(!isPlaying)} className="btn btn-primary" style={{ height: "36px", padding: "0 18px" }}>
          {isPlaying ? <Pause className="w-4 h-4" strokeWidth={1.5} /> : <Play className="w-4 h-4" strokeWidth={1.5} />}
          <span>{isPlaying ? "Pause" : "Play"}</span>
        </button>
        <div className="w-px h-5 mx-1" style={{ background: "var(--glass-stroke)" }} />
        {[1, 10, 60].map((s) => (
          <button key={s} onClick={() => setSpeed(s)} className="type-mono transition-colors"
            style={{
              padding: "0 14px", height: "36px", borderRadius: "9999px", fontSize: "12px", border: "none", cursor: "pointer",
              background: speed === s ? "var(--ember-500)" : "transparent",
              color: speed === s ? "var(--ink-950)" : "var(--ink-400)",
            }}>
            {s}x
          </button>
        ))}
        <div className="w-px h-5 mx-1" style={{ background: "var(--glass-stroke)" }} />
        <span style={{ fontSize: "12px", color: "var(--ink-500)", padding: "0 8px" }}>Space to play</span>
      </div>
    </div>
  );
}

function SignalRow({ signal }: { signal: any }) {
  const sourceMap: Record<string, { color: string; label: string }> = {
    openweather: { color: "var(--signal-ocean)", label: "OpenWeather" },
    reddit: { color: "var(--signal-sand)", label: "Reddit" },
    rss_mathrubhumi: { color: "var(--signal-moss)", label: "Mathrubhumi" },
    imd: { color: "var(--ember-500)", label: "IMD" },
    cwc: { color: "#60a5fa", label: "CWC" },
  };
  const src = sourceMap[signal.source] || { color: "var(--ink-400)", label: signal.source };
  const content = signal.data?.title || signal.data?.title_en || signal.data?.content || signal.data?.weather_desc || signal.data?.body?.slice(0, 80) || "";
  const detail = signal.data?.rainfall_mm_3h ? `${signal.data.rainfall_mm_3h}mm rainfall`
    : signal.data?.alert_level ? `${signal.data.alert_level.toUpperCase()} alert`
    : signal.data?.capacity_pct ? `${signal.data.capacity_pct}% capacity`
    : "";

  return (
    <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] as const }}
      className="surface rounded-md px-5 py-4 flex items-start gap-4">
      <div className="self-stretch rounded-full" style={{ width: "3px", background: src.color, minHeight: "40px" }} />
      <div className="flex-1 min-w-0">
        <div className="type-mono mb-1" style={{ fontSize: "12px", color: src.color }}>{src.label}</div>
        <div style={{ fontSize: "14px", color: "var(--ink-0)", lineHeight: 1.5 }}>{content}</div>
        {detail && <div className="type-mono mt-1" style={{ fontSize: "12px", color: "var(--ember-500)" }}>{detail}</div>}
      </div>
    </motion.div>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ maxWidth: "400px", margin: "0 auto" }}>
      <div className="flex justify-between items-baseline mb-3">
        <span style={{ fontSize: "13px", color: "var(--ink-400)" }}>Confidence</span>
        <span className="type-mono" style={{ fontSize: "36px", fontWeight: 500, color: pct >= 65 ? "var(--ember-500)" : "var(--signal-sand)" }}>{pct}%</span>
      </div>
      <div className="meter-track" style={{ height: "3px" }}>
        <motion.div className="meter-fill" initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: [0.25, 1, 0.5, 1] as const }} style={{ height: "100%" }} />
      </div>
      {pct >= 65 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 text-center"
          style={{ fontSize: "13px", color: "var(--ember-500)" }}>
          Threshold crossed
        </motion.div>
      )}
    </div>
  );
}

function GroundTruthReveal() {
  return (
    <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 3, duration: 0.8 }}
      className="surface rounded-lg p-8 mt-16">
      <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--ink-400)", marginBottom: "24px" }}>
        For comparison &mdash; what actually happened that morning
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "32px" }}>
        <TimelineEntry time="08:14" label="Prahari alert" color="var(--ember-500)" note="Would have fired" />
        <TimelineEntry time="08:47" label="First news article" color="var(--signal-sand)" note="33 min later" />
        <TimelineEntry time="10:15" label="Govt advisory" color="var(--signal-rust)" note="2h 1min later" />
      </div>
      <div className="mt-8 pt-6 text-center" style={{ borderTop: "1px solid var(--glass-stroke)" }}>
        <p className="type-display" style={{ fontSize: "1.5rem" }}>Two and a half hours of head start.</p>
        <p className="mt-2" style={{ fontSize: "13px", color: "var(--ink-400)" }}>
          Official death toll: 483 &middot; Displaced: 1,000,000
        </p>
      </div>
    </motion.div>
  );
}

function TimelineEntry({ time, label, color, note }: { time: string; label: string; color: string; note: string }) {
  return (
    <div>
      <div className="type-mono" style={{ fontSize: "36px", fontWeight: 500, color, lineHeight: 1 }}>{time}</div>
      <div className="mt-2" style={{ fontSize: "14px", fontWeight: 500, color: "var(--ink-200)" }}>{label}</div>
      <div className="mt-1" style={{ fontSize: "13px", color: "var(--ink-400)" }}>{note}</div>
    </div>
  );
}
