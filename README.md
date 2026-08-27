# FraudLens - Automated Transaction Fraud Detection Platform

FraudLens is an end-to-end machine learning platform designed to ingest, clean, evaluate, train, and run real-time inference on credit card fraud datasets.

Built with a high-performance **FastAPI** Python backend integrated with a modern **React + Vite + Tailwind CSS** frontend pipeline dashboard.

---

## Key Features

1. **Phase 01 · Upload & Validate:** Accepts transaction CSV files (up to 200MB), validates schemas, handles null values, and sets up dataset isolation automatically.
2. **Phase 02 · Exploratory Analysis (EDA):** Statistical profiling of transaction rows, class imbalance metrics, missing value distributions, and top discriminative features.
3. **Phase 03 · Model Training Studio:** Select ML algorithms (XGBoost, Random Forest, Logistic Regression), balance classes with SMOTE, execute training pipelines, and evaluate precision, recall, F1 score, and AUC-ROC metrics.
4. **Phase 04 · Fraud Inference & Batch Scoring:** Single transaction risk assessment with real-time risk scores and SHAP feature contributions, plus batch CSV file scoring with download-ready outputs.

---

## Repository Structure

```
.
├── app/                      # FastAPI Python Backend
│   ├── main.py               # Main application entrypoint & API router mounting
│   ├── routers/              # Endpoint controllers
│   │   ├── upload.py         # CSV dataset upload & list endpoints
│   │   ├── eda.py            # Statistical profiling & EDA metrics
│   │   ├── train.py          # Model training pipeline endpoints
│   │   ├── predict.py        # Single & batch fraud inference
│   │   └── downloads.py      # Artifact exports & downloads
│   ├── services/             # Business logic & database services
│   └── models/               # Pydantic data models
│
├── frontend/                 # React + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/       # Stepper, PhaseShell, Navbar components
│   │   ├── pages/            # UploadPage, EDADashboard, TrainDashboard, PredictDashboard
│   │   └── lib/              # Styling utilities
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration & backend proxy setup
│
├── tests/                    # Backend pytest test suite
├── Dockerfile                # Production container deployment file
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## Local Setup Instructions

### 1. Backend Setup (FastAPI)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server (runs on port 8000)
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (React + Vite)

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server (runs on port 3000)
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## Production Build

To build the static React SPA bundle for FastAPI static serving:

```bash
cd frontend
npm run build
```

FastAPI will automatically serve the built bundle from `frontend/dist/` at `http://localhost:8000`.

---

## 🛡️ Git Security & Data Privacy Policy

To protect sensitive financial transaction data and maintain a clean repository when pushing to GitHub:

| Category | Tracked & Pushed to GitHub | Ignored & Excluded (`.gitignore`) |
| :--- | :--- | :--- |
| **Source Code** | `app/`, `frontend/src/`, `tests/` | None |
| **Configurations** | `package.json`, `requirements.txt`, `vite.config.ts`, `docker-compose.yml`, `Dockerfile`, `.gitignore` | `.env`, `.env.local` (secrets) |
| **Datasets** | Directory structure via `.gitkeep` | `data/raw/*.csv`, `data/cleaned/*.csv` |
| **Databases** | None | `fraudlens.db`, `data/metadata.db`, `*.sqlite` |
| **ML Models** | None (generated locally) | `data/models/*.joblib`, `*.pkl` |
| **Dependencies** | None | `.venv/`, `node_modules/`, `frontend/node_modules/` |
| **Builds** | None | `dist/`, `frontend/dist/`, `__pycache__/`, `.pytest_cache/` |

