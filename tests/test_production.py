import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from app.database import Base, get_db
from app.main import app
from app.db_models import User, Product, Warehouse, InventoryBalance
from app.services.auth_utils import get_current_user

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

def override_get_current_user():
    return User(email="test@test.com", id="test-user-id")

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    db = TestingSessionLocal()
    # Create products
    paddy = Product(id="prod-paddy", sku="PADDY-01", name="Paddy", type="paddy", uom="KG", current_mac=5000)
    rice = Product(id="prod-rice", sku="RICE-01", name="Beras Premium", type="milled_rice", uom="KG", current_mac=0)
    dedak = Product(id="prod-dedak", sku="DEDAK-01", name="Dedak", type="byproduct", uom="KG", current_mac=0)

    # Create warehouse
    wh = Warehouse(id="wh-1", code="WH-01", name="Main WH", type="mixed")

    # Create initial inventory for paddy (1000 KG @ 5000 MAC)
    inv = InventoryBalance(id="inv-1", product_id="prod-paddy", warehouse_id="wh-1", current_qty=1000, current_mac=5000)

    db.add_all([paddy, rice, dedak, wh, inv])
    db.commit()
    yield db
    # Cleanup after tests
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_production_flow(setup_db):
    # 1. Create a draft production run
    res = client.post(
        "/api/v1/production",
        json={"type": "paddy_milling", "notes": "Test milling"}
    )
    assert res.status_code == 200
    run_id = res.json()["id"]

    # 2. Add Inputs (1000 KG of paddy)
    res = client.post(
        f"/api/v1/production/{run_id}/inputs",
        json={"product_id": "prod-paddy", "warehouse_id": "wh-1", "qty": 1000}
    )
    assert res.status_code == 200

    # 3. Add Outputs (600 KG Rice, 300 KG Dedak)
    # Option A: Rice absorbs 100% cost, Dedak absorbs 0%
    res = client.post(
        f"/api/v1/production/{run_id}/outputs",
        json={"product_id": "prod-rice", "warehouse_id": "wh-1", "qty": 600, "cost_allocation_percent": 100}
    )
    assert res.status_code == 200

    res = client.post(
        f"/api/v1/production/{run_id}/outputs",
        json={"product_id": "prod-dedak", "warehouse_id": "wh-1", "qty": 300, "cost_allocation_percent": 0}
    )
    assert res.status_code == 200

    # 4. Commit Run
    res = client.post(f"/api/v1/production/{run_id}/commit")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"

    # 5. Verify Database State
    db = TestingSessionLocal()

    # Paddy should be 0
    paddy_inv = db.query(InventoryBalance).filter_by(product_id="prod-paddy").first()
    assert paddy_inv.current_qty == 0

    # Total input cost was 1000 * 5000 = 5,000,000
    # Rice gets 100% of cost = 5,000,000 for 600 KG -> MAC = 8333.33
    rice_inv = db.query(InventoryBalance).filter_by(product_id="prod-rice").first()
    assert rice_inv.current_qty == 600
    assert float(rice_inv.current_mac) == pytest.approx(8333.33, rel=1e-2)

    # Dedak gets 0 cost -> MAC = 0
    dedak_inv = db.query(InventoryBalance).filter_by(product_id="prod-dedak").first()
    assert dedak_inv.current_qty == 300
    assert float(dedak_inv.current_mac) == 0
    db.close()
