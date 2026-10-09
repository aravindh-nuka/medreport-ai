# MedReport AI — Digital Medical Report Interpreter

A production-ready, free-and-open-source system that turns a digital (text-based)
medical report PDF into a clear, trustworthy explanation — in Patient, Student, or
Doctor mode, in English or Telugu — without ever inventing information that isn't
in the report.

> **Not a diagnostic tool.** This app provides educational information only and is
> not a substitute for professional medical advice.

---

## Now installable as a mobile app (PWA)

The frontend is now a Progressive Web App — installable on a phone's home
screen with a real app icon, running full-screen with no browser address bar,
and able to open instantly (cached app shell) even with a weak connection.
This reuses the exact same codebase rather than a separate mobile rewrite, so
there's nothing new to maintain.

**To install on a phone**, deploy the frontend (see the deployment guide
below) and open it in a mobile browser:
- **Android (Chrome)**: tap the menu (⋮) → "Install app" or "Add to Home screen"
- **iPhone (Safari)**: tap Share → "Add to Home Screen" (iOS requires Safari
  specifically — installation from Chrome on iOS won't offer this option, a
  restriction Apple applies to all browsers, not something this app can work
  around)

Once installed, it opens like any other app — no browser chrome, its own icon,
own entry in the app switcher.

**What's cached vs. not**: the app shell (HTML/CSS/JS, fonts, icons) is cached
so the interface itself loads instantly and works offline. Report data, chat
answers, and AI explanations are deliberately **never cached** — every request
for medical content always goes to the live backend, since serving stale
medical data from a cache would be a real safety issue.

**If you want an actual app-store binary** (Google Play / Apple App Store)
instead of a home-screen PWA, real native Android and iOS projects are
already generated and ready to build — see the next section.

## Native Android & iOS projects (via Capacitor)

`frontend/android/` and `frontend/ios/` are complete, real native projects
(not stubs) wrapping the exact same web app — same React code, same backend
calls, nothing duplicated or rewritten. Brand icons and splash screens are
already generated for every required density on both platforms.

**Before building, change the app ID.** `frontend/capacitor.config.ts` uses
`com.medreportai.app` as a placeholder — change this to your own reverse-domain
ID before any real store submission (Google Play and the App Store both treat
this as a permanent, unchangeable identifier once published).

### Android — requires [Android Studio](https://developer.android.com/studio) (Windows/Mac/Linux)

```bash
cd frontend
npm run build          # rebuild the web app after any code change
npx cap sync android    # copy the new build into the native project
npx cap open android    # opens the project in Android Studio
```
From Android Studio: Run ▶ to test on an emulator/device, or Build → Generate
Signed Bundle/APK to produce a Play Store-ready `.aab` file.

### iOS — requires a Mac with [Xcode](https://developer.apple.com/xcode/)

There is no way around this — Apple requires Xcode specifically to build iOS
apps, and Xcode only runs on macOS. This isn't a limitation of this project;
it's true for every iOS app from every developer.

```bash
cd frontend
npm run build
npx cap sync ios
npx cap open ios        # opens the project in Xcode
```
From Xcode: ▶ to test on a simulator/device, or Product → Archive to produce
an App Store-ready build (requires an active Apple Developer account, $99/yr,
to actually publish — free to build and test on your own device without one).

### After any code change

Both platforms load the built `dist/` folder, so the workflow is always:
`npm run build` → `npx cap sync` → reopen/rebuild in Android Studio or Xcode.
`npx cap sync` handles both platforms at once if you drop the platform name.

## What's new in this latest, latest version

- **Fixed placeholder-key bug**: copying `.env.example` to `.env` and only filling
  in some providers caused the OTHER providers' literal placeholder text (e.g.
  `your_groq_key_here`) to be treated as a real key and attempted, producing
  confusing 401 errors for providers you never configured. Now filtered out —
  only providers with a real key are ever tried.
- **Fixed Cerebras and Sarvam default models** — both had been silently
  deprecated (`llama-3.3-70b` on Cerebras, Feb 2026; `sarvam-30b`, Aug 2026).
  Updated to `gpt-oss-120b` and `sarvam-105b` respectively.
- **Rewrote the Report Overview prompts** per clarified intent: short summary
  stays a brief overview; detailed explanation now explicitly covers every
  significant finding in patient-friendly language (not just top-level
  highlights); final verdict is now framed as a doctor speaking directly to
  the patient — what the report shows AND what to do next. Same length
  targets as before (3-5 / 6-8 / 4-5 sentences).
- **LOINC dataset now imported from the real, official LOINC release** — 533
  tests across 27 categories, up from the 184 hand-curated ones. Every code
  comes directly from the authoritative source file (loinc.org, free
  registration), filtered to genuinely common tests (LOINC's own
  `COMMON_TEST_RANK` field, rank 1-1000) with real, LOINC-provided synonyms —
  zero risk of the fabrication issue described above, since nothing here was
  recalled from memory. See `backend/scripts/import_official_loinc.py` if you
  want to re-run this yourself against a newer LOINC release, or adjust
  `MAX_RANK` / `CLASS_TO_CATEGORY` to include more test categories.

## What's new in this latest version

- **Fixed the "AI unavailable" bug that showed even when the API call succeeded.**
  Prompts used to require strict JSON, and free models (especially Llama-family
  ones on Groq) often wrap valid content in extra text or slightly invalid JSON —
  the parser would then silently discard a successful response and fall back to
  the basic template. Explanations now use a forgiving marker-based format
  (`###FIELD_NAME###`) that tolerates messy output and missing sections.
- **Flowing prose, not bullet points.** Report Overview sections are now written
  as natural paragraphs with explicit length targets: short summary 3-5
  sentences, detailed explanation 6-8 sentences as one continuous narrative,
  final verdict 4-5 sentences — no bullet lists anywhere.
- **Stronger, explicit Telugu instructions** demanding everyday spoken register
  (like a WhatsApp voice message) and explicitly rejecting bookish/literary/
  government-document Telugu.
- **Telugu requests route to Gemini first, English to Groq first** — two
  separate provider orders (`LLM_PROVIDER_ORDER_EN` / `_TE`), since Google
  produces noticeably more natural Telugu than the Llama models on Groq/Cerebras.
- **Flashcards are no longer LLM-generated at all** — built directly from
  extracted test data + a hand-authored glossary, instant and always available.

## What's new in this version

- **Report Overview page** — one page, in order: report title, abstract, a
  doctor-style narrative (told as one medical story, not a per-test list),
  a final verdict, Key Findings grouped as Verified Abnormal → Verified Normal →
  Unverified (computed directly from extracted data, no AI involved), then all
  recommendation categories stacked in one place.
- **Individual Test Analysis** is now its own page, separate from the overview,
  with verified parameters listed before unverified ones.
- **Multi-provider LLM chain** — Groq, Sarvam, Mistral, Gemini,
  tried in order with automatic failover.
- **Two independent language settings:**
  - *Explanation Language* (English/Telugu) — the LLM writes AI content (overview,
    test explanations, chat) **directly in natural, everyday Telugu**,
    not machine-translated word-for-word. Medical test names stay in English/Roman
    script, as they're actually said in practice.
  - *Interface Language* (English/తెలుగు) — the app's menus, buttons, and labels,
    translated via a **pre-built static dictionary** (`frontend/src/i18n/`), so
    switching is instant with zero runtime API or LLM calls.
- **Flashcards** support bookmarking (persisted per report in the backend) and
  cover abnormal findings, vocabulary, and reference ranges as their own cards.

## Why it's trustworthy, not just "AI-sounding"

| Control | What it does |
|---|---|
| **No OCR** | Only digital PDFs are accepted. Scanned/handwritten reports are rejected outright rather than mis-read. |
| **Local LOINC verification** | Every extracted test name is checked against a local LOINC subset. Unverified names are shown but flagged, never silently "corrected" by the LLM. |
| **Facts vs. AI, always separated** | The database and the UI keep extracted values (`LabParameter`) and AI text (`ParameterExplanation`, `ReportSummary`) in distinct tables/badges — "From your report" vs "AI explanation". |
| **Grounded RAG chat** | Chat answers are generated only from retrieved chunks of *that* report. A similarity-score gate skips the LLM call entirely (returning *"I couldn't find that information in this report."*) when nothing relevant was retrieved. |
| **Unknown over guessed** | Any field that can't be confidently extracted is stored and shown as "Unknown" — never inferred. |

---

## Architecture

```
medreport-ai/
├── backend/                  FastAPI application
│   ├── app/                  config, db, models, schemas, routes, LLM client
│   ├── extraction/           PDF text extraction, regex+spaCy parsing, LOINC validator
│   ├── rag/                  chunking, FAISS vector store, grounded chat engine
│   ├── explanation/          adaptive (patient/student/doctor) explanation engine
│   ├── translation/          free EN→TE translation (deep-translator)
│   ├── data/loinc_subset.csv local LOINC reference (extend freely)
│   └── requirements.txt
└── frontend/                 React + TypeScript + Vite + Tailwind + Shadcn-style UI
    └── src/
        ├── pages/            Home, Upload, Report Summary, Chat, Flashcards, Settings
        ├── components/       AppShell, ParameterCard ("ledger card"), ModeSwitcher, ui/
        ├── lib/               typed API client, shared types
        └── hooks/            global mode/language/theme state
```

**Data flow:** PDF upload → `pdfplumber`/PyMuPDF text extraction → regex + spaCy
structured parsing → LOINC verification → SQLite storage of extracted facts →
FAISS index built from report text → on demand, the LLM generates mode-specific
explanations/summaries/flashcards *grounded in the stored facts*, cached in the DB,
and translated to Telugu if requested.

---

## Tech stack (all free / open-source)

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **PDF extraction:** pdfplumber, PyMuPDF (no OCR, no paid vision APIs)
- **NLP:** spaCy + regex rule-based parsing
- **Verification:** local LOINC subset (CSV, extendable)
- **RAG:** sentence-transformers (`all-MiniLM-L6-v2`) + FAISS
- **Translation:** deep-translator (Google Translate backend, no API key)
- **LLM:** any OpenAI-compatible endpoint — defaults to Groq's free tier as primary
  and an OpenRouter free model as fallback; also works with a local Ollama server
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Shadcn-style primitives, Framer Motion

---

## Local setup

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

cp .env.example .env
# edit .env: fill in at least 2-3 provider keys (see "LLM setup" section below)
# for automatic failover — a single provider is a single point of failure

uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (proxies `/api` to the backend automatically in dev)

---

## LLM setup — multi-provider failover (important)

This app tries multiple LLM providers **in order** for every AI request,
automatically moving to the next one if a provider is rate-limited or down.
You don't need all of them — fill in at least 2-3 keys so a single provider's
limits never block the app. There are two separate orders: English requests
use `LLM_PROVIDER_ORDER_EN`, Telugu requests use `LLM_PROVIDER_ORDER_TE` —
see below for why they differ.

| English order | Telugu order | Provider | Free tier | Get a key |
|---|---|---|---|---|
| 1 | 3 | **Groq** (recommended EN primary) | 30 req/min, 1,000 req/day, no credit card | https://console.groq.com/keys |
| 3 | 5 | **Mistral** | 1B tokens/month | https://console.mistral.ai |
| — | 1 | **Sarvam AI** (Telugu only — see below) | ₹100-1,000 signup credits (fixed pool, not a resetting tier) | https://dashboard.sarvam.ai |
| 5 | 2 | **Gemini** | Currently unreliable — see note below | https://aistudio.google.com/apikey |
| 6 | 7 | **OpenAI** (optional, off by default) | Trial credit only, then paid | https://platform.openai.com/api-keys |

**Sarvam is deliberately excluded from the English order** — it's Telugu-only
in this app, both to conserve its fixed credit pool (see note above) for the
language it actually specializes in, and because Groq/Cerebras/Mistral are
all better English options anyway.

**Why Sarvam is first for Telugu:** it's an Indian company (Bengaluru) building
models specifically for 22 Indian languages — including Telugu — rather than
as a side feature of a general-purpose model. In practice this produces
noticeably more natural, everyday spoken Telugu than Llama-family models
(Groq/Cerebras) or Gemini. The tradeoff: unlike the other providers' true
daily/monthly-resetting free tiers, Sarvam's free access is a **fixed signup
credit pool** — generous, but it eventually runs out and requires payment,
closer to a trial than a permanent free tier.

**Why Gemini is demoted, not removed:** Google significantly cut Gemini API
free-tier rate limits in late 2025, and there's a widely-reported bug where
newly created API keys show "Free tier" in AI Studio but every request returns
`429 RESOURCE_EXHAUSTED, limit: 0` regardless of what the console displays —
real-world testing on this project saw daily limits as low as 20 requests/day.
This affects both genuinely free accounts and, in some cases, paid accounts
where Cloud Billing isn't correctly linked to the project hosting the key. If
you want to rely on Gemini more, verify billing is linked at
console.cloud.google.com (not just AI Studio) and regenerate your key after
linking it.

**Why OpenAI is optional and inactive by default:** its "free tier" is really
a one-time trial credit ($5-18, historically) that expires, after which it
requires a payment method and per-token billing — this doesn't fit the
free-tier-first approach used everywhere else in this app. It's included only
as an opt-in extra (commented out in `.env.example`) if you want to add paid
capacity on top of the free chain later.

**If you're demoing this product live:** pre-generate explanations for your
demo reports beforehand by opening every parameter card, both languages, and
all three modes ahead of time — the app caches every successful AI response
permanently, so nothing calls the API live during the actual demo, avoiding
any risk of hitting Sarvam's credit pool or Gemini's daily cap mid-presentation.

Change either order or drop providers entirely via `LLM_PROVIDER_ORDER_EN` /
`_TE` in `.env` — no code changes needed. To run fully offline/free with a
local model instead, install [Ollama](https://ollama.com), pull a model
(`ollama pull llama3.1`), and point any provider slot's `_BASE_URL` at
`http://localhost:11434/v1`.

### If every provider fails: offline template fallback

If all configured providers are unavailable at once (rare, but possible), the
app does not show a raw error in place of an answer. Instead:

- **Report Overview & test explanations** fall back to deterministic templates
  built entirely from the extracted facts (test name, value, status, reference
  range) — no network call, always available, in both English and Telugu.
- **Chat** falls back to showing the raw, most-relevant excerpt from the report
  directly, rather than an AI-synthesized answer it can't safely produce.
- Every fallback response is honestly labeled in the UI ("Basic explanation ·
  AI unavailable") rather than presented as if it were real AI output — see
  the `source_of_truth` field (`ai_generated` vs `template_fallback`) on API
  responses.
- Fallback content is **not cached** — the next request retries the real LLM
  chain fresh, so a temporary outage never permanently traps a report on the
  basic template version.

## Extending the LOINC reference

`backend/data/loinc_subset.csv` ships with **533 tests across 27 categories, every one individually confirmed against the real LOINC table**:
CBC, Chemistry, LFT, KFT, Lipid, Thyroid, Diabetes, Urine, Cardiac markers,
Coagulation, Inflammatory markers, Iron studies, Vitamins, Hormones, Tumor
markers, ABG, Vitals, Toxicology, Infectious, and more.

**Provenance, so this stays trustworthy:** 184 of these entries were manually
curated and cross-checked in early development. The remaining 349 were
imported directly from the official LOINC release (`LoincTable/Loinc.csv`,
version 2.82) using `backend/scripts/import_official_loinc.py`, filtered to
LOINC's own `COMMON_TEST_RANK` field (rank 1-1000, i.e. genuinely common to
moderately specialized tests — validated against known cases like
Hemoglobin=17, Creatinine=4, Glucose=6) with real synonyms pulled from
LOINC's `RELATEDNAMES2` field, and deduplicated by test name so that where
LOINC has multiple codes for the same test (different specimen types or
methods — e.g. Hemoglobin has 6+ codes for blood, urine, and other specimen
types), only the single best-ranked variant is kept. An earlier version of
this script didn't dedupe by name, which pulled
in 435 total entries with 53 redundant near-duplicates; matching against report
text would have been fragile in that state, since which duplicate "won" depended
on arbitrary file order rather than actual clinical commonness.

**A previous expansion attempt** (documented in earlier project history)
pushed this file to ~270 entries by asking an LLM to recall additional codes,
and an audit found roughly 55 of those were fabricated — codes generated by
incrementing a digit off a real nearby code rather than looked up. Those were
all removed. That incident is the reason this file is now grown exclusively
via the official source rather than AI recall — see the case study in the
project's research paper (if generated) for the full account.

**To grow this further** (e.g. a newer LOINC release, or additional test
categories): download the current release from https://loinc.org (free
registration) and either run `python scripts/import_official_loinc.py
/path/to/Loinc.csv` yourself, or share the file for it to be run directly.
Adjust `MAX_RANK` (currently 400) or add entries to `CLASS_TO_CATEGORY` in
that script to include more/fewer tests — never hand-edit in codes from
memory.

## Extending the interface translation

`frontend/src/i18n/en.json` is the source of truth for all UI text; `te.json`
mirrors its keys with hand-authored, natural (not literary) Telugu. If you add
a new UI string, add it to `en.json` first, then either translate it by hand in
`te.json` or run the optional draft-translation helper (needs internet + the
`deep-translator` package already in `requirements.txt`):

```bash
cd backend
python scripts/generate_ui_translations.py
```

This only fills in missing keys — it won't overwrite existing translations —
and always review machine-drafted Telugu by hand before shipping, since it
tends to read more formal than the everyday register used elsewhere.

---

## Free-tier deployment guide (zero cost, no card required anywhere)

This whole path — hosting, database, everything — stays free. No trial
periods that expire, no "free for 30 days" traps.

**Step 1 — Free persistent database (skip this only if you're fine with data
resetting between demos):** Create a free account at
[neon.tech](https://neon.tech) or [supabase.com](https://supabase.com) (both
genuinely free forever, no card), create a project, and copy the Postgres
connection string they give you. You'll paste this into Render's dashboard in
step 2. Without this step, uploaded reports and chat history disappear every
time the free backend host restarts or wakes from sleep — fine for a quick
demo, not great if your expo runs for hours with gaps between visitors.

**Step 2 — Backend → Render.com free web service**
1. Push this repo to GitHub.
2. In Render: New → Blueprint → point at your repo. It'll read `render.yaml`
   at the repo root automatically and set up the build/start commands for you
   — no manual configuration needed.
3. Once created, go to the service's Environment tab and fill in the actual
   values: your LLM provider API keys (Groq, Sarvam, etc. — see the LLM setup
   section above), `DATABASE_URL` (the Neon/Supabase string from step 1, if
   you're using one), and `CORS_ORIGINS` (fill this in after step 3, once you
   know your frontend's URL).
4. Deploy. Note the backend's URL, e.g. `https://medreport-ai-backend.onrender.com`.

**Step 3 — Frontend → Vercel free tier**
1. In Vercel: New Project → point at the same repo, set root directory to
   `frontend`. It'll pick up `vercel.json` automatically.
2. Add environment variable `VITE_API_BASE_URL` = your Render backend URL +
   `/api`, e.g. `https://medreport-ai-backend.onrender.com/api`. Required
   because frontend and backend are on different domains — without this,
   every request silently goes to Vercel's own domain instead of your
   backend and fails.
3. Deploy. Note the frontend's URL, e.g. `https://your-app.vercel.app`.

**Step 4 — close the loop:** go back to Render, set `CORS_ORIGINS` to
`["https://your-app.vercel.app"]` (your actual Vercel URL from step 3), and
redeploy the backend. Skipping this means the browser blocks every request
with a CORS error even though the backend itself is working fine.

## Recommended path: single Hugging Face Space (one container, one URL)

Given this backend's memory needs (spaCy + sentence-transformers) and the
reliability requirements of a live demo, this is the recommended path over
the Render+Vercel split above — more free RAM (16GB vs Render's ~512MB),
longer idle-sleep window (48 hours vs Render's 15 minutes), and no CORS
configuration needed since everything shares one domain. The `Dockerfile` at
the repo root and `app/main.py`'s static-file serving logic are already set
up for this — verified working (tested the actual static-serving/SPA-fallback
routing with live HTTP requests, not just written and assumed correct).

**Setup:**
1. Create a free account at [huggingface.co](https://huggingface.co), then
   New Space → SDK: **Docker** → any name/visibility.
2. **Rename `README_HF_SPACE.md` to `README.md`** when you push to the
   Space's repo — Hugging Face requires its config frontmatter (the `---
   sdk: docker ... ---` block) to live in a file with that exact name at the
   repo root. This project's main `README.md` (this file) is the detailed
   project documentation and would conflict if both are pushed with the same
   name — the Space's git repo is separate from your GitHub repo, so this
   only matters for what you push *there*, not your main repo.
3. In the Space's **Settings → Repository secrets** (not "Variables" — secrets
   stay hidden from logs and public view): add `GROQ_API_KEY`, `SARVAM_API_KEY`,
   and any other provider keys you're using.
4. Optional, for data to survive restarts: add `DATABASE_URL` as a secret too,
   pointing at a free Neon/Supabase Postgres instance. Without it, the Space's
   local SQLite resets whenever it sleeps or rebuilds — same tradeoff as
   every free host, not specific to Hugging Face.
5. Push this repo to the Space's git remote. It builds automatically from the
   `Dockerfile` — first build takes a few minutes (installing spaCy/PyTorch),
   subsequent ones are faster via layer caching.

**Alternative — two separate free services (Render + Vercel):** more
configurable, but needs manual CORS setup and has the RAM/sleep-window
tradeoffs above. Steps below if you'd rather go this route.

### For the expo specifically

- **Render's free tier sleeps after 15 minutes of no traffic**, and takes
  ~30-60 seconds to wake back up on the next request. If there might be gaps
  between visitors at your booth, open the app yourself every so often to
  keep it warm, or plan for that first-load delay (e.g. start your intro
  talk while it wakes up).
- **Pre-warm your demo reports** (upload them and open every parameter card,
  in every mode/language you'll show, before the event starts) — the app
  caches every successful AI response permanently, so your main walkthrough
  loads instantly with zero dependence on live API calls, even if a provider
  is having a bad moment. Live chat for spontaneous questions still works
  normally on top of that.
- **Put your Vercel URL in a QR code** and let people install the app on
  their own phones (Android: Chrome menu → "Install app"; iPhone: Safari
  specifically → Share → "Add to Home Screen") — since this is a full PWA,
  that's a genuinely good live demo moment, not just a link to a webpage.

**PWA note:** the service worker only activates over HTTPS or localhost —
Vercel, Render, and Hugging Face Spaces all serve HTTPS by default, so
nothing extra to configure there.

---

## Important product boundaries (by design, not limitations to "fix")

- No login, subscriptions, or payments — this is a lightweight, single-purpose tool.
- No OCR / scanned image support — digital PDFs only, to protect extraction accuracy.
- The AI never states a diagnosis; explanations are interpretive/educational and
  always point to a doctor for concerning results.
