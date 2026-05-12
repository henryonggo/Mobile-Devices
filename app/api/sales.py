from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from ..database import get_db
from ..db_models import (
    SalesOrder, SalesOrderItem, DeliveryOrder, DeliveryOrderItem,
    TradeOrderStatus, TradeDocumentStatus, InventoryBalance, StockLedger, RefType, User
)
from ..schemas.trade import (
    SalesOrderCreate, SalesOrderResponse,
    SalesOrderItemCreate, SalesOrderItemResponse,
    DeliveryOrderCreate, DeliveryOrderResponse,
    DeliveryOrderItemCreate, DeliveryOrderItemResponse
)
from ..services.auth_utils import get_current_user

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])

# --- Sales Orders ---

@router.post("/sales-orders", response_model=SalesOrderResponse)
def create_sales_order(so: SalesOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_so = SalesOrder(**so.model_dump())
    db.add(db_so)
    db.commit()
    db.refresh(db_so)
    return db_so

@router.post("/sales-orders/{so_id}/items", response_model=SalesOrderItemResponse)
def add_so_item(so_id: str, item: SalesOrderItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not db_so:
        raise HTTPException(status_code=404, detail="Sales Order not found")
    if db_so.status != TradeOrderStatus.draft:
        raise HTTPException(status_code=400, detail="Can only add items to draft SOs")

    db_item = SalesOrderItem(so_id=so_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Delivery Orders ---

@router.post("/delivery-orders", response_model=DeliveryOrderResponse)
def create_delivery_order(do: DeliveryOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_do = DeliveryOrder(**do.model_dump())
    db.add(db_do)
    db.commit()
    db.refresh(db_do)
    return db_do

@router.post("/delivery-orders/{do_id}/items", response_model=DeliveryOrderItemResponse)
def add_do_item(do_id: str, item: DeliveryOrderItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).first()
    if not db_do:
        raise HTTPException(status_code=404, detail="Delivery Order not found")
    if db_do.status != TradeDocumentStatus.draft:
        raise HTTPException(status_code=400, detail="Can only add items to draft DOs")

    db_item = DeliveryOrderItem(do_id=do_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.post("/delivery-orders/{do_id}/commit", response_model=DeliveryOrderResponse)
def commit_delivery_order(do_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).first()
    if not db_do:
        raise HTTPException(status_code=404, detail="Delivery Order not found")
    if db_do.status != TradeDocumentStatus.draft:
        raise HTTPException(status_code=400, detail="Delivery Order is already committed")

    now = datetime.utcnow()

    try:
        for item in db_do.items:
            # 1. Deduct Inventory Balance
            inv = db.query(InventoryBalance).filter(
                InventoryBalance.product_id == item.product_id,
                InventoryBalance.warehouse_id == db_do.warehouse_id
            ).first()

            if not inv or inv.current_qty < item.qty_delivered:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product {item.product_id} in warehouse {db_do.warehouse_id}")

            inv.current_qty -= item.qty_delivered

            # 2. Write Stock Ledger
            ledger = StockLedger(
                transaction_date=now,
                reference_type=RefType.delivery_order,
                reference_id=db_do.id,
                product_id=item.product_id,
                warehouse_id=db_do.warehouse_id,
                qty_change=-item.qty_delivered,
                balance_after=inv.current_qty
            )
            db.add(ledger)

            # 3. Update SO Item if linked
            if item.so_item_id:
                so_item = db.query(SalesOrderItem).filter(SalesOrderItem.id == item.so_item_id).first()
                if so_item:
                    so_item.qty_delivered += item.qty_delivered

        db_do.status = TradeDocumentStatus.committed

        # If SO is linked, potentially update its status
        if db_do.so_id:
            so = db.query(SalesOrder).filter(SalesOrder.id == db_do.so_id).first()
            if so and so.status == TradeOrderStatus.draft:
                 so.status = TradeOrderStatus.open

        db.commit()
        db.refresh(db_do)
        return db_do
    except Exception as e:
        db.rollback()
        raise e
