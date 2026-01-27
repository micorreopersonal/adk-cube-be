from typing import List, Dict, Any, Optional

class ResponseBuilder:
    def __init__(self):
        self.content: List[Dict[str, Any]] = []

    def add_text(self, text: str, variant: str = "standard", severity: str = "info"):
        """
        Adds a text block. 
        Variant: 'standard' or 'insight'.
        Severity (for insights): 'info', 'warning', 'critical'.
        """
        self.content.append({
            "type": "text",
            "payload": text,
            "variant": variant,
            "severity": severity
        })
        return self

    def add_insight_alert(self, text: str, severity: str = "critical"):
        """Short-hand for adding an Executive Insight."""
        return self.add_text(text, variant="insight", severity=severity)


    def add_kpi_row(self, kpis: List[Dict[str, Any]]):
        """
        Adds a row of KPI cards.
        Each KPI dict should have: 'label', 'value', and optional 'delta', 'color'.
        """
        self.content.append({
            "type": "kpi_row",
            "payload": kpis
        })
        return self

    def add_plot(self, title: str, x: List[Any], y: List[Any], subtype: str = "bar", **kwargs):
        """
        Adds a plot block (agnostic schema).
        Subtypes: 'bar', 'line', 'pie', 'histogram'.
        """
        plot_data = {
            "type": "plot",
            "subtype": subtype,
            "title": title,
            "data": {
                "x": x,
                "y": y,
                **kwargs # For extra fields like 'colors', 'names', 'values'
            }
        }
        self.content.append(plot_data)
        return self

    def add_table(self, data: List[Dict[str, Any]]):
        """Adds a data table."""
        self.content.append({
            "type": "table",
            "payload": data
        })
        return self

    def add_debug_sql(self, query: str):
        """Adds a SQL query block for debugging purposes."""
        self.content.append({
            "type": "debug_sql",
            "payload": query
        })
        return self

    def add_data_series(self, data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Adds a data series block for interactive visualizations.
        Data should contain arrays for x-axis and multiple y-axis series.
        Example: {"months": [...], "rotacion_general": [...], "rotacion_voluntaria": [...]}
        """
        block = {
            "type": "data_series",
            "payload": data
        }
        if metadata:
            block["metadata"] = metadata
        self.content.append(block)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Returns the full VisualDataPackage structure."""
        return {
            "response_type": "visual_package",
            "content": self.content
        }
