from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_page_response():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "FraudLens" in response.text

def test_eda_page_response():
    response = client.get("/eda-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_train_page_response():
    response = client.get("/train-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_predict_page_response():
    response = client.get("/predict-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_history_page_response():
    response = client.get("/history-dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_api_cleaned_datasets_endpoint():
    response = client.get("/api/cleaned-datasets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
