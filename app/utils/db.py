from pathlib import Path
import json

## Relative to ROOT
DB_PATH = Path(__file__).parent.parent.parent / "purchase_orders.json"

db = None

def get_db():
    global db
    if db is None:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)

    return db.get("purchase_orders", [])
