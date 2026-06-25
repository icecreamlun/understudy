# Understudy — Codex as your company's forward-deployed engineer

> **Built with the OpenAI Codex CLI.**
> Understudy watches how your team does its repetitive work, then **Codex steps in like a
> forward-deployed engineer**: it turns the workflow into a runnable skill, generates and
> refines it, and runs it end-to-end — under human sign-off. Like an understudy, it learns
> the role by watching, then performs it.

## The idea
A forward-deployed engineer (FDE) embeds in a company, watches how people actually work,
and ships the automation that removes the toil. **Understudy makes Codex that FDE.**

It observes a repeated workflow (e.g. a daily bank reconciliation across email + Excel),
proposes turning it into a **skill**, and then **Codex does the engineering**: drafting the
skill, refining its plan, and running it for real — reading the input, doing the work,
writing the output, all reviewable before anything is committed.

## Codex is the engine
Every AI call in Understudy runs through the **OpenAI Codex CLI** (`codex exec`) in API-key
mode — see [`skillforge_local/llm.py`](skillforge_local/llm.py). One function (`complete_text`)
shells out to Codex (read-only, ephemeral session, final message captured), so the **entire
product is powered by Codex**: workflow detection → skill generation → plan refinement →
execution all reason through Codex.

```python
# skillforge_local/llm.py — the whole app's AI goes through here
codex exec --skip-git-repo-check --ephemeral -s read-only \
  -c preferred_auth_method=apikey -o <final_message_file>   # auth via OPENAI_API_KEY
```

Deterministic guardrails stay deterministic — Codex shapes the plan and does the
engineering, but triggers, permissions, and "human approval before any write" are enforced
in code. Codex personalizes and executes; it never weakens safety.

## What it does (the flow)
1. **Observe** — watches email + spreadsheet activity, detects a repeated workflow.
2. **Recommend** — proposes turning it into a skill, with ROI.
3. **Generate (Codex)** — Codex drafts + refines the skill plan.
4. **Run (Codex)** — Codex executes the skill on a new event: reads the bank attachment,
   reconciles, writes a real reconciled `.xlsx` + reply draft + audit record.
5. **Learn** — 👍/👎 + notes are remembered (HydraDB, with a local fallback) and folded into
   the next generation, so it stops making you repeat yourself.

## Architecture
- **Backend** (Python) — `autoskill_agent/`: observe → recommend → generate → run → ops;
  `skillforge_local/`: email/Excel parsing, the Codex engine, the feedback-memory layer.
- **Frontend** (React + Vite + TS) — `frontend/`: Connections, Activity, Recommendations,
  Skills (feedback + Run), Memory, Workflows, Overview.
- **Engine:** OpenAI **Codex CLI** (`codex exec`, apikey mode). Optional: HydraDB for
  cross-session feedback memory.

## Quickstart
```bash
# 0. Prereq: the Codex CLI, logged in or with an API key
npm i -g @openai/codex

# 1. Key (.env.local is git-ignored)
cp .env.example .env.local       # set OPENAI_API_KEY

# 2. Backend
pip install -r requirements.txt
python -m autoskill_agent.cli skillgen-model-check   # confirms Codex is reachable
python -m autoskill_agent.api_server --host 127.0.0.1 --port 8017

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev            # proxies /api to the backend

# Reset the demo between runs:
python -m autoskill_agent.cli reset-demo --clear-memory
```
Pure-frontend preview (in-browser mock data, no backend): `cd frontend && VITE_USE_MOCKS=1 npm run dev`.

## Demo (≈2–3 min)
1. **Recommendations → Accept** → Codex generates the skill.
2. **Skills → Run** → Codex executes it: 1 exception flagged (a known $10 timing difference),
   real reconciled `.xlsx` produced.
3. **Teach it** — "that's a known timing difference, treat as matched."
4. **Run again** → it remembers, auto-resolves it (exceptions 1 → 0). Codex did the engineering;
   you only signed off.

> Codex isn't just helping you write code — it *is* the engineer doing the company's
> repetitive work.
