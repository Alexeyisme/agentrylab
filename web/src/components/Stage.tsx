import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { useRoom } from "../store";
import type { Message, Mood } from "../types";
import AndroidCard from "./AndroidCard";
import Guest from "./Guest";

function sizeFor(n: number, width: number) {
  const base = n <= 2 ? 210 : n <= 4 ? 180 : n <= 6 ? 150 : n <= 9 ? 125 : 105;
  if (width >= 1024) return base;
  // Narrow screens: fit two or three per row.
  const cols = n <= 1 ? 1 : width < 480 ? 2 : 3;
  return Math.max(84, Math.min(base, Math.floor(width / cols) - 48));
}

function useWidth() {
  const [w, setW] = useState(() => window.innerWidth);
  useEffect(() => {
    const on = () => setW(window.innerWidth);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return w;
}

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/**
 * The room itself: androids laid out responsively, the latest line of each as a
 * speech bubble, the human guest, and an empty-state call to action. Each
 * android's mood is derived here from the store's `thinking` / `speaking`.
 */
export default function Stage({ onAdd }: { onAdd: () => void }) {
  const personas = useRoom((s) => s.personas);
  const messages = useRoom((s) => s.messages);
  const thinking = useRoom((s) => s.thinking);
  const speaking = useRoom((s) => s.speaking);
  const finishedSpeaking = useRoom((s) => s.finishedSpeaking);
  const removePersona = useRoom((s) => s.removePersona);
  const userName = useRoom((s) => s.userName);

  // Latest line per speaker, plus which one is the freshest overall.
  const { lastBySpeaker, latest } = useMemo(() => {
    const map = new Map<string, Message>();
    let latest: Message | null = null;
    for (const m of messages) {
      if (m.kind === "system") continue;
      map.set(m.speaker_id, m);
      latest = m;
    }
    return { lastBySpeaker: map, latest };
  }, [messages]);

  const width = useWidth();
  const size = sizeFor(personas.length + (lastBySpeaker.has("user") ? 1 : 0), width);
  const guestLine = lastBySpeaker.get("user") ?? null;

  return (
    <section className="relative flex min-h-0 flex-1 flex-col overflow-hidden noise">
      {/* ambient lights */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-40 top-10 h-[420px] w-[420px] rounded-full bg-cyan-400/10 blur-[120px]" />
        <div className="absolute -right-40 top-40 h-[380px] w-[380px] rounded-full bg-fuchsia-400/10 blur-[120px]" />
        <div className="absolute bottom-0 left-1/2 h-[220px] w-[80%] -translate-x-1/2 rounded-full bg-cyan-300/5 blur-[100px]" />
      </div>
      <div className="stage-floor pointer-events-none absolute inset-x-[-20%] bottom-0 h-[52%]" />

      <div className="scrollbar-thin relative z-10 flex min-h-0 flex-1 flex-col items-center overflow-y-auto px-4 pb-12 pt-4 lg:justify-center lg:px-6">
        {personas.length === 0 && !guestLine ? (
          <EmptyStage onAdd={onAdd} />
        ) : (
          <motion.div layout className="my-auto flex w-full flex-wrap items-end justify-center gap-x-2 gap-y-8">
            <AnimatePresence mode="popLayout">
              {personas.map((p) => {
                const last = lastBySpeaker.get(p.id) ?? null;
                const mood: Mood = thinking === p.id ? "thinking" : speaking?.personaId === p.id ? "talking" : "idle";
                const isLatest = !!last && latest?.id === last.id;
                const bubble = last && (isLatest || Date.now() - last.t * 1000 < 12000) ? last : null;
                return (
                  <AndroidCard
                    key={p.id}
                    persona={p}
                    mood={mood}
                    size={size}
                    seed={hash(p.id)}
                    bubble={bubble}
                    bubbleLive={!!bubble && speaking?.messageId === bubble.id}
                    bubbleDimmed={!!bubble && !isLatest}
                    onBubbleDone={() => bubble && finishedSpeaking(bubble.id)}
                    onRemove={() => removePersona(p.id)}
                  />
                );
              })}
              {guestLine && (
                <Guest key="guest" name={guestLine.speaker_name || userName || "You"} line={guestLine} isLatest={latest?.id === guestLine.id} size={size} />
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      {/* footer hint */}
      <div className="pointer-events-none absolute bottom-3 left-0 right-0 z-10 hidden justify-center sm:flex">
        <span className="rounded-full border border-white/5 bg-ink-900/60 px-3 py-1 font-mono text-[10.5px] tracking-wide text-fog-400 backdrop-blur">
          {personas.length} on stage · hover an android to read its personality or remove it
        </span>
      </div>
    </section>
  );
}

function EmptyStage({ onAdd }: { onAdd: () => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10 flex max-w-md flex-col items-center text-center">
      <motion.div
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="mb-6 grid h-20 w-20 place-items-center rounded-3xl border border-white/10 bg-white/5 text-4xl shadow-glass"
      >
        <span aria-hidden>🤖</span>
      </motion.div>
      <h2 className="text-2xl font-semibold tracking-tight">The stage is empty</h2>
      <p className="mt-2 text-fog-400">Add a couple of androids and watch them riff. You can drop in and talk to them whenever you like.</p>
      <button onClick={onAdd} className="mt-6 rounded-full bg-cyan-400 px-5 py-2.5 font-semibold text-ink-950 shadow-[0_10px_30px_-10px_#22d3ee] transition hover:bg-cyan-300 active:scale-95">
        + Add an android
      </button>
    </motion.div>
  );
}
