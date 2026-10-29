# Keepup

## Goal
Keepup is a free ($0) news briefing app. Each day it serves "Today's Read":
about 8 story cards in three buckets (must-know, trending, for-you), followed
by a 5-question quiz. Main audience: data, AI, and DevOps people; general news
is a secondary set of categories. It must work on desktop and phone as a
responsive web app.

## Features (build in this order)
1. Pipeline: ingest → dedupe → cluster → classify → summarize → rank
2. API
3. Today's Read UI
4. Quiz
5. Pipeline health page
6. "Ask Keepup" news Q&A (plain RAG baseline first)
7. Keepup MCP server (FastMCP)
8. Agentic Ask Keepup (LangGraph) that uses the MCP tools
9. One or two small agents (pipeline-failure triage, quiz critic)
10. Evaluation (baseline vs agent)
11. Deploy
12. CI

Ingest, dedupe, clustering, classification, and ranking are plain
deterministic code, **not agents**.

### Topic following
- Users pick the categories they care about. Two presets (Tech, Everyday) sit
  behind a header chip.
- It only affects selection and ranking at serve time, **never the pipeline**.
- Preferences are stored in the browser.

### PWA
Installable PWA: manifest, service worker, and an offline cache of Today's Read.

## Stack
- Python 3.11+, FastAPI
- Postgres + pgvector (Neon free tier later)
- sentence-transformers, scikit-learn
- A free-tier LLM API behind a swappable wrapper
- Next.js + Tailwind (Vercel later)
- Docker, GitHub Actions

## Rules
- **$0 rule:** everything must stay free. No paid APIs, no paid tiers.
- **Small steps, stop and wait:** the user is a beginner. For each step,
  explain what you're about to do in 2-3 sentences, make the smallest change
  that runs, then STOP and wait for the user. Create at most 3 files per step
  (.gitkeep placeholders don't count).
- **Parallel work:** backend/ and frontend/ are separate tracks on separate
  branches. Only edit files inside your own track's folder. Shared files
  (CLAUDE.md, README.md, docs/) are edited from the main branch only.

## Layout
- `backend/`: Python pipeline + FastAPI
- `frontend/`: Next.js app
- `docs/`: shared docs
- `data/`: local data
