import { AnimatePresence, motion } from "motion/react";
import { useEffect, type ReactNode } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  width?: string;
  children: ReactNode;
  actions?: ReactNode;
}

/** Shared glass dialog with backdrop, Escape to close, spring entrance. */
export default function Modal({ open, onClose, title, subtitle, width = "max-w-2xl", children, actions }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/70 p-4 backdrop-blur-sm"
          onMouseDown={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            className={`glass flex max-h-[88vh] w-full ${width} flex-col overflow-hidden rounded-3xl bg-ink-900/90`}
          >
            <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
                {subtitle && <p className="text-xs text-fog-400">{subtitle}</p>}
              </div>
              <div className="flex items-center gap-2">
                {actions}
                <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-full text-fog-300 hover:bg-white/10" aria-label="Close">
                  ✕
                </button>
              </div>
            </div>
            <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-6">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export const inputCls = "w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-fog-100 outline-none placeholder:text-fog-400/50 focus:border-cyan-400/60";
export const primaryBtn = "rounded-xl bg-cyan-400 px-5 py-2.5 font-semibold text-ink-950 shadow-[0_10px_30px_-12px_#22d3ee] transition hover:bg-cyan-300 active:scale-95 disabled:opacity-40";
export const ghostBtn = "rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-fog-200 transition hover:bg-white/10 disabled:opacity-40";

export function Field({ label, children, hint }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10.5px] uppercase tracking-wider text-fog-400">{label}</span>
      {children}
      {hint && <span className="text-[11.5px] text-fog-400">{hint}</span>}
    </label>
  );
}

export function ErrorLine({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>;
}
