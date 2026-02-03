from typing import List, Dict, Any, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field

# --- NEXUS v2.0 ATOMIC BLOCKS ---

# 1. TEXT BLOCK (Essential for Chat)
class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    payload: str
    variant: str = "standard"  # 'standard', 'insight', 'quote'
    severity: str = "info"    # 'info', 'warning', 'critical'

# 2. KPI ROW BLOCK (Nexus Standard)
class KPIItem(BaseModel):
    label: str
    value: Union[str, float, int]
    delta: Optional[str] = None
    status: Literal["NEUTRAL", "POSITIVE", "NEGATIVE", "CRITICAL"] = "NEUTRAL"
    tooltip: Optional[str] = None

class KPIBlock(BaseModel):
    type: Literal["KPI_ROW"] = "KPI_ROW"
    payload: List[KPIItem]

# 3. CHART BLOCK (Nexus Standard)
class Dataset(BaseModel):
    label: str
    data: List[Union[float, int, None]]
    borderColor: Optional[str] = None
    backgroundColor: Optional[str] = None

class ChartPayload(BaseModel):
    labels: List[str] = Field(..., description="Eje X (Categorías)")
    datasets: List[Dataset]

class ChartMetadata(BaseModel):
    title: str
    y_axis_label: Optional[str] = None
    show_legend: bool = True

class ChartBlock(BaseModel):
    type: Literal["CHART"] = "CHART"
    subtype: Literal["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"] = "LINE"
    payload: ChartPayload
    metadata: ChartMetadata

# 4. TABLE BLOCK (Nexus Standard)
class TablePayload(BaseModel):
    headers: List[str]
    rows: List[List[Any]]

class TableBlock(BaseModel):
    type: Literal["TABLE"] = "TABLE"
    payload: TablePayload

# 5. DEBUG BLOCKS
class DebugBlock(BaseModel):
    type: Literal["debug_sql", "debug_json"]
    payload: Any

# --- MASTER OUTPUT PAYLOAD ---

# Union para el discriminador
VisualBlock = Annotated[
    Union[TextBlock, KPIBlock, ChartBlock, TableBlock, DebugBlock], 
    Field(discriminator='type')
]

class VisualDataPackage(BaseModel):
    response_type: Literal["visual_package", "error"] = "visual_package"
    summary: str = "Resumen del análisis"
    content: List[VisualBlock]

# --- LEGACY ALIASES (Backward Compatibility for ResponseBuilder) ---
ContentBlock = VisualBlock
KPIRowBlock = KPIBlock
KPICard = KPIItem
DataSeriesBlock = ChartBlock # Mapeivo preventivo
DataSeriesMetadata = ChartMetadata
TableBlockV1 = TableBlock    # TableBlock ya existe en v2
PlotBlock = ChartBlock       # Mapeo preventivo
PlotMetadata = ChartMetadata
DebugSQLBlock = DebugBlock
DebugJSONBlock = DebugBlock
