from app.database import engine, Base
from app.db_models import ProductionRun, ProductionInput, ProductionOutput

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
