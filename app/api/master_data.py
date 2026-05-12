from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..db_models import Product, Warehouse, Partner
from ..schemas.core import (
    ProductCreate, ProductResponse,
    WarehouseCreate, WarehouseResponse,
    PartnerCreate, PartnerResponse
)
from ..services.auth_utils import get_current_user
from ..db_models import User

router = APIRouter(prefix="/api/v1", tags=["master_data"])

# --- Products ---
@router.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_product = db.query(Product).filter(Product.sku == product.sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="SKU already exists")
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/products", response_model=List[ProductResponse])
def get_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

# --- Warehouses ---
@router.post("/warehouses", response_model=WarehouseResponse)
def create_warehouse(warehouse: WarehouseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_warehouse = db.query(Warehouse).filter(Warehouse.code == warehouse.code).first()
    if db_warehouse:
        raise HTTPException(status_code=400, detail="Warehouse code already exists")
    db_warehouse = Warehouse(**warehouse.model_dump())
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse

@router.get("/warehouses", response_model=List[WarehouseResponse])
def get_warehouses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    warehouses = db.query(Warehouse).offset(skip).limit(limit).all()
    return warehouses

# --- Partners ---
@router.post("/partners", response_model=PartnerResponse)
def create_partner(partner: PartnerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_partner = db.query(Partner).filter(Partner.code == partner.code).first()
    if db_partner:
        raise HTTPException(status_code=400, detail="Partner code already exists")
    db_partner = Partner(**partner.model_dump())
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    return db_partner

@router.get("/partners", response_model=List[PartnerResponse])
def get_partners(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    partners = db.query(Partner).offset(skip).limit(limit).all()
    return partners
