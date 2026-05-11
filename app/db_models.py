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
