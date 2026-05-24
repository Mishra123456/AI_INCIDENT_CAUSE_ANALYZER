/**
 * Sentinel AI — Frontend Application
 * SPA controller handling navigation, data fetching, rendering, and AI interactions.
 */

(function () {
    "use strict";

    // ---- State ----
    const state = {
        currentView: "dashboard",
        incidents: [],
        dashboard: null,
        services: [],
        selectedIncident: null,
        analysisResult: null,
        chatHistory: [],
        isAnalyzing: false,
        isChatting: false,
    };

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);
    const contentArea = () => $("#content-area");

    // ---- API helpers ----
    async function api(path, opts = {}) {
        const resp = await fetch(`/api/v1${path}`, {
            headers: { "Content-Type": "application/json" },
            ...opts,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || "Request failed");
        }
        return resp.json();
    }

    // ---- Clock ----
    function updateClock() {
        const el = $("#topbar-clock");
        if (el) {
            const now = new Date();
            el.textContent = now.toLocaleTimeString("en-US", { hour12: false }) +
                " UTC" + (now.getTimezoneOffset() > 0 ? "-" : "+") +
                String(Math.abs(now.getTimezoneOffset() / 60)).padStart(2, "0");
        }
    }

    // ---- Navigation ----
    function initNav() {
        $$(".nav-item").forEach((btn) => {
            btn.addEventListener("click", () => {
                const view = btn.dataset.view;
                navigateTo(view);
            });
        });
    }

    function navigateTo(view, data) {
        state.currentView = view;
        $$(".nav-item").forEach((b) => b.classList.remove("active"));
        const activeBtn = $(`[data-view="${view}"]`);
        if (activeBtn) activeBtn.classList.add("active");

        const titles = {
            dashboard: "Dashboard",
            incidents: "Incidents",
            services: "Service Health",
            analysis: "Investigations",
            incident_detail: "Incident Detail",
        };
        $("#page-title").textContent = titles[view] || "Dashboard";

        if (data) state.selectedIncident = data;

        renderView(view);
    }

    // ---- Rendering ----
    async function renderView(view) {
        const area = contentArea();
        area.innerHTML = '<div class="loading-screen"><div class="loader-ring"></div><p>Loading...</p></div>';

        try {
            switch (view) {
                case "dashboard": await renderDashboard(area); break;
                case "incidents": await renderIncidents(area); break;
                case "services": await renderServices(area); break;
                case "analysis": await renderAnalysis(area); break;
                case "incident_detail": renderIncidentDetail(area); break;
            }
        } catch (err) {
            area.innerHTML = `<div class="loading-screen"><p style="color:var(--severity-critical)">Error: ${esc(err.message)}</p></div>`;
        }
    }

    // ---- Dashboard ----
    async function renderDashboard(area) {
        const [dash, incidents, services] = await Promise.all([
            api("/dashboard"),
            api("/incidents"),
            api("/services/health"),
        ]);
        state.dashboard = dash;
        state.incidents = incidents;
        state.services = services;

        area.innerHTML = `
            <div class="dashboard-grid">
                ${statCard(dash.active_incidents, "Active Incidents", dash.active_incidents > 0)}
                ${statCard(dash.total_incidents, "Total Incidents")}
                ${statCard(dash.mttr_minutes.toFixed(0) + "m", "MTTR")}
                ${statCard(dash.alert_count_24h, "Alerts (24h)")}
            </div>
            <div class="dashboard-grid">
                ${statCard(dash.services_monitored, "Services Monitored")}
                ${statCard(dash.services_healthy, "Healthy", false, "healthy")}
                ${statCard(dash.services_degraded, "Degraded", false, "degraded")}
                ${statCard(dash.services_down, "Down", dash.services_down > 0, "down")}
            </div>
            <div class="content-grid" style="margin-top:20px">
                <div class="card">
                    <div class="card-header"><span class="card-title">Recent Incidents</span></div>
                    <div class="incident-list">${incidents.slice(0, 5).map(incidentRowSmall).join("")}</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Service Status</span></div>
                    <div style="display:flex;flex-direction:column;gap:6px">
                        ${services.slice(0, 8).map(serviceRowSmall).join("")}
                    </div>
                </div>
            </div>
            <div class="content-grid content-grid--full" style="margin-top:16px">
                <div class="card">
                    <div class="card-header"><span class="card-title">Error Rate — Last 60 Minutes</span></div>
                    <div class="chart-area"><canvas id="error-chart" class="chart-canvas"></canvas></div>
                </div>
            </div>`;

        bindIncidentClicks();
        drawChart();
    }

    function statCard(value, label, critical, colorType) {
        let cls = "";
        if (critical) cls = "critical";
        let dotHtml = "";
        if (colorType === "healthy") dotHtml = '<span style="color:var(--status-healthy)">●</span> ';
        if (colorType === "degraded") dotHtml = '<span style="color:var(--status-degraded)">●</span> ';
        if (colorType === "down") dotHtml = '<span style="color:var(--status-down)">●</span> ';
        return `<div class="card stat-card">
            <div class="stat-value ${cls}">${dotHtml}${value}</div>
            <div class="stat-label">${label}</div>
        </div>`;
    }

    function incidentRowSmall(inc) {
        return `<div class="incident-row" data-id="${esc(inc.id)}">
            <span class="incident-id">${esc(inc.id)}</span>
            <span class="incident-title">${esc(inc.title)}</span>
            <span class="badge badge--${inc.severity}">${inc.severity}</span>
            <span class="badge badge--${inc.status}">${inc.status}</span>
            <span class="incident-time">${timeAgo(inc.started_at)}</span>
        </div>`;
    }

    function serviceRowSmall(svc) {
        const dotColor = svc.status === "healthy" ? "var(--status-healthy)" :
            svc.status === "degraded" ? "var(--status-degraded)" : "var(--status-down)";
        return `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
            <span style="display:flex;align-items:center;gap:8px">
                <span style="width:8px;height:8px;border-radius:50%;background:${dotColor};display:inline-block"></span>
                <span style="font-size:0.85rem">${esc(svc.name)}</span>
            </span>
            <span style="font-family:var(--font-mono);font-size:0.78rem;color:var(--text-muted)">
                ${svc.latency_p99_ms.toFixed(0)}ms / ${svc.error_rate_percent.toFixed(1)}% err
            </span>
        </div>`;
    }

    // ---- Incidents View ----
    async function renderIncidents(area) {
        const incidents = await api("/incidents");
        state.incidents = incidents;

        area.innerHTML = `
            <div class="card" style="margin-bottom:20px">
                <div class="card-header">
                    <span class="card-title">All Incidents (${incidents.length})</span>
                </div>
                <div class="incident-list">
                    ${incidents.map(incidentRowSmall).join("")}
                </div>
            </div>`;
        bindIncidentClicks();
    }

    // ---- Incident Detail ----
    async function renderIncidentDetail(area) {
        const inc = state.selectedIncident;
        if (!inc) { navigateTo("incidents"); return; }

        // Fetch full detail if we only have summary
        let detail = inc;
        if (!inc.logs || inc.logs.length === 0) {
            try { detail = await api(`/incidents/${inc.id}`); } catch (e) { /* use what we have */ }
        }
        state.selectedIncident = detail;

        area.innerHTML = `
            <button class="back-btn" id="back-to-incidents">← Back to Incidents</button>
            <div class="incident-detail-header">
                <h2>${esc(detail.title)}</h2>
                <div class="incident-meta">
                    <span class="meta-item"><strong>ID:</strong> ${esc(detail.id)}</span>
                    <span class="badge badge--${detail.severity}">${detail.severity}</span>
                    <span class="badge badge--${detail.status}">${detail.status}</span>
                    <span class="meta-item">Started: ${formatDate(detail.started_at)}</span>
                </div>
                <p style="margin-top:12px;color:var(--text-secondary);font-size:0.9rem">${esc(detail.description)}</p>
            </div>
            <div style="margin-bottom:16px">
                <button class="analyze-btn" id="analyze-btn" data-id="${esc(detail.id)}">
                    ⚡ Run Root Cause Analysis
                </button>
            </div>
            <div id="analysis-container"></div>
            <div class="content-grid" style="margin-top:20px">
                <div class="card">
                    <div class="card-header"><span class="card-title">Timeline</span></div>
                    <div class="timeline">${(detail.timeline || []).map(renderTimelineItem).join("")}</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Alerts (${(detail.alerts || []).length})</span></div>
                    ${(detail.alerts || []).map(renderAlert).join("")}
                </div>
            </div>
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">Logs (${(detail.logs || []).length} entries)</span></div>
                <div class="log-viewer">${(detail.logs || []).map(renderLogEntry).join("")}</div>
            </div>`;

        $("#back-to-incidents").addEventListener("click", () => navigateTo("incidents"));
        $("#analyze-btn").addEventListener("click", () => runAnalysis(detail.id));
    }

    function renderTimelineItem(t) {
        const sevClass = t.severity === "critical" ? "critical" : t.severity === "high" ? "high" : t.severity === "medium" ? "medium" : "";
        return `<div class="timeline-item">
            <div class="timeline-dot ${sevClass}"></div>
            <div class="timeline-time">${formatTime(t.timestamp)}</div>
            <div class="timeline-event">${esc(t.event)}</div>
            <div class="timeline-source">${esc(t.source)}</div>
        </div>`;
    }

    function renderAlert(a) {
        return `<div style="padding:8px 0;border-bottom:1px solid var(--border)">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:0.85rem;font-weight:500">${esc(a.title)}</span>
                <span class="badge badge--${a.severity}">${a.severity}</span>
            </div>
            <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">
                Source: ${esc(a.source)} · ${a.metric_name}: ${a.metric_value} (threshold: ${a.threshold})
            </div>
        </div>`;
    }

    function renderLogEntry(l) {
        return `<div class="log-entry">
            <span class="log-level ${l.level}">${l.level}</span>
            <span class="log-ts">${formatTime(l.timestamp)}</span>
            <span class="log-msg">${esc(l.message)}</span>
        </div>`;
    }

    // ---- AI Analysis ----
    async function runAnalysis(incidentId) {
        const btn = $("#analyze-btn");
        const container = $("#analysis-container");
        if (!btn || !container) return;

        btn.disabled = true;
        btn.textContent = "⏳ Analyzing...";
        state.isAnalyzing = true;

        try {
            const result = await api("/analyze", {
                method: "POST",
                body: JSON.stringify({ incident_id: incidentId }),
            });
            state.analysisResult = result;
            container.innerHTML = renderAnalysisResult(result);
            btn.textContent = "✓ Analysis Complete";
        } catch (err) {
            container.innerHTML = `<div class="card" style="border-color:var(--severity-critical)">
                <p style="color:var(--severity-critical)">Analysis failed: ${esc(err.message)}</p>
            </div>`;
            btn.textContent = "⚡ Retry Analysis";
            btn.disabled = false;
        }
        state.isAnalyzing = false;
    }

    function renderAnalysisResult(result) {
        const rcHtml = (result.root_causes || []).map((rc, i) => `
            <div class="root-cause-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <strong>Root Cause #${i + 1}: ${esc(rc.category)}</strong>
                    <span class="badge badge--info">${(rc.confidence * 100).toFixed(0)}% confidence</span>
                </div>
                <p style="margin-top:8px;font-size:0.88rem;color:var(--text-secondary)">${esc(rc.summary)}</p>
                <div class="confidence-bar"><div class="confidence-fill" style="width:${rc.confidence * 100}%"></div></div>
                <div style="margin-top:6px;font-size:0.75rem;color:var(--text-muted)">Affected: ${esc(rc.affected_component)}</div>
                ${rc.evidence.length ? `<div class="evidence-list">${rc.evidence.map(e => `<div class="evidence-item">${esc(e)}</div>`).join("")}</div>` : ""}
            </div>`).join("");

        const fixHtml = (result.suggested_fixes || []).map(fx => `
            <div class="fix-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <strong>${esc(fx.title)}</strong>
                    <span class="badge badge--${fx.priority === 'immediate' ? 'critical' : fx.priority === 'short_term' ? 'medium' : 'low'}">${fx.priority}</span>
                </div>
                <p style="margin-top:8px;font-size:0.85rem;color:var(--text-secondary)">${esc(fx.description)}</p>
                ${fx.commands.length ? `<div class="commands">${fx.commands.map(c => `<div>$ ${esc(c)}</div>`).join("")}</div>` : ""}
                <div style="margin-top:6px;font-size:0.75rem;color:var(--text-muted)">Risk: ${fx.risk_level}</div>
            </div>`).join("");

        return `
            <div class="analysis-section">
                <h3>🔍 Root Causes Identified</h3>
                ${rcHtml}
            </div>
            <div class="analysis-section">
                <h3>🛠️ Suggested Fixes</h3>
                ${fixHtml}
            </div>
            <div class="card" style="margin-top:16px;border-left:3px solid var(--accent)">
                <div class="card-header"><span class="card-title">Executive Summary</span></div>
                <p style="font-size:0.88rem;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">${esc(result.analysis_summary)}</p>
            </div>`;
    }

    // ---- Services View ----
    async function renderServices(area) {
        const services = await api("/services/health");
        state.services = services;

        area.innerHTML = `
            <div class="service-grid">
                ${services.map(svc => {
                    const dotColor = svc.status === "healthy" ? "var(--status-healthy)" :
                        svc.status === "degraded" ? "var(--status-degraded)" : "var(--status-down)";
                    return `<div class="card service-card">
                        <div class="service-name">
                            <span class="service-status-dot" style="background:${dotColor}"></span>
                            ${esc(svc.name)}
                        </div>
                        <div class="service-metric"><span class="metric-label">Status</span><span class="metric-value" style="color:${dotColor}">${svc.status}</span></div>
                        <div class="service-metric"><span class="metric-label">Latency P99</span><span class="metric-value">${svc.latency_p99_ms.toFixed(0)}ms</span></div>
                        <div class="service-metric"><span class="metric-label">Error Rate</span><span class="metric-value">${svc.error_rate_percent.toFixed(2)}%</span></div>
                        <div class="service-metric"><span class="metric-label">Req/min</span><span class="metric-value">${svc.request_rate_rpm.toFixed(0)}</span></div>
                        <div class="service-metric"><span class="metric-label">Uptime</span><span class="metric-value">${svc.uptime_percent.toFixed(2)}%</span></div>
                    </div>`;
                }).join("")}
            </div>`;
    }

    // ---- AI Analysis Chat View ----
    async function renderAnalysis(area) {
        if (!state.incidents.length) {
            try { state.incidents = await api("/incidents"); } catch (e) { /* ignore */ }
        }

        area.innerHTML = `
            <div class="card" style="margin-bottom:16px">
                <div class="card-header"><span class="card-title">Incident Investigator</span></div>
                <p style="font-size:0.88rem;color:var(--text-secondary);margin-bottom:12px">
                    Select an incident to investigate. The analyzer has full context of logs, alerts, metrics, and timeline.
                </p>
                <select class="incident-select" id="chat-incident-select">
                    <option value="">— Select Incident —</option>
                    ${state.incidents.map(i => `<option value="${esc(i.id)}">[${i.severity.toUpperCase()}] ${esc(i.id)} — ${esc(i.title)}</option>`).join("")}
                </select>
            </div>
            <div class="card chat-container" id="chat-panel" style="display:none">
                <div class="chat-messages" id="chat-messages">
                    <div class="chat-bubble assistant">
                        👋 I'm the Sentinel Investigator. Select an incident above and ask me anything — I'll analyze logs, correlate alerts, and help identify the root cause.
                    </div>
                </div>
                <div class="chat-input-area">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Ask about this incident..." maxlength="2000">
                    <button class="btn btn-primary" id="chat-send">Send</button>
                </div>
            </div>`;

        const select = $("#chat-incident-select");
        select.addEventListener("change", () => {
            const panel = $("#chat-panel");
            if (select.value) {
                panel.style.display = "flex";
                state.chatHistory = [];
            } else {
                panel.style.display = "none";
            }
        });

        const sendBtn = $("#chat-send");
        const input = $("#chat-input");
        const sendMessage = async () => {
            const msg = input.value.trim();
            const incId = select.value;
            if (!msg || !incId || state.isChatting) return;

            state.chatHistory.push({ role: "user", content: msg });
            appendChatBubble("user", msg);
            input.value = "";
            state.isChatting = true;
            sendBtn.disabled = true;

            try {
                const resp = await api("/chat", {
                    method: "POST",
                    body: JSON.stringify({
                        incident_id: incId,
                        messages: state.chatHistory,
                    }),
                });
                state.chatHistory.push({ role: "assistant", content: resp.content });
                appendChatBubble("assistant", resp.content);
            } catch (err) {
                appendChatBubble("assistant", `❌ Error: ${err.message}`);
            }
            state.isChatting = false;
            sendBtn.disabled = false;
        };

        sendBtn.addEventListener("click", sendMessage);
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
        });
    }

    function appendChatBubble(role, content) {
        const container = $("#chat-messages");
        if (!container) return;
        const div = document.createElement("div");
        div.className = `chat-bubble ${role}`;
        div.innerHTML = role === "assistant" ? formatMarkdown(content) : esc(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    // ---- Utilities ----
    function esc(str) {
        if (!str) return "";
        const d = document.createElement("div");
        d.textContent = String(str);
        return d.innerHTML;
    }

    function formatMarkdown(text) {
        if (!text) return "";
        let s = esc(text);
        // Code blocks
        s = s.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        // Inline code
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Line breaks
        s = s.replace(/\n/g, '<br>');
        return s;
    }

    function timeAgo(dateStr) {
        const diff = Date.now() - new Date(dateStr).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        return `${Math.floor(hrs / 24)}d ago`;
    }

    function formatDate(d) {
        return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    }

    function formatTime(d) {
        return new Date(d).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function bindIncidentClicks() {
        $$(".incident-row").forEach((row) => {
            row.addEventListener("click", async () => {
                const id = row.dataset.id;
                try {
                    const detail = await api(`/incidents/${id}`);
                    navigateTo("incident_detail", detail);
                } catch (e) {
                    navigateTo("incident_detail", { id, title: "Loading...", severity: "info", status: "active", started_at: new Date().toISOString(), description: "", services_affected: [], alerts: [], logs: [], timeline: [] });
                }
            });
        });
    }

    // ---- Simple Canvas Chart ----
    function drawChart() {
        const canvas = document.getElementById("error-chart");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        const w = canvas.width, h = canvas.height;
        const pad = { top: 20, right: 20, bottom: 30, left: 50 };

        // Generate data with a spike
        const pts = 60;
        const data = [];
        const spikeS = 20, spikeE = 32;
        for (let i = 0; i < pts; i++) {
            if (i >= spikeS && i <= spikeE) {
                data.push(50 + Math.random() * 45);
            } else {
                data.push(1 + Math.random() * 6);
            }
        }

        const maxVal = Math.max(...data) * 1.1;
        const xStep = (w - pad.left - pad.right) / (pts - 1);

        // Grid lines
        ctx.strokeStyle = "rgba(30,41,59,0.5)";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = pad.top + (h - pad.top - pad.bottom) * (i / 4);
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(w - pad.right, y);
            ctx.stroke();

            ctx.fillStyle = "#64748b";
            ctx.font = "11px 'JetBrains Mono'";
            ctx.textAlign = "right";
            ctx.fillText((maxVal * (1 - i / 4)).toFixed(0) + "%", pad.left - 8, y + 4);
        }

        // Area fill
        const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
        gradient.addColorStop(0, "rgba(79, 70, 229, 0.25)");
        gradient.addColorStop(1, "rgba(79, 70, 229, 0.0)");

        ctx.beginPath();
        ctx.moveTo(pad.left, h - pad.bottom);
        for (let i = 0; i < pts; i++) {
            const x = pad.left + i * xStep;
            const y = pad.top + (h - pad.top - pad.bottom) * (1 - data[i] / maxVal);
            ctx.lineTo(x, y);
        }
        ctx.lineTo(pad.left + (pts - 1) * xStep, h - pad.bottom);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // Line
        ctx.beginPath();
        for (let i = 0; i < pts; i++) {
            const x = pad.left + i * xStep;
            const y = pad.top + (h - pad.top - pad.bottom) * (1 - data[i] / maxVal);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "#4f46e5";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Spike annotation
        const spikeX = pad.left + ((spikeS + spikeE) / 2) * xStep;
        ctx.fillStyle = "rgba(239,68,68,0.8)";
        ctx.font = "bold 11px Inter";
        ctx.textAlign = "center";
        ctx.fillText("⚠ Anomaly Detected", spikeX, pad.top - 4);
    }

    // ---- Init ----
    async function init() {
        initNav();
        setInterval(updateClock, 1000);
        updateClock();
        await navigateTo("dashboard");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
