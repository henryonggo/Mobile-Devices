from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from ..database import get_db
from ..db_models import (
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    TradeOrderStatus, TradeDocumentStatus, InventoryBalance, StockLedger, RefType, User
)
from ..schemas.trade import (
    PurchaseOrderCreate, PurchaseOrderResponse,
    PurchaseOrderItemCreate, PurchaseOrderItemResponse,
    GoodsReceiptCreate, GoodsReceiptResponse,
    GoodsReceiptItemCreate, GoodsReceiptItemResponse
)
from ..services.auth_utils import get_current_user

router = APIRouter(prefix="/api/v1/purchasing", tags=["purchasing"])

# --- Purchase Orders ---

@router.post("/purchase-orders", response_model=PurchaseOrderResponse)
def create_purchase_order(po: PurchaseOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_po = PurchaseOrder(**po.model_dump())
    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    return db_po

@router.post("/purchase-orders/{po_id}/items", response_model=PurchaseOrderItemResponse)
def add_po_item(po_id: str, item: PurchaseOrderItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if db_po.status != TradeOrderStatus.draft:
        raise HTTPException(status_code=400, detail="Can only add items to draft POs")

    db_item = PurchaseOrderItem(po_id=po_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Goods Receipts ---

@router.post("/goods-receipts", response_model=GoodsReceiptResponse)
def create_goods_receipt(gr: GoodsReceiptCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_gr = GoodsReceipt(**gr.model_dump())
    db.add(db_gr)
    db.commit()
    db.refresh(db_gr)
    return db_gr

@router.post("/goods-receipts/{gr_id}/items", response_model=GoodsReceiptItemResponse)
def add_gr_item(gr_id: str, item: GoodsReceiptItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_gr = db.query(GoodsReceipt).filter(GoodsReceipt.id == gr_id).first()
    if not db_gr:
        raise HTTPException(status_code=404, detail="Goods Receipt not found")
    if db_gr.status != TradeDocumentStatus.draft:
        raise HTTPException(status_code=400, detail="Can only add items to draft GRs")

    db_item = GoodsReceiptItem(gr_id=gr_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.post("/goods-receipts/{gr_id}/commit", response_model=GoodsReceiptResponse)
def commit_goods_receipt(gr_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_gr = db.query(GoodsReceipt).filter(GoodsReceipt.id == gr_id).first()
    if not db_gr:
        raise HTTPException(status_code=404, detail="Goods Receipt not found")
    if db_gr.status != TradeDocumentStatus.draft:
        raise HTTPException(status_code=400, detail="Goods Receipt is already committed")

    now = datetime.utcnow()

    try:
        for item in db_gr.items:
            # 1. Update PO Item if linked
            if item.po_item_id:
                po_item = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.id == item.po_item_id).first()
                if po_item:
                    po_item.qty_received += item.qty_received

            # 2. Update Inventory Balance & MAC
            inv = db.query(InventoryBalance).filter(
                InventoryBalance.product_id == item.product_id,
                InventoryBalance.warehouse_id == db_gr.warehouse_id
            ).first()

            incoming_value = item.qty_received * item.unit_price

            if inv:
                total_existing_value = inv.current_qty * inv.current_mac
                new_total_value = total_existing_value + incoming_value
                new_total_qty = inv.current_qty + item.qty_received

                if new_total_qty > 0:
                    inv.current_mac = new_total_value / new_total_qty
                inv.current_qty = new_total_qty
            else:
                inv = InventoryBalance(
                    product_id=item.product_id,
                    warehouse_id=db_gr.warehouse_id,
                    current_qty=item.qty_received,
                    current_mac=item.unit_price
                )
                db.add(inv)

            # 3. Write Stock Ledger
            ledger = StockLedger(
                transaction_date=now,
                reference_type=RefType.goods_receipt,
                reference_id=db_gr.id,
                product_id=item.product_id,
                warehouse_id=db_gr.warehouse_id,
                qty_change=item.qty_received,
                balance_after=inv.current_qty
            )
            db.add(ledger)

        db_gr.status = TradeDocumentStatus.committed

        # If PO is fully received, we could update its status here. For MVP, we leave it to manual update or keep it simple.
        if db_gr.po_id:
            po = db.query(PurchaseOrder).filter(PurchaseOrder.id == db_gr.po_id).first()
            if po and po.status == TradeOrderStatus.draft:
                 po.status = TradeOrderStatus.open # automatically open it if it was draft

        db.commit()
        db.refresh(db_gr)
        return db_gr
    except Exception as e:
        db.rollback()
        raise e
