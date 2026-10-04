import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useRoom } from "../store";
import BrainBadge from "./BrainBadge";
import { RoomsMenu } from "./RoomsMenu";

export default function TopBar({ onAdd }: { onAdd: () => void }) {
  const topic = useRoom((s) => s.topic);
  const status = useRoom((s) => s.status);
  const speed = useRoom((s) => s.speed);
  const turn = useRoom((s) => s.turn);
  const connected = useRoom((s) => s.connected);
  const personas = useRoom((s) => s.personas);
  const catalog = useRoom((s) => s.catalog);
  const control = useRoom((s) => s.control);
  const setTopic = useRoom((s) => s.setTopic);
  const setSpeed = useRoom((s) => s.setSpeed);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(topic);
  useEffect(() => setDraft(topic), [topic]);

  const full = !!catalog && personas.length >= catalog.limits.max_personas;
  const running = status === "running";

  return (
    <header className="glass relative z-30 flex items-center gap-3 border-x-0 border-t-0 px-4 py-2.5">
      {/* brand */}
      <div className="flex items-center gap-2.5">
        <img src="/favicon.svg" alt="" className="h-7 w-7" />
        <div className="leading-none">
          <div className="text-[15px] font-bold tracking-tight">AgentryLab</div>
          <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-cyan-300/80">room</div>
        </div>
      </div>

      <div className="mx-2 h-6 w-px bg-white/10" />

      {/* topic */}
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <span className="hidden font-mono text-[10px] uppercase tracking-wider text-fog-400 sm:inline">topic</span>
        {editing ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              setEditing(false);
              if (draft.trim() && draft !== topic) void setTopic(draft);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              if (e.key === "Escape") {
                setDraft(topic);
                setEditing(false);
              }
            }}
            className="h-8 min-w-0 flex-1 rounded-lg border border-cyan-400/50 bg-white/5 px-3 text-sm outline-none"
          />
        ) : (
          <button onClick={() => setEditing(true)} className="group flex min-w-0 items-center gap-2 rounded-lg px-2 py-1 text-left hover:bg-white/5" title="Click to change the topic">
            <span className="truncate text-[15px] font-medium">{topic || "…"}</span>
            <svg className="h-3.5 w-3.5 shrink-0 text-fog-400 opacity-0 transition group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>
        )}
      </div>

      {/* transport */}
      <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
        <button
          onClick={() => void control(running ? "pause" : "play")}
          className={`grid h-8 w-8 place-items-center rounded-lg transition ${running ? "bg-cyan-400/15 text-cyan-300" : "text-fog-300 hover:bg-white/10"}`}
          title={running ? "Pause" : "Play"}
        >
          {running ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="5" y="4" width="5" height="16" rx="1" />
              <rect x="14" y="4" width="5" height="16" rx="1" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 4l13 8-13 8z" />
            </svg>
          )}
        </button>
        <button onClick={() => void control("step")} disabled={running} className="grid h-8 w-8 place-items-center rounded-lg text-fog-300 transition hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent" title="Step one turn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5 4l10 8-10 8z" />
            <rect x="17" y="4" width="3" height="16" rx="1" />
          </svg>
        </button>
        <div className="mx-1 hidden items-center gap-2 pl-1 md:flex" title="Seconds between turns">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-fog-400">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
          <input
            type="range"
            min={catalog?.limits.min_speed ?? 0.5}
            max={Math.min(15, catalog?.limits.max_speed ?? 15)}
            step={0.5}
            value={Math.min(15, speed)}
            onChange={(e) => void setSpeed(parseFloat(e.target.value))}
            className="h-1 w-24"
          />
          <span className="w-10 font-mono text-[11px] text-fog-300">{speed.toFixed(1)}s</span>
        </div>
      </div>

      <button
        onClick={onAdd}
        disabled={full}
        className="flex h-10 items-center gap-2 rounded-xl bg-cyan-400 px-3.5 font-semibold text-ink-950 shadow-[0_10px_30px_-12px_#22d3ee] transition hover:bg-cyan-300 active:scale-95 disabled:opacity-40"
        title={full ? "Room is full" : "Add an android"}
      >
        <span className="text-lg leading-none">+</span>
        <span className="hidden sm:inline">Add android</span>
      </button>

      {/* status */}
      <div className="hidden items-center gap-3 pl-1 lg:flex">
        <span className="font-mono text-[10.5px] text-fog-400">turn {turn}</span>
        <BrainBadge />
        <motion.span
          className="block h-2 w-2 rounded-full"
          style={{ background: connected ? "#34d399" : "#fb7185" }}
          animate={connected ? { opacity: [1, 0.5, 1] } : { opacity: 1 }}
          transition={{ duration: 2, repeat: Infinity }}
          title={connected ? "Live" : "Reconnecting…"}
        />
      </div>

      <RoomsMenu />
      <UserMenu />
    </header>
  );
}


function UserMenu() {
  const me = useRoom((s) => s.me);
  const openModal = useRoom((s) => s.openModal);
  const logout = useRoom((s) => s.logout);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [open]);

  if (!me?.user) {
    return (
      <button onClick={() => openModal("auth")} className="h-10 rounded-xl border border-white/10 bg-white/5 px-3.5 text-sm font-medium text-fog-100 transition hover:bg-white/10">
        Sign in
      </button>
    );
  }
  const initial = me.user.email[0]?.toUpperCase() ?? "?";
  const keyCount = me.keys.filter((k) => k.available).length;
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title={me.user.email}
        className="grid h-10 w-10 place-items-center rounded-full border border-cyan-400/40 bg-cyan-400/15 font-semibold text-cyan-200 transition hover:bg-cyan-400/25"
      >
        {initial}
        {!me.vault_unlocked && me.keys.length > 0 && <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-ink-900 bg-amber-400" title="Vault locked" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            className="glass absolute right-0 top-12 z-40 w-64 rounded-2xl bg-ink-900/95 p-2 text-sm"
          >
            <div className="truncate px-3 py-2 text-[12px] text-fog-400">{me.user.email}</div>
            <button
              onClick={() => {
                setOpen(false);
                openModal("keys");
              }}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left hover:bg-white/5"
            >
              <span>Brains & keys</span>
              <span className={`font-mono text-[10px] uppercase ${me.vault_unlocked ? "text-fog-400" : "text-amber-300"}`}>
                {me.vault_unlocked ? `${keyCount} key${keyCount === 1 ? "" : "s"}` : "locked"}
              </span>
            </button>
            <button
              onClick={() => {
                setOpen(false);
                openModal("newRoom");
              }}
              className="w-full rounded-xl px-3 py-2 text-left hover:bg-white/5"
            >
              New private room
            </button>
            <div className="mt-1 border-t border-white/5 pt-1">
              <button
                onClick={() => {
                  setOpen(false);
                  void logout();
                }}
                className="w-full rounded-xl px-3 py-2 text-left text-rose-200 hover:bg-rose-500/10"
              >
                Sign out &amp; wipe keys
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
