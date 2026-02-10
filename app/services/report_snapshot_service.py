import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import firestore

logger = logging.getLogger(__name__)

class ReportSnapshotService:
    """
    Handles persistence of partial and complete report data in Firestore.
    Collection: report_snapshots
    """
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self.db = firestore.Client(project=self.project_id)
        self.collection = self.db.collection("report_snapshots")

    def create_snapshot(self, period: str, scope: str) -> str:
        """Creates a new report entry and returns its ID."""
        report_id = str(uuid.uuid4())
        doc_ref = self.collection.document(report_id)
        doc_ref.set({
            "report_id": report_id,
            "period": period,
            "scope": scope,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "GATHERING_DATA",
            "blocks": []
        })
        return report_id

    def update_snapshot(self, report_id: str, blocks: List[Dict], status: str = "DATA_GATHERED"):
        """Updates blocks and status of a report."""
        doc_ref = self.collection.document(report_id)
        doc_ref.update({
            "blocks": blocks,
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP
        })

    def get_snapshot(self, report_id: str) -> Dict[str, Any]:
        """Retrieves the full snapshot data."""
        doc = self.collection.document(report_id).get()
        if doc.exists:
            return doc.to_dict()
        return {}

    def save_narratives(self, report_id: str, narratives: Dict[str, str]):
        """Saves generated AI narratives to the snapshot."""
        doc_ref = self.collection.document(report_id)
        doc_ref.update({
            "narratives": narratives,
            "status": "COMPLETED",
            "completed_at": firestore.SERVER_TIMESTAMP
        })
