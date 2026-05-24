"""
AI analysis service powered by Google Gemini.

Handles root cause analysis, incident investigation chat, and
fix suggestions. Includes prompt engineering, input sanitization,
and graceful fallback when the API key is unavailable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from backend.config import settings
from backend.models.schemas import (
    AnalysisResult, ChatMessage, Incident, LogLevel, RootCause, SuggestedFix,
)

logger = logging.getLogger("sentinel.ai")

_client = None


def _get_client():
    """Lazy-init the Gemini client so import never crashes."""
    global _client
    if _client is not None:
        return _client
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return _client
    except Exception as exc:
        logger.warning("Failed to initialize Gemini client: %s", exc)
        return None


# ---- system prompts -------------------------------------------------------

_RCA_SYSTEM = """You are Sentinel AI, an expert Site Reliability Engineering assistant.
You analyze production incidents and identify root causes with precision.

Given incident data (title, description, alerts, logs, affected services),
you must respond with a JSON object containing:
{
  "root_causes": [
    {
      "summary": "...",
      "confidence": 0.0-1.0,
      "category": "infrastructure|deployment|dependency|configuration|code_bug",
      "affected_component": "...",
      "evidence": ["log line or metric that supports this"]
    }
  ],
  "suggested_fixes": [
    {
      "title": "...",
      "description": "...",
      "priority": "immediate|short_term|long_term",
      "risk_level": "low|medium|high",
      "commands": ["optional shell commands"]
    }
  ],
  "analysis_summary": "2-3 paragraph executive summary"
}

Rules:
- Provide 1-3 root causes ranked by confidence.
- Provide 2-4 suggested fixes with concrete steps.
- Be specific. Reference actual service names, log patterns, and metrics.
- Think like a senior SRE who has debugged hundreds of outages.
- ONLY output valid JSON, nothing else."""

_CHAT_SYSTEM = """You are Sentinel AI, an expert SRE assistant helping an engineer investigate a production incident in real-time.

Current Incident Context:
{context}

Guidelines:
- Be concise, precise, and actionable.
- Reference specific services, log patterns, metrics, and alert data.
- Suggest concrete debugging steps and commands.
- If you identify a likely root cause, explain your reasoning clearly.
- Use SRE terminology naturally (SLO, SLI, error budget, blast radius, etc).
- Format responses with markdown for readability."""


def _build_incident_context(incident: Incident) -> str:
    """Serialize incident data into a compact text block for the LLM."""
    log_sample = []
    for entry in incident.logs[:20]:
        log_sample.append(
            f"  [{entry.level.value}] {entry.timestamp.isoformat()} "
            f"{entry.service}: {entry.message}"
        )

    alert_lines = []
    for a in incident.alerts:
        alert_lines.append(
            f"  [{a.severity.value}] {a.title} (source: {a.source.value}, "
            f"metric: {a.metric_name}={a.metric_value}, threshold: {a.threshold})"
        )

    timeline_lines = []
    for t in incident.timeline:
        timeline_lines.append(
            f"  {t.timestamp.isoformat()} [{t.source}] {t.event}"
        )

    return (
        f"Incident: {incident.id}\n"
        f"Title: {incident.title}\n"
        f"Severity: {incident.severity.value}\n"
        f"Status: {incident.status.value}\n"
        f"Services Affected: {', '.join(incident.services_affected)}\n"
        f"Description: {incident.description}\n\n"
        f"Alerts:\n" + "\n".join(alert_lines) + "\n\n"
        f"Recent Logs:\n" + "\n".join(log_sample) + "\n\n"
        f"Timeline:\n" + "\n".join(timeline_lines)
    )


def _parse_rca_response(raw: str, incident_id: str) -> AnalysisResult:
    """Best-effort parse of the LLM JSON response."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: wrap raw text as a single root cause
        return AnalysisResult(
            incident_id=incident_id,
            root_causes=[RootCause(
                summary=raw[:500], confidence=0.5,
                category="unknown", affected_component="unknown",
                evidence=["AI response was not structured JSON"],
            )],
            suggested_fixes=[SuggestedFix(
                title="Review AI analysis manually",
                description=raw[:1000], priority="immediate",
                risk_level="low",
            )],
            analysis_summary=raw[:1500],
            generated_at=datetime.now(timezone.utc),
        )

    root_causes = []
    for rc in data.get("root_causes", []):
        root_causes.append(RootCause(
            summary=rc.get("summary", ""),
            confidence=min(1.0, max(0.0, float(rc.get("confidence", 0.5)))),
            category=rc.get("category", "unknown"),
            affected_component=rc.get("affected_component", "unknown"),
            evidence=rc.get("evidence", []),
        ))

    fixes = []
    for fx in data.get("suggested_fixes", []):
        fixes.append(SuggestedFix(
            title=fx.get("title", ""),
            description=fx.get("description", ""),
            priority=fx.get("priority", "short_term"),
            risk_level=fx.get("risk_level", "medium"),
            commands=fx.get("commands", []),
        ))

    return AnalysisResult(
        incident_id=incident_id,
        root_causes=root_causes,
        suggested_fixes=fixes,
        analysis_summary=data.get("analysis_summary", ""),
        generated_at=datetime.now(timezone.utc),
    )


# ---- public interface -----------------------------------------------------

async def analyze_incident(incident: Incident, custom_context: str = "") -> AnalysisResult:
    """Run AI-powered root cause analysis on an incident."""
    client = _get_client()
    context = _build_incident_context(incident)
    if custom_context:
        context += f"\n\nAdditional Context from Engineer:\n{custom_context}"

    if client is None:
        logger.info("Gemini unavailable — returning heuristic analysis")
        return _heuristic_analysis(incident)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": _RCA_SYSTEM + "\n\n" + context}]},
            ],
        )
        return _parse_rca_response(response.text, incident.id)
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        return _heuristic_analysis(incident)


async def chat_about_incident(
    incident: Incident,
    messages: list[ChatMessage],
) -> str:
    """Conversational AI assistant for incident investigation."""
    client = _get_client()
    context = _build_incident_context(incident)
    system = _CHAT_SYSTEM.format(context=context)

    if client is None:
        return (
            "⚠️ AI service is unavailable (no API key configured). "
            "Please set GEMINI_API_KEY in your .env file to enable "
            "conversational incident analysis."
        )

    try:
        contents = [{"role": "user", "parts": [{"text": system}]}]
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
        )
        return response.text
    except Exception as exc:
        logger.error("Chat API call failed: %s", exc)
        err_msg = str(exc).lower()
        if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
            return "⚠️ Google Gemini API quota exceeded. You have hit the rate limit for this API key. Please try again later or use a different key."
        if "api key" in err_msg or "400" in err_msg or "expired" in err_msg:
            return "⚠️ The provided API Key is expired or invalid. Please check the GOOGLE_API_KEY in your .env file."
        return f"❌ Analysis temporarily unavailable: {type(exc).__name__}"


def _heuristic_analysis(incident: Incident) -> AnalysisResult:
    """Fallback rule-based analysis when AI is unavailable."""
    error_logs = [l for l in incident.logs if l.level in (LogLevel.ERROR, LogLevel.FATAL)]

    evidence = [e.message for e in error_logs[:5]]

    category = "infrastructure"
    if any("deploy" in a.title.lower() for a in incident.alerts):
        category = "deployment"
    elif any("timeout" in l.message.lower() for l in error_logs):
        category = "dependency"

    return AnalysisResult(
        incident_id=incident.id,
        root_causes=[RootCause(
            summary=f"Elevated error rate detected across {', '.join(incident.services_affected)}. "
                    f"Pattern suggests {category} issue based on {len(error_logs)} error log entries.",
            confidence=0.6, category=category,
            affected_component=incident.services_affected[0] if incident.services_affected else "unknown",
            evidence=evidence,
        )],
        suggested_fixes=[
            SuggestedFix(
                title="Check recent deployments",
                description="Review the deployment history for the affected services in the last 2 hours.",
                priority="immediate", risk_level="low",
            ),
            SuggestedFix(
                title="Review resource utilization",
                description="Check CPU, memory, and connection pool metrics for the affected services.",
                priority="immediate", risk_level="low",
                commands=["kubectl top pods -n production", "kubectl describe nodes"],
            ),
        ],
        analysis_summary=(
            f"Heuristic analysis identified {len(error_logs)} error-level log entries "
            f"across {len(incident.services_affected)} services. The failure pattern "
            f"is consistent with a {category} issue. AI-powered deep analysis requires "
            f"a valid GEMINI_API_KEY."
        ),
        generated_at=datetime.now(timezone.utc),
    )
