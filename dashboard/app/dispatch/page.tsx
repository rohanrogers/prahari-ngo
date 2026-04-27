"use client";

import { motion } from "framer-motion";
import { Brain, Activity, MapPin, Users, Zap, TrendingUp, Shield, AlertTriangle } from "lucide-react";
import DispatchGlyph from "../../components/glyphs/DispatchGlyph";
import { useState, useEffect } from "react";

// Kerala district data matching our RL environment
const DISTRICTS = [
  { id: "TVM", name: "Thiruvananthapuram", lat: 8.5241, lng: 76.9366, risk: "low" },
  { id: "KLM", name: "Kollam", lat: 8.8932, lng: 76.6141, risk: "moderate" },
  { id: "PTA", name: "Pathanamthitta", lat: 9.2648, lng: 76.787, risk: "high" },
  { id: "ALP", name: "Alappuzha", lat: 9.4981, lng: 76.3388, risk: "critical" },
  { id: "KTM", name: "Kottayam", lat: 9.5916, lng: 76.5222, risk: "high" },
  { id: "IDK", name: "Idukki", lat: 9.85, lng: 76.9833, risk: "critical" },
  { id: "EKM", name: "Ernakulam", lat: 9.9812, lng: 76.2999, risk: "high" },
  { id: "TSR", name: "Thrissur", lat: 10.5276, lng: 76.2144, risk: "moderate" },
  { id: "PKD", name: "Palakkad", lat: 10.7867, lng: 76.6548, risk: "moderate" },
  { id: "MLP", name: "Malappuram", lat: 11.05, lng: 76.0711, risk: "moderate" },
  { id: "KZH", name: "Kozhikode", lat: 11.2588, lng: 75.7804, risk: "moderate" },
  { id: "WYD", name: "Wayanad", lat: 11.7172, lng: 76.13, risk: "critical" },
  { id: "KNR", name: "Kannur", lat: 11.8745, lng: 75.3704, risk: "low" },
  { id: "KSD", name: "Kasaragod", lat: 12.5004, lng: 74.9873, risk: "low" },
];

const WEATHER_STATES = ["clear", "light_rain", "moderate_rain", "heavy_rain", "catastrophic"];

const SKILLS = [
  "first_aid", "boat_operation", "swimming", "driving", "cooking",
  "translation", "construction", "electrical", "counseling", "communication"
];

const STAGES = Array.from({ length: 15 }, (_, i) => ({
  num: i + 1,
  name: [
    "Static Dispatch", "Dynamic Arrivals", "Multi-Skill", "Geography",
    "Road Closures", "Partial Obs", "Multi-Zone", "Fatigue", "Comm Delay",
    "Weather", "Weather+Roads", "Zone Alloc", "Adversarial", "Real Skills", "Full Kerala"
  ][i],
  status: i < 1 ? "trained" : i < 9 ? "ready" : "locked",
}));

// Simulated RL agent metrics
function useSimulatedMetrics() {
  const [metrics, setMetrics] = useState({
    serviceRate: 0.73,
    livesPerHour: 4.2,
    avgResponseMin: 28,
    activeVolunteers: 18,
    activeMissions: 5,
    weather: "moderate_rain",
    step: 0,
    reward: 0,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => {
        const weatherIdx = WEATHER_STATES.indexOf(prev.weather);
        const nextWeather = Math.random() > 0.7
          ? WEATHER_STATES[Math.min(weatherIdx + 1, 4)]
          : Math.random() > 0.5
            ? prev.weather
            : WEATHER_STATES[Math.max(weatherIdx - 1, 0)];

        const missionDelta = Math.random() > 0.6 ? 1 : Math.random() > 0.3 ? 0 : -1;

        return {
          serviceRate: Math.min(1, Math.max(0.4, prev.serviceRate + (Math.random() - 0.45) * 0.03)),
          livesPerHour: Math.max(1, prev.livesPerHour + (Math.random() - 0.45) * 0.3),
          avgResponseMin: Math.max(10, Math.min(60, prev.avgResponseMin + (Math.random() - 0.5) * 3)),
          activeVolunteers: Math.max(5, Math.min(30, prev.activeVolunteers + Math.floor((Math.random() - 0.5) * 3))),
          activeMissions: Math.max(1, Math.min(12, prev.activeMissions + missionDelta)),
          weather: nextWeather,
          step: prev.step + 1,
          reward: prev.reward + (prev.serviceRate * 2 - 0.5),
        };
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return metrics;
}

function riskColor(risk: string) {
  return risk === "critical" ? "var(--ember-500)"
    : risk === "high" ? "#e67e22"
    : risk === "moderate" ? "var(--signal-sand)"
    : "var(--signal-moss)";
}

function weatherEmoji(w: string) {
  return w === "clear" ? "☀️"
    : w === "light_rain" ? "🌦️"
    : w === "moderate_rain" ? "🌧️"
    : w === "heavy_rain" ? "⛈️"
    : "🌊";
}

export default function DispatchPage() {
  const m = useSimulatedMetrics();
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);

  return (
    <div className="min-h-screen" style={{ paddingTop: "96px", paddingBottom: "64px" }}>
      <div className="container">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center justify-center rounded-lg"
              style={{ width: "56px", height: "56px", background: "rgba(168,85,247,0.12)", color: "#a855f7" }}>
              <DispatchGlyph className="w-7 h-7" />
            </div>
            <div>
              <div className="type-mono" style={{ fontSize: "12px", color: "var(--ink-400)" }}>AGENT 04</div>
              <h1 style={{ fontSize: "28px", fontWeight: 600 }}>Dispatch Optimizer</h1>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <div className="w-2 h-2 rounded-full pulse-breathe" style={{ background: "#a855f7" }} />
              <span className="type-mono" style={{ fontSize: "12px", color: "#a855f7" }}>PPO ACTIVE</span>
            </div>
          </div>
          <p style={{ fontSize: "15px", color: "var(--ink-200)", maxWidth: "640px", lineHeight: 1.65 }}>
            Reinforcement Learning agent trained through 15 curriculum stages on Kerala flood scenarios.
            Optimizes volunteer-to-mission assignment under stochastic conditions — weather, road closures,
            skill constraints, and communication delays.
          </p>
        </motion.div>

        {/* Stat Pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "32px" }}
        >
          <StatPill icon={<TrendingUp className="w-4 h-4" />} label="Service Rate" value={`${(m.serviceRate * 100).toFixed(1)}%`} color="#a855f7" />
          <StatPill icon={<Users className="w-4 h-4" />} label="Lives / Hour" value={m.livesPerHour.toFixed(1)} color="var(--signal-moss)" />
          <StatPill icon={<Zap className="w-4 h-4" />} label="Avg Response" value={`${m.avgResponseMin.toFixed(0)}m`} color="var(--signal-sand)" />
          <StatPill icon={<Activity className="w-4 h-4" />} label="Weather" value={`${weatherEmoji(m.weather)} ${m.weather.replace("_", " ")}`} color="var(--ember-500)" />
        </motion.div>

        {/* Main Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: "20px" }}>
          {/* Kerala District Map (simplified) */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="surface rounded-lg p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 style={{ fontSize: "17px", fontWeight: 600 }}>Kerala District Status</h2>
              <div className="flex items-center gap-3" style={{ fontSize: "11px" }}>
                {["critical", "high", "moderate", "low"].map(r => (
                  <div key={r} className="flex items-center gap-1">
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: riskColor(r) }} />
                    <span style={{ color: "var(--ink-400)", textTransform: "capitalize" }}>{r}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Simplified district visualization */}
            <div style={{ position: "relative", height: "420px", border: "1px solid var(--glass-stroke)", borderRadius: "8px", overflow: "hidden", background: "rgba(0,0,0,0.2)" }}>
              {DISTRICTS.map((d, i) => {
                // Normalize coordinates to fit container
                const x = ((d.lng - 74.5) / (77.5 - 74.5)) * 100;
                const y = (1 - (d.lat - 8.0) / (13.0 - 8.0)) * 100;
                const isSelected = selectedDistrict === d.id;
                const pulseSize = d.risk === "critical" ? 20 : d.risk === "high" ? 16 : 12;

                return (
                  <motion.div
                    key={d.id}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.4 + i * 0.05 }}
                    onClick={() => setSelectedDistrict(isSelected ? null : d.id)}
                    style={{
                      position: "absolute",
                      left: `${x}%`,
                      top: `${y}%`,
                      transform: "translate(-50%, -50%)",
                      cursor: "pointer",
                      zIndex: isSelected ? 10 : 1,
                    }}
                  >
                    {/* Pulse ring for critical/high */}
                    {(d.risk === "critical" || d.risk === "high") && (
                      <div className="pulse-breathe" style={{
                        position: "absolute", left: "50%", top: "50%",
                        transform: "translate(-50%, -50%)",
                        width: pulseSize * 2, height: pulseSize * 2,
                        borderRadius: "50%",
                        background: `${riskColor(d.risk)}22`,
                        border: `1px solid ${riskColor(d.risk)}44`,
                      }} />
                    )}

                    {/* District dot */}
                    <div style={{
                      width: pulseSize, height: pulseSize,
                      borderRadius: "50%",
                      background: riskColor(d.risk),
                      border: isSelected ? "2px solid var(--ink-0)" : "1px solid rgba(255,255,255,0.2)",
                      boxShadow: `0 0 ${pulseSize}px ${riskColor(d.risk)}66`,
                    }} />

                    {/* Label */}
                    <div className="type-mono" style={{
                      position: "absolute", left: "50%", top: "100%",
                      transform: "translateX(-50%)",
                      marginTop: 4, fontSize: "9px", whiteSpace: "nowrap",
                      color: isSelected ? "var(--ink-0)" : "var(--ink-400)",
                      fontWeight: isSelected ? 600 : 400,
                    }}>
                      {d.id}
                    </div>

                    {/* Tooltip on select */}
                    {isSelected && (
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="surface-glass rounded-lg px-3 py-2"
                        style={{
                          position: "absolute", bottom: "100%", left: "50%",
                          transform: "translateX(-50%)",
                          marginBottom: 12, whiteSpace: "nowrap", fontSize: "12px",
                          zIndex: 20,
                        }}
                      >
                        <div style={{ fontWeight: 600, marginBottom: 2 }}>{d.name}</div>
                        <div style={{ color: riskColor(d.risk), textTransform: "uppercase", fontSize: "10px", fontWeight: 500 }}>
                          {d.risk} flood risk
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>

          {/* Right Sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Live Dispatch Log */}
            <motion.div
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="surface rounded-lg p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-4 h-4" style={{ color: "#a855f7" }} />
                <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Agent Decisions</h3>
                <div className="ml-auto type-mono" style={{ fontSize: "10px", color: "var(--ink-400)" }}>
                  step {m.step}
                </div>
              </div>
              <DispatchLog step={m.step} />
            </motion.div>

            {/* Curriculum Progress */}
            <motion.div
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
              className="surface rounded-lg p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <Brain className="w-4 h-4" style={{ color: "#a855f7" }} />
                <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Curriculum</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {STAGES.map(s => (
                  <div key={s.num} className="flex items-center gap-2" style={{ fontSize: "11px" }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: s.status === "trained" ? "var(--signal-moss)" : s.status === "ready" ? "var(--signal-sand)" : "var(--ink-600)",
                    }} />
                    <span className="type-mono" style={{ color: "var(--ink-400)", width: "20px" }}>{String(s.num).padStart(2, "0")}</span>
                    <span style={{ color: s.status === "trained" ? "var(--ink-0)" : "var(--ink-400)" }}>{s.name}</span>
                    {s.status === "trained" && <span style={{ color: "var(--signal-moss)", marginLeft: "auto" }}>✓</span>}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Model Info */}
            <motion.div
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
              className="surface rounded-lg p-5"
            >
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>PPO Configuration</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
                <InfoRow label="Policy" value="MlpPolicy" />
                <InfoRow label="Learning Rate" value="3×10⁻⁴" />
                <InfoRow label="Discount (γ)" value="0.99" />
                <InfoRow label="Clip Range" value="0.2" />
                <InfoRow label="Entropy Coef" value="0.01" />
                <InfoRow label="Framework" value="SB3 + Gymnasium" />
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatPill({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="surface rounded-lg px-4 py-3 flex items-center gap-3">
      <div style={{ color }}>{icon}</div>
      <div>
        <div className="type-mono" style={{ fontSize: "10px", color: "var(--ink-400)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
        <div style={{ fontSize: "17px", fontWeight: 600, marginTop: 2 }}>{value}</div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span style={{ color: "var(--ink-400)" }}>{label}</span>
      <span className="type-mono" style={{ color: "var(--ink-200)" }}>{value}</span>
    </div>
  );
}

// Simulated dispatch decisions the RL agent is making
const DISPATCH_TEMPLATES = [
  { action: "DISPATCH", detail: "boat_op → water_rescue", district: "ALP", severity: "critical" },
  { action: "DISPATCH", detail: "medic + driver → medical_evac", district: "IDK", severity: "high" },
  { action: "WAIT", detail: "holding swimmer for incoming rescue", district: "WYD", severity: "moderate" },
  { action: "DISPATCH", detail: "cook → shelter_feeding", district: "EKM", severity: "moderate" },
  { action: "DISPATCH", detail: "HAM_radio → comm_setup", district: "PTA", severity: "high" },
  { action: "REASSIGN", detail: "redirecting electrician IDK→ALP", district: "ALP", severity: "critical" },
  { action: "WAIT", detail: "conserving medic for predicted surge", district: "KTM", severity: "low" },
  { action: "DISPATCH", detail: "construction crew → road_clearing", district: "TSR", severity: "moderate" },
];

function DispatchLog({ step }: { step: number }) {
  // Show last 6 decisions based on step counter
  const decisions = Array.from({ length: 6 }, (_, i) => {
    const idx = (step + i) % DISPATCH_TEMPLATES.length;
    return { ...DISPATCH_TEMPLATES[idx], time: `${Math.max(0, step - i * 3)}` };
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {decisions.map((d, i) => (
        <motion.div
          key={`${step}-${i}`}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          className="flex items-start gap-2"
          style={{ fontSize: "11px", opacity: 1 - i * 0.12 }}
        >
          <span className="type-mono" style={{
            fontSize: "9px", fontWeight: 600, padding: "1px 4px", borderRadius: 3,
            background: d.action === "DISPATCH" ? "rgba(34,197,94,0.15)" : d.action === "WAIT" ? "rgba(234,179,8,0.15)" : "rgba(168,85,247,0.15)",
            color: d.action === "DISPATCH" ? "var(--signal-moss)" : d.action === "WAIT" ? "var(--signal-sand)" : "#a855f7",
            whiteSpace: "nowrap",
          }}>
            {d.action}
          </span>
          <span style={{ color: "var(--ink-200)", lineHeight: 1.4 }}>
            {d.detail}
            <span style={{ color: "var(--ink-400)" }}> · {d.district}</span>
          </span>
        </motion.div>
      ))}
    </div>
  );
}
