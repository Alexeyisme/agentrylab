import { motion } from "motion/react";
import type { Message } from "../types";
import SpeechBubble from "./SpeechBubble";

const ACCENT = "#f8fafc";

/** The human on stage: a simple silhouette with their latest line. */
export default function Guest({ name, line, isLatest, size }: { name: string; line: Message; isLatest: boolean; size: number }) {
  const h = size * 1.25;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.6, y: 40 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.6, y: -20 }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      className="relative flex flex-col items-center"
      style={{ width: size + 40 }}
    >
      <div className="flex h-[112px] w-full items-end justify-center pb-2">
        <SpeechBubble key={line.id} text={line.content} accent={ACCENT} live={false} dimmed={!isLatest} />
      </div>
      <motion.svg viewBox="0 0 200 250" width={size} height={h} animate={{ y: [0, -3, 0] }} transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut" }} style={{ overflow: "visible" }}>
        <ellipse cx={100} cy={240} rx={50} ry={8} fill="white" opacity={0.12} style={{ filter: "blur(8px)" }} />
        <defs>
          <linearGradient id="guest-g" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#f1f5f9" stopOpacity="0.9" />
            <stop offset="1" stopColor="#94a3b8" stopOpacity="0.5" />
          </linearGradient>
        </defs>
        <circle cx={100} cy={62} r={34} fill="url(#guest-g)" />
        <path d="M44 236 C44 160 70 118 100 118 C130 118 156 160 156 236 Z" fill="url(#guest-g)" />
        <circle cx={100} cy={160} r={6} fill="#0b0e17" opacity={0.5} />
      </motion.svg>
      <div className="mt-1 flex flex-col items-center text-center">
        <span className="font-semibold tracking-tight text-fog-100">{name}</span>
        <span className="text-[11px] text-fog-400">guest · human</span>
      </div>
    </motion.div>
  );
}
