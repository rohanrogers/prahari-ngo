"use client";

import { motion } from "framer-motion";
import { MapPin, User } from "lucide-react";

const skillLabels: Record<string, string> = {
  first_aid: "First Aid", medical_professional: "Medical", boat_operation: "Boat",
  driving: "Driver", swimming: "Swimming", cooking: "Cooking",
  language_translation: "Translator", logistics: "Logistics", coordination: "Coordination",
  technical_rescue: "Rescue", electrical: "Electrical", social_work: "Social Work",
  transport_vehicle: "Vehicle", local_knowledge: "Local",
};

const langNames: Record<string, string> = {
  ml: "Malayalam", ta: "Tamil", hi: "Hindi", en: "English", kn: "Kannada", te: "Telugu",
};

interface Props {
  name: string;
  skills: string[];
  languages: string[];
  location: { district: string; state: string };
  confidence: number;
  matchScore?: number;
  matchReasons?: string[];
  distanceKm?: number;
}

export default function VolunteerCard({
  name, skills, languages, location, confidence, matchScore, matchReasons, distanceKm,
}: Props) {
  return (
    <motion.div
      className="surface rounded-md p-5 transition-colors"
      whileHover={{ y: -2, borderColor: "var(--ink-500)" }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: "var(--ink-700)" }}>
            <User className="w-3.5 h-3.5" strokeWidth={1.5} style={{ color: "var(--ink-400)" }} />
          </div>
          <div>
            <div style={{ fontSize: "14px", fontWeight: 500 }}>{name}</div>
            <div className="flex items-center gap-1 mt-0.5" style={{ fontSize: "12px", color: "var(--ink-400)" }}>
              <MapPin className="w-3 h-3" strokeWidth={1.5} />
              {location.district}
              {distanceKm !== undefined && (
                <span style={{ color: "var(--ember-500)" }}>&middot; {distanceKm.toFixed(1)}km</span>
              )}
            </div>
          </div>
        </div>

        {matchScore !== undefined ? (
          <div className="type-mono px-2 py-1 rounded" style={{
            fontSize: "12px",
            background: matchScore > 0.7 ? "rgba(122,145,104,0.15)" : "rgba(191,161,107,0.15)",
            color: matchScore > 0.7 ? "var(--signal-moss)" : "var(--signal-sand)",
          }}>
            {Math.round(matchScore * 100)}%
          </div>
        ) : (
          <div className="type-mono" style={{ fontSize: "12px", color: "var(--ink-400)" }}>
            {Math.round(confidence * 100)}%
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2">
        {skills.map((skill) => (
          <span key={skill} className="type-mono px-2 py-0.5 rounded"
                style={{ fontSize: "12px", background: "var(--ink-700)", color: "var(--ink-200)" }}>
            {skillLabels[skill] || skill}
          </span>
        ))}
      </div>

      <div className="flex gap-1.5">
        {languages.map((lang) => (
          <span key={lang} style={{ fontSize: "12px", color: "var(--ember-300)" }}>
            {langNames[lang] || lang}
          </span>
        ))}
      </div>

      {matchReasons && matchReasons.length > 0 && (
        <div className="mt-3 pt-3" style={{
          borderTop: "1px solid var(--glass-stroke)", fontSize: "12px", color: "var(--ink-400)",
        }}>
          {matchReasons.join(" \u00b7 ")}
        </div>
      )}
    </motion.div>
  );
}
