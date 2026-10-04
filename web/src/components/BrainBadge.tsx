import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useRoom } from "../store";
import type { Brain } from "../types";
import { ghostBtn, primaryBtn } from "./Modal";
import { BrainPicker } from "./RoomsMenu";

/** Shows which model drives the room; owners can click it to switch brains. */
export default function BrainBadge() {
  const provider = useRoom((s) => s.provider);
  const brain = useRoom((s) => s.brain);
  const ownerId = useRoom((s) => s.ownerId);
  const me = useRoom((s) => s.me);
  const setBrain = useRoom((s) => s.setBrain);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Brain>(brain);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const editable = !!ownerId && me?.user?.id === ownerId;

  useEffect(() => setDraft(brain), [brain]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [open]);

  if (!provider) return null;
  const tone = provider.demo ? "border-amber-400/40 bg-amber-400/10 text-amber-300" : "border-emerald-400/40 bg-emerald-400/10 text-emerald-300";
  const title = provider.demo
    ? ownerId
      ? "This room runs on the offline demo brain. Click to pick a real model."
      : "No server API key configured: the public stage uses the offline demo brain. Sign in and create a private room to use your own keys."
    : `Powered by ${provider.kind} · ${provider.model}`;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => editable && setOpen((v) => !v)}
        title={title}
        className={`rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${tone} ${editable ? "cursor-pointer hover:brightness-125" : "cursor-default"}`}
      >
        {provider.demo ? "demo brain" : provider.model}
        {editable && " ▾"}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            className="glass absolute right-0 top-10 z-40 w-80 rounded-2xl bg-ink-900/95 p-4"
          >
            <BrainPicker value={draft} onChange={setDraft} />
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className={ghostBtn}>
                Cancel
              </button>
              <button
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  if (await setBrain(draft)) setOpen(false);
                  setBusy(false);
                }}
                className={primaryBtn}
              >
                Switch
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
