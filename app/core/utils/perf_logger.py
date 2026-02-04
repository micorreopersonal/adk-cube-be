from typing import Any, Dict
import json
import time
import os
from datetime import datetime
from pathlib import Path

# Definir ruta de logs
LOG_DIR = Path(".agent/logs")
LOG_FILE = LOG_DIR / "performance.jsonl"

class PerformanceLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceLogger, cls).__new__(cls)
            cls._instance._ensure_log_dir()
        return cls._instance

    def _ensure_log_dir(self):
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, tool_name: str, duration: float, metadata: Dict[str, Any] = None):
        """
        Registra una entrada de rendimiento.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "duration_seconds": round(duration, 4),
            "metadata": metadata or {}
        }
        
        # Write to JSONL (Append mode)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        # Optional: Keep printing to stdout for dev visibility
        print(f"⏱️ [PERF_SAVED] {tool_name}: {duration:.4f}s")

_perf_logger = PerformanceLogger()

def log_perf(tool_name: str, duration: float, metadata: Dict[str, Any] = None):
    _perf_logger.log(tool_name, duration, metadata)
