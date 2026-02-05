from typing import List, Dict, Any
import pandas as pd
import json
from app.core.auth.security import mask_document_id, mask_salary
from app.core.analytics.registry import DIMENSIONS_REGISTRY

def format_dataframe_for_export(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Format a pandas DataFrame for JSON export in API responses.
    
    Processing steps:
    1. Security: Masks sensitive columns (ids, salaries).
    2. Dates: Formats datetime columns to 'YYYY-MM-DD' string (stripping time).
    3. Ratios: Detects 'ratio' types in registry (e.g. per_anual) and formats as percentage.
    4. Rounds: Rounds all other floats to 2 decimals.
    5. Serialization: Converts to list of records.
    
    Args:
        df: Input pandas DataFrame
        
    Returns:
        List of dictionaries (records) ready for JSON response
    """
    if df.empty:
        return []
        
    # Operate on a copy to avoid side effects
    df = df.copy()

    # --- SECURITY LAYER: MASKING SENSITIVE DATA ---
    sensitive_cols = {
        "codigo_persona": mask_document_id,
        "dni": mask_document_id,
        "ce": mask_document_id,
        "salary": mask_salary,
        "sueldo": mask_salary,
        "remuneracion": mask_salary
    }
    
    for col, masker in sensitive_cols.items():
        if col in df.columns:
            # Apply mask and ensure string
            df[col] = df[col].apply(lambda x: masker(str(x)) if pd.notnull(x) else x)

    # --- TYPE-BASED FORMATTING (REGISTRY + DTYPES) ---
    for col in df.columns:
        # 1. Dates: Robust detection via name substring or dtype
        # BigQuery often returns DB-Dates as objects/strings.
        is_date_col = "fecha" in col.lower() or pd.api.types.is_datetime64_any_dtype(df[col])
        
        if is_date_col:
            try:
                # Force conversion to datetime to handle strings "2025-01-01" or objects
                df[col] = pd.to_datetime(df[col], errors='ignore') 
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime('%Y-%m-%d')
            except Exception:
                pass # Keep original if conversion fails
            continue # Done with this col
            
        # 2. Registry Metadata Lookup
        # 2. Registry Metadata Lookup
        dim_def = DIMENSIONS_REGISTRY.get(col)
        semantic_type = dim_def.get("type", "") if isinstance(dim_def, dict) else ""
        
        # 3. Ratios (e.g. per_anual: 0.128 -> 12.80)
        if semantic_type == "ratio" or semantic_type == "percentage":
             # Force numeric conversion (handle strings like "0.128")
             df[col] = pd.to_numeric(df[col], errors='coerce')
             # Multiply by 100
             df[col] = df[col] * 100

        
        # 4. Global Float Rounding (2 decimals)
        # Re-check dtype after potential coercion
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(2)
            
    # Serialize to Records (List[Dict])
    # date_format="iso" is a fallback, but our explicit strftime handles the main requirement
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    
    return records
