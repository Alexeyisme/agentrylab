import { motion } from "motion/react";
import { useEffect, useMemo, useRef } from "react";
import Android from "../avatars/Android";
import { accentFor } from "../avatars/palettes";
import { useRoom } from "../store";
import type { Message, Persona } from "../types";

function fmt(t: number) {
  return new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatLog() {
  const messages = useRoom((s) => s.messages);
  const personas = useRoom((s) => s.personas);
  const ref = useRef<HTMLDivElement>(null);
  const byId = useMemo(() => new Map(personas.map((p) => [p.id, p])), [personas]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160;
    if (nearBottom) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  return (
    <div ref={ref} className="scrollbar-thin flex-1 overflow-y-auto px-4 py-3">
      {messages.length === 0 && (
        <p className="mt-10 text-center text-sm text-fog-400">Transcript will appear here.</p>
      )}
      <ul className="flex flex-col gap-3">
        {messages.map((m) => (
          <Row key={m.id} m={m} persona={byId.get(m.speaker_id)} />
        ))}
      </ul>
    </div>
  );
}

function Row({ m, persona }: { m: Message; persona?: Persona }) {
  if (m.kind === "system") {
    return (
      <motion.li initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="my-1 text-center font-mono text-[10.5px] uppercase tracking-[0.14em] text-fog-400/80">
        — {m.content} —
      </motion.li>
    );
  }
  if (m.kind === "user") {
    return (
      <motion.li initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-fog-100 px-3.5 py-2 text-[13.5px] leading-snug text-ink-950 shadow-lg">
          <div className="mb-0.5 flex items-baseline justify-between gap-3 text-[10.5px] font-semibold uppercase tracking-wider text-ink-950/60">
            <span>{m.speaker_name}</span>
            <span className="font-mono font-normal">{fmt(m.t)}</span>
          </div>
          {m.content}
        </div>
      </motion.li>
    );
  }
  const accent = persona ? accentFor(persona.avatar.palette) : "#8b93a7";
  return (
    <motion.li initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="flex gap-2.5">
      <div className="mt-0.5 h-9 w-7 shrink-0 overflow-visible">
        {persona ? <Android avatar={persona.avatar} size={28} still /> : <div className="h-7 w-7 rounded-full bg-shell-600" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-[12.5px] font-semibold" style={{ color: accent }}>
            {m.speaker_name}
          </span>
          <span className="font-mono text-[10px] text-fog-400">{fmt(m.t)}</span>
        </div>
        <p className="text-[13.5px] leading-snug text-fog-100/90">{m.content}</p>
      </div>
    </motion.li>
  );
}
