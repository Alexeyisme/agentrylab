import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { alpha } from "../avatars/palettes";

interface Props {
  text: string;
  accent: string;
  /** Reveal progressively and call onDone when finished. */
  live: boolean;
  onDone?: () => void;
  dimmed?: boolean;
}

/** Word-by-word typewriter. Pace scales with length so long lines don't drag. */
export default function SpeechBubble({ text, accent, live, onDone, dimmed }: Props) {
  const words = text.split(/(\s+)/);
  const [count, setCount] = useState(live ? 0 : words.length);

  useEffect(() => {
    if (!live) {
      setCount(words.length);
      return;
    }
    setCount(0);
    const total = Math.min(6500, Math.max(1100, words.length * 95));
    const step = total / words.length;
    let i = 0;
    const timer = window.setInterval(() => {
      i += 1;
      setCount(i);
      if (i >= words.length) {
        window.clearInterval(timer);
        onDone?.();
      }
    }, step);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, live]);

  const shown = words.slice(0, count).join("");
  const typing = live && count < words.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.85 }}
      animate={{ opacity: dimmed ? 0.55 : 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.9, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 420, damping: 26 }}
      className="relative max-w-[280px] rounded-2xl px-4 py-3 text-[14px] leading-snug text-fog-100 shadow-2xl"
      style={{
        background: `linear-gradient(180deg, ${alpha(accent, 0.22)}, rgb(20 24 36 / 0.92))`,
        border: `1px solid ${alpha(accent, 0.5)}`,
        boxShadow: `0 20px 40px -20px ${alpha(accent, 0.6)}, 0 0 0 1px rgb(0 0 0 / 0.4)`,
        backdropFilter: "blur(10px)",
      }}
    >
      <span className={typing ? "caret" : undefined}>{shown}</span>
      {/* tail */}
      <span
        className="absolute -bottom-[7px] left-1/2 h-3.5 w-3.5 -translate-x-1/2 rotate-45"
        style={{
          background: "rgb(20 24 36 / 0.95)",
          borderRight: `1px solid ${alpha(accent, 0.5)}`,
          borderBottom: `1px solid ${alpha(accent, 0.5)}`,
        }}
      />
    </motion.div>
  );
}
