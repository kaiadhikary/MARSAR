from fastapi import APIRouter
from fastapi import Depends
from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.graph import router as graph_router
from app.api.v1.trace import router as trace_router
from app.api.v1.dashboard import router as dashboard_router, public_router as dashboard_public_router
from app.core.security import require_investigator

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(alerts_router, prefix="/alerts", tags=["Investigative Alerts"], dependencies=[Depends(require_investigator)])
api_v1_router.include_router(graph_router, prefix="/graph", tags=["Entity & Link Topology"], dependencies=[Depends(require_investigator)])
api_v1_router.include_router(trace_router, prefix="/trace", tags=["Transaction & Flow Tracing"], dependencies=[Depends(require_investigator)])
api_v1_router.include_router(compliance_router, prefix="/compliance", tags=["Compliance & Illicit Seeds"], dependencies=[Depends(require_investigator)])
api_v1_router.include_router(dashboard_public_router, tags=["Dashboard Compatibility"])
api_v1_router.include_router(dashboard_router, tags=["Dashboard Compatibility"], dependencies=[Depends(require_investigator)])
