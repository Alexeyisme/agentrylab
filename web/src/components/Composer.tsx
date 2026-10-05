import { useState } from "react";
import { useRoom } from "../store";

/** The human's input: a remembered display name plus a message box (Enter sends, Shift+Enter breaks a line). */
export default function Composer() {
  const say = useRoom((s) => s.say);
  const userName = useRoom((s) => s.userName);
  const setUserName = useRoom((s) => s.setUserName);
  const personas = useRoom((s) => s.personas);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const content = text.trim();
    if (!content || busy) return;
    setBusy(true);
    setText("");
    await say(content);
    setBusy(false);
  };

  const hint = personas.length
    ? `Say something… mention ${personas[Math.floor(Math.random() * personas.length)].name} to address them`
    : "Say something… (add an android so someone can answer)";

  return (
    <div className="border-t border-white/5 bg-ink-950/40 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-mono text-[10.5px] uppercase tracking-wider text-fog-400">You are</span>
        <input
          value={userName}
          onChange={(e) => setUserName(e.target.value.slice(0, 24))}
          placeholder="Your name"
          className="h-7 w-32 rounded-md border border-white/10 bg-white/5 px-2 text-xs text-fog-100 outline-none placeholder:text-fog-400/60 focus:border-cyan-400/60"
        />
      </div>
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          rows={Math.min(4, Math.max(1, text.split("\n").length))}
          placeholder={hint}
          className="min-h-[40px] flex-1 resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[13.5px] leading-snug text-fog-100 outline-none placeholder:text-fog-400/60 focus:border-cyan-400/60"
        />
        <button
          onClick={() => void submit()}
          disabled={!text.trim() || busy}
          className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-400 text-ink-950 transition hover:bg-cyan-300 active:scale-95 disabled:opacity-40 disabled:hover:bg-cyan-400"
          title="Send (Enter)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
