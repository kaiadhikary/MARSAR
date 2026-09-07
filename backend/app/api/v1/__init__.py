from fastapi import APIRouter
from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.graph import router as graph_router
from app.api.v1.trace import router as trace_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(alerts_router, prefix="/alerts", tags=["Investigative Alerts"])
api_v1_router.include_router(graph_router, prefix="/graph", tags=["Entity & Link Topology"])
api_v1_router.include_router(trace_router, prefix="/trace", tags=["Transaction & Flow Tracing"])
api_v1_router.include_router(compliance_router, prefix="/compliance", tags=["Compliance & Illicit Seeds"])