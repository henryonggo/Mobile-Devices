from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..db_models import ProductionRunType, ProductionRunStatus

class ProductionInputBase(BaseModel):
    product_id: str
    warehouse_id: str
    qty: Decimal = Field(..., max_digits=10, decimal_places=2)

class ProductionInputCreate(ProductionInputBase):
    pass

class ProductionInputResponse(ProductionInputBase):
    id: str
    run_id: str
    total_cost: Decimal

    class Config:
        from_attributes = True

class ProductionOutputBase(BaseModel):
    product_id: str
    warehouse_id: str
    qty: Decimal = Field(..., max_digits=10, decimal_places=2)
    cost_allocation_percent: Decimal = Field(default=0, max_digits=5, decimal_places=2)

class ProductionOutputCreate(ProductionOutputBase):
    pass

class ProductionOutputResponse(ProductionOutputBase):
    id: str
    run_id: str
    total_cost: Decimal

    class Config:
        from_attributes = True

class ProductionRunBase(BaseModel):
    type: ProductionRunType
    notes: Optional[str] = None

class ProductionRunCreate(ProductionRunBase):
    pass

class ProductionRunResponse(ProductionRunBase):
    id: str
    run_date: datetime
    status: ProductionRunStatus
    inputs: List[ProductionInputResponse] = []
    outputs: List[ProductionOutputResponse] = []

    class Config:
        from_attributes = True
