"""
Pydantic schemas for request / response validation.

Every data boundary in the application is typed through these models,
which keeps the API contract explicit and self-documenting.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class AlertSource(str, enum.Enum):
    DATADOG = "datadog"
    GRAFANA = "grafana"
    NEW_RELIC = "new_relic"
    PROMETHEUS = "prometheus"
    CLOUDWATCH = "cloudwatch"
    CUSTOM = "custom"


class LogLevel(str, enum.Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    service: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4096)
    trace_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Alert(BaseModel):
    id: str
    source: AlertSource
    title: str = Field(..., min_length=1, max_length=512)
    severity: Severity
    triggered_at: datetime
    service: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    tags: list[str] = Field(default_factory=list)


class MetricDatapoint(BaseModel):
    timestamp: datetime
    value: float
    metric_name: str
    service: str
    unit: str = ""


class ServiceHealth(BaseModel):
    name: str
    status: str  # healthy, degraded, down
    latency_p99_ms: float
    error_rate_percent: float
    request_rate_rpm: float
    uptime_percent: float


class Incident(BaseModel):
    id: str
    title: str = Field(..., min_length=1, max_length=512)
    severity: Severity
    status: IncidentStatus
    started_at: datetime
    updated_at: datetime
    services_affected: list[str]
    description: str = Field(default="")
    alerts: list[Alert] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    timestamp: datetime
    event: str
    source: str
    severity: Severity = Severity.INFO


# Forward-ref resolution (Incident references TimelineEvent)
Incident.model_rebuild()


# ---------------------------------------------------------------------------
# AI Analysis models
# ---------------------------------------------------------------------------

class RootCause(BaseModel):
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    category: str  # e.g. "infrastructure", "deployment", "dependency"
    affected_component: str
    evidence: list[str] = Field(default_factory=list)


class SuggestedFix(BaseModel):
    title: str
    description: str
    priority: str  # immediate, short_term, long_term
    risk_level: str  # low, medium, high
    commands: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    incident_id: str
    root_causes: list[RootCause]
    suggested_fixes: list[SuggestedFix]
    similar_incidents: list[str] = Field(default_factory=list)
    analysis_summary: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# API request / response wrappers
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=64)
    include_logs: bool = True
    include_metrics: bool = True
    custom_context: str = Field(default="", max_length=2048)

    @field_validator("incident_id")
    @classmethod
    def sanitize_incident_id(cls, v: str) -> str:
        """Prevent injection via incident IDs."""
        cleaned = v.strip()
        if not cleaned.replace("-", "").replace("_", "").isalnum():
            raise ValueError("incident_id must be alphanumeric (hyphens/underscores allowed)")
        return cleaned


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4096)


class ChatRequest(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=64)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)

    @field_validator("incident_id")
    @classmethod
    def sanitize_incident_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.replace("-", "").replace("_", "").isalnum():
            raise ValueError("incident_id must be alphanumeric (hyphens/underscores allowed)")
        return cleaned


class DashboardSummary(BaseModel):
    total_incidents: int
    active_incidents: int
    mttr_minutes: float  # mean time to resolve
    services_monitored: int
    services_healthy: int
    services_degraded: int
    services_down: int
    alert_count_24h: int
    top_severity: Severity
