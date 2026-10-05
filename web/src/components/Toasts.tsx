import { AnimatePresence, motion } from "motion/react";
import { useRoom } from "../store";

/** Bottom-left stack of transient notifications (click to dismiss). */
export default function Toasts() {
  const toasts = useRoom((s) => s.toasts);
  const dismiss = useRoom((s) => s.dismissToast);
  return (
    <div className="pointer-events-none fixed bottom-4 left-4 z-[60] flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.button
            key={t.id}
            layout
            initial={{ opacity: 0, x: -30, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -20, scale: 0.9 }}
            onClick={() => dismiss(t.id)}
            className={`pointer-events-auto max-w-sm rounded-xl border px-3.5 py-2 text-left text-sm shadow-xl backdrop-blur ${
              t.tone === "error" ? "border-coral-400/40 bg-rose-500/15 text-rose-100" : "border-white/10 bg-ink-900/90 text-fog-100"
            }`}
          >
            {t.text}
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
