/*
 * Copyright (c) 2026 Rafael Casado, Joel Candal, Diego Rodríguez, Santiago Neira
 * Licensed under the MIT License. See LICENSE file for details.
 *
 * Denodo Flick — Frontend Logic
 * HackUDC 2026 - Reto Denodo
 */

document.addEventListener("DOMContentLoaded", () => {
    // ── Theme toggle ────────────────────────────────────────
    initThemeToggle();

    checkHealth();

    // Auto-sync metadatos con "admin" al cargar
    autoSyncMetadata();

    // Discover views button
    document.getElementById("btn-discover-views")?.addEventListener("click", discoverViews);

    // Auto-discover views on page load
    discoverViews();

    // ── Escenarios ──────────────────────────────────────────
    document.querySelectorAll(".scenario-card").forEach(card => {
        card.addEventListener("click", () => {
            const scenario = card.dataset.scenario;
            showScenarioPreview(scenario);
        });
    });

    // ── Custom decision secondary link ──────────────────────────
    document.getElementById("btn-custom-link")?.addEventListener("click", () => {
        showCustomForm();
    });

    // ── Preview buttons ─────────────────────────────────────
    document.getElementById("btn-run-scenario").addEventListener("click", () => {
        const scenario = document.getElementById("btn-run-scenario").dataset.scenario;
        if (scenario) {
            const params = collectScenarioParams();
            runDecision(scenario, null, null, null, params);
        }
    });
    document.getElementById("btn-preview-back").addEventListener("click", showScenarios);

    // ── Custom form ─────────────────────────────────────────
    document.getElementById("btn-custom-run").addEventListener("click", () => {
        const question = document.getElementById("custom-question").value.trim();
        if (!question) {
            alert("Por favor, describe la decisión que necesitas tomar.");
            return;
        }

        const metaRaw = document.getElementById("custom-metadata").value.trim();
        const dataRaw = document.getElementById("custom-data").value.trim();

        const metaQs = metaRaw ? metaRaw.split("\n").filter(l => l.trim()) : null;
        const dataQs = dataRaw ? dataRaw.split("\n").filter(l => l.trim()) : null;

        runDecision("custom", question, metaQs, dataQs);
    });

    document.getElementById("btn-back").addEventListener("click", showScenarios);
    document.getElementById("btn-new")?.addEventListener("click", goBack);
    document.getElementById("btn-cancel-query")?.addEventListener("click", cancelQuery);

});


// ═══════════════════════════════════════════════════════════════
// View selector helper
// ═══════════════════════════════════════════════════════════════

function isAutoViewMode() {
    const btn = document.getElementById("btn-auto-view");
    return btn && btn.classList.contains("active");
}

function getSelectedView() {
    if (isAutoViewMode()) return null;
    const input = document.getElementById("view-select");
    return input ? input.value.trim() || null : null;
}


// ═══════════════════════════════════════════════════════════════
// Auto view toggle
// ═══════════════════════════════════════════════════════════════

function toggleAutoView() {
    const btn = document.getElementById("btn-auto-view");
    const input = document.getElementById("view-select");
    const isActive = btn.classList.toggle("active");

    if (isActive) {
        input.disabled = true;
        input.classList.add("disabled-auto");
    } else {
        input.disabled = false;
        input.classList.remove("disabled-auto");
        input.focus();
    }
}


// ═══════════════════════════════════════════════════════════════
// Dynamic view discovery
// ═══════════════════════════════════════════════════════════════

async function discoverViews() {
    const btn = document.getElementById("btn-discover-views");
    const status = document.getElementById("discover-status");
    const datalist = document.getElementById("view-options");

    btn.classList.add("loading");
    btn.textContent = "⌛";
    status.textContent = "Descubriendo...";

    try {
        const res = await fetch("/api/discover-views");
        const data = await res.json();

        if (data.status === "ok") {
            // El backend devuelve directamente la lista de vistas parseada
            const views = data.views || [];

            datalist.innerHTML = "";
            views.forEach(view => {
                const opt = document.createElement("option");
                opt.value = view;
                datalist.appendChild(opt);
            });

            status.textContent = views.length > 0 ? `${views.length} vistas encontradas` : "Sin vistas detectadas";

            // Auto-fill first view if input is empty and auto mode is off
            const input = document.getElementById("view-select");
            if (!input.value && views.length > 0 && !isAutoViewMode()) {
                input.value = views[0];
            }
        } else {
            status.textContent = data.error ? "Error al descubrir" : "Sin resultados";
        }
    } catch {
        status.textContent = "Error de conexión";
    } finally {
        btn.classList.remove("loading");
        btn.textContent = "⚡";
    }
}


// ═══════════════════════════════════════════════════════════════
// Theme toggle (light / dark)
// ═══════════════════════════════════════════════════════════════

function initThemeToggle() {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    }

    const btn = document.getElementById("theme-toggle");
    if (btn) {
        btn.addEventListener("click", () => {
            const isDark = document.documentElement.getAttribute("data-theme") === "dark";
            if (isDark) {
                document.documentElement.removeAttribute("data-theme");
                localStorage.setItem("theme", "light");
            } else {
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
            }
        });
    }
}


// ═══════════════════════════════════════════════════════════════
// Health check
// ═══════════════════════════════════════════════════════════════

async function checkHealth() {
    const badge = document.getElementById("health-status");
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (data.denodo_ai_sdk === "connected") {
            badge.className = "health-badge connected";
            badge.querySelector(".text").textContent = "Denodo AI SDK conectado";
        } else {
            badge.className = "health-badge disconnected";
            badge.querySelector(".text").textContent = "AI SDK desconectado — verifica Docker";
        }
    } catch {
        badge.className = "health-badge disconnected";
        badge.querySelector(".text").textContent = "Error de conexión";
    }
}


// ═══════════════════════════════════════════════════════════════
// Auto-sync metadata (silently on page load)
// ═══════════════════════════════════════════════════════════════

async function autoSyncMetadata() {
    try {
        await fetch(`/api/sync-metadata?database_names=admin`, { method: "POST" });
    } catch {
        // Silently ignore — health badge already shows connection status
    }
}


// ═══════════════════════════════════════════════════════════════
// Markdown rendering helper
// ═══════════════════════════════════════════════════════════════

function renderMarkdown(text) {
    if (!text) return "";
    if (typeof marked !== "undefined") {
        return marked.parse(text);
    }
    // Basic fallback
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
}


// ═══════════════════════════════════════════════════════════════
// Navigation helpers
// ═══════════════════════════════════════════════════════════════

function hideAllSections() {
    document.getElementById("scenario-section").classList.add("hidden");
    document.getElementById("preview-section").classList.add("hidden");
    document.getElementById("custom-section").classList.add("hidden");
    document.getElementById("results-section").classList.add("hidden");
}

function showCustomForm() {
    hideAllSections();
    document.getElementById("custom-section").classList.remove("hidden");
}

function showScenarios() {
    hideAllSections();
    document.getElementById("scenario-section").classList.remove("hidden");
    document.getElementById("results-content").classList.add("hidden");
    document.getElementById("loading").classList.add("hidden");
}

function showResults() {
    hideAllSections();
    document.getElementById("results-section").classList.remove("hidden");
}

function goBack() {
    if (window.InlineGames) InlineGames.cleanup();
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("results-content").classList.add("hidden");
    document.getElementById("auto-view-warning").classList.add("hidden");
    showScenarios();
}

async function showScenarioPreview(scenarioKey) {
    hideAllSections();
    document.getElementById("preview-section").classList.remove("hidden");

    // Fetch scenario details from backend
    try {
        const res = await fetch(`/api/scenarios/${scenarioKey}`);
        const data = await res.json();

        document.getElementById("preview-title").textContent = data.title;
        document.getElementById("preview-description").textContent = data.description;

        // Render parameters
        const paramsWrapper = document.getElementById("preview-params-wrapper");
        const paramsContainer = document.getElementById("preview-params");
        paramsContainer.innerHTML = "";

        const params = data.parameters || [];
        if (params.length > 0) {
            paramsWrapper.classList.remove("hidden");
            params.forEach(param => {
                const group = document.createElement("div");
                group.className = "param-group";

                const label = document.createElement("label");
                label.textContent = param.label;
                label.setAttribute("for", `param-${param.key}`);
                group.appendChild(label);

                let input;
                if (param.type === "range") {
                    const wrapper = document.createElement("div");
                    wrapper.className = "range-wrapper";

                    input = document.createElement("input");
                    input.type = "range";
                    input.min = param.min ?? 0;
                    input.max = param.max ?? 300;
                    input.step = param.step ?? 5;
                    input.value = param.default ?? Math.round((param.max ?? 300) / 2);

                    const valueLabel = document.createElement("span");
                    valueLabel.className = "range-value";
                    const unit = param.unit || "";
                    valueLabel.textContent = `${input.value} ${unit}`;

                    input.addEventListener("input", () => {
                        valueLabel.textContent = `${input.value} ${unit}`;
                    });

                    wrapper.appendChild(input);
                    wrapper.appendChild(valueLabel);

                    input.id = `param-${param.key}`;
                    input.dataset.paramKey = param.key;
                    input.dataset.unit = unit;
                    input.className = "param-input";
                    group.appendChild(wrapper);
                } else if (param.type === "select") {
                    input = document.createElement("select");
                    const defaultOpt = document.createElement("option");
                    defaultOpt.value = "";
                    defaultOpt.textContent = "Cualquiera";
                    input.appendChild(defaultOpt);
                    (param.options || []).forEach(opt => {
                        const option = document.createElement("option");
                        option.value = opt;
                        option.textContent = opt;
                        input.appendChild(option);
                    });
                    input.id = `param-${param.key}`;
                    input.dataset.paramKey = param.key;
                    input.className = "param-input";
                    group.appendChild(input);
                } else {
                    input = document.createElement("input");
                    input.type = "text";
                    input.placeholder = param.placeholder || "";
                    input.id = `param-${param.key}`;
                    input.dataset.paramKey = param.key;
                    input.className = "param-input";
                    group.appendChild(input);
                }

                paramsContainer.appendChild(group);
            });
        } else {
            paramsWrapper.classList.add("hidden");
        }

        const metaList = document.getElementById("preview-meta-questions");
        metaList.innerHTML = "";
        (data.metadata_questions || []).forEach(q => {
            const li = document.createElement("li");
            li.textContent = q;
            metaList.appendChild(li);
        });

        const dataList = document.getElementById("preview-data-questions");
        dataList.innerHTML = "";
        (data.data_questions || []).forEach(q => {
            const li = document.createElement("li");
            li.textContent = q;
            dataList.appendChild(li);
        });

        document.getElementById("btn-run-scenario").dataset.scenario = scenarioKey;
    } catch (err) {
        document.getElementById("preview-title").textContent = "Error";
        document.getElementById("preview-description").textContent = err.message;
    }
}


function collectScenarioParams() {
    const params = {};
    document.querySelectorAll("#preview-params .param-input").forEach(input => {
        const key = input.dataset.paramKey;
        if (!key) return;
        let value;
        if (input.type === "range") {
            const unit = input.dataset.unit || "";
            value = `${input.value} ${unit}`.trim();
        } else {
            value = input.value.trim();
        }
        if (value) params[key] = value;
    });
    return Object.keys(params).length > 0 ? params : null;
}


// ═══════════════════════════════════════════════════════════════
// Main decision pipeline
// ═══════════════════════════════════════════════════════════════

let _previousSection = "scenario-section";
let _activeAbortController = null;

function cancelQuery() {
    if (_activeAbortController) {
        _activeAbortController.abort();
        _activeAbortController = null;
    }
    if (window.InlineGames) InlineGames.cleanup();
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("auto-view-warning").classList.add("hidden");
    hideAllSections();
    document.getElementById(_previousSection).classList.remove("hidden");
}

async function runDecision(scenario, customQuestion = null, customMetaQs = null, customDataQs = null, params = null) {
    // Track which section was visible before so cancel can return there
    ["preview-section", "custom-section", "scenario-section"].forEach(id => {
        if (!document.getElementById(id).classList.contains("hidden")) {
            _previousSection = id;
        }
    });

    showResults();
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("results-content").classList.add("hidden");

    // Show inline-games menu while loading
    if (window.InlineGames) InlineGames.showMenu();

    // Show/hide auto-view warning (solo para decisión personalizada)
    const autoWarning = document.getElementById("auto-view-warning");
    if (scenario === "custom" && isAutoViewMode()) {
        autoWarning.classList.remove("hidden");
    } else {
        autoWarning.classList.add("hidden");
    }

    // Reset phase indicators
    const p1 = document.getElementById("phase1-status");
    const p2 = document.getElementById("phase2-status");
    const p3 = document.getElementById("phase3-status");
    [p1, p2, p3].forEach(p => { p.className = "phase-indicator"; });

    // Setup abort controller for cancellation
    _activeAbortController = new AbortController();
    const signal = _activeAbortController.signal;

    try {
        const body = {
            scenario: scenario,
        };
        if (customQuestion) body.custom_question = customQuestion;
        if (customMetaQs) body.custom_metadata_questions = customMetaQs;
        if (customDataQs) body.custom_data_questions = customDataQs;
        if (params) body.parameters = params;
        // Solo enviar use_views para decisiones personalizadas (los escenarios predefinidos tienen vista fija)
        if (scenario === "custom") {
            const useViews = getSelectedView();
            if (useViews) body.use_views = useViews;
        }

        const res = await fetch("/api/decide-stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: signal,
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const parts = buffer.split("\n\n");
            buffer = parts.pop(); // keep incomplete chunk

            for (const part of parts) {
                if (!part.trim()) continue;

                let eventType = "message";
                let eventData = null;

                for (const line of part.split("\n")) {
                    if (line.startsWith("event: ")) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith("data: ")) {
                        try {
                            eventData = JSON.parse(line.slice(6));
                        } catch { /* ignore parse errors */ }
                    }
                }

                if (!eventData) continue;

                if (eventType === "progress") {
                    // Update phase indicators
                    const phase = eventData.phase;
                    if (phase === "metadata") {
                        p1.className = "phase-indicator active";
                        p1.querySelector(".phase-text").textContent =
                            `Fase 1: Explorando metadatos (${eventData.phase_step}/${eventData.phase_total})...`;
                    } else if (phase === "data") {
                        p1.className = "phase-indicator done";
                        p2.className = "phase-indicator active";
                        p2.querySelector(".phase-text").textContent =
                            `Fase 2: Consultando datos (${eventData.phase_step}/${eventData.phase_total})...`;
                    } else if (phase === "decision") {
                        p1.className = "phase-indicator done";
                        p2.className = "phase-indicator done";
                        p3.className = "phase-indicator active";
                        p3.querySelector(".phase-text").textContent =
                            "Fase 3: Generando recomendación...";
                    }
                } else if (eventType === "complete") {
                    finalData = eventData.data;
                    // Mark all done
                    [p1, p2, p3].forEach(p => { p.className = "phase-indicator done"; });
                }
            }
        }

        // Show results
        if (finalData) {
            setTimeout(() => {
                if (window.InlineGames) InlineGames.cleanup();
                document.getElementById("loading").classList.add("hidden");
                renderResults(finalData);
                document.getElementById("results-content").classList.remove("hidden");
            }, 400);
        } else {
            if (window.InlineGames) InlineGames.cleanup();
            document.getElementById("loading").classList.add("hidden");
            document.getElementById("results-content").classList.remove("hidden");
            document.getElementById("decision-text").innerHTML = "<p>No se recibieron resultados del servidor.</p>";
        }

    } catch (err) {
        if (err.name === "AbortError") return; // User cancelled — already handled
        if (window.InlineGames) InlineGames.cleanup();
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("results-content").classList.remove("hidden");
        document.getElementById("decision-text").innerHTML = `<p>Error: ${err.message}</p>`;
        document.getElementById("phase1-results").innerHTML = "";
        document.getElementById("phase2-results").innerHTML = "";
    } finally {
        _activeAbortController = null;
        document.getElementById("auto-view-warning").classList.add("hidden");
    }
}


// ═══════════════════════════════════════════════════════════════
// Render results
// ═══════════════════════════════════════════════════════════════

function renderResults(data) {
    // Stash data for PDF/email export
    window._lastResultData = data;

    // Charts — render if statistics scenario
    const chartsSection = document.getElementById("charts-section");
    const chartsGrid = document.getElementById("charts-grid");
    chartsGrid.innerHTML = "";
    // Destroy any previous Chart.js instances
    if (window._activeCharts) {
        window._activeCharts.forEach(c => c.destroy());
    }
    window._activeCharts = [];

    if (data.scenario_key === "statistics" && data.chart_config && data.phase2_data) {
        chartsSection.classList.remove("hidden");
        renderCharts(data);
    } else {
        chartsSection.classList.add("hidden");
    }

    // Decision — render as markdown
    const decisionEl = document.getElementById("decision-text");
    decisionEl.innerHTML = renderMarkdown(data.decision || "No se pudo generar una recomendación.");

    // Phase 1
    const p1Container = document.getElementById("phase1-results");
    p1Container.innerHTML = "";
    (data.phase1_metadata || []).forEach(item => {
        p1Container.appendChild(createQABlock(item));
    });

    // Phase 2
    const p2Container = document.getElementById("phase2-results");
    p2Container.innerHTML = "";
    (data.phase2_data || []).forEach(item => {
        p2Container.appendChild(createQABlock(item));
    });

    // Errors
    const errSection = document.getElementById("errors-section");
    const errList = document.getElementById("errors-list");
    if (data.errors && data.errors.length > 0) {
        errSection.classList.remove("hidden");
        errList.innerHTML = data.errors.map(e => `<p>⚠️ ${e}</p>`).join("");
    } else {
        errSection.classList.add("hidden");
    }
}

function createQABlock(item) {
    const block = document.createElement("div");
    block.className = "qa-block";

    const q = document.createElement("div");
    q.className = "qa-question";
    q.textContent = `❓ ${item.question}`;
    block.appendChild(q);

    const a = document.createElement("div");
    if (item.error) {
        a.className = "qa-answer qa-error";
        a.textContent = `Error: ${item.error}`;
    } else {
        a.className = "qa-answer markdown-body";
        a.innerHTML = renderMarkdown(item.answer || "Sin respuesta");
    }
    block.appendChild(a);

    return block;
}


// ═══════════════════════════════════════════════════════════════
// Chart rendering (statistics scenario)
// ═══════════════════════════════════════════════════════════════

const CHART_PALETTE = [
    "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    "#e11d48", "#7c3aed", "#0ea5e9", "#d946ef", "#22c55e",
];

function parseDelimitedData(text) {
    /**
     * Parses AI SDK answer text that contains lines in "label | value" format.
     * Returns { labels: string[], values: number[] }.
     */
    const labels = [];
    const values = [];
    if (!text) return { labels, values };

    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
    for (const line of lines) {
        const clean = line.replace(/^[\-\*\d\.\)]+\s*/, "").trim();
        if (!clean.includes("|")) continue;
        const parts = clean.split("|").map(p => p.trim());
        if (parts.length < 2) continue;
        let label = parts[0];
        // Truncate long labels (comma-separated genre lists, etc.)
        if (label.length > 28) label = label.slice(0, 26) + "…";
        const numStr = parts[1].replace(/[^\d.\-]/g, "");
        const val = parseFloat(numStr);
        if (isNaN(val) || /^-+$/.test(parts[1].trim())) continue;
        labels.push(label);
        values.push(val);
    }
    return { labels, values };
}

function renderCharts(data) {
    const grid = document.getElementById("charts-grid");
    const configs = data.chart_config || [];
    const phase2 = data.phase2_data || [];

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)";
    const textColor = isDark ? "#cbd5e1" : "#475569";

    configs.forEach((cfg, i) => {
        const item = phase2[i];
        if (!item || item.error || !item.answer) return;

        const { labels, values } = parseDelimitedData(item.answer);
        if (labels.length === 0) return;

        const wrapper = document.createElement("div");
        wrapper.className = "chart-card";

        const title = document.createElement("h3");
        title.className = "chart-title";
        title.textContent = cfg.title;
        wrapper.appendChild(title);

        const canvas = document.createElement("canvas");
        wrapper.appendChild(canvas);
        grid.appendChild(wrapper);

        let chartType = cfg.type === "horizontalBar" ? "bar" : cfg.type;
        const isHorizontal = cfg.type === "horizontalBar";
        const isDoughnut = cfg.type === "doughnut";

        const colors = isDoughnut
            ? labels.map((_, j) => CHART_PALETTE[j % CHART_PALETTE.length])
            : cfg.color || CHART_PALETTE[i % CHART_PALETTE.length];

        const chartData = {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: isDoughnut ? colors : (Array.isArray(colors) ? colors : colors + "cc"),
                borderColor: isDoughnut ? "#fff" : (Array.isArray(colors) ? colors : colors),
                borderWidth: isDoughnut ? 2 : 1,
                borderRadius: isDoughnut ? 0 : 4,
            }],
        };

        const options = {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: isHorizontal ? "y" : "x",
            plugins: {
                legend: { display: isDoughnut, labels: { color: textColor, font: { size: 12 } } },
                tooltip: {
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    callbacks: {
                        label: (ctx) => {
                            const v = ctx.parsed !== undefined
                                ? (typeof ctx.parsed === "object" ? (isHorizontal ? ctx.parsed.x : ctx.parsed.y) : ctx.parsed)
                                : ctx.raw;
                            return ` ${ctx.label}: ${Number(v).toLocaleString("es-ES")}`;
                        }
                    }
                },
            },
            scales: isDoughnut ? {} : {
                x: {
                    ticks: { color: textColor, font: { size: isHorizontal ? 12 : 11 }, maxRotation: isHorizontal ? 0 : 40 },
                    grid: { color: gridColor },
                },
                y: {
                    ticks: { color: textColor, font: { size: isHorizontal ? 11 : 11 } },
                    grid: { color: gridColor },
                    beginAtZero: true,
                },
            },
        };

        const chart = new Chart(canvas, { type: chartType, data: chartData, options });
        window._activeCharts.push(chart);
    });
}


// ═══════════════════════════════════════════════════════════════
// PDF Download
// ═══════════════════════════════════════════════════════════════

// _lastResultData is stored on window by renderResults()

function openPdfModal() {
    document.getElementById("pdf-modal").classList.remove("hidden");
}
function closePdfModal() {
    document.getElementById("pdf-modal").classList.add("hidden");
}

async function downloadPdf() {
    const inclMeta = document.getElementById("pdf-include-meta").checked;
    const inclData = document.getElementById("pdf-include-data").checked;
    closePdfModal();

    // Build a temporary container with only the content we want
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "position:absolute;left:-9999px;top:0;width:700px;background:#fff;color:#1e293b;font-family:Inter,system-ui,sans-serif;padding:20px 24px;line-height:1.7;";
    document.body.appendChild(wrapper);

    // ── Title
    const title = document.createElement("h1");
    title.textContent = "\uD83C\uDFAF Denodo Flick — Recomendación";
    title.style.cssText = "font-size:22px;margin:0 0 6px 0;color:#1e293b;";
    wrapper.appendChild(title);

    const subtitle = document.createElement("p");
    subtitle.textContent = "Generado el " + new Date().toLocaleString("es-ES");
    subtitle.style.cssText = "font-size:12px;color:#64748b;margin:0 0 18px 0;";
    wrapper.appendChild(subtitle);

    // ── Charts (if visible)
    const chartsOrig = document.getElementById("charts-section");
    if (chartsOrig && !chartsOrig.classList.contains("hidden")) {
        const chartsClone = chartsOrig.cloneNode(true);
        chartsClone.classList.remove("hidden");
        chartsClone.style.cssText = "margin-bottom:18px;";
        chartsClone.querySelectorAll("canvas").forEach(c => {
            c.style.maxHeight = "260px";
            c.style.pageBreakInside = "avoid";
        });
        wrapper.appendChild(chartsClone);
    }

    // ── Decision card
    const decisionOrig = document.getElementById("decision-card");
    if (decisionOrig) {
        const decisionClone = decisionOrig.cloneNode(true);
        decisionClone.style.cssText = "background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#1e40af 100%);color:white;padding:20px 22px;border-radius:10px;margin-bottom:18px;page-break-inside:auto;overflow:visible;";
        // Ensure all text nodes are white
        decisionClone.querySelectorAll("*").forEach(el => {
            el.style.color = "white";
            el.style.pageBreakInside = "auto";
            el.style.overflow = "visible";
        });
        // Fix tables inside decision
        decisionClone.querySelectorAll("th").forEach(th => {
            th.style.background = "rgba(255,255,255,0.15)";
        });
        decisionClone.querySelectorAll("td, th").forEach(cell => {
            cell.style.borderColor = "rgba(255,255,255,0.2)";
            cell.style.padding = "6px 10px";
            cell.style.fontSize = "12px";
        });
        decisionClone.querySelectorAll("table").forEach(tbl => {
            tbl.style.width = "100%";
            tbl.style.borderCollapse = "collapse";
            tbl.style.pageBreakInside = "auto";
        });
        wrapper.appendChild(decisionClone);
    }

    // ── Phase details (optional)
    const phaseDetails = document.querySelectorAll("#results-content details.phase-details");
    if (inclMeta && phaseDetails[0]) {
        const clone = phaseDetails[0].cloneNode(true);
        clone.setAttribute("open", "");
        _stylePdfPhaseDetail(clone);
        wrapper.appendChild(clone);
    }
    if (inclData && phaseDetails[1]) {
        const clone = phaseDetails[1].cloneNode(true);
        clone.setAttribute("open", "");
        _stylePdfPhaseDetail(clone);
        wrapper.appendChild(clone);
    }

    const opt = {
        margin: [8, 8, 8, 8],
        filename: "denodo-flick-recomendacion.pdf",
        image: { type: "jpeg", quality: 0.95 },
        html2canvas: {
            scale: 2,
            useCORS: true,
            backgroundColor: "#ffffff",
            scrollY: 0,
            windowWidth: 700,
        },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"], avoid: ["tr", "li", "h2", "h3"] },
    };

    try {
        await html2pdf().set(opt).from(wrapper).save();
    } finally {
        wrapper.remove();
    }
}

function _stylePdfPhaseDetail(detail) {
    detail.style.cssText = "margin-bottom:14px;border:1px solid #d1d5db;border-radius:8px;padding:12px 16px;page-break-inside:auto;overflow:visible;";
    const summary = detail.querySelector("summary");
    if (summary) summary.style.cssText = "font-weight:700;font-size:14px;color:#1e293b;margin-bottom:8px;cursor:default;";
    detail.querySelectorAll(".result-box, .markdown-body").forEach(el => {
        el.style.color = "#1e293b";
        el.style.overflow = "visible";
        el.style.maxHeight = "none";
    });
    detail.querySelectorAll("table").forEach(tbl => {
        tbl.style.width = "100%";
        tbl.style.borderCollapse = "collapse";
        tbl.style.pageBreakInside = "auto";
    });
    detail.querySelectorAll("th").forEach(th => {
        th.style.background = "#f1f5f9";
        th.style.color = "#1e293b";
        th.style.padding = "6px 10px";
        th.style.fontSize = "11px";
    });
    detail.querySelectorAll("td").forEach(td => {
        td.style.padding = "5px 10px";
        td.style.fontSize = "11px";
        td.style.color = "#1e293b";
        td.style.borderBottom = "1px solid #e2e8f0";
    });
}



