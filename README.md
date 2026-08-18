# FraudLens - Transaction Fraud Detection Platform

FraudLens is an end-to-end automated machine learning platform designed to ingestion, pre-process, evaluate, and explain transaction credit card fraud data. 

Built using a high-performance **FastAPI** backend integrated with an interactive **Jinja2 + Tailwind CSS + Chart.js** frontend dashboard, the platform enables analysts to upload transaction batches, run cleaning pipelines, analyze data via EDA charts, trigger asynchronous ML training, activate model runs, audit model predictions, and visualize feature contribution impacts with SHAP Tree/Linear explainers.

---

## Key Features

1. **Upload & Clean Pipeline:** Accepts credit card transaction CSV files (up to 200MB), validates schemas, removes duplicate rows, flags outliers in transaction amounts using IQR, and handles missing values.
2. **Exploratory Data Analysis (EDA) Dashboard:** Dynamic visualization of class balance distributions (doughnut charts), amount distributions grouped by class (min, max, mean, percentiles), correlation matrix heatmaps, and top 10 features ranked by absolute mean difference.
3. **Model Training Studio:** Queue asynchronous training jobs (Logistic Regression, Random Forest, XGBoost fallbacks) utilizing stratified splits and SMOTE. Inspect comparative model evaluation tables (Precision, Recall, F1, ROC-AUC, PR-AUC).
4. **Inference Center:** Run predictions on individual transactions (autofilled with template legit/fraud profiles) showing color-coded risk levels (Low/Medium/High) and real-time SHAP feature contribution charts, or execute batch scoring with download-ready scored CSV output files.
5. **Prediction Logs Audit:** Paginated lookup of all historical predictions with page controls and risk label / date range filters. Offers a sliding SHAP breakdown panel detailing each feature's contribution towards model risk.

---

## Directory Structure

```
.
├── app/
│   ├── main.py              # Application entrypoint with CORS & lifespan initialization
│   ├── routers/             # API & Page HTML routers
│   │   ├── upload.py        # Dataset CSV upload endpoint
│   │   ├── cleaning.py      # Pre-cleaning process endpoints
│   │   ├── eda.py           # Statistical calculation outputs
│   │   ├── train.py         # Asynchronous training loops
│   │   ├── models.py        # Model list & activation handlers
│   │   ├── predict.py       # Single, batch, SHAP, and history logs
│   │   └── pages.py         # HTML page rendering routers (Jinja2 templates)
│   ├── services/            # Business & DB query services
│   │   └── database.py      # SQLite connection context managers (WAL mode)
│   ├── models/              # Pydantic validation schemas
│   ├── ml/                  # Machine learning preprocessing and training helpers
│   └── templates/           # Jinja2 template views (Tailwind + Chart.js)
│       ├── base.html        # Shell template layout
│       ├── upload.html      # CSV upload & cleaning UI
│       ├── eda.html         # Statistical analysis dashboards
│       ├── train.html       # Model training studio
│       ├── predict.html     # Real-time transaction inference
│       └── history.html     # Audited prediction history logs
├── tests/                   # 23-case test suites (covering ML logic, DB, & pages)
├── Dockerfile               # Production container image file
├── requirements.txt         # Project package requirements
├── .env.example             # Configuration variables template
└── README.md                # This setup guide
```

---

## Local Setup Instructions

### 1. Prerequisites
Ensure you have **Python 3.11+** installed on your system.

### 2. Create and Activate Virtual Environment
Clone the repository and run:

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (macOS / Linux)
source .venv/bin/activate

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Copy the sample environment variables:
```bash
cp .env.example .env
```

### 5. Running locally
```bash
uvicorn app.main:app --reload
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to view the interactive dashboard.
*   Interactive API Documentation (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 6. Running Tests
```bash
rm -rf data/raw/ data/cleaned/ && rm -f data/metadata.db data/metadata.db-wal data/metadata.db-shm
PYTHONPATH=. pytest tests/ -v
```

---

## Running with Docker

To build and run the application locally inside a container:

```bash
# Build the image
docker build -t fraudlens .

# Run the container
docker run -p 8000:8000 -e PORT=8000 fraudlens
```
Go to `http://localhost:8000` to interact with the containerized application.

---

## Deployment Instructions

### Render Deployment (Backend & Frontend)
Render supports deploying containerized web apps directly:
1. Push your code to your GitHub repository.
2. Sign in to [Render](https://render.com) and click **New > Web Service**.
3. Select your repository.
4. Set the following configurations:
   - **Runtime:** `Docker`
   - **Branch:** `main` (or your active branch)
5. Add environment variables under the **Environment** tab:
   - `PORT`: `8000`
6. Click **Deploy Web Service**.

### Railway Deployment
Railway offers quick container-based deployment:
1. Log in to [Railway](https://railway.app).
2. Click **New Project** and select **Deploy from GitHub repo**.
3. Choose your repository.
4. Click **Deploy Now**. Railway will automatically detect the `Dockerfile` and build/deploy the container.
5. In the service settings, click **Generate Domain** to expose your service URL to the web.

---

## Screenshot Placeholders

### 1. Upload & Cleaning Pipeline
`![Upload UI](docs/screenshots/upload_page.png)` *(Placeholder: Uploading datasets, viewing duplicate counts and column missing value reports.)*

### 2. Statistical EDA Dashboard
`![EDA Dashboard](docs/screenshots/eda_page.png)` *(Placeholder: Class balance pie chart, amount statistics tables, and correlation matrix heatmap.)*

### 3. Training Control Studio
`![Training Studio](docs/screenshots/train_page.png)` *(Placeholder: Asynchronous training status tracker, model metrics comparison table, and activation status buttons.)*

### 4. Inference Center with SHAP Graphs
`![Inference Center](docs/screenshots/predict_page.png)` *(Placeholder: Pre-filling legit/fraud sample profiles, risk classification card, and horizontal SHAP bars.)*

### 5. Log History & Slide Panel Explainers
`![Logs Audit](docs/screenshots/history_page.png)` *(Placeholder: Paginated audit history log list, filtering, and side panel SHAP visualizer.)*
