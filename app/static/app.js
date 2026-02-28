/* ════════════════════════════════════════════════════════════
   DecisionLens — Frontend Logic
   HackUDC 2026 - Reto Denodo
   ════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
    // ── Theme toggle ────────────────────────────────────────
    initThemeToggle();

    checkHealth();

    // Auto-sync metadatos con "admin" al cargar
    autoSyncMetadata();

    // Discover views button
    document.getElementById("btn-discover-views")?.addEventListener("click", discoverViews);

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
    document.getElementById("btn-new")?.addEventListener("click", showScenarios);

});


// ═══════════════════════════════════════════════════════════════
// View selector helper
// ═══════════════════════════════════════════════════════════════

function getSelectedView() {
    const input = document.getElementById("view-select");
    return input ? input.value.trim() || null : null;
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

        if (data.status === "ok" && data.answer) {
            // Parse view names from the answer text (pattern: database.view_name)
            const viewPattern = /\b(\w+\.\w+)\b/g;
            const matches = data.answer.match(viewPattern) || [];
            // Dedupe and filter reasonable view names
            const views = [...new Set(matches)].filter(v => {
                const parts = v.split(".");
                return parts.length === 2 && parts[0].length > 1 && parts[1].length > 1
                    && !v.match(/^(e\.g|i\.e|vs\.|etc\.)$/i);
            });

            datalist.innerHTML = "";
            views.forEach(view => {
                const opt = document.createElement("option");
                opt.value = view;
                datalist.appendChild(opt);
            });

            status.textContent = views.length > 0 ? `${views.length} vistas encontradas` : "Sin vistas detectadas";

            // Auto-fill first view if input is empty
            const input = document.getElementById("view-select");
            if (!input.value && views.length > 0) {
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

async function runDecision(scenario, customQuestion = null, customMetaQs = null, customDataQs = null, params = null) {
    showResults();
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("results-content").classList.add("hidden");

    // Reset phase indicators
    const p1 = document.getElementById("phase1-status");
    const p2 = document.getElementById("phase2-status");
    const p3 = document.getElementById("phase3-status");
    [p1, p2, p3].forEach(p => { p.className = "phase-indicator"; });



    try {
        const body = {
            scenario: scenario,
        };
        if (customQuestion) body.custom_question = customQuestion;
        if (customMetaQs) body.custom_metadata_questions = customMetaQs;
        if (customDataQs) body.custom_data_questions = customDataQs;
        if (params) body.parameters = params;
        const useViews = getSelectedView();
        if (useViews) body.use_views = useViews;

        const res = await fetch("/api/decide-stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
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
                document.getElementById("loading").classList.add("hidden");
                renderResults(finalData);
                document.getElementById("results-content").classList.remove("hidden");
            }, 400);
        } else {
            document.getElementById("loading").classList.add("hidden");
            document.getElementById("results-content").classList.remove("hidden");
            document.getElementById("decision-text").innerHTML = "<p>No se recibieron resultados del servidor.</p>";
        }

    } catch (err) {
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("results-content").classList.remove("hidden");
        document.getElementById("decision-text").innerHTML = `<p>Error: ${err.message}</p>`;
        document.getElementById("phase1-results").innerHTML = "";
        document.getElementById("phase2-results").innerHTML = "";
    }
}


// ═══════════════════════════════════════════════════════════════
// Render results
// ═══════════════════════════════════════════════════════════════

function renderResults(data) {
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




