---
title: MedReport AI
emoji: 🩺
colorFrom: teal
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# MedReport AI — Digital Medical Report Interpreter

An AI-assisted medical report interpreter that explains lab reports in plain
language, in Patient/Student/Doctor modes, in English or Telugu — grounded
entirely in extracted report data, never fabricating values.

See the main [README.md](./README.md) for full documentation.

## Deploying this Space

1. Set your API keys under **Settings → Repository secrets** (not regular
   variables — secrets are hidden from the Space's public logs and code):
   `GROQ_API_KEY`, `SARVAM_API_KEY`, and any others you're using.
2. Optional but recommended for data to survive restarts: add `DATABASE_URL`
   as a secret too, pointing at a free Neon or Supabase Postgres instance —
   without it, uploaded reports and chat history reset whenever this Space
   sleeps (free tier sleeps after 48 hours of inactivity) or rebuilds.
3. Push to this Space's git repository — it builds and deploys automatically
   from the `Dockerfile` at the repo root.
