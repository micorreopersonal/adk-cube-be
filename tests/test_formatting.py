import pytest
import pandas as pd
from datetime import datetime
from app.core.utils.formatting import format_dataframe_for_export

def test_format_dataframe_dates():
    """Verify datetime columns are formatted as YYYY-MM-DD strings."""
    df = pd.DataFrame([
        {
            "id": 1,
            "date_col": datetime(2025, 12, 31, 23, 59, 59),
            "text_col": "foo"
        },
        {
            "id": 2,
            "date_col": datetime(2026, 1, 1, 0, 0, 0),
            "text_col": "bar"
        }
    ])
    
    formatted = format_dataframe_for_export(df)
    
    assert len(formatted) == 2
    assert formatted[0]["date_col"] == "2025-12-31"
    assert formatted[1]["date_col"] == "2026-01-01"
    # Ensure other columns remain touched
    assert formatted[0]["text_col"] == "foo"

def test_format_dataframe_masking():
    """Verify sensitive columns are masked."""
    df = pd.DataFrame([
        {
            "nombre": "Juan",
            "dni": "12345678",
            "sueldo": 5000.00
        }
    ])
    
    formatted = format_dataframe_for_export(df)
    
    # dni should be masked (assuming mask_document_id returns *** or similar)
    # We don't check exact mask implementation, just that it changed or is masked
    assert formatted[0]["dni"] != "12345678"
    assert "123" not in formatted[0]["dni"] # Assuming mask hides prefixes
    
    # sueldo should be masked
    assert formatted[0]["sueldo"] != 5000.00

def test_format_empty_dataframe():
    """Verify handling of empty dataframes."""
    df = pd.DataFrame()
    formatted = format_dataframe_for_export(df)
    assert formatted == []
