# Architecture Improvement Roadmap

This roadmap breaks down the agreed architecture plan into actionable workstreams.
Each section documents the goal, key tasks, success criteria, and potential risks
so we can tackle the initiatives incrementally.

## 1. Transactional Turn Handling

- **Goal:** Make moderator rollbacks consistent by preventing transcripts or
  checkpoints from retaining reverted turns.
- **Key Tasks:**
  - Design a persistence strategy (buffered writes vs. reversible storage) that
    works with the existing JSONL transcripts and SQLite checkpoints.
  - Adjust `Engine.tick()` so actions (e.g., `STEP_BACK`) are applied before
    persisting state or prune persisted data after actions.
  - Add regression tests that reproduce moderator rollbacks and verify both
    transcript and checkpoint contents.
- **Success Criteria:** After a moderator rollback, subsequent resumes and
  transcripts reflect only the retained conversation history.
- **Risks:** Changes to persistence may affect existing transcripts and
  checkpoints if migration tooling is not provided.

## 2. Scheduler Contract Alignment

- **Goal:** Resolve ambiguity around `run_on_last` and `non_blocking` scheduler
  knobs by either implementing them or removing them.
- **Key Tasks:**
  - Audit current scheduler usage and decide whether to support or deprecate the
    knobs.
  - If supported, update engine scheduling logic to honor these flags (e.g.,
    ensure advisors run without blocking and summarizers fire on the last turn).
  - Expand tests to cover the updated semantics across representative presets.
- **Success Criteria:** Scheduler behavior matches documented expectations and
  tests capture the new contract.
- **Risks:** Tweaks to scheduling may change preset behavior; documentation and
  migration notes must be updated in tandem.

## 3. Message Normalization Unification

- **Goal:** Eliminate duplicate content/metadata extraction logic by creating a
  shared helper.
- **Key Tasks:**
  - Extract the shared logic used by providers and runtime state into a single
    utility.
  - Update providers and state to use the new helper while maintaining backward
    compatibility for stored transcripts.
  - Add fixtures representing OpenAI, Ollama, JSON tool calls, etc., to lock in
    the behavior.
- **Success Criteria:** Providers and state rely on the same normalization code,
  and tests confirm correct handling of all known payload formats.
- **Risks:** Any regression in normalization can impact existing transcripts or
  tool parsing; thorough fixture coverage is essential.

## 4. Lab Lifecycle Reliability

- **Goal:** Ensure `Lab.start()` and `Lab.extend()` report accurate lifecycle
  state via `LabStatus`.
- **Key Tasks:**
  - Fix lifecycle toggles so `_active` is reset when runs finish or halt.
  - Update Python API and CLI tests to confirm `LabStatus.is_active` and
    iteration counters are correct in all modes (streaming, non-streaming,
    resume).
- **Success Criteria:** Consumers see truthful `LabStatus` values regardless of
  run mode, and regressions are covered by automated tests.
- **Risks:** Minimal; mainly ensuring synchronous and streaming code paths stay
  aligned.

## 5. Telegram Persistence Robustness

- **Goal:** Make the Telegram adapter construct `Store` instances with the same
  configuration as the core runtime.
- **Key Tasks:**
  - Pass preset-aware configuration when instantiating the persistence store.
  - Add integration tests to verify checkpoints/transcripts load without relying
    on patched constructors.
- **Success Criteria:** Adapter methods mirror CLI/pure Python behavior without
  test-only mocks.
- **Risks:** Requires carefully threading configuration into adapter entry
  points; ensure defaults still behave for legacy callers.

## 6. Documentation & Developer Experience

- **Goal:** Improve usability and reduce noise by updating documentation and
  eliminating repetitive warnings.
- **Key Tasks:**
  - Expand the CLI guide with the complete command matrix, interactive caveats,
    and local development hints (e.g., `PYTHONPATH=.`).
  - Rename or configure `UserInputSpec.validate` to silence the repeated
    Pydantic warning.
  - Document production vs. test tool usage, including rate limits and required
    environment variables.
- **Success Criteria:** Documentation reflects the full feature set, warnings no
  longer spam the console, and developers understand how to toggle integrations.
- **Risks:** Ensure doc updates stay aligned with future code changes to avoid
  drift.

## 7. Telemetry & Budget Controls (Optional Enhancement)

- **Goal:** Provide runtime knobs to disable live integrations or limit tool
  usage during tests.
- **Key Tasks:**
  - Introduce configuration flags or budgets to cap tool calls or switch to
    stubs.
  - Supply documentation and sample presets demonstrating the controls.
- **Success Criteria:** Developers can run deterministic tests without hitting
  external services or exceeding budgets.
- **Risks:** Optional scope; should not block earlier phases if deferred.

## 8. QA & Rollout

- **Goal:** Deliver the improvements safely with clear migration guidance.
- **Key Tasks:**
  - Extend integration tests (CLI + Python API) to cover rollback scenarios,
    scheduler semantics, and transcript replay smoke tests.
  - Prepare migration notes for existing transcripts/checkpoints, including any
    cleanup scripts or compatibility flags needed during rollout.
- **Success Criteria:** CI covers the new behavior, and users have a clear path
  to adopt changes without data loss.
- **Risks:** Without migration notes, teams might miss required cleanup steps;
  ensure communication accompanies code changes.


