# FraudLens Backend

FraudLens is an end-to-end automated transaction fraud detection platform. This repository contains the FastAPI backend, which handles transaction data cleaning, automated exploratory data analysis (EDA), model training (Logistic Regression, Random Forest, XGBoost), and SHAP-based model explanations.

---

## Directory Structure

```
.
├── app/
│   ├── main.py              # Application entrypoint with CORS & health endpoint
│   ├── routers/             # API Router endpoints
│   ├── services/            # Core business logic (EDA calculation, data management)
│   ├── models/              # Pydantic schemas / request-response data models
│   └── ml/                  # Machine Learning model definitions & pipelines
├── tests/
│   └── test_eda.py          # Unit & endpoint tests for EDA calculations
├── requirements.txt         # Project package requirements
├── .env.example             # Configuration variables template
└── README.md                # This setup guide
```

---

## Setup Instructions

### 1. Prerequisites
Ensure you have **Python 3.11+** installed on your system.

### 2. Create and Activate Virtual Environment
From the root directory:

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (macOS / Linux)
source .venv/bin/activate

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install all the required python packages:

```bash
pip install -r requirements.txt
```

### 4. Configuration
Copy the sample environment variables file and modify it if needed:

```bash
cp .env.example .env
```

---

## Running the Application

Start the FastAPI local development server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

*   **API Root:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
*   **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
*   **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   **Alternative API Docs (ReDoc):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running Tests

Execute the test suite to verify code correctness and route integration:

```bash
PYTHONPATH=. pytest tests/ -v
```
