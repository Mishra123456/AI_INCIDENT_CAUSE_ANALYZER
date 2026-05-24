"""
Realistic mock data generator for demonstration purposes.

Produces synthetic but believable incidents, logs, alerts, and metrics
that mimic a production microservices environment on Kubernetes.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from backend.models.schemas import (
    Alert, AlertSource, DashboardSummary, Incident, IncidentStatus,
    LogEntry, LogLevel, MetricDatapoint, Severity, ServiceHealth, TimelineEvent,
)

SERVICES = [
    "api-gateway", "auth-service", "user-service", "payment-service",
    "order-service", "inventory-service", "notification-service",
    "search-service", "cache-layer", "message-queue",
    "postgres-primary", "postgres-replica", "redis-cluster", "cdn-edge",
]

_INCIDENT_TEMPLATES = [
    {
        "title": "Payment Service — High Error Rate & Timeout Cascade",
        "severity": Severity.CRITICAL,
        "services": ["payment-service", "api-gateway", "order-service"],
        "category": "dependency",
        "description": (
            "Stripe webhook endpoint returning 503s. Payment confirmations "
            "backing up in the message queue, causing order-service timeouts."
        ),
    },
    {
        "title": "Database Connection Pool Exhaustion — Postgres Primary",
        "severity": Severity.CRITICAL,
        "services": ["postgres-primary", "user-service", "auth-service", "order-service"],
        "category": "infrastructure",
        "description": (
            "Active connections hit 200-connection ceiling. New queries queuing, "
            "p99 latency above 12s. Auth and user services returning 500s."
        ),
    },
    {
        "title": "Redis Cluster — Memory Pressure & Eviction Storm",
        "severity": Severity.HIGH,
        "services": ["redis-cluster", "cache-layer", "search-service"],
        "category": "infrastructure",
        "description": (
            "Redis node exceeded maxmemory. Cache-miss ratio jumped from 2% "
            "to 68%, overloading search-service backend."
        ),
    },
    {
        "title": "Kubernetes Node NotReady — Zone us-east-1b",
        "severity": Severity.HIGH,
        "services": ["api-gateway", "notification-service", "inventory-service"],
        "category": "infrastructure",
        "description": (
            "Two k8s nodes entered NotReady after kernel OOM kills. Pods stuck "
            "in Pending due to resource constraints."
        ),
    },
    {
        "title": "Auth Service — JWT Validation Failures Spike",
        "severity": Severity.HIGH,
        "services": ["auth-service", "api-gateway", "user-service"],
        "category": "deployment",
        "description": (
            "After JWKS rotation, 40%% of requests failing JWT signature "
            "validation. Users being logged out."
        ),
    },
    {
        "title": "Message Queue — Consumer Lag Exceeding 500k Messages",
        "severity": Severity.MEDIUM,
        "services": ["message-queue", "notification-service", "order-service"],
        "category": "infrastructure",
        "description": (
            "Kafka consumer group lag growing for 45 minutes. Notifications "
            "delayed by 20+ minutes."
        ),
    },
]

_ERROR_MSGS = [
    "Connection refused: downstream unreachable",
    "Timeout after 30000ms waiting for response",
    "Circuit breaker OPEN — failing fast",
    "Health check failed: HTTP 503",
    "OOM kill detected in container",
    "Retry budget exhausted (5/5 attempts)",
    "Connection pool exhausted",
    "Rate limit exceeded (429)",
    "DNS resolution failed for upstream",
    "Deadlock detected on table 'orders'",
]

_WARN_MSGS = [
    "Response time degraded: p99 > 2000ms",
    "Retry attempt 3/5 for downstream call",
    "Connection pool utilization at 85%",
    "GC pause exceeded 500ms",
    "Slow query detected: 4200ms",
    "Disk usage at 82% on /data",
]

_INFO_MSGS = [
    "Deployment v2.14.3 rolling update started",
    "Health check passed — service nominal",
    "Auto-scaling triggered: 3 → 5 replicas",
    "Cache invalidation completed",
    "Config reload initiated",
]

_incident_cache: dict[str, Incident] = {}


def _gen_logs(services: list[str], start: datetime, count: int = 35) -> list[LogEntry]:
    trace_id = f"trace-{uuid.uuid4().hex[:12]}"
    entries: list[LogEntry] = []
    for _ in range(count):
        ts = start + timedelta(seconds=random.randint(0, 3600))
        svc = random.choice(services)
        roll = random.random()
        if roll < 0.40:
            level, msg = LogLevel.ERROR, random.choice(_ERROR_MSGS)
        elif roll < 0.70:
            level, msg = LogLevel.WARN, random.choice(_WARN_MSGS)
        elif roll < 0.90:
            level, msg = LogLevel.INFO, random.choice(_INFO_MSGS)
        else:
            level, msg = LogLevel.DEBUG, f"Processing batch #{random.randint(1000, 9999)}"
        entries.append(LogEntry(
            timestamp=ts, level=level, service=svc,
            message=f"[{svc}] {msg}",
            trace_id=trace_id if random.random() > 0.3 else None,
            metadata={"host": f"ip-10-0-{random.randint(1,4)}-{random.randint(10,250)}"},
        ))
    entries.sort(key=lambda e: e.timestamp)
    return entries


def _gen_alerts(tmpl: dict, start: datetime) -> list[Alert]:
    titles = [
        f"High error rate on {tmpl['services'][0]}",
        f"Latency SLA breach — {tmpl['services'][0]} p99 > 5s",
        f"CPU > 90% on {random.choice(tmpl['services'])}",
        f"Memory critical on {random.choice(tmpl['services'])}",
    ]
    alerts = []
    for i, title in enumerate(titles):
        svc = tmpl["services"][i % len(tmpl["services"])]
        alerts.append(Alert(
            id=f"alert-{uuid.uuid4().hex[:8]}",
            source=random.choice(list(AlertSource)),
            title=title, severity=tmpl["severity"] if i < 2 else Severity.HIGH,
            triggered_at=start + timedelta(minutes=random.randint(0, 15)),
            service=svc,
            metric_name=random.choice(["error_rate", "latency_p99", "cpu_percent"]),
            metric_value=round(random.uniform(80, 99), 2),
            threshold=round(random.uniform(50, 80), 2),
            tags=[tmpl["category"], svc],
        ))
    return alerts


def _gen_timeline(start: datetime, services: list[str]) -> list[TimelineEvent]:
    raw = [
        ("Anomaly detected in error rate metrics", "prometheus", Severity.INFO),
        (f"Alert fired: high error rate on {services[0]}", "datadog", Severity.HIGH),
        ("On-call engineer paged via PagerDuty", "pagerduty", Severity.HIGH),
        (f"Investigating {services[0]}", "engineer", Severity.INFO),
        (f"Correlated alert: latency spike on {services[-1]}", "grafana", Severity.MEDIUM),
        ("Root cause identified by Sentinel AI", "sentinel-ai", Severity.INFO),
        ("Mitigation applied: rolling back to v2.14.2", "engineer", Severity.INFO),
        ("Error rate declining — monitoring", "prometheus", Severity.INFO),
    ]
    timeline = []
    for i, (evt, src, sev) in enumerate(raw):
        ts = start + timedelta(minutes=i * random.randint(2, 8))
        timeline.append(TimelineEvent(timestamp=ts, event=evt, source=src, severity=sev))
    return timeline


def generate_incidents(count: int = 5) -> list[Incident]:
    if _incident_cache:
        return list(_incident_cache.values())[:count]
    now = datetime.now(timezone.utc)
    templates = random.sample(_INCIDENT_TEMPLATES, min(count, len(_INCIDENT_TEMPLATES)))
    statuses = [IncidentStatus.ACTIVE, IncidentStatus.INVESTIGATING,
                IncidentStatus.MITIGATED, IncidentStatus.RESOLVED]
    for i, tmpl in enumerate(templates):
        started = now - timedelta(hours=random.randint(1, 48))
        inc_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{str(i+1).zfill(3)}"
        status = statuses[i % len(statuses)]
        _incident_cache[inc_id] = Incident(
            id=inc_id, title=tmpl["title"], severity=tmpl["severity"],
            status=status, started_at=started,
            updated_at=now - timedelta(minutes=random.randint(5, 120)),
            services_affected=tmpl["services"], description=tmpl["description"],
            alerts=_gen_alerts(tmpl, started),
            logs=_gen_logs(tmpl["services"], started),
            timeline=_gen_timeline(started, tmpl["services"]),
        )
    return list(_incident_cache.values())


def get_incident(incident_id: str) -> Incident | None:
    if not _incident_cache:
        generate_incidents()
    return _incident_cache.get(incident_id)


def get_all_incidents() -> list[Incident]:
    if not _incident_cache:
        generate_incidents()
    return list(_incident_cache.values())


def generate_service_health() -> list[ServiceHealth]:
    result = []
    for svc in SERVICES:
        roll = random.random()
        if roll < 0.15:
            st, lat, err = "down", random.uniform(8000, 30000), random.uniform(40, 100)
        elif roll < 0.35:
            st, lat, err = "degraded", random.uniform(2000, 8000), random.uniform(5, 40)
        else:
            st, lat, err = "healthy", random.uniform(10, 500), random.uniform(0, 2)
        result.append(ServiceHealth(
            name=svc, status=st, latency_p99_ms=round(lat, 1),
            error_rate_percent=round(err, 2),
            request_rate_rpm=round(random.uniform(100, 15000)),
            uptime_percent=round(random.uniform(95, 100) if st != "down" else random.uniform(70, 95), 2),
        ))
    return result


def generate_metrics_timeseries(service: str, metric: str = "error_rate", pts: int = 60) -> list[MetricDatapoint]:
    now = datetime.now(timezone.utc)
    data = []
    spike_s, spike_e = pts // 3, pts // 3 + pts // 4
    for i in range(pts):
        ts = now - timedelta(minutes=(pts - i))
        val = random.uniform(60, 95) if spike_s <= i <= spike_e else random.uniform(0.5, 8)
        data.append(MetricDatapoint(
            timestamp=ts, value=round(val, 2), metric_name=metric,
            service=service, unit="percent" if "rate" in metric else "ms",
        ))
    return data


def generate_dashboard_summary() -> DashboardSummary:
    incidents = get_all_incidents()
    services = generate_service_health()
    active = sum(1 for i in incidents if i.status in (IncidentStatus.ACTIVE, IncidentStatus.INVESTIGATING))
    top = Severity.LOW
    for inc in incidents:
        if inc.severity == Severity.CRITICAL:
            top = Severity.CRITICAL
            break
        if inc.severity == Severity.HIGH:
            top = Severity.HIGH
    return DashboardSummary(
        total_incidents=len(incidents), active_incidents=active,
        mttr_minutes=round(random.uniform(15, 120), 1),
        services_monitored=len(SERVICES),
        services_healthy=sum(1 for s in services if s.status == "healthy"),
        services_degraded=sum(1 for s in services if s.status == "degraded"),
        services_down=sum(1 for s in services if s.status == "down"),
        alert_count_24h=sum(len(i.alerts) for i in incidents),
        top_severity=top,
    )
