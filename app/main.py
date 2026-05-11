from fastapi import FastAPI
from .database import engine, Base
from .api import auth, master_data, imports

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rice Factory ERP API",
    description="A focused ERP API tailored for a Palembang-based rice milling operation.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(master_data.router)
app.include_router(imports.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Rice Factory ERP API"}
