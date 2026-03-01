/* ═══════════════════════════════════════════════════════════════
   Inline Games — Minijuegos en la pantalla de carga
   Pong (DOM) + Pac-Man (Canvas + OffscreenCanvas)
   ═══════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // ── Shared state ─────────────────────────────────────────
    let activeGame = null;       // 'pong' | 'pacman' | null
    let pongRAF = null;
    let pmRAF = null;
    let pongCountdownTimer = null;
    let pmMouthTimer = null;

    // ── Spinner-as-ball refs ─────────────────────────────────
    let spinnerEl = null;
    let spinnerOrigParent = null;
    let spinnerOrigNext = null;

    // ══════════════════════════════════════════════════════════
    //  GAME MENU
    // ══════════════════════════════════════════════════════════

    function showGameMenu() {
        const el = document.getElementById("game-menu-panel");
        if (el) el.classList.remove("hidden");
    }

    function hideGameMenu() {
        const el = document.getElementById("game-menu-panel");
        if (el) el.classList.add("hidden");
    }

    // ══════════════════════════════════════════════════════════
    //  CLEANUP  (called externally when data finishes loading)
    // ══════════════════════════════════════════════════════════

    function cleanup() {
        _stopAllLoops();
        _hideGameContainers();
        _removeKeyListeners();
        activeGame = null;
        hideGameMenu();
    }

    // ── Exit to menu (user clicks ❌) ────────────────────────
    function exitToMenu() {
        _stopAllLoops();
        _hideGameContainers();
        _removeKeyListeners();
        activeGame = null;
        showGameMenu();
    }

    function _stopAllLoops() {
        if (pongRAF) { cancelAnimationFrame(pongRAF); pongRAF = null; }
        if (pmRAF) { cancelAnimationFrame(pmRAF); pmRAF = null; }
        if (pongCountdownTimer) { clearInterval(pongCountdownTimer); pongCountdownTimer = null; }
        if (pmMouthTimer) { clearInterval(pmMouthTimer); pmMouthTimer = null; }
    }

    function _hideGameContainers() {
        _restoreSpinner();
        // Reset pong-field inline positioning
        const pf = document.getElementById("pong-field");
        if (pf) {
            pf.style.position = "";
            pf.style.top = "";
            pf.style.left = "";
            pf.style.right = "";
            pf.style.bottom = "";
            pf.style.flex = "";
            pf.style.width = "";
            pf.style.height = "";
        }
        const ids = ["pong-container", "pacman-container", "game-exit-btn"];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.add("hidden");
        });
    }

    /* Move the spinner back to its original loading-inner position */
    function _restoreSpinner() {
        if (!spinnerEl) return;
        spinnerEl.classList.remove("pong-active");
        spinnerEl.style.transform = "";
        if (spinnerOrigParent) {
            if (spinnerOrigNext) {
                spinnerOrigParent.insertBefore(spinnerEl, spinnerOrigNext);
            } else {
                spinnerOrigParent.appendChild(spinnerEl);
            }
        }
        spinnerEl = null;
        spinnerOrigParent = null;
        spinnerOrigNext = null;
    }

    function _removeKeyListeners() {
        document.removeEventListener("keydown", pongKeyDown);
        document.removeEventListener("keyup", pongKeyUp);
        document.removeEventListener("keydown", pmKeyDown);
    }

    // ══════════════════════════════════════════════════════════
    //  PONG  — DOM-Based  (transform only, no top/left)
    // ══════════════════════════════════════════════════════════

    const PONG_PADDLE_W = 10;
    const PONG_PADDLE_H = 100;
    const PONG_BALL_SIZE = 56;
    const PONG_BALL_SPEED = 9;
    const PONG_PADDLE_SPEED = 6;

    let pongState = null;

    // Key flags
    let pUpP1 = false, pDownP1 = false, pUpP2 = false, pDownP2 = false;

    function pongKeyDown(e) {
        if (e.key === "w" || e.key === "W") pUpP1 = true;
        else if (e.key === "s" || e.key === "S") pDownP1 = true;
        if (e.key === "ArrowUp")   { pUpP2 = true; e.preventDefault(); }
        else if (e.key === "ArrowDown") { pDownP2 = true; e.preventDefault(); }
    }

    function pongKeyUp(e) {
        if (e.key === "w" || e.key === "W") pUpP1 = false;
        else if (e.key === "s" || e.key === "S") pDownP1 = false;
        if (e.key === "ArrowUp")   pUpP2 = false;
        else if (e.key === "ArrowDown") pDownP2 = false;
    }

    function startPong() {
        activeGame = "pong";
        hideGameMenu();

        document.getElementById("pong-container").classList.remove("hidden");
        document.getElementById("game-exit-btn").classList.remove("hidden");

        // ── Capture spinner screen position BEFORE moving it ──
        spinnerEl = document.querySelector("#loading-inner .spinner");
        let spinnerRect = null;
        if (spinnerEl) {
            spinnerRect = spinnerEl.getBoundingClientRect();
            spinnerOrigParent = spinnerEl.parentNode;
            spinnerOrigNext = spinnerEl.nextSibling;
            const field = document.getElementById("pong-field");
            field.appendChild(spinnerEl);
            spinnerEl.classList.add("pong-active");
        }

        // ── Position field between header (blue) and footer (white) ──
        const field = document.getElementById("pong-field");
        const headerBottom = document.querySelector("header").getBoundingClientRect().bottom;
        const footerEl = document.querySelector("footer");
        const footerRect = footerEl ? footerEl.getBoundingClientRect() : null;
        const bottomBound = (footerRect && footerRect.top < window.innerHeight)
            ? footerRect.top
            : window.innerHeight;

        field.style.position = "fixed";
        field.style.top = headerBottom + "px";
        field.style.left = "0";
        field.style.right = "0";
        field.style.bottom = (window.innerHeight - bottomBound) + "px";
        field.style.flex = "none";
        field.style.width = "auto";
        field.style.height = "auto";

        // Measure the field after positioning
        const fieldW = field.clientWidth;
        const fieldH = field.clientHeight;
        const fieldRect2 = field.getBoundingClientRect();

        // ── Ball starts exactly where the spinner was ──
        let ballX, ballY;
        if (spinnerRect) {
            ballX = spinnerRect.left - fieldRect2.left;
            ballY = spinnerRect.top - fieldRect2.top;
            ballX = Math.max(0, Math.min(fieldW - PONG_BALL_SIZE, ballX));
            ballY = Math.max(0, Math.min(fieldH - PONG_BALL_SIZE, ballY));
        } else {
            ballX = (fieldW - PONG_BALL_SIZE) / 2;
            ballY = (fieldH - PONG_BALL_SIZE) / 2;
        }

        pUpP1 = pDownP1 = pUpP2 = pDownP2 = false;

        pongState = {
            score1: 0,
            score2: 0,
            p1Y: (fieldH - PONG_PADDLE_H) / 2,
            p2Y: (fieldH - PONG_PADDLE_H) / 2,
            ballX: ballX,
            ballY: ballY,
            dx: PONG_BALL_SPEED,
            dy: PONG_BALL_SPEED * 0.5,
            speed: PONG_BALL_SPEED,
            playing: false,
            fieldW: fieldW,
            fieldH: fieldH,
        };

        document.getElementById("pong-score").textContent = "0 - 0";
        renderPong();

        document.addEventListener("keydown", pongKeyDown);
        document.addEventListener("keyup", pongKeyUp);

        startPongCountdown();
    }

    // ── Countdown 3-2-1-¡YA! ────────────────────────────────
    function startPongCountdown() {
        const overlay = document.getElementById("pong-countdown");
        overlay.classList.remove("hidden");
        overlay.textContent = "3";
        pongState.playing = false;

        let count = 3;
        pongCountdownTimer = setInterval(() => {
            count--;
            if (count > 0) {
                overlay.textContent = String(count);
            } else if (count === 0) {
                overlay.textContent = "¡YA!";
            } else {
                clearInterval(pongCountdownTimer);
                pongCountdownTimer = null;
                overlay.classList.add("hidden");
                pongState.playing = true;
                pongLoop();
            }
        }, 800);
    }

    function resetPongBall() {
        const s = pongState;
        s.ballX = (s.fieldW - PONG_BALL_SIZE) / 2;
        s.ballY = (s.fieldH - PONG_BALL_SIZE) / 2;
        // Alternate direction
        s.dx = s.dx > 0 ? -PONG_BALL_SPEED : PONG_BALL_SPEED;
        s.dy = (Math.random() > 0.5 ? 1 : -1) * PONG_BALL_SPEED * 0.5;
        s.speed = PONG_BALL_SPEED;
    }

    // ── Main Pong loop ───────────────────────────────────────
    function pongLoop() {
        if (activeGame !== "pong" || !pongState || !pongState.playing) return;

        const s = pongState;
        const fW = s.fieldW;
        const fH = s.fieldH;

        // ── Move paddles (clamp to field) ──
        if (pUpP1)   s.p1Y = Math.max(0, s.p1Y - PONG_PADDLE_SPEED);
        if (pDownP1) s.p1Y = Math.min(fH - PONG_PADDLE_H, s.p1Y + PONG_PADDLE_SPEED);
        if (pUpP2)   s.p2Y = Math.max(0, s.p2Y - PONG_PADDLE_SPEED);
        if (pDownP2) s.p2Y = Math.min(fH - PONG_PADDLE_H, s.p2Y + PONG_PADDLE_SPEED);

        // ── Move ball ──
        s.ballX += s.dx;
        s.ballY += s.dy;

        // ── Top / bottom bounce ──
        if (s.ballY <= 0) {
            s.ballY = 0;
            s.dy = Math.abs(s.dy);
        }
        if (s.ballY >= fH - PONG_BALL_SIZE) {
            s.ballY = fH - PONG_BALL_SIZE;
            s.dy = -Math.abs(s.dy);
        }

        // Ball center
        const bcx = s.ballX + PONG_BALL_SIZE / 2;
        const bcy = s.ballY + PONG_BALL_SIZE / 2;
        const bhr = PONG_BALL_SIZE / 2;

        // ── P1 collision (left paddle, x=10) ──
        const p1Right = 10 + PONG_PADDLE_W;
        if (s.dx < 0 && bcx - bhr < p1Right && bcx + bhr > 10 &&
            bcy > s.p1Y && bcy < s.p1Y + PONG_PADDLE_H) {
            s.ballX = p1Right;
            s.speed += 0.05;
            const hit = (bcy - (s.p1Y + PONG_PADDLE_H / 2)) / (PONG_PADDLE_H / 2);
            s.dy = hit * s.speed;
            s.dx = s.speed;
        }

        // ── P2 collision (right paddle) ──
        const p2Left = fW - 10 - PONG_PADDLE_W;
        if (s.dx > 0 && bcx + bhr > p2Left && bcx - bhr < p2Left + PONG_PADDLE_W &&
            bcy > s.p2Y && bcy < s.p2Y + PONG_PADDLE_H) {
            s.ballX = p2Left - PONG_BALL_SIZE;
            s.speed += 0.05;
            const hit = (bcy - (s.p2Y + PONG_PADDLE_H / 2)) / (PONG_PADDLE_H / 2);
            s.dy = hit * s.speed;
            s.dx = -s.speed;
        }

        // ── Scoring ──
        if (s.ballX + PONG_BALL_SIZE < 0) {
            s.score2++;
            document.getElementById("pong-score").textContent = `${s.score1} - ${s.score2}`;
            resetPongBall();
        } else if (s.ballX > fW) {
            s.score1++;
            document.getElementById("pong-score").textContent = `${s.score1} - ${s.score2}`;
            resetPongBall();
        }

        renderPong();
        pongRAF = requestAnimationFrame(pongLoop);
    }

    // ── Render (transforms only — no top/left) ──────────────
    function renderPong() {
        if (!pongState) return;
        const s = pongState;
        document.getElementById("pong-paddle1").style.transform = `translateY(${s.p1Y}px)`;
        document.getElementById("pong-paddle2").style.transform = `translateY(${s.p2Y}px)`;
        if (spinnerEl) spinnerEl.style.transform = `translate(${s.ballX}px, ${s.ballY}px)`;
    }


    // ══════════════════════════════════════════════════════════
    //  PAC-MAN  — Canvas HTML5 + OffscreenCanvas
    // ══════════════════════════════════════════════════════════

    const PM_TILE = 16;
    const PM_COLS = 20;
    const PM_ROWS = 17;
    const PM_W = PM_COLS * PM_TILE;   // 320
    const PM_H = PM_ROWS * PM_TILE;   // 272
    const PM_PAC_R = 6;
    const PM_GHOST_R = 7;
    const PM_GHOST_SPEED = 0.5;

    // 17-row × 20-col maze (scaled from original 22-row version)
    const PM_MAP_INIT = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], // 0
        [1,2,2,2,2,2,2,2,2,1,1,2,2,2,2,2,2,2,2,1], // 1
        [1,2,1,1,1,2,1,1,2,1,1,2,1,1,2,1,1,1,2,1], // 2
        [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1], // 3
        [1,2,1,1,1,2,1,2,1,1,1,1,2,1,2,1,1,1,2,1], // 4
        [1,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,1], // 5
        [1,1,1,1,1,2,1,0,0,0,0,0,0,1,2,1,1,1,1,1], // 6 ← ghosts spawn
        [0,0,0,0,0,2,0,0,1,0,0,1,0,0,2,0,0,0,0,0], // 7 ← tunnel
        [1,1,1,1,1,2,1,0,1,1,1,1,0,1,2,1,1,1,1,1], // 8
        [1,2,2,2,2,2,1,0,0,0,0,0,0,1,2,2,2,2,2,1], // 9
        [1,2,1,1,1,2,1,1,2,1,1,2,1,1,2,1,1,1,2,1], // 10
        [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1], // 11 ← pacman
        [1,2,1,2,1,2,1,1,2,1,1,2,1,1,2,1,2,1,2,1], // 12
        [1,2,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,2,1], // 13
        [1,2,1,1,1,2,1,2,1,1,1,1,2,1,2,1,1,1,2,1], // 14
        [1,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,1], // 15
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], // 16
    ];

    let pmState = null;
    let pmOffscreen = null;      // off-DOM canvas for static maze
    let pmMouthOpen = true;

    function pmKeyDown(e) {
        if (!pmState) return;
        const pm = pmState.pacman;
        if (e.key === "ArrowLeft")  { pm.nextVx = -pm.speed; pm.nextVy = 0; e.preventDefault(); }
        else if (e.key === "ArrowRight") { pm.nextVx = pm.speed; pm.nextVy = 0; e.preventDefault(); }
        else if (e.key === "ArrowUp")    { pm.nextVx = 0; pm.nextVy = -pm.speed; e.preventDefault(); }
        else if (e.key === "ArrowDown")  { pm.nextVx = 0; pm.nextVy = pm.speed; e.preventDefault(); }

        // Unlock ghost AI on first arrow key press
        if (!pmState.started) pmState.started = true;
    }

    function startPacman() {
        activeGame = "pacman";
        hideGameMenu();

        document.getElementById("pacman-container").classList.remove("hidden");
        document.getElementById("game-exit-btn").classList.remove("hidden");
        document.getElementById("pm-restart").classList.add("hidden");
        document.getElementById("pm-controls").classList.remove("hidden");

        initPacmanState();
        buildPacmanOffscreen();

        document.addEventListener("keydown", pmKeyDown);
        pmMouthTimer = setInterval(() => { pmMouthOpen = !pmMouthOpen; }, 150);
        pmLoop();
    }

    function initPacmanState() {
        // Deep-copy map
        const map = PM_MAP_INIT.map(row => [...row]);

        // Count dots
        let dots = 0;
        for (let r = 0; r < PM_ROWS; r++)
            for (let c = 0; c < PM_COLS; c++)
                if (map[r][c] === 2) dots++;

        pmState = {
            map: map,
            score: 0,
            totalDots: dots,
            gameOver: false,
            won: false,
            started: false,           // ghosts frozen until first input
            pacman: {
                x: 10 * PM_TILE + PM_TILE / 2,
                y: 11 * PM_TILE + PM_TILE / 2,
                vx: 0, vy: 0,
                nextVx: 0, nextVy: 0,
                speed: 1,
                radius: PM_PAC_R,
            },
            ghosts: [
                { x: 9  * PM_TILE + PM_TILE / 2, y: 6 * PM_TILE + PM_TILE / 2, vx: PM_GHOST_SPEED, vy: 0, color: "red",  speed: PM_GHOST_SPEED },
                { x: 10 * PM_TILE + PM_TILE / 2, y: 6 * PM_TILE + PM_TILE / 2, vx: -PM_GHOST_SPEED, vy: 0, color: "pink", speed: PM_GHOST_SPEED },
                { x: 11 * PM_TILE + PM_TILE / 2, y: 6 * PM_TILE + PM_TILE / 2, vx: 0, vy: -PM_GHOST_SPEED, color: "cyan", speed: PM_GHOST_SPEED },
            ],
        };

        document.getElementById("pm-score-val").textContent = "0";
    }

    // ── OffscreenCanvas: draw maze walls ONCE ────────────────
    function buildPacmanOffscreen() {
        pmOffscreen = document.createElement("canvas");
        pmOffscreen.width  = PM_W;
        pmOffscreen.height = PM_H;
        const octx = pmOffscreen.getContext("2d");

        // Background
        octx.fillStyle = "#000";
        octx.fillRect(0, 0, PM_W, PM_H);

        // Walls
        const map = pmState.map;
        octx.fillStyle = "#1919a6";
        for (let r = 0; r < PM_ROWS; r++) {
            for (let c = 0; c < PM_COLS; c++) {
                if (map[r][c] === 1) {
                    octx.fillRect(c * PM_TILE, r * PM_TILE, PM_TILE, PM_TILE);
                }
            }
        }
    }

    // ── Tile-based collision helper ──────────────────────────
    function pmCheckCollision(x, y, dx, dy, radius) {
        const map = pmState.map;
        const left   = x + dx - radius;
        const right  = x + dx + radius - 1;
        const top    = y + dy - radius;
        const bottom = y + dy + radius - 1;

        const rowTop    = Math.floor(top    / PM_TILE);
        const rowBottom = Math.floor(bottom / PM_TILE);
        const colLeft   = Math.floor(left   / PM_TILE);
        const colRight  = Math.floor(right  / PM_TILE);

        // Tunnel wrap: no collision at edges
        if (colLeft < 0 || colRight >= PM_COLS) return false;
        if (rowTop < 0 || rowBottom >= PM_ROWS) return false;

        if (map[rowTop]    && map[rowTop][colLeft]    === 1) return true;
        if (map[rowTop]    && map[rowTop][colRight]   === 1) return true;
        if (map[rowBottom] && map[rowBottom][colLeft]  === 1) return true;
        if (map[rowBottom] && map[rowBottom][colRight] === 1) return true;

        return false;
    }

    // ── Update ───────────────────────────────────────────────
    function pmUpdate() {
        if (pmState.gameOver) return;

        const pm = pmState.pacman;

        // Try next buffered direction
        if ((pm.nextVx !== 0 || pm.nextVy !== 0) &&
            !pmCheckCollision(pm.x, pm.y, pm.nextVx, pm.nextVy, pm.radius)) {
            pm.vx = pm.nextVx;
            pm.vy = pm.nextVy;
        }

        // Move if no collision
        if (!pmCheckCollision(pm.x, pm.y, pm.vx, pm.vy, pm.radius)) {
            pm.x += pm.vx;
            pm.y += pm.vy;
        }

        // Tunnel wrap
        if (pm.x < 0)    pm.x = PM_W;
        if (pm.x > PM_W) pm.x = 0;

        // Eat dots
        const cCol = Math.floor(pm.x / PM_TILE);
        const cRow = Math.floor(pm.y / PM_TILE);
        if (pmState.map[cRow] && pmState.map[cRow][cCol] === 2) {
            const cx = cCol * PM_TILE + PM_TILE / 2;
            const cy = cRow * PM_TILE + PM_TILE / 2;
            if (Math.hypot(pm.x - cx, pm.y - cy) < PM_TILE / 2) {
                pmState.map[cRow][cCol] = 0;
                pmState.score += 10;
                pmState.totalDots--;
                document.getElementById("pm-score-val").textContent = pmState.score;
                if (pmState.totalDots <= 0) {
                    pmState.gameOver = true;
                    pmState.won = true;
                    showPmGameOver();
                    return;
                }
            }
        }

        // ── Ghost AI  (only when started) ────────────────────
        if (!pmState.started) return;

        pmState.ghosts.forEach(g => {
            if (pmCheckCollision(g.x, g.y, g.vx, g.vy, PM_GHOST_R)) {
                // Hit wall → pick random valid direction
                const dirs = [
                    { vx: g.speed, vy: 0 }, { vx: -g.speed, vy: 0 },
                    { vx: 0, vy: g.speed }, { vx: 0, vy: -g.speed },
                ];
                const valid = dirs.filter(d => !pmCheckCollision(g.x, g.y, d.vx, d.vy, PM_GHOST_R));
                if (valid.length > 0) {
                    const pick = valid[Math.floor(Math.random() * valid.length)];
                    g.vx = pick.vx;
                    g.vy = pick.vy;
                }
            } else {
                // Tunnel wrap
                if (g.x < 0)    g.x = PM_W;
                if (g.x > PM_W) g.x = 0;

                // Random direction change at intersections
                if (g.x % PM_TILE < g.speed && g.y % PM_TILE < g.speed && Math.random() < 0.2) {
                    const dirs = [
                        { vx: g.speed, vy: 0 }, { vx: -g.speed, vy: 0 },
                        { vx: 0, vy: g.speed }, { vx: 0, vy: -g.speed },
                    ];
                    const valid = dirs.filter(d => !pmCheckCollision(g.x, g.y, d.vx, d.vy, PM_GHOST_R));
                    if (valid.length > 0) {
                        const pick = valid[Math.floor(Math.random() * valid.length)];
                        g.vx = pick.vx;
                        g.vy = pick.vy;
                    }
                }
                g.x += g.vx;
                g.y += g.vy;
            }

            // Ghost ↔ Pac-Man collision
            if (Math.hypot(pm.x - g.x, pm.y - g.y) < pm.radius + PM_GHOST_R) {
                pmState.gameOver = true;
                showPmGameOver();
            }
        });
    }

    // ── Draw (offscreen blit + dynamic elements) ─────────────
    function pmDraw() {
        const canvas = document.getElementById("pm-canvas");
        const ctx = canvas.getContext("2d");
        const map = pmState.map;

        // 1) Blit pre-rendered static maze (walls + bg)
        ctx.drawImage(pmOffscreen, 0, 0);

        // 2) Draw remaining dots (dynamic — they disappear when eaten)
        ctx.fillStyle = "#ffd0b3";
        for (let r = 0; r < PM_ROWS; r++) {
            for (let c = 0; c < PM_COLS; c++) {
                if (map[r][c] === 2) {
                    ctx.beginPath();
                    ctx.arc(c * PM_TILE + PM_TILE / 2, r * PM_TILE + PM_TILE / 2, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }

        // 3) Draw Pac-Man
        const pm = pmState.pacman;
        ctx.save();
        ctx.translate(pm.x, pm.y);
        if      (pm.vx > 0) ctx.rotate(0);
        else if (pm.vx < 0) ctx.rotate(Math.PI);
        else if (pm.vy > 0) ctx.rotate(Math.PI / 2);
        else if (pm.vy < 0) ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = "yellow";
        ctx.beginPath();
        const ang = pmMouthOpen ? 0.2 * Math.PI : 0.05 * Math.PI;
        ctx.arc(0, 0, pm.radius, ang, (2 - 0.2) * Math.PI);
        ctx.lineTo(0, 0);
        ctx.fill();
        ctx.restore();

        // 4) Draw Ghosts
        pmState.ghosts.forEach(g => {
            ctx.fillStyle = g.color;
            ctx.beginPath();
            ctx.arc(g.x, g.y - 2, PM_GHOST_R, Math.PI, 0);
            ctx.lineTo(g.x + PM_GHOST_R, g.y + PM_GHOST_R);
            ctx.lineTo(g.x + PM_GHOST_R * 0.5, g.y + PM_GHOST_R - 2);
            ctx.lineTo(g.x, g.y + PM_GHOST_R);
            ctx.lineTo(g.x - PM_GHOST_R * 0.5, g.y + PM_GHOST_R - 2);
            ctx.lineTo(g.x - PM_GHOST_R, g.y + PM_GHOST_R);
            ctx.fill();

            // Eyes
            ctx.fillStyle = "white";
            ctx.beginPath();
            ctx.arc(g.x - 2.5, g.y - 2.5, 2, 0, Math.PI * 2);
            ctx.arc(g.x + 2.5, g.y - 2.5, 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "blue";
            ctx.beginPath();
            ctx.arc(g.x - 2.5, g.y - 2.5, 0.8, 0, Math.PI * 2);
            ctx.arc(g.x + 2.5, g.y - 2.5, 0.8, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    // ── Main Pac-Man loop ────────────────────────────────────
    function pmLoop() {
        if (activeGame !== "pacman") return;
        pmUpdate();
        pmDraw();
        if (!pmState.gameOver) {
            pmRAF = requestAnimationFrame(pmLoop);
        }
    }

    function showPmGameOver() {
        document.getElementById("pm-controls").classList.add("hidden");
        document.getElementById("pm-restart").classList.remove("hidden");
    }

    function restartPacman() {
        if (pmRAF) { cancelAnimationFrame(pmRAF); pmRAF = null; }
        initPacmanState();
        buildPacmanOffscreen();
        document.getElementById("pm-restart").classList.add("hidden");
        document.getElementById("pm-controls").classList.remove("hidden");
        pmLoop();
    }

    // ══════════════════════════════════════════════════════════
    //  INIT (attach event listeners once)
    // ══════════════════════════════════════════════════════════

    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("game-btn-pong")?.addEventListener("click", startPong);
        document.getElementById("game-btn-pacman")?.addEventListener("click", startPacman);
        document.getElementById("game-exit-btn")?.addEventListener("click", exitToMenu);
        document.getElementById("pm-restart")?.addEventListener("click", restartPacman);
    });

    // ══════════════════════════════════════════════════════════
    //  PUBLIC API  (called from app.js)
    // ══════════════════════════════════════════════════════════

    window.InlineGames = {
        showMenu:  showGameMenu,
        hideMenu:  hideGameMenu,
        cleanup:   cleanup,
        isActive:  () => activeGame !== null,
    };

})();
