# Provenance Guard

A backend system for AI content attribution on creative writing platforms. Provenance Guard classifies submitted text as likely human-written, likely AI-generated, or uncertain — and surfaces a transparency label to readers. Creators can appeal misclassifications, and every decision is captured in a structured audit log.

---

## Architecture Overview

A submitted piece of text passes through three independent detection signals — one semantic (LLM), one structural (stylometric math), one linguistic (informality markers). Their scores are combined into a single confidence score (0.0 = human, 1.0 = AI). That score maps to a transparency label shown to readers. Every decision is written to a SQLite audit log. If a creator disputes the classification, they submit an appeal with their reasoning — the system updates the status to "under review" and logs the appeal without automatic re-classification.

```
POST /submit
  { text, creator_id }
        │
        ▼
  ┌─────────────────────────────────────┐
  │         Detection Pipeline          │
  │                                     │
  │  Signal 1: LLM Judgment (Groq)      │
  │  Signal 2: Stylometric Analysis     │
  │  Signal 3: Informality Scoring      │
  └─────────────────────────────────────┘
        │
        ▼
  Confidence Scoring (weighted average)
        │
        ▼
  Transparency Label Generation
        │
        ▼
  Audit Log (SQLite)
        │
        ▼
  Response { content_id, attribution, confidence, label, signals }
```

---

## Detection Signals

### Signal 1: LLM Judgment (Weight: 55%)
**What it measures:** Semantic coherence, stylistic uniformity, and overall writing pattern. Groq (llama-3.3-70b-versatile) assesses holistically whether the text reads as human or AI-generated — capturing unnatural smoothness, lack of personal voice, and overly balanced sentence structure.

**Why chosen:** Most holistic signal — captures properties that math cannot measure, like voice and authenticity.

**What it misses:** Formal human writing (academic papers) may score high. Deliberately casual AI output may score low.

---

### Signal 2: Stylometric Analysis (Weight: 35%)
**What it measures:** Statistical properties of writing:
- **Sentence length variance** — humans vary dramatically; AI is uniform
- **Type-token ratio (TTR)** — vocabulary diversity; AI reuses words more predictably

**Why chosen:** Purely mathematical, completely independent of the LLM. Structural patterns are hard to fake consistently.

**What it misses:** Short texts (under 3 sentences) produce unreliable variance scores. Academic human writing has naturally low variance.

---

### Signal 3: Informality Score (Weight: 10%)
**What it measures:** Presence of casual human language markers AI almost never produces naturally:
- Informal shorthand: `ok`, `gonna`, `lol`, `gn8`, `btw`, `tbh`
- Casual punctuation: `...`, `!!`, `??`
- Informal sentence starters: `And`, `But`, `So`

**Why chosen:** Strong signal when present — AI almost never uses genuine informal shorthand.

**What it misses:** Formal human writers score as AI-like. Weight kept low (10%) for this reason.

### What we'd change for real deployment

**Detection & Scoring:**
- Fine-tune a dedicated classifier model on labeled human/AI writing pairs instead of a general-purpose LLM — more consistent and cheaper at scale
- Train a logistic regression model on signal scores using labeled data instead of hand-tuned weights
- A/B test the 0.75 threshold against real appeal rates — adjust based on data

**Infrastructure & Scale:**
- Replace Flask dev server with **Gunicorn + Nginx** to handle concurrent requests under real load
- Replace SQLite with **PostgreSQL** — SQLite doesn't handle concurrent writes at scale
- Add a **Redis** cache for rate limiting instead of in-memory storage — in-memory resets on every server restart
- Deploy on **AWS/GCP** with auto-scaling — a single server can't handle traffic spikes
- Add a **message queue (Celery + Redis)** for signal processing — LLM calls are slow, don't block the HTTP response
- Add **authentication** — currently any request can submit or view logs

**Frontend:**
- Build a creator dashboard showing submission history, confidence scores, and appeal status
- Show the transparency label inline on content pages — not just in the API response
- Add a human reviewer interface for processing appeals queue

**Monitoring:**
- Add **Datadog/Grafana** for real-time monitoring of classification distribution and appeal rates
- Alert when appeal rate spikes — signals the classifier may be drifting
- Log model latency per signal to catch when Groq API slows down

---

## Confidence Scoring

### Formula
```
confidence = (0.55 × llm_score) + (0.35 × stylometric_score) + (0.10 × informality_score)
```

### Thresholds
We bias toward protecting human writers — a false positive (calling human work AI) is worse than a false negative.

| Confidence | Attribution | Meaning |
|-----------|-------------|---------|
| 0.0 – 0.35 | likely_human | Strong human patterns |
| 0.36 – 0.74 | uncertain | Signals disagree or insufficient data |
| 0.75 – 1.0 | likely_ai | Strong AI patterns |

### Example Submissions — all three tiers covered

| Text | Confidence | Attribution |
|------|-----------|-------------|
| Casual ramen review (human) | 0.176 | ✅ likely_human |
| Remote work (lightly edited AI) | 0.312 | ✅ likely_human |
| AI paradigm shift (short) | 0.687 | ❓ uncertain |
| AI healthcare paragraph (long) | 0.776 | ⚠️ likely_ai |

**High-confidence human (casual ramen review):**
```json
{
  "text": "ok so i finally tried that new ramen place downtown and honestly? underwhelming...",
  "confidence": 0.176,
  "attribution": "likely_human",
  "label": "✅ Human Written"
}
```

**High-confidence AI (long healthcare paragraph):**
```json
{
  "text": "The implementation of artificial intelligence in healthcare represents a paradigm shift...",
  "confidence": 0.776,
  "attribution": "likely_ai",
  "label": "⚠️ AI Generated"
}
```
Note: Longer text gave Signal 2 (stylometric) enough sentences to detect uniform structure. Short AI text scores uncertain — long AI text crosses the threshold.

**Uncertain (formal human writing — monetary policy):**
```json
{
  "text": "The relationship between monetary policy and asset price inflation...",
  "confidence": 0.688,
  "attribution": "uncertain",
  "label": "❓ Uncertain"
}
```
Note: Formal human writing scores uncertain — the higher threshold (0.75) prevents a false positive here.

---

## Transparency Labels

Three label variants shown to readers:

### High-confidence AI (confidence ≥ 0.75)
```
⚠️ AI Generated
This content shows strong patterns of AI generation (confidence: X%).
This is automated analysis — the creator may appeal this classification.
```

### Uncertain (confidence 0.36 – 0.74)
```
❓ Uncertain
Our system could not confidently determine authorship (confidence: X%).
The creator may appeal this classification.
```

### High-confidence Human (confidence ≤ 0.35)
```
✅ Human Written
This content shows strong patterns of human authorship (confidence: X% human).
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/submit` | Submit text for attribution analysis |
| POST | `/appeal` | Contest a classification |
| POST | `/verify` | Apply for verified human creator badge |
| GET | `/log` | View recent audit log entries |
| GET | `/status/<content_id>` | Check status of a specific submission |
| GET | `/analytics` | View detection statistics |

### Rate Limiting
`/submit` is limited to **10 requests per minute** and **100 requests per day** per IP address.

**Reasoning:** A legitimate writer submitting their own work would rarely need more than a few submissions per minute. 10/minute allows normal usage while preventing automated flooding. 100/day caps abuse across a full day without blocking any realistic single-user workflow.

**Rate limit test evidence** — sending 12 rapid requests:
```
200  ← success
200  ← success
200  ← success
...
429 Too Many Requests - 10 per 1 minute  ← rate limit hit
429 Too Many Requests - 10 per 1 minute  ← rate limit hit
```
Requests 1–10 succeed, requests 11+ return 429.

---

## Audit Log Sample

Three structured entries from `GET /log` — showing a human submission, an uncertain submission, and one with an appeal filed:

```json
{
  "content_id": "d9831cf4-6c53-4d0c-9e0e-875545d8bf10",
  "creator_id": "test-user-1",
  "timestamp": "2026-06-27T20:01:03.674989",
  "attribution": "likely_human",
  "confidence": 0.176,
  "llm_score": 0.1,
  "stylometric_score": 0.112,
  "informality_score": 0.818,
  "status": "classified",
  "appeal_reasoning": null
}

{
  "content_id": "6846118d-4ce6-4f61-a1a9-822523e1bcc4",
  "creator_id": "test-user-2",
  "timestamp": "2026-06-27T20:01:25.874385",
  "attribution": "uncertain",
  "confidence": 0.687,
  "llm_score": 0.9,
  "stylometric_score": 0.263,
  "informality_score": 1.0,
  "status": "classified",
  "appeal_reasoning": null
}

{
  "content_id": "7635470c-d142-458e-8a02-f3ab18740d35",
  "creator_id": "test-user-2",
  "timestamp": "2026-06-27T19:46:04.622484",
  "attribution": "uncertain",
  "confidence": 0.687,
  "llm_score": 0.9,
  "stylometric_score": 0.263,
  "informality_score": 1.0,
  "status": "under_review",
  "appeal_reasoning": "I wrote this myself for a university essay. I am a non-native English speaker and tend to write formally."
}
```

---

## Appeals Workflow

1. Creator submits `POST /appeal` with their `content_id` and written reasoning
2. System updates submission status from `"classified"` to `"under_review"`
3. Appeal reasoning is logged alongside the original classification in the audit log
4. Creator receives confirmation response
5. A human reviewer can view all details via `GET /log` or `GET /status/<content_id>`

No automated re-classification — human reviewers make the final call.

---

## Stretch Features

### Ensemble Detection
Three independent signals with documented weights (55/35/10). Each captures a genuinely different property — semantic, structural, linguistic.

### Provenance Certificate
Creators submit `POST /verify` with a written statement of authorship. Verified creators receive a `✅ Verified Human Creator` badge on all future submissions. Stored in a separate `verified_creators` table in SQLite.

### Analytics Dashboard
`GET /analytics` returns total submissions, attribution distribution, appeal rate, and average confidence score.

### Multi-modal Support
`/submit` accepts an optional `content_type` field (`"text"` or `"image_description"`). Image descriptions are shorter and more structured — the same pipeline applies with content type awareness.

**How the pipeline handles image descriptions:** All three signals run on the text of the description. Short captions naturally have low sentence variance — Signal 2 (stylometric) is less reliable for very short descriptions, so the system defaults to uncertain more often. Signal 1 (LLM) carries more weight for short content.

**Demo — image description submission:**
```json
{
  "text": "Oil on canvas, 24x36 inches. A lighthouse stands at dusk against a dramatic sky...",
  "content_type": "image_description",
  "confidence": 0.7,
  "attribution": "uncertain",
  "label": "❓ Uncertain"
}
```

---

## Known Limitations

### Formal human writing
A professor submitting an academic essay will trigger high AI scores on all three signals — uniform sentence length, formal vocabulary, no informal markers. Our higher threshold (0.75) reduces false positives but does not eliminate them.

### Non-native English speakers
Non-native speakers often write in patterns that resemble AI — consistent grammar, limited vocabulary range, formal phrasing. The appeals workflow is the primary mitigation.

---

## Spec Reflection

**One way the spec helped:** Defining thresholds in `planning.md` before coding directly shaped the 0.75 AI threshold decision — writing it down forced the reasoning about false positives being worse than false negatives.

**One way implementation diverged:** The stylometric signal performs poorly on short texts. The spec didn't anticipate this — discovered during testing when a formal AI paragraph scored `uncertain` instead of `likely_ai` because variance on 3 sentences is unreliable.

---

## AI Usage

**Instance 1:** Directed AI to generate the Flask app skeleton and SQLite database setup using our architecture diagram and API contract from `planning.md` as input. The output included a working `/submit` route and `init_db()` function. Revised: corrected `row_factory = sqlite3.Row` usage (AI used index-based row access), added `os.makedirs(exist_ok=True)` before the file write (AI placed it after, which would crash on first run), and added `try/except` blocks around all signal functions which AI omitted.

**Instance 2:** Directed AI to design the stylometric scoring formula — combining sentence length variance and type-token ratio into a single 0-1 score. AI suggested equal weighting (50/50) between the two metrics and equal signal weights (33/33/33) across all three signals. Overrode both: changed signal weights to 55/35/10 based on our reasoning that LLM is most holistic and informality is too narrow for formal writers. Also added a short-text fallback (`return 0.5` when fewer than 2 sentences) which AI omitted — discovered this gap during testing when single-sentence inputs caused a division by zero error.

---

## Video Walkthrough

Here's a walkthrough of implemented required features:

<img src='https://imgur.com/a/3rvOcQ4.gif' title='Video Walkthrough' width='' alt='Video Walkthrough' />

---

## Setup

```bash
git clone <your-repo-url>
cd ai201-project4-provenance-guard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# create .env and add GROQ_API_KEY=your_key_here
python app.py
```
