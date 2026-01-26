from typing import List, Dict, Any, Optional

class ResponseBuilder:
    def __init__(self):
        self.content: List[Dict[str, Any]] = []

    def add_text(self, text: str):
        """Adds a text block (Markdown supported)."""
        self.content.append({
            "type": "text",
            "payload": text
        })
        return self

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

    def to_dict(self) -> Dict[str, Any]:
        """Returns the full VisualDataPackage structure."""
        return {
            "response_type": "visual_package",
            "content": self.content
        }
