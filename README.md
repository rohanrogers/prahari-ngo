# PRAHARI-NGO

**The sentinel that watches for you.**

> India's first proactive NGO crisis coordination system — built for GDG Solution Challenge 2026 India.

---

## The Problem

**August 15, 2018. Kerala. The worst flooding in a century.** 483 people died. One million displaced. Hundreds of NGOs with thousands of volunteers tried to coordinate through WhatsApp groups, phone calls, and paper registers. They didn't have a data problem — they had twelve data problems, all at once.

Today, most NGO coordination tools require volunteers to sign up on a new platform. They wait for someone to report a crisis. And they assume data arrives clean and structured.

**None of that is reality.**

## The Solution

Prahari is a **four-agent AI system** that:

1. **INGESTOR** — Transforms chaotic NGO data (WhatsApp exports, PDFs, photos of handwritten registers, Excel sheets) into a unified, deduplicated, semantically-searchable Volunteer Graph. Multilingual. Multimodal.

2. **WATCHER** — Continuously monitors Indian public data streams (weather APIs, news RSS, Reddit) and uses multi-source correlation + Google Search grounding to detect emerging threats **before** they become confirmed crises.

3. **COORDINATOR** — When a threat crosses the confidence threshold, uses Gemini function calling to search the Volunteer Graph semantically, filter by geography/language/availability, rank by match quality, and generate ready-to-send WhatsApp messages in the volunteer's native language.

4. **DISPATCH OPTIMIZER** — Uses a 15-stage Reinforcement Learning curriculum (PPO) trained on real Kerala district geography to solve dynamic mission assignment under uncertainty — deciding which volunteers to send where, when to hold scarce specialists, and how to handle stochastic road closures, weather escalation, and volunteer fatigue.

### What Makes Prahari Different

| Feature | Dataminr | iVolunteer | Prahari |
|---|---|---|---|
| Ingests messy NGO data | No | No | Yes — WhatsApp, PDF, images, Excel |
| Proactive threat detection | Yes (enterprise) | No | Yes — Multi-source correlation |
| Indian language support | No | Limited | Yes — Malayalam, Hindi, Tamil, Telugu, Kannada |
| Works with existing NGO workflows | No | No | Yes — No new platform required |
| Pre-stages response before confirmation | No | No | Yes — Gemini function calling |
| RL-optimized dispatch | No | No | Yes — 15-stage PPO curriculum, +202% vs random |

> *"Unlike Dataminr which is a reactive enterprise dashboard, and iVolunteer which requires signup on their platform, Prahari is the only system that ingests the messy data NGOs already have, correlates public crisis signals proactively across Indian-language sources, and pre-stages multilingual response before the crisis is confirmed."*

## Kerala 2018 Replay Mode

The showpiece. Replay real public data streams from the morning of August 15th, 2018, and watch Prahari's agents detect the Alappuzha flooding **33 minutes before the first news article** and **2 hours before the first government advisory**.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          PRAHARI DASHBOARD                               │
│                   Next.js 16 + Firebase Hosting                          │
│       [Prahari] [Ingest] [Live] [Replay] [Dispatch]                      │
└───────────┬────────────────┬──────────────────┬──────────────────────────┘
            │ Upload         │ Real-time        │ Confirm
            ▼                │ Firestore        ▼
┌───────────────┐            │          ┌───────────────┐   ┌───────────────┐
│   INGESTOR    │            │          │  COORDINATOR  │◄──│   DISPATCH    │
│   Agent       │            │          │  Agent        │   │   OPTIMIZER   │
│               │            │          │               │   │               │
│ • WhatsApp    │            │          │ • Semantic    │   │ • 15-stage RL │
│ • PDF/Image   │            │          │   search      │   │ • PPO policy  │
│ • Excel/CSV   │◄───────────┤          │ • Geo filter  │   │ • Kerala geo  │
│ • Gemini      │            │          │ • Ranking     │   │ • Road/weather│
│   multimodal  │            │          │ • Outreach    │   │ • Fatigue     │
│ • Dedup +     │            │          │   (Malayalam, │   └───────────────┘
│   normalize   │            │          │    Hindi...)  │
└───────┬───────┘            │          └───────▲───────┘
        │                    │                  │
        ▼                    │          Pub/Sub │
  ┌──────────┐               │     threats-detected
  │ Firestore│               │                  │
  │ Volunteer│◄──────────────┤          ┌───────┴───────┐
  │ Graph    │               │          │   WATCHER     │
  └──────────┘               │          │   Agent       │
                             │          │               │
                             │          │ • Weather API │
                             │          │ • News RSS    │
                             │          │ • Reddit JSON │
                             │          │ • Gemini +    │
                             │          │   grounding   │
                             │          │ • Correlator  │
                             │          └───────────────┘
                             │            ▲ Cloud Scheduler
                             │            │ (every 5 min)
```

## Tech Stack

| Layer | Technology |
|---|---|
| AI Engine | Gemini 2.5 Flash (multimodal extraction), Gemini 2.5 Pro (function calling, reasoning) |
| Backend | Python 3.11 + FastAPI, deployed on Google Cloud Run |
| Frontend | Next.js 16, Tailwind CSS, shadcn/ui, Framer Motion |
| Database | Google Cloud Firestore (native mode, vector search) |
| Messaging | Google Cloud Pub/Sub |
| Hosting | Firebase Hosting (dashboard), Cloud Run (agents) |
| Maps | Google Maps JavaScript API |
| Scheduling | Google Cloud Scheduler |
| Storage | Google Cloud Storage |
| External Data | OpenWeatherMap API, RSS feeds, Reddit JSON |
| RL Training | Gymnasium 0.29, Stable-Baselines3 (PPO), TensorBoard |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Cloud SDK (`gcloud`)
- GCP project with billing enabled

### Local Development

```bash
# Clone
git clone https://github.com/rohanrogers/prahari-ngo.git
cd prahari-ngo

# Backend agents (each in separate terminal)
cd agents/ingestor && pip install -r requirements.txt && uvicorn main:app --port 8001
cd agents/watcher && pip install -r requirements.txt && uvicorn main:app --port 8002
cd agents/coordinator && pip install -r requirements.txt && uvicorn main:app --port 8003

# Frontend
cd dashboard && npm install && npm run dev
```

### Deploy to Google Cloud

```bash
chmod +x ./scripts/deploy_all.sh
./scripts/deploy_all.sh
```

### Environment Variables

Create a `.env` file in each agent directory and a `.env.local` in `dashboard/`.

| Variable | Default | Required By |
|---|---|---|
| `PROJECT_ID` | `prahari-ngo-rj` | All agents, shared clients |
| `REGION` | `asia-south1` | Gemini / Vertex AI client |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `prahari-ngo-rj` | Dashboard |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | — | Dashboard |

### API Endpoints

**Ingestor** (port 8001)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/ingest/upload` | Upload file for volunteer extraction |
| `POST` | `/ingest/test` | Synchronous demo extraction |

**Watcher** (port 8002)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/watch/cycle` | Trigger one watch cycle |

**Coordinator** (port 8003)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/coordinate` | Manual coordination trigger |
| `POST` | `/on-threat` | Pub/Sub push: threat detected |
| `POST` | `/on-crisis-confirmed` | Pub/Sub push: crisis confirmed |

## Project Structure

```
prahari-ngo/
├── agents/
│   ├── ingestor/          # Multimodal volunteer extraction
│   ├── watcher/           # Public data monitoring + correlation
│   └── coordinator/       # Volunteer matching + outreach
├── rl/                    # Reinforcement Learning dispatch optimizer
│   ├── envs/              # 15-stage Gymnasium environments
│   ├── train.py           # PPO curriculum training pipeline
│   └── evaluate.py        # Deterministic policy evaluation
├── shared/                # Shared Firestore, Gemini, Pub/Sub clients
├── dashboard/             # Next.js 16 frontend
├── replay-data/           # Kerala 2018 replay archive
├── scripts/               # Deployment + data generation
├── infra/                 # Cloud Build, Pub/Sub setup
└── docs/                  # Architecture diagrams, pitch deck
```

## RL Dispatch Optimizer

15-stage curriculum from basic volunteer dispatch to full Kerala flood simulation:

| Stages | Description |
|---|---|
| 1–3 | Foundation: static dispatch, Poisson arrivals, multi-skill matching |
| 4–9 | Advanced: Kerala geography, road closures, fatigue, communication delays |
| 10–15 | Kerala simulation: weather Markov chain, adversarial arrivals, real NGO skill distributions |

Stage 1 training results (50K timesteps):

| Metric | PPO Agent | Random Baseline | Improvement |
|---|---|---|---|
| Mean Reward | 9.66 | 3.20 | +202% |

## Demo

[Live MVP]()

[Demo Video]()

## Team

Built by Rohan Rogers — GDG Solution Challenge 2026 India.

## License

MIT — see [LICENSE](./LICENSE)
