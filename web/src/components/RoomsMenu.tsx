import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { goToRoom, useRoom } from "../store";
import type { Brain } from "../types";
import Modal, { ErrorLine, Field, inputCls, primaryBtn } from "./Modal";

/** Dropdown listing the public stage and the user's own rooms. */
export function RoomsMenu() {
  const rooms = useRoom((s) => s.rooms);
  const roomId = useRoom((s) => s.roomId);
  const me = useRoom((s) => s.me);
  const loadRooms = useRoom((s) => s.loadRooms);
  const deleteRoom = useRoom((s) => s.deleteRoom);
  const openModal = useRoom((s) => s.openModal);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    void loadRooms();
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [open, loadRooms]);

  const current = rooms.find((r) => r.id === roomId);
  const label = roomId === "main" ? "Public stage" : current?.topic || roomId;

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((v) => !v)} className="flex h-10 max-w-[200px] items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-fog-200 hover:bg-white/10" title="Switch room">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-fog-400">
          <path d="M3 9l9-6 9 6v11a1 1 0 01-1 1h-5v-7h-6v7H4a1 1 0 01-1-1z" />
        </svg>
        <span className="truncate">{label}</span>
        <span className="text-[10px] text-fog-400">▾</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            className="glass absolute right-0 top-12 z-40 w-72 rounded-2xl bg-ink-900/95 p-2"
          >
            {rooms.map((r) => (
              <div key={r.id} className={`group flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${r.id === roomId ? "bg-white/10" : "hover:bg-white/5"}`}>
                <button onClick={() => goToRoom(r.id)} className="min-w-0 flex-1 text-left">
                  <div className="truncate font-medium">{r.id === "main" ? "Public stage" : r.topic}</div>
                  <div className="truncate font-mono text-[10px] text-fog-400">
                    {r.id === "main" ? "shared · " : "private · "}
                    {r.brain.model} · {r.personas} on stage
                  </div>
                </button>
                {r.mine && (
                  <button onClick={() => void deleteRoom(r.id)} title="Close room" className="hidden h-6 w-6 shrink-0 place-items-center rounded-full text-fog-400 hover:bg-rose-500/20 hover:text-rose-200 group-hover:grid">
                    ✕
                  </button>
                )}
              </div>
            ))}
            <div className="mt-1 border-t border-white/5 pt-1">
              <button
                onClick={() => {
                  setOpen(false);
                  openModal(me?.user ? "newRoom" : "auth");
                }}
                className="w-full rounded-xl px-3 py-2 text-left text-sm text-cyan-300 hover:bg-white/5"
              >
                + New private room{me?.user ? "" : " (sign in)"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const SLUG = /[^a-z0-9-]+/g;

export function NewRoomModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const createRoom = useRoom((s) => s.createRoom);
  const [topic, setTopic] = useState("");
  const [id, setId] = useState("");
  const [brain, setBrain] = useState<Brain>({ provider: "mock", model: null });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const rid = await createRoom({ id: id || undefined, topic: topic || undefined, brain });
      goToRoom(rid);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="New private room" subtitle="Only you can see it. It runs on the brain you pick, with your own key." width="max-w-lg">
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <Field label="Topic">
          <input className={inputCls} value={topic} onChange={(e) => setTopic(e.target.value.slice(0, 200))} placeholder="e.g. Should robots have weekends?" autoFocus />
        </Field>
        <Field label="Room id (optional)" hint="Shows in the URL. Letters, numbers and dashes.">
          <input className={`${inputCls} font-mono`} value={id} onChange={(e) => setId(e.target.value.toLowerCase().replace(SLUG, "-").slice(0, 40))} placeholder="auto" />
        </Field>
        <BrainPicker value={brain} onChange={setBrain} />
        <ErrorLine error={error} />
        <button type="submit" disabled={busy} className={`${primaryBtn} self-end`}>
          Create room
        </button>
      </form>
    </Modal>
  );
}

/** Provider + model chooser. Key providers are listed only when a key is available. */
export function BrainPicker({ value, onChange }: { value: Brain; onChange: (b: Brain) => void }) {
  const catalog = useRoom((s) => s.catalog);
  const me = useRoom((s) => s.me);
  const openModal = useRoom((s) => s.openModal);
  const available = new Set((me?.keys ?? []).filter((k) => k.available).map((k) => k.provider));
  const specs = catalog?.providers ?? [];
  const spec = specs.find((p) => p.id === value.provider);
  const missing = specs.filter((p) => p.docs && !available.has(p.id));

  return (
    <div className="flex flex-col gap-3">
      <Field label="Brain">
        <select
          className={inputCls}
          value={value.provider}
          onChange={(e) => onChange({ provider: e.target.value, model: null })}
        >
          {specs.map((p) => {
            const needsKey = !!p.docs && !available.has(p.id);
            return (
              <option key={p.id} value={p.id} disabled={needsKey}>
                {p.label}
                {needsKey ? " — add a key first" : ""}
              </option>
            );
          })}
        </select>
      </Field>
      <Field label="Model" hint={spec ? `Default: ${spec.default_model}` : undefined}>
        <input
          className={`${inputCls} font-mono`}
          list="model-suggestions"
          value={value.model ?? ""}
          onChange={(e) => onChange({ ...value, model: e.target.value.trim() || null })}
          placeholder={spec?.default_model ?? "model"}
        />
        <datalist id="model-suggestions">{(spec?.models ?? []).map((m) => <option key={m} value={m} />)}</datalist>
      </Field>
      {missing.length > 0 && (
        <p className="text-[11.5px] text-fog-400">
          Want {missing.map((m) => m.label).join(", ")}?{" "}
          <button type="button" onClick={() => openModal("keys")} className="text-cyan-300 hover:underline">
            Add a key
          </button>
          .
        </p>
      )}
    </div>
  );
}
