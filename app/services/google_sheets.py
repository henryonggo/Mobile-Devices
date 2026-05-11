import pandas as pd
from typing import List, Dict, Any

class GoogleSheetsMockService:
    @staticmethod
    def fetch_data(sheet_url: str) -> List[Dict[str, Any]]:
        # In a real app, this would use gspread or google-api-python-client
        # For now, we simulate fetching data from a sheet based on the URL
        if "mock-products" in sheet_url:
            return [
                {"SKU": "P-001", "Name": "Premium Beras", "Type": "milled_rice", "UOM": "KG"},
                {"SKU": "P-002", "Name": "Dedak", "Type": "byproduct", "UOM": "KG"},
                {"SKU": "P-003", "Name": "Invalid Type", "Type": "unknown", "UOM": "KG"}, # Invalid
            ]
        elif "mock-warehouses" in sheet_url:
            return [
                {"Code": "WH-A", "Name": "Main Warehouse", "Type": "mixed"},
                {"Code": "WH-B", "Name": "Raw Paddy", "Type": "raw_material"},
                {"Code": "WH-A", "Name": "Duplicate", "Type": "mixed"}, # Invalid (duplicate code)
            ]
        elif "mock-partners" in sheet_url:
            return [
                {"Code": "CUST-01", "Name": "Local Store", "Type": "customer", "Phone": "123456", "Address": "Street 1"},
                {"Code": "SUPP-01", "Name": "Farmer Joe", "Type": "supplier", "Phone": "654321", "Address": "Farm 2"},
            ]
        elif "mock-opening-stock" in sheet_url:
             return [
                {"SKU": "P-001", "Warehouse Code": "WH-A", "Quantity": "1000", "As Of Date": "2023-01-01"},
                {"SKU": "P-999", "Warehouse Code": "WH-A", "Quantity": "500", "As Of Date": "2023-01-01"}, # Invalid SKU
             ]
        else:
            return []
