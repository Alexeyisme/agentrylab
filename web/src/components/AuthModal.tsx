import { useState } from "react";
import { useRoom } from "../store";
import Modal, { ErrorLine, Field, inputCls, primaryBtn } from "./Modal";

type Mode = "login" | "register";

/** Sign in / create account dialog; opens the keys vault on success. */
export default function AuthModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const login = useRoom((s) => s.login);
  const register = useRoom((s) => s.register);
  const signupEnabled = useRoom((s) => s.me?.signup_enabled ?? true);
  const openModal = useRoom((s) => s.openModal);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      setPassword("");
      onClose();
      openModal("keys");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={mode === "login" ? "Sign in" : "Create an account"}
      subtitle="Accounts exist so you can bring your own model keys and run private rooms."
      width="max-w-md"
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <div className="flex items-center gap-1 self-start rounded-xl border border-white/10 bg-white/5 p-1 text-sm">
          <button type="button" onClick={() => setMode("login")} className={`rounded-lg px-3 py-1.5 transition ${mode === "login" ? "bg-cyan-400 text-ink-950" : "text-fog-300 hover:bg-white/10"}`}>
            Sign in
          </button>
          <button
            type="button"
            disabled={!signupEnabled}
            onClick={() => setMode("register")}
            className={`rounded-lg px-3 py-1.5 transition disabled:opacity-40 ${mode === "register" ? "bg-cyan-400 text-ink-950" : "text-fog-300 hover:bg-white/10"}`}
          >
            Create account
          </button>
        </div>
        <Field label="Email">
          <input className={inputCls} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </Field>
        <Field label="Password" hint={mode === "register" ? "At least 8 characters. It also encrypts any keys you choose to remember, so there is no reset: forgetting it means re-entering your keys." : undefined}>
          <input
            className={inputCls}
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "register" ? 8 : 1}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </Field>
        <ErrorLine error={error} />
        <button type="submit" disabled={busy || !email || !password} className={`${primaryBtn} mt-1`}>
          {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p className="text-[11.5px] leading-snug text-fog-400">
          OAuth (Google, GitHub) is on the roadmap. Nothing here is shared with third parties; your email is only your login.
        </p>
      </form>
    </Modal>
  );
}
