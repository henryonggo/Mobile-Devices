from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from ..db_models import ProductType, WarehouseType, PartnerType

# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    sku: str
    name: str
    type: ProductType
    uom: str
    current_mac: Decimal = Field(default=0, max_digits=15, decimal_places=2)
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str

    class Config:
        from_attributes = True

# Warehouse Schemas
class WarehouseBase(BaseModel):
    code: str
    name: str
    type: WarehouseType

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseResponse(WarehouseBase):
    id: str

    class Config:
        from_attributes = True

# Partner Schemas
class PartnerBase(BaseModel):
    code: str
    name: str
    type: PartnerType
    phone: Optional[str] = None
    address: Optional[str] = None

class PartnerCreate(PartnerBase):
    pass

class PartnerResponse(PartnerBase):
    id: str

    class Config:
        from_attributes = True

# Import Schemas
class ImportDryRunRequest(BaseModel):
    sheet_url: str
    entity_type: str  # 'product', 'warehouse', 'partner', 'opening_stock'
    mapping: Optional[Dict[str, str]] = None # Maps sheet column name to DB field name

class ImportRowResult(BaseModel):
    row_index: int
    data: Dict[str, Any]
    is_valid: bool
    errors: List[str] = []

class ImportDryRunResponse(BaseModel):
    valid_rows_count: int
    invalid_rows_count: int
    rows: List[ImportRowResult]

class ImportCommitRequest(BaseModel):
    entity_type: str
    valid_data: List[Dict[str, Any]]

class ImportCommitResponse(BaseModel):
    success: bool
    committed_count: int
