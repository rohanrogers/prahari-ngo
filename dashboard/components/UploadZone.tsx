"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, Check } from "lucide-react";

const INGESTOR_URL = process.env.NEXT_PUBLIC_INGESTOR_URL || "http://localhost:8001";

export default function UploadZone({ onResult }: { onResult?: (r: any) => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const handleFile = useCallback(async (file: File) => {
    setFileName(file.name);
    setIsProcessing(true);
    setStatus("idle");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${INGESTOR_URL}/ingest/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const result = await res.json();
      setStatus("success");
      onResult?.({ ...result, file_name: file.name });
    } catch {
      setStatus("error");
    } finally {
      setIsProcessing(false);
    }
  }, [onResult]);

  const handleClick = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,.pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv";
    input.onchange = (e: any) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    };
    input.click();
  };

  return (
    <motion.div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) handleFile(file);
      }}
      onClick={handleClick}
      className="relative cursor-pointer rounded-lg flex flex-col items-center justify-center transition-all"
      style={{
        minHeight: "320px",
        border: `2px dashed ${isDragging ? "var(--ember-500)" : "var(--ink-700)"}`,
        background: isDragging ? "rgba(61, 36, 24, 0.1)" : "rgba(26, 26, 23, 0.3)",
      }}
      whileHover={{ scale: 1.005 }}
    >
      {isProcessing ? (
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin" strokeWidth={1.5} style={{ color: "var(--ember-500)" }} />
          <div className="text-center">
            <p style={{ fontSize: "15px", fontWeight: 500 }}>{fileName}</p>
            <p className="mt-1" style={{ fontSize: "13px", color: "var(--ink-400)" }}>Reading the file...</p>
          </div>
        </div>
      ) : status === "success" ? (
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center gap-4">
          <Check className="w-10 h-10" strokeWidth={1.5} style={{ color: "var(--signal-moss)" }} />
          <p style={{ fontSize: "20px", fontWeight: 600 }}>Done &mdash; here&apos;s what we found.</p>
          <p style={{ fontSize: "13px", color: "var(--ink-400)" }}>{fileName}</p>
        </motion.div>
      ) : (
        <div className="text-center" style={{ padding: "48px" }}>
          <div className="mx-auto mb-6 flex items-center justify-center rounded-2xl"
            style={{ width: "72px", height: "72px", background: "rgba(200,126,87,0.08)", border: "1px solid rgba(200,126,87,0.15)" }}>
            <Upload className="w-7 h-7" strokeWidth={1.5} style={{ color: "var(--ember-500)" }} />
          </div>
          <p style={{ fontSize: "20px", fontWeight: 600, marginBottom: "8px" }}>Drop a file here</p>
          <p style={{ fontSize: "14px", color: "var(--ink-200)", marginBottom: "20px", maxWidth: "320px", marginLeft: "auto", marginRight: "auto", lineHeight: 1.6 }}>
            A WhatsApp export, a photo of a signup register, a PDF form &mdash; we&apos;ll read all of them.
          </p>
          <div style={{ fontSize: "13px", color: "var(--ink-500)" }}>
            Or{" "}
            <span style={{ color: "var(--ember-300)", textDecoration: "underline", textUnderlineOffset: "3px" }}>
              click to choose one
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}
