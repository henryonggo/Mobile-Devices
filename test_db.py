from app.database import engine, Base
from app.db_models import PurchaseOrder, GoodsReceipt, SalesOrder, DeliveryOrder

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
