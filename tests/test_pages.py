from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_page_response():
    """
    Verifies that GET / renders the dataset upload page.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Upload & Clean" in response.text
    assert "FraudLens" in response.text

def test_eda_page_response():
    """
    Verifies that GET /eda-dashboard renders the EDA dashboard page.
    """
    response = client.get("/eda-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Exploratory Data Analysis" in response.text

def test_train_page_response():
    """
    Verifies that GET /train-dashboard renders the model training studio page.
    """
    response = client.get("/train-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Model Training Studio" in response.text

def test_predict_page_response():
    """
    Verifies that GET /predict-dashboard renders the inference center page.
    """
    response = client.get("/predict-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Inference Center" in response.text

def test_history_page_response():
    """
    Verifies that GET /history-dashboard renders the prediction history logs page.
    """
    response = client.get("/history-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Prediction Execution History" in response.text

def test_api_cleaned_datasets_endpoint():
    """
    Verifies that GET /api/pages/cleaned-datasets returns a valid list.
    """
    response = client.get("/api/pages/cleaned-datasets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
