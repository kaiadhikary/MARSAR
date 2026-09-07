"""
Unified parsing interface maintaining compatibility across legacy and offline pipelines.
Routes dataset files into the BulkDataParser.
"""

from typing import List, Dict, Any
from pathlib import Path
from app.ingestion.bulk_parser import BulkDataParser


class TransactionParser:
    def __init__(self):
        self._parser = BulkDataParser()

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".csv":
            return self._parser.parse_csv(str(path))
        elif ext == ".json":
            return self._parser.parse_json(str(path))
        elif ext == ".xml":
            return self._parser.parse_xml(str(path))
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Expected CSV, JSON, or XML.")

    def parse_and_commit(self, file_path: str) -> int:
        records = self.parse_file(file_path)
        return self._parser.ingest_to_db(records)