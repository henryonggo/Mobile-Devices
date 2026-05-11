from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.core import (
    ImportDryRunRequest, ImportDryRunResponse, ImportRowResult,
    ImportCommitRequest, ImportCommitResponse,
    ProductCreate, WarehouseCreate, PartnerCreate
)
from ..services.google_sheets import GoogleSheetsMockService
from ..db_models import Product, Warehouse, Partner, StockLedger, InventoryBalance, RefType, User
from ..services.auth_utils import get_current_user
from pydantic import ValidationError
from datetime import datetime

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

def map_data(raw_data: dict, mapping: dict) -> dict:
    if not mapping:
        # Default lowercasing mapping
        return {k.lower().replace(" ", "_"): v for k, v in raw_data.items()}
    return {mapping.get(k, k.lower().replace(" ", "_")): v for k, v in raw_data.items()}

@router.post("/dry-run", response_model=ImportDryRunResponse)
def import_dry_run(request: ImportDryRunRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raw_data_list = GoogleSheetsMockService.fetch_data(request.sheet_url)

    results = []
    valid_count = 0
    invalid_count = 0

    for idx, raw_row in enumerate(raw_data_list):
        mapped_row = map_data(raw_row, request.mapping or {})
        errors = []
        is_valid = True

        try:
            if request.entity_type == "product":
                ProductCreate(**mapped_row)
                if db.query(Product).filter(Product.sku == mapped_row.get("sku")).first():
                    errors.append(f"SKU '{mapped_row.get('sku')}' already exists in database.")
                    is_valid = False
            elif request.entity_type == "warehouse":
                WarehouseCreate(**mapped_row)
                if db.query(Warehouse).filter(Warehouse.code == mapped_row.get("code")).first():
                    errors.append(f"Warehouse Code '{mapped_row.get('code')}' already exists in database.")
                    is_valid = False
            elif request.entity_type == "partner":
                PartnerCreate(**mapped_row)
                if db.query(Partner).filter(Partner.code == mapped_row.get("code")).first():
                     errors.append(f"Partner Code '{mapped_row.get('code')}' already exists in database.")
                     is_valid = False
            elif request.entity_type == "opening_stock":
                sku = mapped_row.get("sku")
                wh_code = mapped_row.get("warehouse_code")
                qty = mapped_row.get("quantity")

                prod = db.query(Product).filter(Product.sku == sku).first()
                if not prod:
                    errors.append(f"SKU '{sku}' not found.")
                    is_valid = False

                wh = db.query(Warehouse).filter(Warehouse.code == wh_code).first()
                if not wh:
                    errors.append(f"Warehouse '{wh_code}' not found.")
                    is_valid = False

                try:
                    float(qty)
                except (ValueError, TypeError):
                    errors.append("Quantity must be a number.")
                    is_valid = False
            else:
                 raise HTTPException(status_code=400, detail="Unknown entity type")
        except ValidationError as e:
            for err in e.errors():
                errors.append(f"{err['loc'][0]}: {err['msg']}")
            is_valid = False

        results.append(ImportRowResult(
            row_index=idx + 1,
            data=mapped_row,
            is_valid=is_valid,
            errors=errors
        ))

        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

    return ImportDryRunResponse(
        valid_rows_count=valid_count,
        invalid_rows_count=invalid_count,
        rows=results
    )

@router.post("/commit", response_model=ImportCommitResponse)
def import_commit(request: ImportCommitRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    committed = 0
    try:
        for row in request.valid_data:
            if request.entity_type == "product":
                obj = Product(**row)
                db.add(obj)
            elif request.entity_type == "warehouse":
                 obj = Warehouse(**row)
                 db.add(obj)
            elif request.entity_type == "partner":
                 obj = Partner(**row)
                 db.add(obj)
            elif request.entity_type == "opening_stock":
                 from decimal import Decimal
                 sku = row.get("sku")
                 wh_code = row.get("warehouse_code")
                 qty = Decimal(str(row.get("quantity")))

                 prod = db.query(Product).filter(Product.sku == sku).first()
                 wh = db.query(Warehouse).filter(Warehouse.code == wh_code).first()

                 if prod and wh:
                     ledger = StockLedger(
                         transaction_date=datetime.utcnow(),
                         reference_type=RefType.opening_balance,
                         reference_id="IMPORT",
                         product_id=prod.id,
                         warehouse_id=wh.id,
                         qty_change=qty,
                         balance_after=qty # simplified for opening stock if no prior tx
                     )
                     db.add(ledger)

                     inv = db.query(InventoryBalance).filter(
                         InventoryBalance.product_id == prod.id,
                         InventoryBalance.warehouse_id == wh.id
                     ).first()

                     if inv:
                         inv.current_qty += qty
                     else:
                         inv = InventoryBalance(
                             product_id=prod.id,
                             warehouse_id=wh.id,
                             current_qty=qty
                         )
                         db.add(inv)
            committed += 1
        db.commit()
        return ImportCommitResponse(success=True, committed_count=committed)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
