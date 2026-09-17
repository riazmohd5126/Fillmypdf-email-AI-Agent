# FillMyPDF Cold Email AI Agent

An AI agent for cold email marketing outreach for FillMyPDF — generating
personalized outreach emails and managing send campaigns to prospective leads.

Design reference: `Core Email Sending Engine — Design Document` (multi-touch
Gmail sequences to specialty clinic contacts, with reply/bounce/unsubscribe
handling and deliverability guardrails).

## Project structure

```
src/
  agent/          # Core agent logic (email generation, personalization) — not yet built
  leads/          # Lead list ingestion and enrichment — not yet built
  mailer/         # Core sending engine (this is what's implemented so far)
    send_window.py       # business-day math, US holidays, send-window checks
    message_builder.py   # MIME message, threading headers, unsubscribe footer
    gmail_client.py       # Gmail API send wrapper (OAuth, internal Workspace app)
    pre_send_checks.py   # the 9 ordered pre-send checks (design doc section 6.1)
    send_worker.py       # the worker loop: pulls due enrollments, sends, reschedules
  db/
    models.py       # leads, sequences/sequence_steps, enrollments, messages, suppression
    base.py          # SQLAlchemy engine/session, init_db()
    create_tables.py # one-off script to create tables from the current models
  config.py       # configuration loading
  main.py         # entry point
data/              # Lead lists, templates (gitignored where sensitive)
tests/             # Tests
```

## What's implemented

The core sending engine: the five-table data model, the Gmail send integration
(MIME building, `List-Unsubscribe` headers, follow-up threading via
`In-Reply-To`/`References`), the ordered pre-send safety checks, and the
worker loop that ties them together (`src/mailer/send_worker.py:run_send_cycle`).

**Not yet built** (later stages per the design doc): the inbox watcher that
detects replies/bounces/auto-replies, the unsubscribe HTTP endpoints, the
admin UI, auto-pause monitoring, and the FastAPI/cron wiring that calls
`run_send_cycle()` on a schedule. `pre_send_checks.run_pre_send_checks`
already has the seam for the inbox watcher (`sync_inbox_if_stale`,
`has_new_reply` callables) — wire it up once that piece exists.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in DB, Gmail OAuth, and sender details
python -m src.db.create_tables
```

By default `DATABASE_URL` falls back to a local SQLite file for development;
set it to a Postgres URL for anything resembling production, per the design
doc.

## Status

Core sending engine in place; lead ingestion, AI drafting, and the reply/
bounce/unsubscribe pieces are next.
