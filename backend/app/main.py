import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.sqlite_client import init_db, get_db_connection, reset_database
from app.api.v1 import api_v1_router
from app.ingestion.bulk_parser import BulkDataParser
from app.ingestion.elliptic_parser import EllipticDataParser, ELLIPTIC_DIR
from app.engine.clustering import EntityClusterEngine
from app.engine.alert_generator import generate_investigative_alerts

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Air-gapped offline forensic monitoring system for Bitcoin P2P telemetry and blockchain traffic.",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def on_startup():
    """Initialize SQLite schemas on launch."""
    init_db()


@app.get("/", tags=["System Status"])
def root() -> Dict[str, Any]:
    """Root status endpoint."""
    return {
        "system": settings.PROJECT_NAME,
        "version": "2.0.0",
        "mode": "STRICT_OFFLINE_AIRGAP",
        "database_connected": settings.DB_PATH.exists(),
        "endpoints": {
            "docs": "/docs",
            "ranked_alerts": f"{settings.API_V1_STR}/alerts/ranked",
            "graph_topology": f"{settings.API_V1_STR}/graph/topology",
            "file_ingest": f"{settings.API_V1_STR}/ingest/file",
            "run_pipeline": f"{settings.API_V1_STR}/pipeline/run"
        }
    }


@app.get("/health", tags=["System Status"])
def health_check() -> Dict[str, Any]:
    """Report SQLite health and table row counts."""
    try:
        conn = get_db_connection()
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        cluster_count = conn.execute("SELECT COUNT(DISTINCT cluster_id) FROM entity_clusters").fetchone()[0]
        alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        seed_count = conn.execute("SELECT COUNT(*) FROM illicit_seeds").fetchone()[0]
        conn.close()

        return {
            "status": "healthy",
            "storage_mode": "local_sqlite_wal",
            "record_counts": {
                "transactions": tx_count,
                "unique_entity_clusters": cluster_count,
                "investigative_alerts": alert_count,
                "watchlist_seeds": seed_count
            }
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database health check failed: {str(exc)}"
        )


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the local offline dashboard."""
    return FileResponse(Path(__file__).parent / "dashboard.html")


@app.post(f"{settings.API_V1_STR}/ingest/file", tags=["Data Ingestion"])
async def ingest_bulk_metadata_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Ingest offline CSV, JSON, or XML telemetry into SQLite."""
    filename = file.filename.lower()
    suffix = Path(filename).suffix

    if suffix not in (".csv", ".json", ".xml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Accepted formats are .csv, .json, and .xml."
        )

    parser = BulkDataParser()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_path = Path(tmp_file.name)
        shutil.copyfileobj(file.file, tmp_file)

    try:
        records = parser.parse_file(str(tmp_path))
        ingested_count = parser.ingest_to_db(records)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return {
        "status": "success",
        "file_processed": file.filename,
        "format": suffix.replace(".", "").upper(),
        "transactions_ingested": ingested_count,
        "records_rejected": len(parser.rejected_records)
    }


@app.post(f"{settings.API_V1_STR}/ingest/elliptic", tags=["Data Ingestion"])
def ingest_elliptic_dataset(
    data_dir: str | None = None,
    limit: int | None = None,
) -> Dict[str, Any]:
    """Ingest the Elliptic Bitcoin dataset into the forensic engine."""
    parser = EllipticDataParser(data_dir or ELLIPTIC_DIR)
    try:
        ingested, gt_count = parser.parse_and_ingest(limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return {
        "status": "success",
        "source": "elliptic",
        "data_dir": str(parser.data_dir),
        "transactions_ingested": ingested,
        "ground_truth_labels": gt_count,
        "records_rejected": len(parser.rejected_records),
    }


@app.post(f"{settings.API_V1_STR}/pipeline/run", tags=["Pipeline Execution"])
def execute_offline_pipeline() -> Dict[str, Any]:
    """Run clustering and alert generation on ingested data."""
    try:
        cluster_engine = EntityClusterEngine()
        clusters = cluster_engine.run_clustering()
        alerts = generate_investigative_alerts()

        return {
            "status": "completed",
            "clusters_identified": len(clusters),
            "alerts_generated": len(alerts)
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution encountered an error: {str(exc)}"
        )


@app.post(f"{settings.API_V1_STR}/system/reset", tags=["System Maintenance"])
def purge_database() -> Dict[str, str]:
    """Purge transactions, clusters, and alerts."""
    reset_database()
    return {"status": "success", "message": "Analytical database purged successfully."}
