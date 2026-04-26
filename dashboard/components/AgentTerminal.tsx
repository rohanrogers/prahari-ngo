"use client";

import { motion, AnimatePresence } from "framer-motion";

interface Line {
  id: string | number;
  type: "fn" | "result" | "reasoning" | "error";
  text: string;
}

const agentPrompts: Record<string, string> = {
  ingestor: "ingestor::",
  watcher: "watcher::",
  coordinator: "coord::",
};

const agentColors: Record<string, string> = {
  ingestor: "var(--signal-ocean)",
  watcher: "var(--signal-sand)",
  coordinator: "var(--signal-moss)",
};

export default function AgentTerminal({ lines, agent = "ingestor" }: { lines: Line[]; agent?: string }) {
  const promptColor = agentColors[agent] || "var(--ink-400)";
  const prompt = agentPrompts[agent] || "agent::";

  return (
    <div className="terminal">
      <div className="flex items-center justify-between mb-3 pb-3" style={{ borderBottom: "1px solid var(--glass-stroke)" }}>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--signal-rust)", opacity: 0.5 }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--signal-sand)", opacity: 0.5 }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--signal-moss)", opacity: 0.5 }} />
          </div>
          <span className="type-mono text-xs ml-3" style={{ color: "var(--ink-400)" }}>
            {agent}.log
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full pulse-breathe" style={{ background: promptColor }} />
          <span className="type-mono text-xs" style={{ color: promptColor }}>LIVE</span>
        </div>
      </div>

      <div className="space-y-1" style={{ minHeight: "200px", maxHeight: "400px", overflowY: "auto" }}>
        <AnimatePresence>
          {lines.map((line) => (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-2 type-agent"
            >
              <span style={{ color: promptColor, userSelect: "none" }}>{prompt}</span>
              {line.type === "fn" && <span className="terminal-fn">{line.text}</span>}
              {line.type === "result" && <span className="terminal-result">{"\u2192"} {line.text}</span>}
              {line.type === "reasoning" && <span style={{ color: "var(--ink-200)" }}>{line.text}</span>}
              {line.type === "error" && <span style={{ color: "var(--signal-rust)" }}>{"\u2717"} {line.text}</span>}
            </motion.div>
          ))}
        </AnimatePresence>

        {lines.length === 0 && (
          <div className="flex items-center gap-2 type-agent" style={{ color: "var(--ink-500)" }}>
            <span style={{ color: promptColor }}>{prompt}</span>
            <span className="animate-pulse">_</span>
          </div>
        )}
      </div>
    </div>
  );
}
