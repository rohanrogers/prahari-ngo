"use client";

import { motion, AnimatePresence } from "framer-motion";

const narrations: Record<string, string> = {
  idle: "",
  signals: "First, separate signals from different sources...",
  thinking: "Five independent sources — including government data. The Watcher is weighing them.",
  emitted: "At 65% confidence, it alerts \u2014 33 minutes before the first news article would appear.",
  coordinator: "Now the Coordinator reaches into the volunteer graph, picks the right people, drafts messages.",
  complete: "Two and a half hours of head start. That\u2019s what Prahari would have given Kerala.",
};

export default function Narrator({ phase }: { phase: string }) {
  const text = narrations[phase] || "";

  return (
    <div style={{ minHeight: "24px", maxWidth: "600px" }}>
      <AnimatePresence mode="wait">
        {text && (
          <motion.p
            key={phase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.4 }}
            style={{
              fontSize: "14px",
              color: "var(--ink-400)",
              fontStyle: "italic",
              lineHeight: 1.5,
            }}
          >
            {text}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
