
from app.schemas.payloads import TablePayload, TableBlock
from pydantic import ValidationError
import json

def test_table_schema_records():
    print("🧪 Verifying TablePayload (Records Format)...")
    
    # 1. Valid Input (List[Dict])
    valid_data = {
        "headers": ["name", "age"],
        "rows": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
    }
    
    try:
        model = TablePayload(**valid_data)
        print("✅ Correctly validated List[Dict] structure.")
    except ValidationError as e:
        print(f"❌ Failed valid input: {e}")
        exit(1)

    # 2. Block Integration
    try:
        block = TableBlock(payload=model)
        print(f"✅ Block integration successful: {block.type}")
    except ValidationError as e:
        print(f"❌ Failed block integration: {e}")
        exit(1)

    print("\nSUCCESS: Schema is robust and compatible with Records format.")

if __name__ == "__main__":
    test_table_schema_records()
