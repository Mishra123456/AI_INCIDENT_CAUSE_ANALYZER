# 🛡️ Sentinel Ops Center — Incident Root Cause Analyzer for SRE Teams

> **During outages, every second counts.** Sentinel AI connects with your monitoring stack, analyzes logs and alerts in real-time, identifies probable root causes using AI, and suggests actionable fixes — instantly.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![Gemini](https://img.shields.io/badge/Google%20Gemini-AI%20Powered-yellow?logo=google)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **Real-Time Dashboard** | Live overview of system health, active incidents, MTTR, and service status across your infrastructure |
| **Incident Investigation** | Deep-dive into any incident with correlated alerts, structured logs, and event timeline |
| **AI Root Cause Analysis** | One-click AI-powered analysis that identifies root causes with confidence scores and evidence |
| **Suggested Fixes** | Actionable remediation steps with priority, risk assessment, and ready-to-run commands |
| **AI Chat Investigator** | Conversational interface to ask questions about any incident — Sentinel AI has full context |
| **Service Health Monitor** | Real-time health metrics for all microservices: latency, error rates, request volume, uptime |
| **Multi-Source Integration** | Designed for Datadog, Grafana, New Relic, Prometheus, CloudWatch, and custom sources |
| **Safety Guardrails** | Rate limiting, input sanitization, XSS prevention, and security headers out of the box |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (SPA)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │Dashboard │ │Incidents │ │Services  │ │AI Analysis   │   │
│  │  View    │ │  View    │ │  View    │ │Chat Interface│   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────────┐   │
│  │ API Routes │ │ Guardrails │ │ Security Middleware     │   │
│  └─────┬──────┘ └─────┬──────┘ └────────────────────────┘   │
│        │              │                                      │
│  ┌─────┴──────────────┴─────────────────────────────────┐   │
│  │              Service Layer                            │   │
│  │  ┌──────────────┐  ┌──────────────────────────────┐  │   │
│  │  │  Mock Data   │  │  AI Service (Google Gemini)  │  │   │
│  │  │  Generator   │  │  - Root Cause Analysis       │  │   │
│  │  │              │  │  - Chat Investigation        │  │   │
│  │  │              │  │  - Heuristic Fallback        │  │   │
│  │  └──────────────┘  └──────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Quick Start

### Prerequisites

- Python 3.11 or higher
- Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/sentinel-ai.git
cd sentinel-ai

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the application
python run.py
```

Open your browser to **http://localhost:8000** and you're live.

---

## 🔑 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (required for AI features) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode with hot reload |
| `RATE_LIMIT_REQUESTS` | `30` | Max requests per window per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window duration |

---

## 🔒 Safety & Security

Sentinel AI is built with production-grade guardrails:

- **Rate Limiting** — Per-IP sliding window rate limiter prevents abuse
- **Input Sanitization** — All user inputs are HTML-escaped and checked for injection patterns
- **Security Headers** — CSP, X-Frame-Options, XSS protection, and more
- **Schema Validation** — Every API request is validated through strict Pydantic models
- **Graceful Degradation** — AI features fall back to heuristic analysis when the API is unavailable
- **No Credentials in Code** — All secrets loaded from environment variables

---

## 📁 Project Structure

```
sentinel-ai/
├── backend/
│   ├── main.py              # FastAPI application factory
│   ├── config.py             # Environment configuration
│   ├── api/
│   │   └── routes.py         # REST API endpoints
│   ├── core/                 # Business logic (extensible)
│   ├── models/
│   │   └── schemas.py        # Pydantic data models
│   ├── services/
│   │   ├── ai_service.py     # Gemini AI integration
│   │   └── mock_data.py      # Realistic data generator
│   └── utils/
│       └── guardrails.py     # Rate limiting & sanitization
├── frontend/
│   ├── index.html            # SPA shell
│   └── static/
│       ├── css/styles.css    # Design system
│       └── js/app.js         # Frontend application
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── run.py                    # Entry point
└── README.md
```

---

## 🛠️ API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard` | Dashboard summary metrics |
| `GET` | `/api/v1/incidents` | List all incidents |
| `GET` | `/api/v1/incidents/{id}` | Get incident details |
| `GET` | `/api/v1/services/health` | Service health status |
| `GET` | `/api/v1/metrics/{service}/{metric}` | Time-series metrics |
| `POST` | `/api/v1/analyze` | Run AI root cause analysis |
| `POST` | `/api/v1/chat` | Chat with AI about an incident |

---

## 🧠 How the AI Analysis Works

1. **Context Assembly** — Sentinel aggregates all incident data: logs, alerts, metrics, timeline, and affected services into a structured context payload.

2. **Prompt Engineering** — A carefully crafted system prompt instructs Gemini to act as a senior SRE, analyze the data, and respond with structured JSON containing root causes, confidence scores, evidence, and suggested fixes.

3. **Structured Output** — The AI response is parsed into typed Pydantic models, ensuring consistent, reliable output for the frontend.

4. **Fallback Heuristics** — When the AI is unavailable, rule-based analysis takes over, examining log patterns, alert correlations, and deployment timelines.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for SRE teams who are tired of 3 AM war rooms.
</p>
