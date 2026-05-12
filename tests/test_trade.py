import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.db_models import User, Product, Warehouse, Partner, InventoryBalance
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
    rice = Product(id="prod-rice", sku="RICE-01", name="Beras Premium", type="milled_rice", uom="KG", current_mac=10000)

    # Create warehouse
    wh = Warehouse(id="wh-1", code="WH-01", name="Main WH", type="mixed")

    # Create partners
    supplier = Partner(id="supp-1", code="SUPP-01", name="Supplier A", type="supplier")
    customer = Partner(id="cust-1", code="CUST-01", name="Customer A", type="customer")

    db.add_all([paddy, rice, wh, supplier, customer])
    db.commit()
    yield db
    # Cleanup after tests
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_purchasing_flow(setup_db):
    # 1. Create a PO
    res = client.post(
        "/api/v1/purchasing/purchase-orders",
        json={"po_number": "PO-001", "supplier_id": "supp-1"}
    )
    assert res.status_code == 200
    po_id = res.json()["id"]

    # Add PO Item
    res = client.post(
        f"/api/v1/purchasing/purchase-orders/{po_id}/items",
        json={"product_id": "prod-paddy", "qty_ordered": 1000, "unit_price": 5200}
    )
    assert res.status_code == 200
    po_item_id = res.json()["id"]

    # 2. Create GR linked to PO
    res = client.post(
        "/api/v1/purchasing/goods-receipts",
        json={"gr_number": "GR-001", "po_id": po_id, "supplier_id": "supp-1", "warehouse_id": "wh-1"}
    )
    assert res.status_code == 200
    gr_id = res.json()["id"]

    # Add GR Item
    res = client.post(
        f"/api/v1/purchasing/goods-receipts/{gr_id}/items",
        json={"product_id": "prod-paddy", "po_item_id": po_item_id, "qty_received": 1000, "unit_price": 5200}
    )
    assert res.status_code == 200

    # 3. Commit GR
    res = client.post(f"/api/v1/purchasing/goods-receipts/{gr_id}/commit")
    assert res.status_code == 200

    # Verify Database state
    db = TestingSessionLocal()
    # Inventory for paddy should be 1000 with MAC 5200
    inv = db.query(InventoryBalance).filter_by(product_id="prod-paddy").first()
    assert inv.current_qty == 1000
    assert float(inv.current_mac) == 5200.0
    db.close()

def test_direct_goods_receipt(setup_db):
    # Direct GR without PO
    res = client.post(
        "/api/v1/purchasing/goods-receipts",
        json={"gr_number": "GR-DIRECT-01", "supplier_id": "supp-1", "warehouse_id": "wh-1"}
    )
    assert res.status_code == 200
    gr_id = res.json()["id"]

    # Add GR Item
    res = client.post(
        f"/api/v1/purchasing/goods-receipts/{gr_id}/items",
        json={"product_id": "prod-paddy", "qty_received": 500, "unit_price": 4900}
    )
    assert res.status_code == 200

    # Commit
    res = client.post(f"/api/v1/purchasing/goods-receipts/{gr_id}/commit")
    assert res.status_code == 200

    # Verify MAC and Qty update
    db = TestingSessionLocal()
    inv = db.query(InventoryBalance).filter_by(product_id="prod-paddy").first()
    assert inv.current_qty == 1500
    # Old MAC: 5200 * 1000 = 5,200,000. New Incoming: 4900 * 500 = 2,450,000. Total Value: 7,650,000 / 1500 = 5100.
    assert float(inv.current_mac) == 5100.0
    db.close()

def test_sales_flow(setup_db):
    # Setup initial inventory for rice to be sold
    db = TestingSessionLocal()
    inv = InventoryBalance(id="inv-rice", product_id="prod-rice", warehouse_id="wh-1", current_qty=500, current_mac=10000)
    db.add(inv)
    db.commit()

    # 1. Create SO
    res = client.post(
        "/api/v1/sales/sales-orders",
        json={"so_number": "SO-001", "customer_id": "cust-1"}
    )
    assert res.status_code == 200
    so_id = res.json()["id"]

    # Add SO Item
    res = client.post(
        f"/api/v1/sales/sales-orders/{so_id}/items",
        json={"product_id": "prod-rice", "qty_ordered": 200, "unit_price": 12000}
    )
    assert res.status_code == 200
    so_item_id = res.json()["id"]

    # 2. Create DO
    res = client.post(
        "/api/v1/sales/delivery-orders",
        json={"do_number": "DO-001", "so_id": so_id, "customer_id": "cust-1", "warehouse_id": "wh-1"}
    )
    assert res.status_code == 200
    do_id = res.json()["id"]

    # Add DO Item
    res = client.post(
        f"/api/v1/sales/delivery-orders/{do_id}/items",
        json={"product_id": "prod-rice", "so_item_id": so_item_id, "qty_delivered": 200}
    )
    assert res.status_code == 200

    # 3. Commit DO
    res = client.post(f"/api/v1/sales/delivery-orders/{do_id}/commit")
    assert res.status_code == 200

    # Verify inventory deducted
    inv = db.query(InventoryBalance).filter_by(product_id="prod-rice").first()
    db.refresh(inv)
    assert inv.current_qty == 300
    db.close()
