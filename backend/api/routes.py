"""
API route handlers for the Sentinel AI platform.

All endpoints are grouped under /api/v1 and return JSON responses
validated through Pydantic schemas.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.models.schemas import AnalyzeRequest, ChatRequest
from backend.services import mock_data, ai_service
from backend.utils.guardrails import sanitize_text, validate_incident_id

logger = logging.getLogger("sentinel.api")

router = APIRouter(prefix="/api/v1", tags=["sentinel"])


# ---------------------------------------------------------------------------
# Dashboard & overview
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_dashboard():
    """Return aggregated dashboard metrics."""
    summary = mock_data.generate_dashboard_summary()
    return summary.model_dump()


@router.get("/services/health")
async def get_services_health():
    """Return current health status for all monitored services."""
    services = mock_data.generate_service_health()
    return [s.model_dump() for s in services]


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/incidents")
async def list_incidents():
    """Return all known incidents."""
    incidents = mock_data.get_all_incidents()
    # Return a lighter payload for the list view (exclude full logs)
    result = []
    for inc in incidents:
        data = inc.model_dump()
        data["log_count"] = len(inc.logs)
        data["alert_count"] = len(inc.alerts)
        data.pop("logs", None)
        result.append(data)
    return result


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Return full incident details including logs and alerts."""
    clean_id = validate_incident_id(incident_id)
    incident = mock_data.get_incident(clean_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@router.get("/metrics/{service}/{metric_name}")
async def get_metrics(service: str, metric_name: str):
    """Return time-series data for a specific service metric."""
    data = mock_data.generate_metrics_timeseries(service, metric_name)
    return [d.model_dump() for d in data]


# ---------------------------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def analyze_incident(request: AnalyzeRequest):
    """Run AI root cause analysis on a specific incident."""
    incident = mock_data.get_incident(request.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    custom_ctx = sanitize_text(request.custom_context) if request.custom_context else ""
    result = await ai_service.analyze_incident(incident, custom_ctx)
    return result.model_dump()


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Conversational AI interface for incident investigation."""
    incident = mock_data.get_incident(request.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Sanitize user messages
    for msg in request.messages:
        msg.content = sanitize_text(msg.content)

    response_text = await ai_service.chat_about_incident(incident, request.messages)
    return {"role": "assistant", "content": response_text}
