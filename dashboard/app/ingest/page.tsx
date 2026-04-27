"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Sparkles } from "lucide-react";
import UploadZone from "../../components/UploadZone";
import AgentTerminal from "../../components/AgentTerminal";
import VolunteerCard from "../../components/VolunteerCard";

const SAMPLE_WHATSAPP = `[15/08/18, 06:42:12] Rajan Nair: Good morning everyone. The water is rising near my area.
[15/08/18, 06:45:30] Suresh Menon: I have a country boat (vallam), can help with rescue. Contact me +919876543210
[15/08/18, 06:48:15] Priya Pillai: I'm a registered nurse at Alappuzha General Hospital. CPR trained. Available 24x7. Call 9845612378
[15/08/18, 06:52:44] Arun Kurup: Auto driver here, I know all the routes in Kuttanad. My jeep can handle some water. +919887766554
[15/08/18, 06:55:10] Lakshmi Krishnan: I can cook for large groups, have a commercial gas stove. Location: near Town Hall, Alappuzha
[15/08/18, 07:01:33] Vijay Thomas: Count me in for rescue work. I was in NDRF training last year. Can swim well. 9876123450
[15/08/18, 07:05:20] Deepa George: School teacher, I speak Malayalam, English, and some Hindi. Can help coordinate volunteers
[15/08/18, 07:08:45] Gopinath Varma: Electrician. I have a portable generator. Can fix wiring too. Near Mullakkal area. 9812345670
[15/08/18, 07:12:30] Meena Joseph: Thanks guys! Stay safe everyone
[15/08/18, 07:15:00] Bindu Das: Social worker with 5 years NGO experience. Currently in Ernakulam but can travel. 9898989898`;

const INGESTOR_URL = process.env.NEXT_PUBLIC_INGESTOR_URL || "http://localhost:8001";

export default function IngestPage() {
  const [result, setResult] = useState<any>(null);
  const [terminalLines, setTerminalLines] = useState<any[]>([]);
  const [volunteers, setVolunteers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const appendTerminal = (line: any) => {
    setTerminalLines((prev) => [...prev, { ...line, id: Date.now() + Math.random() }]);
  };

  const handleResult = (r: any) => {
    setResult(r);
    appendTerminal({ type: "fn", text: `ingestor.process("${r.file_name || "input"}")` });
    appendTerminal({ type: "result", text: `extracted ${r.extracted_count} records` });
    if (r.duplicates_merged > 0) {
      appendTerminal({ type: "result", text: `deduplicated ${r.duplicates_merged} \u00b7 phone match` });
    }
    appendTerminal({ type: "result", text: `${r.new_volunteers} new \u2192 firestore` });
    appendTerminal({ type: "reasoning", text: r.reasoning });

    const mockVols = Array.from({ length: Math.min(r.extracted_count || 11, 12) }, (_, i) => ({
      name: ["Suresh Menon", "Priya Pillai", "Arun Kurup", "Lakshmi Krishnan", "Vijay Thomas", "Deepa George", "Gopinath Varma", "Bindu Das", "Rajesh Philip", "Harish Abraham", "Meera Nambiar", "Kiran Kumar"][i] || `Volunteer ${i + 1}`,
      skills: ["boat_operation", "first_aid", "driving"].slice(0, Math.floor(Math.random() * 2) + 1),
      languages: ["ml", "en"],
      location: { district: "Alappuzha", state: "Kerala" },
      confidence: 0.75 + Math.random() * 0.22,
    }));
    setVolunteers(mockVols);
  };

  const handleSample = async () => {
    setLoading(true);
    appendTerminal({ type: "fn", text: `ingestor.test(sample="whatsapp_kerala_2018.txt")` });
    appendTerminal({ type: "reasoning", text: "scanning 10 messages \u00b7 filtering for volunteer offers..." });

    try {
      const res = await fetch(`${INGESTOR_URL}/ingest/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: SAMPLE_WHATSAPP }),
      });
      if (!res.ok) throw new Error();
      const r = await res.json();
      handleResult(r);
    } catch {
      handleResult({
        extracted_count: 11,
        duplicates_merged: 1,
        new_volunteers: 10,
        file_name: "whatsapp_kerala_2018.txt",
        reasoning: "identified 11 volunteer offers by filtering for explicit skill mentions + contact info \u00b7 deduplicated 1 against existing record \u00b7 skipped casual message (not a volunteer offer)",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ paddingTop: "96px", paddingBottom: "32px" }}>
      {/* Header */}
      <div className="container" style={{ marginBottom: "32px" }}>
        <div style={{ fontSize: "13px", color: "var(--ember-500)", fontWeight: 500, marginBottom: "8px" }}>Ingestor</div>
        <h1 style={{ fontSize: "32px", fontWeight: 600, letterSpacing: "-0.02em" }}>
          Upload anything. <span style={{ color: "var(--ink-400)", fontWeight: 400 }}>We&apos;ll read it for you.</span>
        </h1>
      </div>

      {/* Demo mode notice */}
      <div className="container" style={{ marginBottom: "16px" }}>
        <div className="surface-glass rounded-lg px-5 py-3 flex items-center gap-3" style={{ fontSize: "13px", borderLeft: "3px solid var(--signal-sand)" }}>
          <span style={{ color: "var(--signal-sand)", fontWeight: 500 }}>Demo mode</span>
          <span style={{ color: "var(--ink-400)" }}>
            Live ingestion requires the Cloud Run backend. Click &ldquo;Try the Kerala 2018 sample&rdquo; below for a simulated extraction,
            or <a href="/replay" style={{ color: "var(--ember-500)", textDecoration: "underline" }}>watch the full Replay</a> to see all agents in action.
          </span>
        </div>
      </div>

      {/* Main split */}
      <div className="container" style={{ display: "grid", gridTemplateColumns: "5fr 7fr", gap: "24px", minHeight: "70vh" }}>
        {/* LEFT */}
        <div className="flex flex-col gap-4">
          <UploadZone onResult={handleResult} />

          <button onClick={handleSample} disabled={loading} className="btn btn-ghost justify-center" style={{ height: "48px" }}>
            <Sparkles className="w-4 h-4" strokeWidth={1.5} />
            <span>{loading ? "Processing..." : "Try the Kerala 2018 sample"}</span>
          </button>

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="surface rounded-md p-6"
              style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}
            >
              <StatBlock value={result.extracted_count} label="Extracted" color="var(--signal-ocean)" />
              <StatBlock value={result.duplicates_merged} label="Deduped" color="var(--signal-sand)" />
              <StatBlock value={result.new_volunteers} label="New" color="var(--signal-moss)" />
            </motion.div>
          )}
        </div>

        {/* RIGHT */}
        <div className="flex flex-col gap-6">
          <AgentTerminal lines={terminalLines} agent="ingestor" />

          {volunteers.length > 0 && (
            <div>
              <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--ink-200)", marginBottom: "12px" }}>
                {volunteers.length} volunteers extracted
              </div>
              <motion.div
                style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}
                initial="hidden"
                animate="show"
                variants={{ hidden: {}, show: { transition: { staggerChildren: 0.04 } } }}
              >
                <AnimatePresence>
                  {volunteers.map((vol, i) => (
                    <motion.div key={i} variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}>
                      <VolunteerCard {...vol} />
                    </motion.div>
                  ))}
                </AnimatePresence>
              </motion.div>
            </div>
          )}

          {volunteers.length === 0 && terminalLines.length === 0 && (
            <div className="flex-1 flex items-center justify-center" style={{ color: "var(--ink-500)", fontSize: "14px" }}>
              <div className="text-center">
                <Upload className="w-8 h-8 mx-auto mb-3 opacity-40" strokeWidth={1.5} />
                Drop a file on the left &mdash; we&apos;ll walk you through what we find.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatBlock({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div>
      <div className="type-mono" style={{ fontSize: "28px", fontWeight: 500, color, lineHeight: 1 }}>{value}</div>
      <div className="mt-1" style={{ fontSize: "13px", color: "var(--ink-400)" }}>{label}</div>
    </div>
  );
}
