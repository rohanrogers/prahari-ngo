"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, MapPin, Radio, Users, X } from "lucide-react";
import AgentTerminal from "../../components/AgentTerminal";

const severityLabels = ["", "Low", "Moderate", "High", "Severe", "Critical"];

const MOCK_THREATS = [
  {
    id: "threat_demo_1", type: "flood", severity: 4, confidence: 0.78,
    location: { city: "Alappuzha", district: "Alappuzha", state: "Kerala", lat: 9.4981, lon: 76.3388, radius_km: 15 },
    status: "pre_staged",
    watcher_reasoning: "Three independent sources (OpenWeather, Reddit r/kerala, Mathrubhumi) agree on flooding in Alappuzha district. Rainfall at 94mm/3h far exceeds the 50mm alert threshold. Reddit eyewitness reports confirm ground-level impact.",
    evidence_chain: [
      { source: "OpenWeather", content: "Alappuzha: heavy intensity rain, 94mm in 3 hours", weight: 0.9 },
      { source: "r/kerala", content: "Water level rising in Kuttanad area \u2014 multiple reports", weight: 0.4 },
      { source: "Mathrubhumi", content: "\u0D06\u0D32\u0D2A\u0D4D\u0D2A\u0D41\u0D34\u0D2F\u0D3F\u0D7D \u0D15\u0D28\u0D24\u0D4D\u0D24 \u0D2E\u0D34; \u0D35\u0D46\u0D33\u0D4D\u0D33\u0D2A\u0D4D\u0D2A\u0D4A\u0D15\u0D4D\u0D15 \u0D2D\u0D40\u0D37\u0D23\u0D3F", weight: 0.7 },
    ],
    est_escalation_window_min: 60,
    matched_count: 14,
  },
  {
    id: "threat_demo_2", type: "flood", severity: 3, confidence: 0.62,
    location: { city: "Kochi", district: "Ernakulam", state: "Kerala", lat: 9.9312, lon: 76.2673, radius_km: 10 },
    status: "monitoring",
    watcher_reasoning: "Two sources (OpenWeather, RSS) indicate heavy rain in Ernakulam. Below confirmation threshold but increasing. We're watching it.",
    evidence_chain: [
      { source: "OpenWeather", content: "Kochi: 48mm rain in 3 hours, wind 28kmph", weight: 0.8 },
      { source: "Times of India", content: "Waterlogging reported in parts of Ernakulam", weight: 0.6 },
    ],
    est_escalation_window_min: 90,
    matched_count: 0,
  },
];

const MOCK_ACTIVITIES = [
  { id: "act_1", type: "fn" as const, text: "watcher.scan(weather=12, rss=5, reddit=8)" },
  { id: "act_2", type: "result" as const, text: "23 signals collected \u2192 2 situations above threshold" },
  { id: "act_3", type: "fn" as const, text: "coordinator.match(threat=alappuzha, mode=pre_staged)" },
  { id: "act_4", type: "result" as const, text: "14 volunteers matched \u00b7 8 boats \u00b7 4 medical \u00b7 2 logistics" },
];

export default function LivePage() {
  const [threats] = useState(MOCK_THREATS);
  const [selectedThreat, setSelectedThreat] = useState<string | null>(null);

  const selected = threats.find((t) => t.id === selectedThreat);

  return (
    <div className="flex" style={{ height: "100vh" }}>
      {/* MAP AREA */}
      <div className="flex-1 relative" style={{ background: "var(--ink-900)" }}>
        {/* Stats header */}
        <div className="surface-glass absolute top-20 left-4 right-4 z-10 flex items-center gap-8 px-6 py-4 rounded-lg">
          <StatPill icon={<Radio className="w-4 h-4" strokeWidth={1.5} />} value="12" label="cities watched" color="var(--ink-200)" />
          <div className="w-px h-6" style={{ background: "var(--glass-stroke)" }} />
          <StatPill icon={<AlertTriangle className="w-4 h-4" strokeWidth={1.5} />} value={threats.length.toString()} label="situations developing" color="var(--ember-500)" />
          <div className="w-px h-6" style={{ background: "var(--glass-stroke)" }} />
          <StatPill icon={<Users className="w-4 h-4" strokeWidth={1.5} />} value="94" label="volunteers ready to help" color="var(--signal-moss)" />
        </div>

        {/* Map placeholder */}
        <div className="w-full h-full flex items-center justify-center relative" style={{
          background: "radial-gradient(circle at 30% 40%, rgba(91,139,160,0.03) 0%, transparent 50%), radial-gradient(circle at 70% 60%, rgba(168,84,69,0.03) 0%, transparent 50%), var(--ink-900)",
        }}>
          <div style={{ fontSize: "14px", color: "var(--ink-500)", opacity: 0.5, textAlign: "center" }}>
            <MapIcon className="w-6 h-6 mx-auto mb-2" strokeWidth={1.5} />
            Connect Google Maps API to enable
          </div>

          {threats.map((threat, i) => (
            <motion.div key={threat.id}
              onClick={() => setSelectedThreat(threat.id === selectedThreat ? null : threat.id)}
              initial={{ scale: 0 }} animate={{ scale: 1 }}
              className="absolute cursor-pointer"
              style={{ top: `${35 + i * 15}%`, left: `${25 + i * 20}%` }}>
              <div className="pulse-breathe flex items-center justify-center" style={{
                width: "44px", height: "44px", borderRadius: "50%",
                background: `rgba(${threat.severity >= 4 ? "168,84,69" : "191,161,107"}, 0.2)`,
              }}>
                <div style={{
                  width: "16px", height: "16px", borderRadius: "50%",
                  background: threat.severity >= 4 ? "var(--signal-rust)" : "var(--signal-sand)",
                  boxShadow: `0 0 12px ${threat.severity >= 4 ? "var(--signal-rust)" : "var(--signal-sand)"}`,
                }} />
              </div>
              <div className="text-center mt-1" style={{ fontSize: "12px", color: "var(--ink-400)" }}>
                {threat.location.district}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Detail panel */}
        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25 }}
              className="absolute top-0 right-0 bottom-0 surface-glass overflow-y-auto"
              style={{ width: "420px", borderLeft: "1px solid var(--glass-stroke)", padding: "96px 24px 24px" }}>
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className="type-mono px-2 py-1 rounded" style={{
                    fontSize: "12px",
                    background: selected.severity >= 4 ? "rgba(168,84,69,0.15)" : "rgba(191,161,107,0.15)",
                    color: selected.severity >= 4 ? "var(--signal-rust)" : "var(--signal-sand)",
                  }}>
                    {severityLabels[selected.severity]}
                  </span>
                  <h2 className="mt-3" style={{ fontSize: "22px", fontWeight: 600 }}>
                    {selected.type.charAt(0).toUpperCase() + selected.type.slice(1)} &mdash; {selected.location.district}
                  </h2>
                </div>
                <button onClick={() => setSelectedThreat(null)} style={{
                  background: "none", border: "none", color: "var(--ink-400)", cursor: "pointer",
                }}>
                  <X className="w-5 h-5" strokeWidth={1.5} />
                </button>
              </div>

              {/* Confidence */}
              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <span style={{ fontSize: "13px", color: "var(--ink-400)" }}>Confidence</span>
                  <span className="type-mono" style={{ fontSize: "28px", fontWeight: 500 }}>{Math.round(selected.confidence * 100)}%</span>
                </div>
                <div className="meter-track" style={{ height: "3px" }}>
                  <div className="meter-fill" style={{ width: `${selected.confidence * 100}%`, height: "100%" }} />
                </div>
              </div>

              {/* Reasoning */}
              <div className="surface rounded-md p-5 mb-6">
                <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink-400)", marginBottom: "8px" }}>
                  Why the Watcher flagged this
                </div>
                <div style={{ fontSize: "14px", color: "var(--ink-200)", lineHeight: 1.65 }}>
                  {selected.watcher_reasoning}
                </div>
              </div>

              {/* Evidence */}
              <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink-400)", marginBottom: "12px" }}>
                What we saw
              </div>
              <div className="space-y-2 mb-6">
                {selected.evidence_chain.map((e: any, i: number) => (
                  <div key={i} className="surface rounded-md px-4 py-3 flex items-start gap-3">
                    <div className="self-stretch rounded-full" style={{ width: "3px", background: "var(--signal-sand)", minHeight: "32px" }} />
                    <div>
                      <div className="type-mono mb-1" style={{ fontSize: "12px", color: "var(--signal-sand)" }}>{e.source}</div>
                      <div style={{ fontSize: "14px", color: "var(--ink-200)" }}>{e.content}</div>
                    </div>
                  </div>
                ))}
              </div>

              {selected.status === "pre_staged" && (
                <button className="btn btn-primary w-full justify-center">
                  Confirm and notify {selected.matched_count} volunteers
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* RIGHT SIDEBAR */}
      <div style={{ width: "340px", borderLeft: "1px solid var(--glass-stroke)", padding: "96px 16px 16px", overflowY: "auto", background: "var(--ink-950)" }}>
        <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink-400)", marginBottom: "12px" }}>Agent activity</div>
        <AgentTerminal lines={MOCK_ACTIVITIES} agent="watcher" />
        <div className="mt-6" style={{ fontSize: "13px", color: "var(--ink-500)", textAlign: "center" }}>
          Nothing else developing right now. The Watcher scans every 5 minutes.
        </div>
      </div>
    </div>
  );
}

function StatPill({ icon, value, label, color }: { icon: React.ReactNode; value: string; label: string; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <div style={{ color }}>{icon}</div>
      <div className="flex items-baseline gap-2">
        <span className="type-mono" style={{ fontSize: "18px", fontWeight: 500, color }}>{value}</span>
        <span style={{ fontSize: "13px", color: "var(--ink-400)" }}>{label}</span>
      </div>
    </div>
  );
}

function MapIcon({ className, strokeWidth }: { className?: string; strokeWidth?: number }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth || 2} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
      <line x1="8" y1="2" x2="8" y2="18" /><line x1="16" y1="6" x2="16" y2="22" />
    </svg>
  );
}
