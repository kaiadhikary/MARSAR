"""Section 65B Indian Evidence Act — STR (Suspicious Transaction Report) PDF export."""
from fastapi import APIRouter

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post("/export-str/{cluster_id}")
async def export_str(cluster_id: str):
    """
    Generate a Section 65B-compliant STR PDF for the given entity cluster.
    Wire this to app.reports.generator once the dossier engine is built.
    """
    return {"status": "not_implemented", "cluster_id": cluster_id}
