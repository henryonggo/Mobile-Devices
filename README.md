# Rice Factory ERP

A focused, lightweight ERP system tailored for a rice milling and processing operation. This system centralizes operational workflows covering master data, multi-warehouse inventory, batch production (paddy-to-rice and rice-to-rice), and order fulfillment, while treating Google Sheets ingestion as a first-class citizen.

## Project Structure
- `app/` - Contains the FastAPI application code.
  - `api/` - REST API endpoints.
  - `models/` - (Unused directly) Kept for structural consistency.
  - `schemas/` - Pydantic models for request/response validation.
  - `services/` - Business logic and utility services (e.g., auth, Google Sheets).
  - `database.py` - Database connection setup.
  - `db_models.py` - SQLAlchemy ORM models.
  - `main.py` - FastAPI application entry point.
- `tests/` - Pytest test suite.

## Prerequisites
- Python 3.12+
- `pip`

## Running the Development Server

1. **Install dependencies:**
   Ensure you are in the project root directory, then run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   Use `uvicorn` to start the development server with live reloading:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Access the API Documentation:**
   Open your browser and navigate to:
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Testing
To run the test suite:
```bash
pytest
```
