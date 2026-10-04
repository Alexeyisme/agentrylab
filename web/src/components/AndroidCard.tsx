import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import Android from "../avatars/Android";
import { accentFor, alpha } from "../avatars/palettes";
import type { Message, Mood, Persona } from "../types";
import SpeechBubble from "./SpeechBubble";

interface Props {
  persona: Persona;
  mood: Mood;
  size: number;
  bubble: Message | null;
  bubbleLive: boolean;
  bubbleDimmed: boolean;
  onBubbleDone: () => void;
  onRemove: () => void;
  seed: number;
}

export default function AndroidCard({ persona, mood, size, bubble, bubbleLive, bubbleDimmed, onBubbleDone, onRemove, seed }: Props) {
  const accent = accentFor(persona.avatar.palette);
  const [hover, setHover] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.4, y: 60, filter: "blur(8px)" }}
      animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
      exit={{ opacity: 0, scale: 0.5, y: -40, filter: "blur(10px)", transition: { duration: 0.35 } }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      className="group relative flex flex-col items-center"
      style={{ width: size + 40 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* bubble / thinking */}
      <div className="flex h-[112px] w-full items-end justify-center pb-2">
        <AnimatePresence mode="wait">
          {mood === "thinking" ? (
            <motion.div
              key="thinking"
              initial={{ opacity: 0, scale: 0.6, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.6 }}
              className="flex items-center gap-1.5 rounded-full px-3 py-2"
              style={{ background: alpha(accent, 0.12), border: `1px solid ${alpha(accent, 0.35)}` }}
            >
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="block h-2 w-2 rounded-full"
                  style={{ background: accent }}
                  animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                />
              ))}
            </motion.div>
          ) : bubble ? (
            <SpeechBubble key={bubble.id} text={bubble.content} accent={accent} live={bubbleLive} dimmed={bubbleDimmed} onDone={onBubbleDone} />
          ) : null}
        </AnimatePresence>
      </div>

      <motion.div
        animate={mood === "talking" ? { scale: 1.04 } : { scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 18 }}
        style={{ filter: mood === "talking" ? `drop-shadow(0 0 24px ${alpha(accent, 0.45)})` : "none" }}
      >
        <Android avatar={persona.avatar} mood={mood} seed={seed} size={size} />
      </motion.div>

      {/* nameplate */}
      <div className="mt-1 flex flex-col items-center text-center">
        <div className="flex items-center gap-1.5">
          <motion.span
            className="block h-1.5 w-1.5 rounded-full"
            style={{ background: accent }}
            animate={mood === "idle" ? { opacity: 0.5 } : { opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
          <span className="font-semibold tracking-tight" style={{ color: accent }}>
            {persona.name}
          </span>
        </div>
        <span className="text-[11px] text-fog-400">{persona.tagline}</span>
      </div>

      {/* remove */}
      <AnimatePresence>
        {hover && (
          <motion.button
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.6 }}
            onClick={onRemove}
            title={`Remove ${persona.name}`}
            className="absolute right-1 top-[100px] grid h-7 w-7 place-items-center rounded-full border border-white/10 bg-ink-900/90 text-fog-300 hover:border-coral-400 hover:text-white"
            style={{ boxShadow: "0 6px 16px rgb(0 0 0 / 0.5)" }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M2 2l8 8M10 2l-8 8" />
            </svg>
          </motion.button>
        )}
      </AnimatePresence>

      {/* personality tooltip */}
      <AnimatePresence>
        {hover && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            className="glass pointer-events-none absolute -bottom-2 left-1/2 z-20 w-[240px] -translate-x-1/2 translate-y-full rounded-xl p-3 text-[12px] leading-snug text-fog-300"
          >
            {persona.personality}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
