from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from ..database import get_db
from ..db_models import (
    ProductionRun, ProductionInput, ProductionOutput, ProductionRunStatus,
    InventoryBalance, StockLedger, RefType, User
)
from ..schemas.production import (
    ProductionRunCreate, ProductionRunResponse,
    ProductionInputCreate, ProductionInputResponse,
    ProductionOutputCreate, ProductionOutputResponse
)
from ..services.auth_utils import get_current_user

router = APIRouter(prefix="/api/v1/production", tags=["production"])

@router.post("", response_model=ProductionRunResponse)
def create_production_run(run: ProductionRunCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_run = ProductionRun(**run.model_dump())
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run

@router.post("/{run_id}/inputs", response_model=ProductionInputResponse)
def add_production_input(run_id: str, input_data: ProductionInputCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Production Run not found")
    if db_run.status != ProductionRunStatus.draft:
        raise HTTPException(status_code=400, detail="Cannot add inputs to a non-draft run")

    db_input = ProductionInput(run_id=run_id, **input_data.model_dump())
    db.add(db_input)
    db.commit()
    db.refresh(db_input)
    return db_input

@router.post("/{run_id}/outputs", response_model=ProductionOutputResponse)
def add_production_output(run_id: str, output_data: ProductionOutputCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Production Run not found")
    if db_run.status != ProductionRunStatus.draft:
        raise HTTPException(status_code=400, detail="Cannot add outputs to a non-draft run")

    db_output = ProductionOutput(run_id=run_id, **output_data.model_dump())
    db.add(db_output)
    db.commit()
    db.refresh(db_output)
    return db_output

@router.post("/{run_id}/commit", response_model=ProductionRunResponse)
def commit_production_run(run_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Production Run not found")
    if db_run.status != ProductionRunStatus.draft:
        raise HTTPException(status_code=400, detail="Run is already completed")

    total_input_cost = Decimal(0)
    now = datetime.utcnow()

    try:
        # Process Inputs
        for inp in db_run.inputs:
            inv = db.query(InventoryBalance).filter(
                InventoryBalance.product_id == inp.product_id,
                InventoryBalance.warehouse_id == inp.warehouse_id
            ).first()

            if not inv or inv.current_qty < inp.qty:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product {inp.product_id} in warehouse {inp.warehouse_id}")

            # Calculate cost based on MAC
            inp_cost = inp.qty * inv.current_mac
            inp.total_cost = inp_cost
            total_input_cost += inp_cost

            # Deduct inventory
            inv.current_qty -= inp.qty

            # Write ledger
            ledger_out = StockLedger(
                transaction_date=now,
                reference_type=RefType.production_out,
                reference_id=db_run.id,
                product_id=inp.product_id,
                warehouse_id=inp.warehouse_id,
                qty_change=-inp.qty,
                balance_after=inv.current_qty
            )
            db.add(ledger_out)

        # Process Outputs (Cost allocation Option A: sum of percentages must equal 100)
        total_allocation = sum([out.cost_allocation_percent for out in db_run.outputs])
        if total_allocation != Decimal(100) and len(db_run.outputs) > 0:
            raise HTTPException(status_code=400, detail="Output cost allocation percentages must sum to 100")

        for out in db_run.outputs:
            allocated_cost = total_input_cost * (out.cost_allocation_percent / Decimal(100))
            out.total_cost = allocated_cost

            inv = db.query(InventoryBalance).filter(
                InventoryBalance.product_id == out.product_id,
                InventoryBalance.warehouse_id == out.warehouse_id
            ).first()

            new_qty = out.qty
            if inv:
                # Update MAC
                total_value_existing = inv.current_qty * inv.current_mac
                new_total_value = total_value_existing + allocated_cost
                new_total_qty = inv.current_qty + out.qty
                if new_total_qty > 0:
                    inv.current_mac = new_total_value / new_total_qty
                inv.current_qty = new_total_qty
            else:
                new_mac = allocated_cost / out.qty if out.qty > 0 else 0
                inv = InventoryBalance(
                    product_id=out.product_id,
                    warehouse_id=out.warehouse_id,
                    current_qty=out.qty,
                    current_mac=new_mac
                )
                db.add(inv)

            # Write ledger
            ledger_in = StockLedger(
                transaction_date=now,
                reference_type=RefType.production_in,
                reference_id=db_run.id,
                product_id=out.product_id,
                warehouse_id=out.warehouse_id,
                qty_change=out.qty,
                balance_after=inv.current_qty if inv.current_qty else out.qty
            )
            db.add(ledger_in)

        db_run.status = ProductionRunStatus.completed
        db.commit()
        db.refresh(db_run)
        return db_run

    except Exception as e:
        db.rollback()
        raise e
