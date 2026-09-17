# FillMyPDF Cold Email AI Agent

An AI agent for cold email marketing outreach for FillMyPDF — generating
personalized outreach emails and managing send campaigns to prospective leads.

## Project structure

```
src/
  agent/          # Core agent logic (email generation, personalization)
  leads/          # Lead list ingestion and enrichment
  email/          # Email sending integration (SMTP / provider API)
  config.py       # Configuration loading
  main.py         # Entry point
data/              # Lead lists, templates (gitignored where sensitive)
tests/             # Tests
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
```

## Status

Early scaffold — core agent functionality not yet implemented.
