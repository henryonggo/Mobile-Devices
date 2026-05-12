from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..db_models import TradeOrderStatus, TradeDocumentStatus

# --- Purchasing Schemas ---

class PurchaseOrderItemBase(BaseModel):
    product_id: str
    qty_ordered: Decimal = Field(..., max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(..., max_digits=15, decimal_places=2)

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    id: str
    po_id: str
    qty_received: Decimal

    class Config:
        from_attributes = True

class PurchaseOrderBase(BaseModel):
    po_number: str
    supplier_id: str
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrderResponse(PurchaseOrderBase):
    id: str
    order_date: datetime
    status: TradeOrderStatus
    items: List[PurchaseOrderItemResponse] = []

    class Config:
        from_attributes = True

class GoodsReceiptItemBase(BaseModel):
    product_id: str
    po_item_id: Optional[str] = None
    qty_received: Decimal = Field(..., max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(..., max_digits=15, decimal_places=2)

class GoodsReceiptItemCreate(GoodsReceiptItemBase):
    pass

class GoodsReceiptItemResponse(GoodsReceiptItemBase):
    id: str
    gr_id: str

    class Config:
        from_attributes = True

class GoodsReceiptBase(BaseModel):
    gr_number: str
    po_id: Optional[str] = None
    supplier_id: str
    warehouse_id: str

class GoodsReceiptCreate(GoodsReceiptBase):
    pass

class GoodsReceiptResponse(GoodsReceiptBase):
    id: str
    receipt_date: datetime
    status: TradeDocumentStatus
    items: List[GoodsReceiptItemResponse] = []

    class Config:
        from_attributes = True

# --- Sales Schemas ---

class SalesOrderItemBase(BaseModel):
    product_id: str
    qty_ordered: Decimal = Field(..., max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(..., max_digits=15, decimal_places=2)

class SalesOrderItemCreate(SalesOrderItemBase):
    pass

class SalesOrderItemResponse(SalesOrderItemBase):
    id: str
    so_id: str
    qty_delivered: Decimal

    class Config:
        from_attributes = True

class SalesOrderBase(BaseModel):
    so_number: str
    customer_id: str
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None

class SalesOrderCreate(SalesOrderBase):
    pass

class SalesOrderResponse(SalesOrderBase):
    id: str
    order_date: datetime
    status: TradeOrderStatus
    items: List[SalesOrderItemResponse] = []

    class Config:
        from_attributes = True

class DeliveryOrderItemBase(BaseModel):
    product_id: str
    so_item_id: Optional[str] = None
    qty_delivered: Decimal = Field(..., max_digits=10, decimal_places=2)

class DeliveryOrderItemCreate(DeliveryOrderItemBase):
    pass

class DeliveryOrderItemResponse(DeliveryOrderItemBase):
    id: str
    do_id: str

    class Config:
        from_attributes = True

class DeliveryOrderBase(BaseModel):
    do_number: str
    so_id: Optional[str] = None
    customer_id: str
    warehouse_id: str

class DeliveryOrderCreate(DeliveryOrderBase):
    pass

class DeliveryOrderResponse(DeliveryOrderBase):
    id: str
    delivery_date: datetime
    status: TradeDocumentStatus
    items: List[DeliveryOrderItemResponse] = []

    class Config:
        from_attributes = True
