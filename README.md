# Understudy — Codex as your company's forward-deployed engineer

Every enterprise wants AI to "just work" on their workflows. But deploying it today looks
like 2015: you hire a forward-deployed engineer, they shadow your team for weeks,
hand-build an integration, and leave. Scale that across an org? Impossible.

**Understudy is the agent that does what a forward-deployed engineer does — autonomously,
with Codex as the engineer.** Connect your tools (email, spreadsheets, Slack). It silently
observes. It detects the repeated workflows hiding in plain sight. It surfaces them **on a
dashboard** with ROI estimates. Accept one, and **Codex generates a production-grade skill**
— complete with guardrails, validation, and a live execution diagram — then **installs it
straight into Codex as a runnable `/workflow`**, ready to fire on your next trigger.

### One step beyond ambient Codex
Codex can already *watch* what you're doing — its ambient/computer-use awareness knows your
activity. Understudy goes a step further: it's a **dashboard that auto-discovers the
workflows inside that activity** and turns each one into an **installed Codex workflow**
(`~/.codex/prompts/<skill>.md` → invoke it as `/<skill>` inside Codex). Codex stops being a
thing you prompt and becomes the engineer that ships your team's automation.

### Why it's real, not a demo: it evolves with you
Correct it once — *"that $10 difference is a known timing issue"* — and it never asks again.
Rate a generated skill — *"match against the Payment Export sheet, not the raw feed"* — and
every future generation reflects that preference. **Memory isn't a feature; it's why this
agent compounds instead of resetting to zero every morning.** Long-term memory is stored in
and recalled from **HydraDB** — cross-session, cross-skill, per-reviewer namespaced (with a
local fallback if no key is set). A live **Memory tab** streams every autonomous read/write
in real time; wipe all local state and regenerate, and it still remembers, because HydraDB
does.

**Engine:** every AI call — workflow detection, skill generation, plan refinement, and
execution — runs through the **OpenAI Codex CLI** (`codex exec`, API-key mode). Deterministic
guardrails (triggers, permissions, *human approval before any write*) stay enforced in code:
Codex personalizes and does the engineering; it never weakens safety.

**Stack:** Codex · HydraDB · Python · React + Vite

---

## The flow
1. **Observe** — watch email + spreadsheet activity; detect a repeated workflow.
2. **Discover (dashboard)** — surface it with ROI (time saved, throughput, AI cost).
3. **Generate (Codex)** — accept → Codex drafts + refines a production-grade skill.
4. **Install into Codex** — the skill lands in `~/.codex/prompts/` as a `/workflow`.
5. **Run (Codex)** — execute on a new event: read the bank attachment, reconcile, write a
   real reconciled `.xlsx` + reply draft + audit record — under human sign-off.
6. **Learn** — feedback + corrections are remembered (HydraDB) and folded into the next run.

## Architecture
- **Backend** (Python) — `autoskill_agent/`: observe → recommend → generate → run → ops;
  `skillforge_local/`: email/Excel parsing, the **Codex engine** (`llm.py`), the
  feedback-memory layer.
- **Frontend** (React + Vite + TS) — `frontend/`: Connections, Activity, Recommendations,
  Skills (feedback + Run), Memory, Workflows, Overview.
- **Engine:** OpenAI **Codex CLI**. Optional: HydraDB for cross-session memory.

## Quickstart
```bash
# 0. Prereq: the Codex CLI (login or API key)
npm i -g @openai/codex

# 1. Key (.env.local is git-ignored)
cp .env.example .env.local            # set OPENAI_API_KEY

# 2. Backend
pip install -r requirements.txt
python -m autoskill_agent.cli skillgen-model-check     # confirms Codex is reachable
python -m autoskill_agent.api_server --host 127.0.0.1 --port 8017

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev              # proxies /api to the backend

# Reset the demo between runs:
python -m autoskill_agent.cli reset-demo --clear-memory
```
Pure-frontend preview (in-browser mock data, no backend): `cd frontend && VITE_USE_MOCKS=1 npm run dev`.

## Demo (≈2–3 min)
1. **Recommendations → Accept** → Codex generates the skill and installs it into Codex as
   `/daily-cash-reconciliation`.
2. **Skills → Run** → Codex executes it: 1 exception flagged (a known $10 timing difference),
   a real reconciled `.xlsx` produced.
3. **Teach it** — "that's a known timing difference, treat as matched."
4. **Run again** → it remembers, auto-resolves it (exceptions 1 → 0). Codex did the
   engineering; you only signed off.
