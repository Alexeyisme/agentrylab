import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import Android from "../avatars/Android";
import { PALETTES, accentFor, alpha } from "../avatars/palettes";
import { useRoom } from "../store";
import type { Avatar, BodyId, FaceId, Mood, PaletteId, Persona } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

type Tab = "library" | "custom";

export default function AddPersonaModal({ open, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("library");

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
            className="glass flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl bg-ink-900/90"
          >
            <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">Add an android</h2>
                <p className="text-xs text-fog-400">Pick a personality from the library or build your own.</p>
              </div>
              <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1 text-sm">
                {(["library", "custom"] as Tab[]).map((t) => (
                  <button key={t} onClick={() => setTab(t)} className={`rounded-lg px-3 py-1.5 capitalize transition ${tab === t ? "bg-cyan-400 text-ink-950" : "text-fog-300 hover:bg-white/10"}`}>
                    {t === "library" ? "Library" : "Build your own"}
                  </button>
                ))}
              </div>
              <button onClick={onClose} className="ml-3 grid h-9 w-9 place-items-center rounded-full text-fog-300 hover:bg-white/10" aria-label="Close">
                ✕
              </button>
            </div>
            <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-6">{tab === "library" ? <Library onDone={onClose} /> : <Builder onDone={onClose} />}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ------------------------------------------------------------------ library
function Library({ onDone }: { onDone: () => void }) {
  const catalog = useRoom((s) => s.catalog);
  const personas = useRoom((s) => s.personas);
  const addFromLibrary = useRoom((s) => s.addFromLibrary);
  const toast = useRoom((s) => s.toast);
  const [hover, setHover] = useState<string | null>(null);
  const inRoom = useMemo(() => new Set(personas.map((p) => p.template_id)), [personas]);

  if (!catalog) return <p className="text-fog-400">Loading library…</p>;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {catalog.library.map((t: Persona) => {
        const accent = accentFor(t.avatar.palette);
        const already = inRoom.has(t.id);
        return (
          <motion.button
            key={t.id}
            whileHover={{ y: -3 }}
            whileTap={{ scale: 0.97 }}
            onMouseEnter={() => setHover(t.id)}
            onMouseLeave={() => setHover(null)}
            onClick={async () => {
              await addFromLibrary(t.id);
              toast(`${t.name} is walking on stage`);
              onDone();
            }}
            className="group relative flex flex-col items-center rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-center transition hover:border-white/20 hover:bg-white/[0.06]"
            style={{ boxShadow: hover === t.id ? `0 20px 40px -24px ${alpha(accent, 0.9)}` : undefined }}
          >
            {already && <span className="absolute right-2 top-2 rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-fog-300">on stage</span>}
            <Android avatar={t.avatar} size={84} mood={hover === t.id ? "talking" : "idle"} seed={t.id.length} />
            <div className="mt-1 font-semibold" style={{ color: accent }}>
              {t.name}
            </div>
            <div className="text-[11.5px] text-fog-400">{t.tagline}</div>
          </motion.button>
        );
      })}
    </div>
  );
}

// ------------------------------------------------------------------ builder
const FACE_IDS: FaceId[] = ["visor", "duo", "cyclops", "pixel", "feline", "crt"];
const BODY_IDS: BodyId[] = ["capsule", "boxy", "hover", "slim", "orb", "tank"];
const PALETTE_IDS = Object.keys(PALETTES) as PaletteId[];

function Builder({ onDone }: { onDone: () => void }) {
  const addCustom = useRoom((s) => s.addCustom);
  const toast = useRoom((s) => s.toast);
  const catalog = useRoom((s) => s.catalog);
  const [name, setName] = useState("");
  const [tagline, setTagline] = useState("");
  const [personality, setPersonality] = useState("");
  const [temperature, setTemperature] = useState(0.8);
  const [avatar, setAvatar] = useState<Avatar>({ face: "duo", body: "capsule", palette: "cyan" });
  const [preview, setPreview] = useState<Mood>("idle");
  const [busy, setBusy] = useState(false);

  const labelFor = (kind: "faces" | "bodies", id: string) => catalog?.avatars[kind].find((p) => p.id === id)?.label ?? id;
  const canSubmit = name.trim().length > 0 && personality.trim().length > 8 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    await addCustom({ name: name.trim(), tagline: tagline.trim(), personality: personality.trim(), avatar, temperature });
    setBusy(false);
    toast(`${name.trim()} is walking on stage`);
    onDone();
  };

  const shuffle = () => {
    const pick = <T,>(arr: T[]) => arr[Math.floor(Math.random() * arr.length)];
    setAvatar({ face: pick(FACE_IDS), body: pick(BODY_IDS), palette: pick(PALETTE_IDS) });
  };

  return (
    <div className="grid gap-6 md:grid-cols-[280px_1fr]">
      {/* preview */}
      <div className="flex flex-col items-center">
        <div className="relative flex w-full flex-col items-center rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-4">
          <div className="pointer-events-none absolute inset-x-6 bottom-4 h-10 rounded-full blur-2xl" style={{ background: alpha(accentFor(avatar.palette), 0.25) }} />
          <Android avatar={avatar} size={190} mood={preview} seed={7} />
          <div className="mt-2 text-center">
            <div className="font-semibold" style={{ color: accentFor(avatar.palette) }}>
              {name || "Unnamed unit"}
            </div>
            <div className="text-[11.5px] text-fog-400">{tagline || "no tagline yet"}</div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1 text-xs">
          {(["idle", "thinking", "talking"] as Mood[]).map((m) => (
            <button key={m} onClick={() => setPreview(m)} className={`rounded-lg px-2.5 py-1 capitalize ${preview === m ? "bg-white/15 text-white" : "text-fog-400 hover:text-fog-100"}`}>
              {m}
            </button>
          ))}
          <button onClick={shuffle} className="rounded-lg px-2.5 py-1 text-fog-400 hover:text-fog-100" title="Random look">
            🎲
          </button>
        </div>
      </div>

      {/* form */}
      <div className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value.slice(0, 40))} placeholder="e.g. Captain Fizz" className={inputCls} />
          </Field>
          <Field label="Tagline">
            <input value={tagline} onChange={(e) => setTagline(e.target.value.slice(0, 60))} placeholder="e.g. Never met a pun it didn't like" className={inputCls} />
          </Field>
        </div>
        <Field label="Personality (becomes the system prompt)">
          <textarea
            value={personality}
            onChange={(e) => setPersonality(e.target.value.slice(0, 2000))}
            rows={4}
            placeholder="You are Captain Fizz, a retired starship captain who relates everything to a near-death experience in space. Dramatic, generous, secretly sentimental…"
            className={`${inputCls} resize-y leading-snug`}
          />
        </Field>

        <Field label={`Face · ${labelFor("faces", avatar.face)}`}>
          <PartPicker ids={FACE_IDS} current={avatar.face} onPick={(face) => setAvatar({ ...avatar, face: face as FaceId })} render={(id) => <Android avatar={{ ...avatar, face: id as FaceId }} size={46} still />} />
        </Field>
        <Field label={`Body · ${labelFor("bodies", avatar.body)}`}>
          <PartPicker ids={BODY_IDS} current={avatar.body} onPick={(body) => setAvatar({ ...avatar, body: body as BodyId })} render={(id) => <Android avatar={{ ...avatar, body: id as BodyId }} size={46} still />} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-[1fr_200px]">
          <Field label="Colour">
            <div className="flex flex-wrap gap-2">
              {PALETTE_IDS.map((id) => (
                <button
                  key={id}
                  onClick={() => setAvatar({ ...avatar, palette: id })}
                  className={`h-8 w-8 rounded-full border-2 transition ${avatar.palette === id ? "scale-110 border-white" : "border-transparent hover:scale-105"}`}
                  style={{ background: PALETTES[id], boxShadow: `0 6px 16px -6px ${PALETTES[id]}` }}
                  title={id}
                />
              ))}
            </div>
          </Field>
          <Field label={`Creativity · ${temperature.toFixed(1)}`}>
            <input type="range" min={0} max={1.5} step={0.1} value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full" />
          </Field>
        </div>

        <div className="mt-1 flex justify-end">
          <button onClick={() => void submit()} disabled={!canSubmit} className="rounded-xl bg-cyan-400 px-5 py-2.5 font-semibold text-ink-950 shadow-[0_10px_30px_-12px_#22d3ee] transition hover:bg-cyan-300 active:scale-95 disabled:opacity-40">
            Add to room
          </button>
        </div>
      </div>
    </div>
  );
}

const inputCls = "w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-fog-100 outline-none placeholder:text-fog-400/50 focus:border-cyan-400/60";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10.5px] uppercase tracking-wider text-fog-400">{label}</span>
      {children}
    </label>
  );
}

function PartPicker({ ids, current, onPick, render }: { ids: string[]; current: string; onPick: (id: string) => void; render: (id: string) => React.ReactNode }) {
  return (
    <div className="flex flex-wrap gap-2">
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          onClick={() => onPick(id)}
          className={`grid h-16 w-14 place-items-center overflow-hidden rounded-xl border transition ${current === id ? "border-cyan-400 bg-cyan-400/10" : "border-white/10 bg-white/[0.03] hover:border-white/25"}`}
          title={id}
        >
          {render(id)}
        </button>
      ))}
    </div>
  );
}
