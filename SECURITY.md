# Security Policy

## Supported versions

- Active development happens on the default branch.
- We test on Python 3.11 and 3.12 in CI.

## Reporting a vulnerability

- Please open a GitHub Security Advisory or email the maintainer.
- Include reproduction steps and environment details where possible.
- We will acknowledge receipt within 72 hours and work on a fix or mitigation plan.

## How the Room handles secrets

The web app (`agentrylab serve`) lets users bring their own model API keys. The
full threat model lives in
[`src/agentrylab/docs/ROOM.md` → Accounts & keys](src/agentrylab/docs/ROOM.md#accounts--keys-bring-your-own-model);
the short version:

- **Keys live in server memory only** by default, per signed-in user, and are
  wiped on sign-out, "forget", or process restart. They are never logged, never
  returned by any endpoint (only a `…1234` hint), and never written to transcripts.
- **"Remember" is opt-in per key** and stores the key AES-256-GCM encrypted under
  a key derived from the user's password (scrypt). The password is not stored, so
  the database alone cannot be decrypted, including by the operator.
- **Passwords** are scrypt-hashed; login is rate-limited and uses constant-time
  comparison. **Sessions** are random tokens stored hashed, in an
  `HttpOnly; SameSite=Lax` cookie (`Secure` behind HTTPS).
- **Known limitation:** a compromised live server process can read keys from
  memory while a user is signed in. Browser-held keys are on the roadmap to remove
  that trust requirement.

## Hardening checklist for operators

- Serve behind HTTPS and set `AGENTRYLAB_COOKIE_SECURE=1`.
- Set `AGENTRYLAB_ALLOW_SIGNUP=0` once your users have registered.
- Run a single uvicorn worker (rooms and the vault are per-process).
- Back up `outputs/room.db` (accounts, encrypted keys); it contains no plaintext secrets.
- Keep `OPENAI_API_KEY` out of the environment of a public deployment unless you
  want anonymous visitors to spend it on the public stage; the demo brain is free.
- Ask users to create provider keys with a spending cap.
