import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

# Use the same test DB
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

from app.services.auth_utils import get_current_user
from app.db_models import User

def override_get_current_user():
    return User(email="test@test.com", id="test-user-id")

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_dry_run_products():
    response = client.post(
        "/api/v1/imports/dry-run",
        json={"sheet_url": "mock-products", "entity_type": "product"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows_count"] == 2 # P-001, P-002 are valid
    assert data["invalid_rows_count"] == 1 # P-003 has invalid type
    assert len(data["rows"]) == 3
    assert data["rows"][2]["is_valid"] == False

def test_commit_products():
    # Only send the valid ones
    response = client.post(
        "/api/v1/imports/commit",
        json={
            "entity_type": "product",
            "valid_data": [
                {"sku": "P-001", "name": "Premium Beras", "type": "milled_rice", "uom": "KG", "current_mac": "0"},
                {"sku": "P-002", "name": "Dedak", "type": "byproduct", "uom": "KG", "current_mac": "0"}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["committed_count"] == 2

    # Verify they were saved
    res = client.get("/api/v1/products")
    prods = [p["sku"] for p in res.json()]
    assert "P-001" in prods
    assert "P-002" in prods

def test_dry_run_opening_stock():
    # First need to create the warehouse for the mock stock to be valid
    client.post(
        "/api/v1/imports/commit",
        json={
            "entity_type": "warehouse",
            "valid_data": [
                {"code": "WH-A", "name": "Main Warehouse", "type": "mixed"}
            ]
        }
    )

    response = client.post(
        "/api/v1/imports/dry-run",
        json={"sheet_url": "mock-opening-stock", "entity_type": "opening_stock"}
    )
    assert response.status_code == 200
    data = response.json()
    # P-001 exists and WH-A exists, so row 0 is valid. P-999 doesn't exist, row 1 invalid.
    assert data["valid_rows_count"] == 1
    assert data["invalid_rows_count"] == 1

def test_commit_opening_stock():
    response = client.post(
        "/api/v1/imports/commit",
        json={
            "entity_type": "opening_stock",
            "valid_data": [
                {"sku": "P-001", "warehouse_code": "WH-A", "quantity": "1000", "as_of_date": "2023-01-01"}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["committed_count"] == 1
    # Stock ledger and balance verification would typically happen against DB directly here in tests
