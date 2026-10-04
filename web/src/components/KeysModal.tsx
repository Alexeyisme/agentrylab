import { motion } from "motion/react";
import { useState } from "react";
import { useRoom } from "../store";
import type { KeyInfo, ProviderSpec } from "../types";
import Modal, { ErrorLine, ghostBtn, inputCls, primaryBtn } from "./Modal";

export default function KeysModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const me = useRoom((s) => s.me);
  const catalog = useRoom((s) => s.catalog);
  const forgetAll = useRoom((s) => s.forgetAllKeys);
  const logout = useRoom((s) => s.logout);
  const toast = useRoom((s) => s.toast);
  const providers = (catalog?.providers ?? []).filter((p) => p.docs);
  const keys = new Map((me?.keys ?? []).map((k) => [k.provider, k]));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Brains & keys"
      subtitle={me?.user ? `Signed in as ${me.user.email}` : "Sign in to add keys"}
      width="max-w-3xl"
      actions={
        me?.user ? (
          <button onClick={() => void logout().then(onClose)} className={ghostBtn}>
            Sign out
          </button>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        <SecurityNote />
        {me?.user && !me.vault_unlocked && <UnlockBanner />}
        <div className="flex flex-col gap-3">
          {providers.map((p) => (
            <KeyRow key={p.id} spec={p} info={keys.get(p.id)} locked={!me?.vault_unlocked} />
          ))}
        </div>
        {me?.keys.length ? (
          <div className="flex items-center justify-between rounded-2xl border border-rose-400/20 bg-rose-500/5 px-4 py-3">
            <div className="text-sm">
              <div className="font-medium text-rose-100">Forget all keys now</div>
              <div className="text-[11.5px] text-fog-400">Wipes every key from server memory and deletes the encrypted copies.</div>
            </div>
            <button
              onClick={() => {
                void forgetAll().then(() => toast("All keys forgotten."));
              }}
              className="rounded-xl border border-rose-400/40 px-3 py-1.5 text-sm text-rose-200 hover:bg-rose-500/15"
            >
              Forget all
            </button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

function SecurityNote() {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3 text-[13px] leading-snug text-fog-200">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-lg" aria-hidden>
          🔐
        </span>
        <div className="flex-1">
          <p>
            <strong className="text-fog-100">Your keys stay in this server's memory only</strong> and are wiped when you sign out, click
            "forget", or the server restarts. Nobody can read them from the database or logs, including the operator.
          </p>
          <button onClick={() => setOpen((v) => !v)} className="mt-1 text-[12px] text-cyan-300 hover:underline">
            {open ? "Hide details" : "How does “remember” work?"}
          </button>
          {open && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-[12.5px] text-fog-300">
              <li>Keys are never written to disk unless you tick “remember on this server”.</li>
              <li>A remembered key is encrypted (AES-256-GCM) with a key derived from your password (scrypt). The server does not store your password, so the database alone cannot be decrypted.</li>
              <li>After a restart the vault is locked until you sign in or enter your password again.</li>
              <li>Keys are only ever sent to the provider you chose (OpenAI, Anthropic, DeepSeek, xAI) and only when one of your rooms takes a turn.</li>
              <li>Prefer keys with a spending cap, and revoke them at the provider if in doubt.</li>
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function UnlockBanner() {
  const unlock = useRoom((s) => s.unlock);
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="flex flex-col gap-2 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        unlock(pw).then(() => setPw(""), (err: Error) => setError(err.message));
      }}
    >
      <div className="text-sm text-amber-100">
        <strong>Vault locked.</strong> The server restarted, so your remembered keys are still encrypted. Enter your password to unlock them.
      </div>
      <div className="flex gap-2">
        <input className={inputCls} type="password" autoComplete="current-password" placeholder="Password" value={pw} onChange={(e) => setPw(e.target.value)} />
        <button type="submit" disabled={!pw} className={primaryBtn}>
          Unlock
        </button>
      </div>
      <ErrorLine error={error} />
    </form>
  );
}

function KeyRow({ spec, info, locked }: { spec: ProviderSpec; info?: KeyInfo; locked: boolean }) {
  const saveKey = useRoom((s) => s.saveKey);
  const removeKey = useRoom((s) => s.removeKey);
  const toast = useRoom((s) => s.toast);
  const [editing, setEditing] = useState(!info);
  const [key, setKey] = useState("");
  const [remember, setRemember] = useState(info?.remembered ?? false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await saveKey(spec.id, key.trim(), remember);
      setKey("");
      setEditing(false);
      toast(`${spec.label} key ${remember ? "remembered (encrypted)" : "loaded for this session"}.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const status = !info ? null : !info.available ? { text: "locked", cls: "border-amber-400/40 text-amber-300" } : info.remembered ? { text: "remembered", cls: "border-emerald-400/40 text-emerald-300" } : { text: "this session", cls: "border-cyan-400/40 text-cyan-300" };

  return (
    <motion.div layout className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[140px] flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{spec.label}</span>
            {status && <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${status.cls}`}>{status.text}</span>}
          </div>
          <div className="text-[11.5px] text-fog-400">
            {info ? `key ${info.hint}` : "no key"} ·{" "}
            <a href={spec.docs} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline">
              get a key ↗
            </a>
          </div>
        </div>
        {!editing && (
          <div className="flex gap-2">
            <button onClick={() => setEditing(true)} className={ghostBtn}>
              Replace
            </button>
            <button
              onClick={() => {
                void removeKey(spec.id).then(() => toast(`${spec.label} key removed.`));
              }}
              className="rounded-xl border border-rose-400/30 px-3 py-2 text-sm text-rose-200 hover:bg-rose-500/10"
            >
              Remove
            </button>
          </div>
        )}
      </div>
      {editing && (
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <div className="flex gap-2">
            <input
              className={`${inputCls} font-mono`}
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder={spec.key_hint ?? "API key"}
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
            <button type="submit" disabled={busy || key.trim().length < 8} className={primaryBtn}>
              Save
            </button>
            {info && (
              <button type="button" onClick={() => setEditing(false)} className={ghostBtn}>
                Cancel
              </button>
            )}
          </div>
          <label className={`flex items-center gap-2 text-[12.5px] ${locked ? "text-fog-400" : "text-fog-200"}`}>
            <input type="checkbox" disabled={locked} checked={remember && !locked} onChange={(e) => setRemember(e.target.checked)} className="accent-cyan-400" />
            Remember on this server (encrypted with your password){locked ? " — unlock the vault first" : ""}
          </label>
          <ErrorLine error={error} />
        </form>
      )}
    </motion.div>
  );
}
