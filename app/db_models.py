from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Enum, Numeric, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ProductType(str, enum.Enum):
    paddy = "paddy"
    milled_rice = "milled_rice"
    byproduct = "byproduct"
    packaging = "packaging"

class WarehouseType(str, enum.Enum):
    raw_material = "raw_material"
    finished_goods = "finished_goods"
    mixed = "mixed"

class PartnerType(str, enum.Enum):
    customer = "customer"
    supplier = "supplier"
    both = "both"

class RefType(str, enum.Enum):
    opening_balance = "opening_balance"
    goods_receipt = "goods_receipt"
    delivery_order = "delivery_order"
    production_in = "production_in"
    production_out = "production_out"
    adjustment = "adjustment"

class ProductionRunType(str, enum.Enum):
    paddy_milling = "paddy_milling"
    rice_reprocessing = "rice_reprocessing"

class ProductionRunStatus(str, enum.Enum):
    draft = "draft"
    completed = "completed"

class TradeOrderStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    completed = "completed"
    cancelled = "cancelled"

class TradeDocumentStatus(str, enum.Enum):
    draft = "draft"
    committed = "committed"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    type = Column(Enum(ProductType))
    uom = Column(String)
    current_mac = Column(Numeric(15, 2), default=0)
    is_active = Column(Boolean, default=True)

    inventory_balances = relationship("InventoryBalance", back_populates="product")
    stock_ledger = relationship("StockLedger", back_populates="product")

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    type = Column(Enum(WarehouseType))

    inventory_balances = relationship("InventoryBalance", back_populates="warehouse")
    stock_ledger = relationship("StockLedger", back_populates="warehouse")

class Partner(Base):
    __tablename__ = "partners"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    type = Column(Enum(PartnerType))
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)

class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(String, primary_key=True, default=generate_uuid)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    reference_type = Column(Enum(RefType))
    reference_id = Column(String) # E.g., PO-123 or Sheet Import ID
    product_id = Column(String, ForeignKey("products.id"))
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    qty_change = Column(Numeric(10, 2)) # Positive for IN, Negative for OUT
    balance_after = Column(Numeric(10, 2))

    product = relationship("Product", back_populates="stock_ledger")
    warehouse = relationship("Warehouse", back_populates="stock_ledger")

class InventoryBalance(Base):
    __tablename__ = "inventory_balances"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), index=True)
    warehouse_id = Column(String, ForeignKey("warehouses.id"), index=True)
    current_qty = Column(Numeric(10, 2), default=0)
    current_mac = Column(Numeric(15, 2), default=0)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_balances")
    warehouse = relationship("Warehouse", back_populates="inventory_balances")

class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_date = Column(DateTime, default=datetime.utcnow)
    type = Column(Enum(ProductionRunType))
    status = Column(Enum(ProductionRunStatus), default=ProductionRunStatus.draft)
    notes = Column(Text, nullable=True)

    inputs = relationship("ProductionInput", back_populates="run", cascade="all, delete-orphan")
    outputs = relationship("ProductionOutput", back_populates="run", cascade="all, delete-orphan")

class ProductionInput(Base):
    __tablename__ = "production_inputs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("production_runs.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    qty = Column(Numeric(10, 2))
    total_cost = Column(Numeric(15, 2), default=0)

    run = relationship("ProductionRun", back_populates="inputs")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

class ProductionOutput(Base):
    __tablename__ = "production_outputs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("production_runs.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    qty = Column(Numeric(10, 2))
    cost_allocation_percent = Column(Numeric(5, 2), default=0)
    total_cost = Column(Numeric(15, 2), default=0)

    run = relationship("ProductionRun", back_populates="outputs")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    po_number = Column(String, unique=True, index=True)
    supplier_id = Column(String, ForeignKey("partners.id"))
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_date = Column(DateTime, nullable=True)
    status = Column(Enum(TradeOrderStatus), default=TradeOrderStatus.draft)
    notes = Column(Text, nullable=True)

    supplier = relationship("Partner")
    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    po_id = Column(String, ForeignKey("purchase_orders.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    qty_ordered = Column(Numeric(10, 2))
    qty_received = Column(Numeric(10, 2), default=0)
    unit_price = Column(Numeric(15, 2))

    po = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(String, primary_key=True, default=generate_uuid)
    gr_number = Column(String, unique=True, index=True)
    po_id = Column(String, ForeignKey("purchase_orders.id"), nullable=True)
    supplier_id = Column(String, ForeignKey("partners.id"))
    receipt_date = Column(DateTime, default=datetime.utcnow)
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    status = Column(Enum(TradeDocumentStatus), default=TradeDocumentStatus.draft)

    po = relationship("PurchaseOrder")
    supplier = relationship("Partner")
    warehouse = relationship("Warehouse")
    items = relationship("GoodsReceiptItem", back_populates="gr", cascade="all, delete-orphan")

class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    gr_id = Column(String, ForeignKey("goods_receipts.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    po_item_id = Column(String, ForeignKey("purchase_order_items.id"), nullable=True)
    qty_received = Column(Numeric(10, 2))
    unit_price = Column(Numeric(15, 2)) # Important for direct GR MAC updates

    gr = relationship("GoodsReceipt", back_populates="items")
    product = relationship("Product")

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    so_number = Column(String, unique=True, index=True)
    customer_id = Column(String, ForeignKey("partners.id"))
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_date = Column(DateTime, nullable=True)
    status = Column(Enum(TradeOrderStatus), default=TradeOrderStatus.draft)
    notes = Column(Text, nullable=True)

    customer = relationship("Partner")
    items = relationship("SalesOrderItem", back_populates="so", cascade="all, delete-orphan")

class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    so_id = Column(String, ForeignKey("sales_orders.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    qty_ordered = Column(Numeric(10, 2))
    qty_delivered = Column(Numeric(10, 2), default=0)
    unit_price = Column(Numeric(15, 2))

    so = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")

class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    do_number = Column(String, unique=True, index=True)
    so_id = Column(String, ForeignKey("sales_orders.id"), nullable=True)
    customer_id = Column(String, ForeignKey("partners.id"))
    delivery_date = Column(DateTime, default=datetime.utcnow)
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    status = Column(Enum(TradeDocumentStatus), default=TradeDocumentStatus.draft)

    so = relationship("SalesOrder")
    customer = relationship("Partner")
    warehouse = relationship("Warehouse")
    items = relationship("DeliveryOrderItem", back_populates="do", cascade="all, delete-orphan")

class DeliveryOrderItem(Base):
    __tablename__ = "delivery_order_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    do_id = Column(String, ForeignKey("delivery_orders.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    so_item_id = Column(String, ForeignKey("sales_order_items.id"), nullable=True)
    qty_delivered = Column(Numeric(10, 2))

    do = relationship("DeliveryOrder", back_populates="items")
    product = relationship("Product")
