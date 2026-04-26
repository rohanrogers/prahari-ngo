"use client";

import { motion, AnimatePresence } from "framer-motion";

interface SignalRibbonProps {
  signals: any[];
  confidence: number;
  phase: string;
}

const sourceColors: Record<string, string> = {
  openweather: "var(--signal-ocean)",
  reddit: "var(--signal-sand)",
  rss_mathrubhumi: "var(--signal-moss)",
  prahari_watcher: "var(--ember-500)",
};

export default function SignalRibbon({ signals, confidence, phase }: SignalRibbonProps) {
  return (
    <div className="relative surface rounded-lg h-16 overflow-hidden">
      <div
        className="absolute left-4 top-1/2 -translate-y-1/2 z-10 type-mono text-xs tracking-widest pr-10"
        style={{ color: "var(--ink-400)", background: "linear-gradient(90deg, var(--ink-800) 70%, transparent)" }}
      >
        SIGNAL STREAM
      </div>

      {/* Baseline */}
      <div className="absolute left-0 right-0 top-1/2 h-px" style={{ background: "var(--glass-stroke)" }} />

      {/* Grid ticks */}
      <div className="absolute inset-0 flex items-center">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="flex-1 h-px" style={{ background: i % 3 === 0 ? "var(--glass-stroke)" : "transparent" }} />
        ))}
      </div>

      {/* Signal pulses */}
      <div className="absolute inset-0 pl-32 pr-16 flex items-center">
        <AnimatePresence>
          {signals.slice(-20).map((signal: any) => (
            <motion.div
              key={signal._i}
              initial={{ x: "100%", opacity: 0, scale: 0.6 }}
              animate={{ x: "-100%", opacity: [0, 1, 1, 0], scale: 1 }}
              transition={{ duration: 8, ease: "linear" as const }}
              className="absolute"
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: sourceColors[signal.source] || "var(--ink-400)",
                boxShadow: `0 0 12px ${sourceColors[signal.source] || "var(--ink-400)"}`,
              }}
            />
          ))}
        </AnimatePresence>

        {/* Threat spike */}
        <AnimatePresence>
          {(phase === "emitted" || phase === "coordinator" || phase === "complete") && (
            <motion.div
              initial={{ opacity: 0, scaleY: 0 }}
              animate={{ opacity: 1, scaleY: 1 }}
              className="absolute right-12"
              style={{
                width: "4px",
                height: "40px",
                background: "var(--ember-500)",
                boxShadow: "0 0 20px var(--ember-500)",
                borderRadius: "2px",
              }}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Confidence readout */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 type-mono text-xs">
        <span style={{ color: "var(--ink-400)" }}>CONF </span>
        <span style={{ color: confidence > 0.65 ? "var(--ember-500)" : "var(--signal-sand)" }}>
          {Math.round(confidence * 100)}%
        </span>
      </div>
    </div>
  );
}
