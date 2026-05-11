import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Note: Before each test we ideally clear the DB, but since it's a test db we will assume ordering
# In a real setup we might use a fixture to yield a fresh db session

# Helper to override auth for tests
from app.services.auth_utils import get_current_user
from app.db_models import User

def override_get_current_user():
    return User(email="test@test.com", id="test-user-id")

app.dependency_overrides[get_current_user] = override_get_current_user

def test_create_product():
    response = client.post(
        "/api/v1/products",
        json={"sku": "TEST-SKU-1", "name": "Test Product", "type": "paddy", "uom": "KG", "current_mac": "15000.50", "is_active": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "TEST-SKU-1"
    assert "id" in data
    assert data["current_mac"] == "15000.50"

def test_get_products():
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_create_warehouse():
    response = client.post(
        "/api/v1/warehouses",
        json={"code": "WH-TEST", "name": "Test WH", "type": "mixed"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "WH-TEST"
    assert "id" in data

def test_get_warehouses():
    response = client.get("/api/v1/warehouses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_create_partner():
    response = client.post(
        "/api/v1/partners",
        json={"code": "PART-TEST", "name": "Test Partner", "type": "customer", "phone": "123", "address": "Add"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "PART-TEST"
    assert "id" in data

def test_get_partners():
    response = client.get("/api/v1/partners")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
