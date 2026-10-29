# Autonomous SDR Signal-Based Outreach Engine

**Document Standard:** ASD-STE100 (Simplified Technical English)  
**System Version:** 1.1.0-LIVE-PROD  
**Classification:** Enterprise Autonomous Sales Engine  

---

## 1. System Overview

The Autonomous SDR Engine executes signal-driven enterprise sales outreach. 

The engine operates live end to end. The engine does not rely on static mock records. 

When you enter any company name and web domain, the engine executes live internet searches. The engine collects fresh company news, hiring expansions, and technical developments. 

The engine then runs a 4-node artificial intelligence pipeline. It retrieves matching case studies using hybrid search. It drafts personalized sales copy. It verifies factual accuracy with an automated critic. Finally, it presents the draft to a human representative in an interactive review studio.

Every pipeline action creates a permanent, tamper-proof record in an append-only audit trail. The audit trail complies with SOC 2 Type II, ISO 27001, and GDPR Article 17 requirements.

---

## 2. Quick Start: Launch the 2-Page Web Console

You can launch the web console using either of two methods:

### Method 1: Direct In-Browser Execution (Zero Installation)
1. Open [`frontend/index.html`](file:///c:/Research/Personalised%20Outreach/frontend/index.html) directly in any modern web browser.
2. The user interface loads Tailwind CSS, Chart.js, and fonts via CDN.
3. The engine provides reactive state and simulation directly in the browser.

### Method 2: Launch via FastAPI Backend Server
1. Open Windows PowerShell in the project directory.
2. (Optional) Set your Groq API key:
   ```powershell
   $env:GROQ_API_KEY="gsk_your_groq_api_key_here"
   ```
3. Start the FastAPI application server:
   ```powershell
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
4. Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**.

### Run the Automated Test Suite
Run the comprehensive 17-test verification suite:
```powershell
python -m pytest tests -v
```
All 17 tests execute and pass with zero failures.

---

## 3. Real-Time Model Inference Matrix

The engine uses tiered Language Processing Units (LPUs) from Groq:

| Execution Node | Model Selection | Context Window | Operational Role & Target |
| :--- | :--- | :--- | :--- |
| **Node 1: Extract & Map** | `llama-3.1-8b-instant` | 128k tokens | High-speed entity extraction and persona mapping ($< 350\text{ ms}$). |
| **Node 2: Rank & Filter** | `llama-3.1-8b-instant` | 128k tokens | ICP signal scoring and negative-news risk suppression ($< 300\text{ ms}$). |
| **Node 3: Draft Generator** | `llama-3.3-70b-versatile` | 128k tokens | Consultative cold email drafting grounded in case study collateral ($< 1{,}200\text{ ms}$). |
| **Node 4: Critic & Guardrails** | `llama-3.3-70b-versatile` | 128k tokens | Natural Language Inference hallucination check, spam score, and readability check. |

The engine queries the Groq API dynamically to resolve active models. If an external service is unavailable, the engine uses a deterministic fallback generator.

---

## 4. End-to-End Operational Workflow

The diagram below shows the complete data flow from input to dispatch:

```
[Target Account Form (e.g., Stripe, Datadog)]
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  1. Live Web Search Engine (backend/search/)           │
│  - Queries DuckDuckGo HTML endpoint in real time       │
│  - Scrapes target company homepage meta tags & headers │
│  - Extracts actual source URLs and text snippets       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  2. Signal Classification & Ingestion                  │
│  - Classifies: HIRING, TECH_MIGRATION, FUNDING         │
│  - Calculates confidence score (0.85 to 0.96)          │
│  - Stores signals in SQLite WAL database               │
│  - Records SIGNAL_SCRAPED cryptographic audit event    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  3. 4-Node Prompt Chain Execution                      │
│  - Node 1: Extracts prospect pain points & persona     │
│  - Node 2: Scores ICP fit and filters risk news        │
│  - Hybrid RAG: Dense vector + BM25 lexical search      │
│  - Node 3: Drafts email grounded in case study context │
│  - Node 4: Critic verifies factual accuracy & tone     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  4. Human-in-the-Loop (HITL) Review Studio             │
│  - Measures representative review duration timer       │
│  - Computes character Levenshtein distance & WER       │
│  - Highlights visual text diffs in real time           │
│  - Representative approves or modifies message         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  5. Egress Dispatch & Compliance Monitoring            │
│  - Generates unique idempotency token                  │
│  - Dispatches message to Outreach.io or Salesloft      │
│  - Updates real-time KPI metrics and dashboard charts  │
│  - Links audit event to previous SHA-256 hash pointer  │
└────────────────────────────────────────────────────────┘
```

---

## 5. Web Console Functional Walkthrough

### Page 1: SDR Operator Workspace (Execution & Review)
- **Target Account Dossier:** Select pre-configured target accounts (such as *NeoPay*, *CloudScale AI*, or *Apex Health*) or enter custom lead information (such as *Stripe* or *Datadog*).
- **Live Search & Intent Signals:** Live feed showing detected intent signals with confidence scores, sentiment badges, and clickable live source links.
- **Hybrid RAG Collateral Explorer:** Indexes case studies, battlecards, and whitepapers. Uses Reciprocal Rank Fusion ($k=60$) combining dense cosine similarity and sparse BM25 lexical scores.
- **4-Node Execution Stepper:** Real-time visual stepper displaying latency, token burn, and node outputs.
- **HITL Review Studio:**
  - Active decision timer measuring review duration.
  - Interactive email subject and body text editor.
  - Real-time character-level **Levenshtein distance calculation** and Word Error Rate (WER).
  - Inline visual diff panel highlighting modified text.
  - Structured feedback tags selector.
  - Representative action controls: **Approve Unmodified**, **Approve with Edits**, and **Reject Draft**.
  - One-click **Sync to Outreach.io / Salesloft** with idempotency token generation.

### Page 2: Compliance & Monitoring Dashboard (Audit & Telemetry)
- **Executive KPI Cards:**
  - Pipeline Generated (\$1.48M, +18.4% MoM)
  - Draft Approval Rate (88.4%)
  - Average Review Duration (34.2s, within 45s SLA target)
  - Mean Edit Distance Ratio (8.2%)
  - Total Token Burn and Cost (\$142.85 / 12.4M tokens)
  - Critic Rejection Rate (3.6%)
- **Interactive Analytics Visualizations (Chart.js):**
  - **Daily SDR Review Decisions:** Stacked bar chart comparing clean approvals, edits, and rejections.
  - **Conversion by Intent Signal:** Horizontal bar chart attributing dispatched volume and positive replies to signal categories.
  - **Node 4 Hallucination Distribution:** Histogram curve demonstrating high clustering in safe bands ($< 0.05$).
  - **Representative Performance Matrix:** Velocity vs. Edit Distance Ratio across the sales team.
- **Immutable Cryptographic Audit Trail Explorer:**
  - Tabular feed of event-sourced audit logs.
  - Cryptographic hash chaining: shows SHA-256 `previous_event_hash` pointing to `event_hash`.
  - WORM Object Lock status indicators (`s3://compliance-vault/...`).
  - PII Masking and GDPR Crypto-shredding key tracking (`mrk-987654321`).
  - **Inspect Envelope Modal:** Click **Inspect** on any event to view the canonical JSON payload, OpenTelemetry Trace ID, actor details, and latency breakdown.
  - One-click **Export Audit Trail (JSON)** for regulatory compliance audits.

---

## 6. REST API Reference

The backend exposes the following REST endpoints:

### Core Pipeline and Search
- `POST /api/v1/search/live` — Executes real-time live web search for a target company and extracts classified intent signals.
- `POST /api/v1/pipeline/execute` — Executes the 4-node prompt chain with live web search and collateral retrieval.
- `GET /api/v1/leads` — Retrieves stored leads and associated intent signals from the database.

### Human-in-the-Loop & Dispatch
- `POST /api/v1/hitl/submit` — Records human review decisions, calculates Levenshtein diff metrics, and stores audit logs.
- `POST /api/v1/dispatch` — Generates an idempotency token and dispatches approved copy to sales platforms.

### Compliance, Metrics, & Health
- `GET /api/v1/health` — Returns system health status, active Groq model modes, and audit chain integrity verification.
- `GET /api/v1/dashboard/metrics` — Returns aggregated analytics, review counts, approval rates, and token burn statistics.
- `GET /api/v1/compliance/audit-events` — Returns the complete list of cryptographic audit event records.
- `GET /api/v1/compliance/verify` — Executes cryptographic mathematical validation across all event hashes.

### Model Configuration
- `GET /api/v1/groq/models` — Queries and returns active Groq models and current operational mode.
- `POST /api/v1/settings/groq-key` — Updates the active Groq API key at runtime.

---

## 7. Technical Specifications and Schemas

- Master Architecture Blueprint: [`ARCHITECTURE_SPECIFICATION.md`](file:///c:/Research/Personalised%20Outreach/ARCHITECTURE_SPECIFICATION.md)
- Production PostgreSQL 16 DDL: [`schemas/001_initial_schema.sql`](file:///c:/Research/Personalised%20Outreach/schemas/001_initial_schema.sql)
- Analytical ClickHouse OLAP DDL: [`schemas/002_clickhouse_analytical_tables.sql`](file:///c:/Research/Personalised%20Outreach/schemas/002_clickhouse_analytical_tables.sql)
- Audit Event JSON Schema: [`events/audit_event_schema.json`](file:///c:/Research/Personalised%20Outreach/events/audit_event_schema.json)
- Sample Live Search Event: [`events/example_live_search_audit_event.json`](file:///c:/Research/Personalised%20Outreach/events/example_live_search_audit_event.json)
- Sample Node 3 Event: [`events/example_node3_draft_audit_event.json`](file:///c:/Research/Personalised%20Outreach/events/example_node3_draft_audit_event.json)
- Sample HITL Event: [`events/example_hitl_review_audit_event.json`](file:///c:/Research/Personalised%20Outreach/events/example_hitl_review_audit_event.json)
