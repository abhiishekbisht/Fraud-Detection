# Product Requirements Document
## FraudLens — Automated Transaction Fraud Detection Platform

**Owner:** [Your Name] · **Type:** Portfolio / Resume Project · **Status:** v1 Draft

---

## 1. Overview

FraudLens is an end-to-end web platform where a user uploads raw transaction data (CSV) and the system automatically cleans it, runs exploratory data analysis, trains and compares fraud-detection models, and lets the user predict fraud risk on new transactions — either one at a time or in bulk — with explainable results.

**Why this project:** Most student fraud-detection projects stop at "trained a model in a notebook, 99% accuracy." That number is meaningless on imbalanced data. FraudLens is built to prove the opposite — that you understand *why* accuracy is the wrong metric here, how to handle severe class imbalance, and how to ship a model behind a real interface a non-technical person could use.

**One-line pitch (for your resume/README):**
"An end-to-end fraud detection platform — upload transactions, get automated EDA, train and compare ML models on imbalanced data (SMOTE), and get explainable real-time fraud predictions via a FastAPI backend and interactive dashboard."

---

## 2. Goals & Success Metrics

| Goal | Metric |
|---|---|
| Model correctly catches fraud | Recall ≥ 0.85 on fraud class (missing fraud is worse than a false alarm) |
| Model doesn't cry wolf too often | Precision ≥ 0.80 on fraud class |
| Overall ranking quality | ROC-AUC ≥ 0.95, PR-AUC reported (more honest than ROC-AUC on imbalanced data) |
| Prediction is usable | Single prediction returns in <500ms |
| Project is portfolio-ready | Deployed live demo + public GitHub repo + documented README |

---

## 3. User Stories

1. As a user, I upload a CSV of transactions and the system tells me if it's usable (validates schema) before doing anything else.
2. As a user, I see automatic EDA — class balance, amount distributions, time patterns, correlations — without writing any code.
3. As a user, I can trigger training, compare multiple models side by side, and see which one the system recommends and why.
4. As a user, I can enter a single transaction's details and instantly get a fraud probability + explanation of which features drove that score.
5. As a user, I can upload a batch of new transactions and download a scored CSV.
6. As a user (recruiter/interviewer demoing it), I can understand what's happening at every step without reading code.

---

## 4. Scope

**In scope (v1 — build this):**
- CSV upload, validation, automated cleaning
- Automated EDA with interactive charts
- Model training pipeline with SMOTE + 3 model comparison
- Single + batch prediction
- Basic SHAP-based explainability
- Deployed, working demo

**Out of scope (v2 — mention as "future work" in README, don't burn time on it now):**
- True real-time streaming (Kafka)
- User authentication / multi-tenant accounts
- Continuous model retraining / drift monitoring in production
- Multiple dataset schemas beyond a configurable column mapper

---

## 5. System Architecture

```
┌─────────────────┐        ┌──────────────────────────┐        ┌─────────────────┐
│   Frontend       │  REST  │   FastAPI Backend         │        │  Storage         │
│  (React+Tremor   │◄──────►│                            │◄──────►│  - SQLite/Postgres│
│   or Jinja+HTMX) │  JSON  │  /upload  /eda  /train      │        │    (metadata,     │
│                  │        │  /predict /explain          │        │     predictions)  │
│  - Upload page   │        │                            │        │  - /models/ dir    │
│  - EDA dashboard │        │  ┌──────────────────────┐  │        │    (.pkl artifacts)│
│  - Train screen  │        │  │ ML Pipeline           │  │        └─────────────────┘
│  - Predict form  │        │  │ pandas → clean →       │  │
│  - History view  │        │  │ SMOTE → train →        │  │
└─────────────────┘        │  │ evaluate → SHAP        │  │
                             │  └──────────────────────┘  │
                             └──────────────────────────┘
```

Training runs as a background task (FastAPI `BackgroundTasks` or a simple job queue) so the upload/train endpoints don't block — the frontend polls a `/train/status/{job_id}` endpoint and shows progress.

---

## 6. Functional Requirements

### 6.1 Data Upload & Validation
- Accept `.csv`, max 200MB.
- Validate required columns exist (configurable — default schema matches the standard Kaggle "Credit Card Fraud Detection" dataset: `Time, Amount, V1–V28, Class`).
- If a user uploads a different schema, offer a simple column-mapping step ("which column is the label? which is the amount?").
- Reject with a clear error message if validation fails — don't crash silently.

### 6.2 Automated Data Cleaning
- Handle missing values (report % missing per column, impute or drop based on threshold).
- Remove exact duplicate rows, log how many were removed.
- Detect and flag (not silently drop) outliers in `Amount` using IQR.
- Coerce types, log every transformation applied so the user can see a "cleaning report."

### 6.3 Automated EDA (this is a big differentiator — make it good)
Auto-generate and render as interactive charts (not static PNGs):
- Class balance bar chart (fraud vs. legit count + %)
- Transaction amount distribution (fraud vs. legit, side by side)
- Time-of-day / day pattern of fraud vs. legit transactions
- Correlation heatmap of features
- Top features that differ most between fraud and legit (simple statistical test, e.g., mean difference or mutual information ranked)

### 6.4 Model Training
- Split data (stratified, since classes are imbalanced).
- Apply SMOTE (or SMOTE-ENN) on the training set only — never on test data, that's a common student mistake that inflates results artificially.
- Train and compare: Logistic Regression (baseline), Random Forest, XGBoost.
- Report per model: Precision, Recall, F1, ROC-AUC, PR-AUC, confusion matrix.
- Auto-recommend the best model based on PR-AUC (more honest than accuracy/ROC-AUC on rare-event data) and let the user override.
- Save the trained model artifact + the preprocessing pipeline together (so predictions later apply identical transforms).

### 6.5 Prediction
- **Single prediction:** a form for transaction fields → returns fraud probability (0–1), a risk label (Low/Medium/High), and top 3 contributing features.
- **Batch prediction:** upload CSV → returns downloadable CSV with a new `fraud_probability` and `risk_label` column added.
- Log every prediction (with timestamp) to storage for the history view.

### 6.6 Explainability
- Use SHAP to show, per prediction, which features pushed the score up or down (a simple horizontal bar chart works well).
- On the training results page, show global feature importance so the user understands what the model actually learned.

### 6.7 History / Monitoring Dashboard
- Table of past predictions with filters (risk level, date range).
- Simple chart: fraud rate over time, prediction volume over time.

---

## 7. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/upload` | Upload CSV, returns `dataset_id` + validation report |
| GET | `/eda/{dataset_id}` | Returns EDA summary JSON (chart data) |
| POST | `/train/{dataset_id}` | Kicks off training, returns `job_id` |
| GET | `/train/status/{job_id}` | Poll training progress/result |
| GET | `/models` | List trained models + metrics |
| POST | `/predict` | Single transaction → `{fraud_probability, risk_label, top_features}` |
| POST | `/predict/batch` | CSV in → scored CSV out |
| GET | `/predict/history` | Paginated prediction log |
| GET | `/explain/{prediction_id}` | SHAP explanation for a specific past prediction |

Example response for `POST /predict`:
```json
{
  "fraud_probability": 0.873,
  "risk_label": "High",
  "top_features": [
    {"feature": "V14", "impact": 0.31, "direction": "increases risk"},
    {"feature": "Amount", "impact": 0.18, "direction": "increases risk"},
    {"feature": "V4", "impact": -0.09, "direction": "decreases risk"}
  ],
  "model_used": "xgboost_v1",
  "timestamp": "2026-08-18T10:22:00Z"
}
```

---

## 8. Tech Stack

**Backend / ML (your core skills):**
- Python, FastAPI, Uvicorn, Pydantic (request/response validation)
- pandas, numpy — cleaning & EDA
- scikit-learn, XGBoost — modeling
- imbalanced-learn — SMOTE
- SHAP — explainability
- SQLite (fast to set up) or Postgres (more "production" if you want the extra credit) for storing metadata/history
- joblib — saving model + pipeline artifacts

**Frontend — pick ONE track based on your time/comfort:**

*Track A — Fastest, all-Python (recommended if you're on a deadline):*
FastAPI + Jinja2 templates + Tailwind CSS (via CDN) + Chart.js or Plotly.js for interactive charts. No separate frontend build step, no React needed. Still looks modern and clean if you follow a simple design system (see Section 9).

*Track B — More visually impressive, worth it if you have 1–2 extra weeks:*
FastAPI stays a pure JSON API. Separate React frontend using an open-source dashboard kit — **Tremor** (free, MIT-licensed, purpose-built for analytics dashboards with KPI cards and charts — a very natural fit for a fraud dashboard) or **shadcn/ui Admin** (free, ~11k GitHub stars, Tailwind + Radix based, very polished, "copy the code in, own it" philosophy rather than a black-box package). Either gives you a genuinely professional look without designing from scratch.

**Deployment:**
- Backend: Docker container → Render or Railway (both have free tiers)
- Frontend (if Track B): Vercel
- Or, for a single-deploy option: Hugging Face Spaces (supports FastAPI + static frontend together)

---

## 9. UI/UX Design Direction

Keep it simple and consistent rather than flashy:
- **Layout:** left sidebar nav (Upload → EDA → Train → Predict → History), main content area, top bar with dataset name + status.
- **KPI cards at the top of the dashboard:** Total Transactions, Fraud Detected, Fraud Rate %, Current Model AUC — these are the four numbers a recruiter's eyes will go to first.
- **Color coding:** consistent red/orange for high risk, amber for medium, green for low — used consistently across charts, tables, and the prediction result.
- **Progress states matter:** cleaning and training take time — show a progress bar / step indicator (Uploading → Validating → Cleaning → Ready), not a frozen screen. This alone makes a huge UX difference and is easy to build with FastAPI's background tasks + polling.
- **Dark mode toggle** — small effort, disproportionately makes a project look "product-grade" in a demo/interview.

---

## 10. Non-Functional Requirements
- File size cap (200MB) enforced before processing starts, with a clear error.
- Large files processed asynchronously — never block the request thread.
- Don't persist raw uploaded data longer than needed for the session; mention this as a privacy-conscious design choice in your README (recruiters notice this kind of thinking).
- Basic input validation on every endpoint via Pydantic models — reject malformed requests with clear 4xx errors, not 500s.
- Log key events (upload, training start/end, errors) — even a simple log file shows production awareness.

---

## 11. Suggested Timeline (4 weeks, adjust to your deadline)

| Week | Focus |
|---|---|
| 1 | Data pipeline: upload, validation, cleaning + automated EDA (backend + basic UI) |
| 2 | Modeling pipeline: SMOTE, train 3 models, evaluation, model comparison + selection |
| 3 | Prediction endpoints (single + batch) + SHAP explainability |
| 4 | Frontend polish (Track A or B), deployment, README, demo video/GIF, resume bullets |

---

## 12. Dataset

Start with the public **Credit Card Fraud Detection dataset (ULB, on Kaggle)** — ~285K transactions, 492 fraud (0.17%), already anonymized/PCA'd (`V1`–`V28`), so you skip data-collection headaches and go straight to the interesting imbalance + modeling problem. Design the schema mapping step so the platform *could* accept other transaction datasets too — that flexibility is itself a talking point in interviews.

---

## 13. Portfolio Deliverables Checklist
- [ ] Public GitHub repo, clean commit history (not one giant commit)
- [ ] README with: problem statement, architecture diagram, screenshots/GIF of the app, how to run locally, metrics table, live demo link
- [ ] Deployed, working link (test it in incognito before sharing it anywhere)
- [ ] Resume bullet, e.g.: *"Built an end-to-end fraud detection platform (FastAPI + XGBoost + SHAP) handling 0.17% class imbalance via SMOTE, achieving 0.87 recall / 0.95 ROC-AUC, with automated EDA and explainable real-time predictions."*
- [ ] 60–90 second demo video for LinkedIn — projects with a video get noticed more than a GitHub link alone

---

## 14. Open Questions / Risks
- Track A vs. B decision should be made in Week 1, based on realistic time available — don't decide mid-build.
- SHAP can be slow on large datasets — consider `TreeExplainer` (fast for tree models) and cap explanation to top-5 features rather than the full set.
- If the deadline is very tight, Section 6.6 (explainability) and dark mode are the first things to cut — everything else in the MVP is non-negotiable for the "this isn't a toy project" impression.
