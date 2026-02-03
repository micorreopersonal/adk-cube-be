from typing import List, Dict, Any, Optional, Union
from app.schemas.payloads import (
    VisualDataPackage, ContentBlock,
    TextBlock, KPIBlock, KPIItem,
    ChartBlock, ChartPayload, Dataset, ChartMetadata,
    TableBlock, TablePayload, DebugBlock
)

class ResponseBuilder:
    """
    Builder para construir respuestas estandarizadas 'VisualDataPackage' (Nexus v2.0).
    Asegura que las respuestas legacy se adapten al nuevo contrato único.
    """
    def __init__(self):
        self.content: List[ContentBlock] = []

    def add_text(self, text: str, variant: str = "standard", severity: str = "info"):
        """Adds a text block."""
        block = TextBlock(
            type="text",
            payload=text,
            variant=variant,
            severity=severity
        )
        self.content.append(block)
        return self

    def add_insight_alert(self, text: str, severity: str = "critical"):
        """Short-hand for adding an Executive Insight."""
        return self.add_text(text, variant="insight", severity=severity)

    def add_kpi_row(self, kpis: List[Dict[str, Any]]):
        """Adds a row of KPI cards (Nexus Standard)."""
        items = []
        for k in kpis:
            # Mapeo de Color Legacy a Status Nexus
            color = k.get("color")
            status = "NEUTRAL"
            if color == "red": status = "CRITICAL"
            elif color == "orange": status = "NEGATIVE"
            elif color == "green": status = "POSITIVE"
            
            items.append(KPIItem(
                label=k.get("label", "N/A"),
                value=str(k.get("value", "0")),
                delta=k.get("delta"),
                status=status,
                tooltip=k.get("tooltip")
            ))
            
        block = KPIBlock(type="KPI_ROW", payload=items)
        self.content.append(block)
        return self

    def add_chart(self, title: str, labels: List[str], datasets: List[Dict[str, Any]], subtype: str = "LINE"):
        """Adds a Chart block (Nexus Standard)."""
        ds_objects = []
        for ds in datasets:
            ds_objects.append(Dataset(
                label=ds.get("label", "Serie"),
                data=ds.get("data", [])
            ))
            
        block = ChartBlock(
            type="CHART",
            subtype=subtype.upper(),
            payload=ChartPayload(labels=labels, datasets=ds_objects),
            metadata=ChartMetadata(title=title)
        )
        self.content.append(block)
        return self

    def add_table(self, headers: List[str], rows: List[List[Any]]):
        """Adds a Table block (Nexus Standard)."""
        block = TableBlock(
            type="TABLE",
            payload=TablePayload(headers=headers, rows=rows)
        )
        self.content.append(block)
        return self

    def add_debug_sql(self, query: str):
        """Adds a SQL debug block."""
        block = DebugBlock(type="debug_sql", payload=query)
        self.content.append(block)
        return self

    def to_dict(self, summary: str = "Análisis Finalizado") -> Dict[str, Any]:
        """Finaliza y retorna el paquete validado."""
        package = VisualDataPackage(
            response_type="visual_package",
            summary=summary,
            content=self.content
        )
        return package.model_dump()

    # --- LEGACY COMPATIBILITY METHODS ---
    
    def add_plot(self, title: str, x: List[Any], y: List[Any], subtype: str = "bar", **kwargs):
        """Legacy wrapper for add_chart."""
        return self.add_chart(
            title=title, 
            labels=[str(i) for i in x], 
            datasets=[{"label": "Valor", "data": y}],
            subtype="BAR" if subtype == "bar" else "LINE"
        )

    def add_data_series(self, data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Legacy wrapper for add_chart."""
        title = metadata.get("title", "Análisis") if metadata else "Análisis"
        labels = data.get("index", []) # Asunción legacy
        if not labels and len(data) > 0:
            labels = next(iter(data.values())) # Si no hay index, probar con primera serie
            
        datasets = []
        for k, v in data.items():
            if k == "index": continue
            datasets.append({"label": k, "data": v})
            
        return self.add_chart(title=title, labels=[str(l) for l in labels], datasets=datasets)
