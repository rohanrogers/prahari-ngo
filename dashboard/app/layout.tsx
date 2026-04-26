import type { Metadata } from "next";
import { Instrument_Serif, Geist, Geist_Mono, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import NavPill from "../components/NavPill";

const display = Instrument_Serif({
  weight: ["400"],
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const agent = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-agent",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prahari — Proactive NGO Crisis Coordination",
  description: "India's first proactive crisis coordination sentinel. Three Gemini agents that ingest messy data, detect emerging threats, and pre-stage multilingual response.",
  keywords: ["NGO", "crisis response", "Kerala floods", "Gemini AI", "volunteer coordination", "India"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable} ${agent.variable}`}>
      <body>
        <NavPill />
        <main className="relative" style={{ zIndex: 2 }}>
          {children}
        </main>
      </body>
    </html>
  );
}
