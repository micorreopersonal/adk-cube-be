from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
import uuid

# --- CUBE QUERY ---

class ComparisonConfig(BaseModel):
    type: Literal["TIME_PERIOD", "DIMENSION_VALUE"] = Field(..., description="Tipo de comparativa")
    baseline: Dict[str, Union[str, int]] = Field(..., description="Contexto base (ej: {'anio': 2024})")

class FilterCondition(BaseModel):
    dimension: str
    operator: Literal["EQ", "NEQ", "GT", "LT", "IN", "NOT_IN"] = "EQ"
    value: Union[str, int, List[str], List[int]]

class CubeQuery(BaseModel):
    metrics: List[str] = Field(default=[], description="Métricas del Registry (ej: ['tasa_rotacion'])")
    dimensions: List[str] = Field(default=[], description="Dimensiones de agrupación")
    filters: List[FilterCondition] = Field(default=[], description="Lista de filtros explícitos")
    comparison: Optional[ComparisonConfig] = None

# --- METADATA ---

class RequestMetadata(BaseModel):
    requested_viz: Literal["KPI_ROW", "LINE_CHART", "BAR_CHART", "TABLE", "SMART_AUTO"] = "SMART_AUTO"
    title_suggestion: Optional[str] = None

# --- MASTER INPUT PAYLOAD ---

class SemanticRequest(BaseModel):
    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: Literal["COMPARISON", "TREND", "SNAPSHOT", "LISTING"]
    cube_query: CubeQuery
    metadata: RequestMetadata = Field(default_factory=RequestMetadata)
