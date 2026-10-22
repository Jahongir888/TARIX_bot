let examSectionReady = false;
let examScanStream = null;
let examTimerHandle = null;
let examTimerLeft = 0;
let examSubmitting = false;

const examState = {
    quizzes: [],
    activeQuizId: null,
    play: null,
    paperKind: "test",
    regionsMap: null,
    analysis: null,
};

function examTgId() {
    if (typeof getCurrentTelegramId === "function") return getCurrentTelegramId();
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 84920194;
}

function examEsc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[ch]));
}

function examShow(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("ph-open");
}

function examHide(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("ph-open");
}

function examSetHide(id, hidden) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("ph-hide", hidden);
}

function formatExamSum(price) {
    const amount = Number(price) || 0;
    if (amount <= 0) return { text: "Bepul", free: true };
    const formatted = amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return { text: `${formatted} so'm`, free: false };
}

function examLevelClass(level) {
    if (level === "A" || level === "Ustoz") return "text-amber-300 bg-amber-500/10 border-amber-500/30";
    if (level === "B+") return "text-emerald-300 bg-emerald-500/10 border-emerald-500/30";
    if (level === "B" || level === "Bilimdon") return "text-sky-300 bg-sky-500/10 border-sky-500/30";
    return "text-slate-300 bg-slate-500/10 border-slate-500/30";
}

let examCardTicker = null;

function examMoney(amount) {
    return String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function examPriceHtml(quiz) {
    const price = Number(quiz.price) || 0;
    const base = Number(quiz.base_price) || price;
    if (price <= 0 && quiz.free_reason === "course") {
        return '<span class="text-xs font-extrabold text-emerald-400">Kurs egasiga bepul</span>';
    }
    if (price <= 0 && quiz.free_reason === "share") {
        return '<span class="text-xs font-extrabold text-emerald-400">Ulashish orqali bepul</span>';
    }
    if (price <= 0) {
        return '<span class="text-xs font-extrabold text-emerald-400">Bepul</span>';
    }
    if ((Number(quiz.discount_percent) || 0) > 0 && base > price) {
        return `<span class="block text-[10px] line-through text-slate-500">${examMoney(base)} so'm</span><span class="text-xs font-extrabold text-amber-300">${examMoney(price)} so'm</span><span class="block text-[10px] text-emerald-400">−${quiz.discount_percent}% ulashish</span>`;
    }
    return `<span class="text-xs font-extrabold text-amber-300">${examMoney(price)} so'm</span>`;
}

function examRemainLabel(msLeft) {
    const total = Math.max(0, Math.ceil(msLeft / 1000));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    if (days > 0) return `${days} kun ${hours} soat`;
    if (hours > 0) return `${hours} soat ${minutes} daqiqa`;
    const seconds = total % 60;
    return `${minutes} daqiqa ${String(seconds).padStart(2, "0")} s`;
}

function startExamCardCountdowns() {
    if (examCardTicker) {
        clearInterval(examCardTicker);
        examCardTicker = null;
    }
    const tick = () => {
        const nodes = document.querySelectorAll("[data-exam-until]");
        if (!nodes.length) {
            if (examCardTicker) clearInterval(examCardTicker);
            examCardTicker = null;
            return;
        }
        let expired = false;
        nodes.forEach((el) => {
            const left = Number(el.dataset.examUntil) - Date.now();
            if (left <= 0) {
                expired = true;
                return;
            }
            el.textContent = `Boshlanishiga: ${examRemainLabel(left)} qoldi`;
        });
        if (expired) {
            clearInterval(examCardTicker);
            examCardTicker = null;
            loadExamCards();
        }
    };
    tick();
    examCardTicker = setInterval(tick, 1000);
}

function examFigure(url) {
    if (!url) return "";
    const safe = examEsc(url);
    return `<button type="button" class="block w-full my-2 cursor-zoom-in" data-zoom="${safe}" onclick="openExamImageZoom(this.dataset.zoom)">
        <img src="${safe}" alt="Savol rasmi" class="w-full max-h-72 object-contain rounded-xl border border-[#283548] bg-[#0A0E17]">
    </button>`;
}

function examRenderMath(root) {
    if (!root || typeof renderMathInElement !== "function") return;
    try {
        renderMathInElement(root, {
            delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "$", right: "$", display: false },
            ],
            throwOnError: false,
            ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],
        });
    } catch (err) {
        /* formula xatosi matnni yashirmaydi */
    }
}

function examVideoEmbed(url) {
    const raw = String(url || "").trim();
    if (!raw) return "";
    const youtube = raw.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{6,})/);
    if (youtube) {
        return `<iframe class="w-full aspect-video rounded-xl bg-black" src="https://www.youtube.com/embed/${youtube[1]}" title="Video tahlil" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
    }
    const vimeo = raw.match(/vimeo\.com\/(?:video\/)?(\d+)/);
    if (vimeo) {
        return `<iframe class="w-full aspect-video rounded-xl bg-black" src="https://player.vimeo.com/video/${vimeo[1]}" title="Video tahlil" allowfullscreen></iframe>`;
    }
    return `<video class="w-full rounded-xl bg-black" controls playsinline src="${examEsc(raw)}"></video>`;
}

function initTestsSection() {
    if (!examSectionReady) {
        document.getElementById("exam-subject-select")?.addEventListener("change", loadExamCards);
        document.getElementById("exam-type-select")?.addEventListener("change", loadExamCards);
        examSectionReady = true;
    }
    loadExamCards();
}

async function loadExamCards() {
    const root = document.getElementById("exam-cards-root");
    const empty = document.getElementById("exam-empty-state");
    if (!root) return;
    const subject = document.getElementById("exam-subject-select")?.value || "tarix";
    const examType = document.getElementById("exam-type-select")?.value || "milliy_sertifikat";
    root.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Testlar yuklanmoqda...</p>';
    examSetHide("exam-empty-state", true);
    try {
        const res = await fetch(`/api/exams/list?subject=${encodeURIComponent(subject)}&exam_type=${encodeURIComponent(examType)}&telegram_id=${examTgId()}`);
        const data = await res.json();
        examState.quizzes = data.items || [];
        if (!examState.quizzes.length) {
            root.innerHTML = "";
            examSetHide("exam-empty-state", false);
            if (window.lucide) lucide.createIcons();
            return;
        }
        examSetHide("exam-empty-state", true);
        root.innerHTML = examState.quizzes.map(renderExamCard).join("");
        startExamCardCountdowns();
        if (window.lucide) lucide.createIcons();
    } catch (err) {
        root.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Testlarni yuklashda xatolik yuz berdi.</p>';
        if (empty) examSetHide("exam-empty-state", true);
    }
}

function renderExamCard(quiz) {
    const stars = renderExamStars(quiz.id, quiz.my_stars || 0);
    const avg = Number(quiz.avg_rating || 0).toFixed(1);
    const locked = quiz.access === "scheduled";
    const until = Date.now() + (Number(quiz.starts_in_seconds) || 0) * 1000;
    const startBtn = locked
        ? `<button type="button" disabled data-exam-until="${until}" class="w-full px-2 py-2.5 bg-[#161F30] border border-amber-500/40 text-[11px] leading-tight font-bold rounded-xl text-amber-200 cursor-not-allowed">Boshlanishiga: ${examEsc(quiz.starts_in_label || "")} qoldi</button>`
        : `<button type="button" onclick="openExamModes(${quiz.id})" class="w-full px-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-[11px] leading-tight font-bold rounded-xl text-white cursor-pointer">Testni ishlash va tekshirish</button>`;
    const link = quiz.link
        ? `<button type="button" onclick="openExamShareSheet(${quiz.id})" class="mt-3 w-full text-left border border-[#283548] bg-[#0A0E17] hover:border-emerald-500/50 hover:bg-[#0F1623] rounded-xl p-2.5 transition-colors cursor-pointer active:scale-[0.99]">
                <p class="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Havola · ulashish</p>
                <p class="text-[11px] leading-relaxed text-emerald-300 break-all">${examEsc(quiz.link)}</p>
            </button>`
        : "";
    return `
        <article class="bg-[#111827] border border-[#1F2937] rounded-2xl p-4 shadow-sm">
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                    <h3 class="text-sm font-bold text-white leading-snug">${examEsc(quiz.title)}</h3>
                    <p class="text-[11px] text-slate-300 mt-2">👤 ${quiz.participants || 0} qatnashuvchi</p>
                    <p class="text-[11px] text-slate-500 mt-0.5">${examEsc(quiz.announced_label || "")}</p>
                </div>
                <div class="shrink-0 text-right">${examPriceHtml(quiz)}</div>
            </div>
            ${link}
            <div id="exam-stars-${quiz.id}" class="flex items-center justify-center gap-1 mt-3">${stars}</div>
            <p id="exam-avg-${quiz.id}" class="text-center text-[10px] text-slate-400 mt-1">O'rtacha: ${avg} · ${quiz.votes || 0} ovoz</p>
            <div class="mt-4 space-y-2">
                ${startBtn}
                <div class="grid grid-cols-2 gap-2">
                    <button type="button" onclick="openExamLeaderboard(${quiz.id})" class="px-1 py-2 bg-[#161F30] border border-[#283548] text-[10px] leading-tight font-bold rounded-xl text-slate-100 cursor-pointer">Natija</button>
                    <button type="button" onclick="openExamAnalysisModal(${quiz.id})" class="px-1 py-2 bg-[#161F30] border border-[#283548] text-[10px] leading-tight font-bold rounded-xl text-slate-100 cursor-pointer">Tahlil</button>
                </div>
            </div>
        </article>
    `;
}

function renderExamStars(quizId, selected) {
    let html = "";
    for (let star = 1; star <= 5; star += 1) {
        const active = star <= selected;
        html += `<button type="button" onclick="rateExamQuiz(${quizId}, ${star})" class="text-lg leading-none cursor-pointer ${active ? "text-amber-400" : "text-slate-600"}" aria-label="${star} yulduz">★</button>`;
    }
    return html;
}

async function rateExamQuiz(quizId, stars) {
    const box = document.getElementById(`exam-stars-${quizId}`);
    if (box) box.innerHTML = renderExamStars(quizId, stars);
    try {
        const res = await fetch("/api/exams/rate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ quiz_id: quizId, telegram_id: examTgId(), stars }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Baholanmadi");
        if (box) box.innerHTML = renderExamStars(quizId, data.my_stars || stars);
        const avgEl = document.getElementById(`exam-avg-${quizId}`);
        if (avgEl) {
            avgEl.textContent = `O'rtacha: ${Number(data.avg_rating || 0).toFixed(1)} · ${data.votes || 0} ovoz`;
        }
        const quiz = examState.quizzes.find((item) => item.id === quizId);
        if (quiz) {
            quiz.my_stars = data.my_stars;
            quiz.avg_rating = data.avg_rating;
            quiz.votes = data.votes;
        }
    } catch (err) {
        alert("Bahoni saqlashda xatolik yuz berdi.");
        loadExamCards();
    }
}

function quizById(quizId) {
    return examState.quizzes.find((item) => item.id === quizId) || null;
}

function openExamModes(quizId) {
    const quiz = quizById(quizId);
    if (quiz && quiz.access === "scheduled") return;
    examState.activeQuizId = quizId;
    const title = document.getElementById("exam-mode-title");
    if (title) title.textContent = quiz ? quiz.title : "Test";
    examShow("exam-mode-modal");
}

function closeExamModeModal() {
    examHide("exam-mode-modal");
}

async function startElectronicExam() {
    const quizId = examState.activeQuizId;
    if (!quizId) return;
    closeExamModeModal();
    try {
        const res = await fetch(`/api/exams/questions/${quizId}`);
        const data = await res.json();
        if (!res.ok) throw new Error("Savollar yo'q");
        examState.play = {
            quiz: data.quiz,
            questions: data.questions || [],
            index: 0,
            answers: {},
            finished: false,
        };
        const title = document.getElementById("exam-play-title");
        if (title) title.textContent = data.quiz?.title || "Elektron test";
        examSetHide("exam-play-footer", false);
        examShow("exam-play-layer");
        renderExamPlay();
        startExamCountdown(data.quiz?.duration_minutes || 20);
    } catch (err) {
        alert("Elektron testni ochib bo'lmadi.");
    }
}

function renderExamPlay() {
    const play = examState.play;
    if (!play || play.finished) return;
    const grid = document.getElementById("exam-play-grid");
    const body = document.getElementById("exam-play-body");
    if (!grid || !body) return;
    grid.innerHTML = play.questions.map((question, index) => {
        const answered = Object.prototype.hasOwnProperty.call(play.answers, question.id);
        const current = index === play.index;
        let cls = "w-8 h-8 rounded-full text-[11px] font-bold border cursor-pointer ";
        if (current) cls += "border-emerald-300 bg-emerald-500/20 text-emerald-200";
        else if (answered) cls += "border-emerald-500 bg-emerald-500 text-slate-950";
        else cls += "border-[#1F2937] bg-[#161F30] text-slate-400";
        return `<button type="button" onclick="examJump(${index})" class="${cls}">${index + 1}</button>`;
    }).join("");

    renderCurrentQuestion();
    const back = document.getElementById("exam-back-btn");
    if (back) back.disabled = play.index === 0;
    const forward = document.getElementById("exam-forward-btn");
    if (forward) {
        const answered = play.questions.filter((item) => Object.prototype.hasOwnProperty.call(play.answers, item.id)).length;
        const finish = play.index >= play.questions.length - 1 || answered >= play.questions.length;
        forward.textContent = finish ? "Yakunlash" : "Oldinga";
        forward.dataset.mode = finish ? "finish" : "next";
    }
}

function renderCurrentQuestion() {
    const play = examState.play;
    const body = document.getElementById("exam-play-body");
    if (!play || !body || play.finished) return;
    const question = play.questions[play.index];
    if (!question) {
        body.innerHTML = '<p class="text-xs text-slate-400">Bu testda savollar yo\'q.</p>';
        return;
    }
    const labels = ["A", "B", "C", "D"];
    const options = (question.options || []).map((text, optIndex) => {
        const selected = play.answers[question.id] === optIndex;
        const cls = selected
            ? "bg-emerald-500/10 border-emerald-500 text-emerald-200"
            : "bg-[#111827] border-[#1F2937] text-slate-200";
        const badge = selected
            ? "border-emerald-400 bg-emerald-500 text-slate-950"
            : "border-[#1F2937] bg-[#161F30] text-slate-400";
        return `
            <button type="button" onclick="examChoose(${question.id}, ${optIndex})" class="w-full text-left p-3 rounded-xl border text-xs font-medium flex items-center gap-3 cursor-pointer ${cls}">
                <span class="w-6 h-6 rounded-lg flex items-center justify-center text-[11px] font-bold border shrink-0 ${badge}">${labels[optIndex]}</span>
                <span class="exam-math flex-1">${examEsc(text)}</span>
            </button>
        `;
    }).join("");
    const text = question.question_text || question.text || "";
    body.innerHTML = `
        <p class="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-1">Savol ${play.index + 1} / ${play.questions.length}</p>
        ${examFigure(question.image_top)}
        <p class="exam-math text-sm font-semibold text-slate-100 leading-relaxed mb-3">${examEsc(text)}</p>
        ${examFigure(question.image_bottom)}
        <div class="space-y-2">${options}</div>
    `;
    examRenderMath(body);
}

function examJump(index) {
    if (!examState.play) return;
    examState.play.index = index;
    renderExamPlay();
}

function examChoose(questionId, optionIndex) {
    if (!examState.play) return;
    examState.play.answers[questionId] = optionIndex;
    renderExamPlay();
}

function examPlayBack() {
    if (!examState.play || examState.play.index <= 0) return;
    examState.play.index -= 1;
    renderExamPlay();
}

function examPlayForward() {
    const play = examState.play;
    if (!play) return;
    const forward = document.getElementById("exam-forward-btn");
    if (forward && forward.dataset.mode === "finish") {
        const answered = play.questions.filter((item) => Object.prototype.hasOwnProperty.call(play.answers, item.id)).length;
        if (answered < play.questions.length) {
            const ok = confirm(`Belgilanmagan savollar bor (${answered}/${play.questions.length}). Yakunlaysizmi?`);
            if (!ok) return;
        }
        submitElectronicExam(false);
        return;
    }
    if (play.index < play.questions.length - 1) {
        play.index += 1;
        renderExamPlay();
    }
}

function startExamCountdown(minutes) {
    stopExamCountdown();
    examTimerLeft = Math.max(1, Number(minutes) || 20) * 60;
    const box = document.getElementById("test-timer-box");
    if (box) box.style.display = "flex";
    const paint = () => {
        const m = String(Math.floor(examTimerLeft / 60)).padStart(2, "0");
        const s = String(examTimerLeft % 60).padStart(2, "0");
        const label = `${m}:${s}`;
        const headerTimer = document.getElementById("timer");
        const playTimer = document.getElementById("exam-play-timer");
        if (headerTimer) headerTimer.textContent = label;
        if (playTimer) playTimer.textContent = label;
    };
    paint();
    examTimerHandle = setInterval(() => {
        if (examTimerLeft <= 1) {
            examTimerLeft = 0;
            paint();
            stopExamCountdown();
            submitElectronicExam(true);
            return;
        }
        examTimerLeft -= 1;
        paint();
    }, 1000);
}

function stopExamCountdown() {
    if (examTimerHandle) {
        clearInterval(examTimerHandle);
        examTimerHandle = null;
    }
    const box = document.getElementById("test-timer-box");
    if (box) box.style.display = "none";
}

async function submitElectronicExam(isTimeout) {
    const play = examState.play;
    if (!play || play.finished || examSubmitting) return;
    examSubmitting = true;
    play.finished = true;
    stopExamCountdown();
    const answers = {};
    Object.keys(play.answers).forEach((key) => {
        answers[String(key)] = play.answers[key];
    });
    try {
        const res = await fetch("/api/exams/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                quiz_id: play.quiz.id,
                telegram_id: examTgId(),
                mode: "elektron",
                answers,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Yuborilmadi");
        renderExamSubmitResult(data, isTimeout);
        loadExamCards();
    } catch (err) {
        play.finished = false;
        alert("Javoblarni saqlashda xatolik yuz berdi.");
        renderExamPlay();
    } finally {
        examSubmitting = false;
    }
}

function renderExamSubmitResult(data, isTimeout) {
    examSetHide("exam-play-footer", true);
    const grid = document.getElementById("exam-play-grid");
    if (grid) grid.innerHTML = "";
    const body = document.getElementById("exam-play-body");
    if (!body) return;
    body.innerHTML = `
        <div class="py-8 flex flex-col items-center text-center">
            <div class="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-3xl flex items-center justify-center mb-3">🏆</div>
            <h3 class="text-base font-extrabold text-white">${isTimeout ? "Vaqt tugadi" : "Test yakunlandi"}</h3>
            <p class="text-3xl font-extrabold text-emerald-400 mt-2">θ ${data.theta != null ? Number(data.theta).toFixed(2) : "—"}</p>
            <p class="text-xs text-slate-300 mt-1">To'g'ri javoblar: ${data.score} / ${data.total} · ${data.percent}%</p>
            <p class="mt-2 text-[11px] font-bold px-2 py-1 rounded-lg border ${examLevelClass(data.level)}">Daraja: ${examEsc(data.grade || data.level || "")}</p>
            <p class="text-xs text-amber-300 mt-3">${examEsc(data.rank_label || "")}</p>
            <p class="text-[11px] text-slate-500 mt-2">Natija admin ro'yxatiga saqlandi.</p>
            <button type="button" onclick="closeExamPlay()" class="mt-4 px-4 py-2.5 bg-[#161F30] border border-[#283548] rounded-xl text-xs font-semibold text-white cursor-pointer">Yopish</button>
        </div>
    `;
}

function closeExamPlay() {
    stopExamCountdown();
    examState.play = null;
    examHide("exam-play-layer");
}

function openExamPaper() {
    const quizId = examState.activeQuizId;
    if (!quizId) return;
    closeExamModeModal();
    const quiz = quizById(quizId);
    const title = document.getElementById("exam-paper-title");
    if (title) title.textContent = quiz ? quiz.title : "Qog'oz test";
    examState.paperKind = "test";
    examShow("exam-paper-modal");
    setExamPaperKind("test");
}

function closeExamPaper() {
    const frame = document.getElementById("exam-paper-frame");
    if (frame) frame.src = "about:blank";
    examHide("exam-paper-modal");
}

function setExamPaperKind(kind) {
    examState.paperKind = kind === "answers" ? "answers" : "test";
    const quizId = examState.activeQuizId;
    const testTab = document.getElementById("exam-paper-tab-test");
    const answerTab = document.getElementById("exam-paper-tab-answers");
    if (testTab && answerTab) {
        const on = "flex-1 py-2 text-[11px] font-bold rounded-xl bg-emerald-500 text-slate-950 cursor-pointer";
        const off = "flex-1 py-2 text-[11px] font-bold rounded-xl bg-[#161F30] border border-[#283548] text-slate-300 cursor-pointer";
        testTab.className = examState.paperKind === "test" ? on : off;
        answerTab.className = examState.paperKind === "answers" ? on : off;
    }
    const note = document.getElementById("exam-paper-note");
    if (note) {
        note.textContent = examState.paperKind === "test"
            ? "Test varaqasiga sizning ismingiz va ID raqamingiz suv belgisi sifatida tushirilgan."
            : "Javoblar varaqasi toza — shaxsiy ma'lumot tushirilmagan.";
    }
    const base = `/api/exams/paper/${quizId}?telegram_id=${examTgId()}&kind=${examState.paperKind}`;
    const frame = document.getElementById("exam-paper-frame");
    if (frame) frame.src = base;
    const link = document.getElementById("exam-paper-download");
    if (link) link.href = `${base}&download=1`;
}

async function openExamScanner() {
    const quizId = examState.activeQuizId;
    if (!quizId) return;
    closeExamModeModal();
    examSetHide("exam-scan-still", true);
    examSetHide("exam-scan-fallback", true);
    const video = document.getElementById("exam-scan-video");
    if (video) video.classList.remove("ph-hide");
    const status = document.getElementById("exam-scan-status");
    if (status) status.textContent = "Kamera ochilmoqda...";
    const capture = document.getElementById("exam-scan-capture");
    if (capture) {
        capture.textContent = "Rasmga olish";
        capture.onclick = captureExamSheet;
    }
    examShow("exam-scan-modal");
    stopExamCamera();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (status) status.textContent = "Bu qurilmada kamera ochilmadi.";
        examSetHide("exam-scan-fallback", false);
        return;
    }
    try {
        examScanStream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { ideal: "environment" } },
        });
        if (video) {
            video.srcObject = examScanStream;
            await video.play();
        }
        if (status) status.textContent = "Varaqani ramka ichiga qo'yib, rasmga oling.";
    } catch (err) {
        if (status) status.textContent = "Kameraga ruxsat berilmadi. Sinov varaqasini yuborishingiz mumkin.";
        examSetHide("exam-scan-fallback", false);
    }
}

function stopExamCamera() {
    if (examScanStream) {
        examScanStream.getTracks().forEach((track) => track.stop());
        examScanStream = null;
    }
    const video = document.getElementById("exam-scan-video");
    if (video) video.srcObject = null;
}

function closeExamScanner() {
    stopExamCamera();
    examHide("exam-scan-modal");
}

function drawSheetOnCanvas(fromVideo) {
    const canvas = document.getElementById("exam-scan-canvas");
    const video = document.getElementById("exam-scan-video");
    if (!canvas) return "";
    const width = fromVideo && video && video.videoWidth ? video.videoWidth : 720;
    const height = fromVideo && video && video.videoHeight ? video.videoHeight : 960;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (fromVideo && video && video.videoWidth) {
        ctx.drawImage(video, 0, 0, width, height);
    } else {
        ctx.fillStyle = "#f8fafc";
        ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 4;
        ctx.strokeRect(40, 40, width - 80, height - 80);
        ctx.fillStyle = "#0f172a";
        ctx.font = "28px sans-serif";
        ctx.fillText("PHAROS javoblar varaqasi", 70, 100);
        ctx.font = "20px sans-serif";
        for (let i = 1; i <= 5; i += 1) {
            ctx.fillText(`${i}.  (A)  (B)  (C)  (D)`, 70, 140 + i * 48);
        }
    }
    return canvas.toDataURL("image/jpeg", 0.72);
}

async function captureExamSheet() {
    const dataUrl = drawSheetOnCanvas(true);
    if (!dataUrl) return;
    const still = document.getElementById("exam-scan-still");
    const video = document.getElementById("exam-scan-video");
    if (still) {
        still.src = dataUrl;
        examSetHide("exam-scan-still", false);
    }
    if (video) video.classList.add("ph-hide");
    stopExamCamera();
    await submitScanImage(dataUrl);
}

async function submitSimulatedSheet() {
    const dataUrl = drawSheetOnCanvas(false);
    const still = document.getElementById("exam-scan-still");
    if (still) {
        still.src = dataUrl;
        examSetHide("exam-scan-still", false);
    }
    await submitScanImage(dataUrl);
}

async function submitScanImage(dataUrl) {
    const quizId = examState.activeQuizId;
    const status = document.getElementById("exam-scan-status");
    const capture = document.getElementById("exam-scan-capture");
    if (status) status.textContent = "Javoblar tekshirilmoqda...";
    if (capture) capture.disabled = true;
    try {
        const res = await fetch("/api/exams/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                quiz_id: quizId,
                telegram_id: examTgId(),
                mode: "skaner",
                answers: {},
                image_base64: dataUrl,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Skaner natijasi saqlanmadi");
        if (status) {
            status.innerHTML = `Natija: <b class="text-emerald-300">${data.score}/${data.total}</b> · ${data.percent}% · ${examEsc(data.level)}<br>${examEsc(data.rank_label)}. Admin ro'yxatiga yuborildi.`;
        }
        if (capture) {
            capture.disabled = false;
            capture.textContent = "Yopish";
            capture.onclick = closeExamScanner;
        }
        loadExamCards();
    } catch (err) {
        if (status) status.textContent = "Skanerni tekshirishda xatolik yuz berdi.";
        if (capture) capture.disabled = false;
    }
}

async function openExamLeaderboard(quizId) {
    examState.activeQuizId = quizId;
    const quiz = quizById(quizId);
    const title = document.getElementById("exam-board-title");
    if (title) title.textContent = quiz ? quiz.title : "Reyting";
    const badge = document.getElementById("exam-board-myrank");
    if (badge) {
        badge.textContent = "Reyting yuklanmoqda...";
        badge.className = "mt-3 text-center text-xs font-extrabold text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-xl py-2.5 px-3 leading-relaxed";
    }
    examShow("exam-board-modal");
    if (window.lucide) lucide.createIcons();
    await loadExamLeaderboard();
}

function closeExamLeaderboard() {
    examHide("exam-board-modal");
}

function openExamShareSheet(quizId) {
    const quiz = quizById(quizId);
    if (!quiz || !quiz.link) return;
    examState.shareQuizId = quizId;
    examState.shareLink = quiz.link;
    const title = document.getElementById("exam-share-title");
    const linkEl = document.getElementById("exam-share-link");
    if (title) title.textContent = quiz.title || "Test";
    if (linkEl) linkEl.textContent = quiz.link;
    examShow("exam-share-sheet");
}

function closeExamShareSheet() {
    examHide("exam-share-sheet");
}

function shareExamViaTelegram() {
    const link = examState.shareLink;
    if (!link) return;
    const quiz = quizById(examState.shareQuizId);
    const text = quiz ? `${quiz.title} — PHAROS test` : "PHAROS test";
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`;
    const tg = window.Telegram?.WebApp;
    if (tg && typeof tg.openTelegramLink === "function") {
        tg.openTelegramLink(shareUrl);
    } else {
        window.open(shareUrl, "_blank");
    }
}

async function copyExamShareLink() {
    const link = examState.shareLink;
    if (!link) return;
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(link);
        } else {
            const input = document.createElement("textarea");
            input.value = link;
            document.body.appendChild(input);
            input.select();
            document.execCommand("copy");
            document.body.removeChild(input);
        }
        alert("Havola nusxalandi!");
    } catch (err) {
        alert("Nusxa olishda xatolik. Havolani qo'lda belgilang.");
    }
}

function examRankRowClass(rank) {
    if (rank === 1) {
        return "border-amber-500/40 bg-gradient-to-r from-amber-500/10 to-transparent";
    }
    if (rank === 2) {
        return "border-slate-300/40 bg-gradient-to-r from-slate-300/10 to-transparent";
    }
    if (rank === 3) {
        return "border-amber-700/40 bg-gradient-to-r from-amber-700/10 to-transparent";
    }
    return "border-[#1F2937] bg-[#111827]";
}

function examRankBadge(rank) {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return String(rank);
}

function fillRegionSelect(map) {
    const regionSelect = document.getElementById("exam-board-region");
    if (!regionSelect || regionSelect.dataset.ready === "1") return;
    const current = regionSelect.value;
    const options = ['<option value="">Barcha viloyatlar</option>'];
    Object.keys(map || {}).forEach((name) => {
        options.push(`<option value="${examEsc(name)}">${examEsc(name)}</option>`);
    });
    regionSelect.innerHTML = options.join("");
    regionSelect.value = current;
    regionSelect.dataset.ready = "1";
}

function refillDistrictSelect() {
    const regionSelect = document.getElementById("exam-board-region");
    const districtSelect = document.getElementById("exam-board-district");
    if (!districtSelect) return;
    const region = regionSelect ? regionSelect.value : "";
    const previous = districtSelect.value;
    const names = region && examState.regionsMap ? (examState.regionsMap[region] || []) : [];
    const options = ['<option value="">Barcha tumanlar</option>'];
    names.forEach((name) => options.push(`<option value="${examEsc(name)}">${examEsc(name)}</option>`));
    districtSelect.innerHTML = options.join("");
    districtSelect.value = names.includes(previous) ? previous : "";
}

async function onExamBoardRegionChange() {
    refillDistrictSelect();
    await loadExamLeaderboard();
}

async function loadExamLeaderboard() {
    const quizId = examState.activeQuizId;
    const list = document.getElementById("exam-board-list");
    const badge = document.getElementById("exam-board-myrank");
    if (!quizId || !list) return;
    const region = document.getElementById("exam-board-region")?.value || "";
    const district = document.getElementById("exam-board-district")?.value || "";
    list.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Reyting yuklanmoqda...</p>';
    try {
        const params = new URLSearchParams({
            telegram_id: String(examTgId()),
            region,
            district,
        });
        const res = await fetch(`/api/exams/leaderboard/${quizId}?${params.toString()}`);
        const data = await res.json();
        if (!examState.regionsMap && data.regions_map) {
            examState.regionsMap = data.regions_map;
            fillRegionSelect(data.regions_map);
            refillDistrictSelect();
        }
        if (badge) {
            const foreign = data.my_scope === "foreign";
            if (foreign) {
                badge.textContent = data.my_label || "Siz bu hududga tegishli emassiz";
                badge.className = "mt-3 text-center text-xs font-semibold text-slate-400 bg-[#0A0E17] border border-[#1F2937] rounded-xl py-2.5 px-3 leading-relaxed";
            } else {
                badge.textContent = data.my_label || "Siz hali bu testda ishtirok etmadingiz";
                badge.className = "mt-3 text-center text-xs font-extrabold text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-xl py-2.5 px-3 leading-relaxed";
            }
        }
        const items = data.items || [];
        if (!items.length) {
            list.innerHTML = '<p class="text-xs text-slate-500 text-center py-8">Bu filtr bo\'yicha natijalar yo\'q.</p>';
            return;
        }
        list.innerHTML = items.map((item) => {
            const ball = item.ball != null ? item.ball : item.score;
            const rash = item.rash || (item.theta != null
                ? `${Number(item.theta).toFixed(2)}${item.level ? ` (${item.level})` : ""}`
                : "—");
            return `
            <div class="rounded-2xl border px-2.5 py-2.5 grid grid-cols-[2rem_1fr_3.5rem_4.5rem] gap-1 items-center ${examRankRowClass(item.rank)}">
                <div class="text-center font-extrabold text-sm ${item.rank <= 3 ? "text-amber-300" : "text-slate-400"}">${examRankBadge(item.rank)}</div>
                <div class="min-w-0">
                    <button type="button" onclick="openExamStudent(${item.telegram_id}, ${quizId})" class="text-left text-xs font-bold text-emerald-300 underline truncate block cursor-pointer">${examEsc(item.full_name)}</button>
                    <p class="text-[10px] text-slate-400 truncate">${examEsc(item.place)}</p>
                </div>
                <div class="text-right">
                    <p class="text-xs font-extrabold text-white">${ball != null ? ball : "—"}</p>
                    <p class="text-[9px] text-slate-500">ball</p>
                </div>
                <div class="text-right">
                    <p class="text-[11px] font-extrabold text-emerald-300 leading-tight">${examEsc(rash)}</p>
                    <p class="text-[9px] text-slate-500">RASH</p>
                </div>
            </div>`;
        }).join("");
    } catch (err) {
        list.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Reytingni yuklashda xatolik.</p>';
    }
}

async function openExamAnalysisModal(quizId) {
    examState.activeQuizId = quizId;
    const title = document.getElementById("exam-analysis-title");
    const quiz = quizById(quizId);
    if (title) title.textContent = quiz ? quiz.title : "Tahlil";
    const list = document.getElementById("exam-analysis-list");
    if (list) list.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Tahlil yuklanmoqda...</p>';
    examShow("exam-analysis-modal");
    try {
        const res = await fetch(`/api/exams/analysis/${quizId}?telegram_id=${examTgId()}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Tahlil yo'q");
        examState.analysis = data;
        const score = document.getElementById("exam-analysis-score");
        if (score) {
            if (data.locked) {
                score.textContent = data.lock_message || "Tahlil hali ochilmagan";
            } else if (data.has_submission) {
                const thetaBit = data.theta != null ? ` · θ ${Number(data.theta).toFixed(2)}` : "";
                score.textContent = `So'nggi natija: ${data.score}/${data.total} · ${data.percent}%${thetaBit} · ${data.level}`;
            } else {
                score.textContent = "Siz hali bu testni topshirmagansiz. To'g'ri javoblar va manbalar ochiq.";
            }
        }
        const note = document.getElementById("exam-analysis-note");
        if (note) note.textContent = data.locked ? "" : (data.analysis_text || "");
        if (!list) return;
        if (data.locked) {
            list.innerHTML = `<p class="text-xs text-amber-200 text-center py-8 leading-relaxed">${examEsc(data.lock_message || "Tahlil test boshlangach ochiladi.")}</p>`;
            return;
        }
        const fullVideo = data.full_analysis_video
            ? `<button type="button" onclick="openExamFullAnalysisVideo()" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-extrabold text-white cursor-pointer">🎬 Barcha testlar tahlili (Video)</button>`
            : "";
        const questionsHtml = (data.questions || []).map((question, index) => {
            const mark = !data.has_submission ? "" : (question.is_correct ? " · to'g'ri" : " · xato");
            const solution = question.solution_text || question.analysis_text || "";
            const prompt = question.question_text || question.text || "";
            return `
                <div class="bg-[#0A0E17] border border-[#1F2937] rounded-2xl overflow-hidden">
                    <button type="button" onclick="toggleExamAccordion(${index})" class="w-full px-3 py-2.5 flex items-center gap-2 text-left cursor-pointer">
                        <span class="text-[11px] font-bold text-slate-400 w-5">${question.order}</span>
                        <span class="exam-math flex-1 text-xs font-semibold text-slate-100">${examEsc(prompt)}</span>
                        <i id="exam-acc-icon-${index}" data-lucide="chevron-down" class="w-4 h-4 text-slate-400 shrink-0"></i>
                    </button>
                    <div id="exam-acc-${index}" class="ph-hide px-3 pb-3">
                        <p class="text-[10px] text-slate-500 mb-2">${examEsc(question.direction)} · ${examEsc(question.topic)} · ${examEsc(question.difficulty_label)}${examEsc(mark)}</p>
                        ${examFigure(question.image_top)}
                        <p class="exam-math text-xs text-slate-100 leading-relaxed mb-2">${examEsc(prompt)}</p>
                        ${examFigure(question.image_bottom)}
                        <div class="space-y-1.5">
                            ${(question.options || []).map((option) => {
                                let cls = "border-[#1F2937] bg-[#111827]";
                                if (option.is_correct) cls = "border-emerald-500/60 bg-emerald-500/10";
                                if (option.is_user_choice && !option.is_correct) cls = "border-rose-500/60 bg-rose-500/10";
                                const tag = option.is_correct ? "To'g'ri javob" : (option.is_user_choice ? "Sizning javobingiz" : "");
                                return `
                                    <div class="rounded-xl border px-2.5 py-2 ${cls}">
                                        <p class="exam-math text-[11px] text-slate-100"><b>${option.key}.</b> ${examEsc(option.text)}</p>
                                        ${tag ? `<p class="text-[10px] mt-0.5 ${option.is_correct ? "text-emerald-300" : "text-rose-300"}">${tag}</p>` : ""}
                                        ${option.source ? `<p class="text-[10px] text-amber-200/90 mt-1">Manba: ${examEsc(option.source)}</p>` : ""}
                                    </div>
                                `;
                            }).join("")}
                        </div>
                        ${solution ? `<p class="exam-math text-[11px] text-slate-300 mt-2 leading-relaxed whitespace-pre-line">${examEsc(solution)}</p>` : ""}
                        ${question.video_solution_url ? `<button type="button" onclick="openExamQuestionVideo(${index})" class="mt-2 w-full py-2 rounded-xl bg-[#161F30] border border-emerald-500/40 text-[11px] font-bold text-emerald-300 cursor-pointer">🎬 Shu savol tahlili</button>` : ""}
                    </div>
                </div>
            `;
        }).join("");
        list.innerHTML = `${fullVideo}${questionsHtml}`;
        examRenderMath(list);
        if (window.lucide) lucide.createIcons();
    } catch (err) {
        if (list) list.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Tahlilni yuklashda xatolik.</p>';
    }
}

function openExamAnalysis(quizId) {
    return openExamAnalysisModal(quizId);
}

function openExamFullAnalysisVideo() {
    const url = examState.analysis && examState.analysis.full_analysis_video;
    if (!url) return;
    openExamVideo(url, "Barcha testlar tahlili");
}

function openExamQuestionVideo(index) {
    const question = examState.analysis && examState.analysis.questions && examState.analysis.questions[index];
    if (!question || !question.video_solution_url) return;
    openExamVideo(question.video_solution_url, `Savol ${question.order} tahlili`);
}

function openExamImageZoom(url) {
    if (!url) return;
    const img = document.getElementById("exam-zoom-img");
    if (img) img.src = url;
    examShow("exam-zoom-modal");
}

function closeExamImageZoom() {
    const img = document.getElementById("exam-zoom-img");
    if (img) img.removeAttribute("src");
    examHide("exam-zoom-modal");
}

function openExamVideo(url, title) {
    const slot = document.getElementById("exam-video-slot");
    const titleEl = document.getElementById("exam-video-title");
    if (titleEl) titleEl.textContent = title || "Video tahlil";
    if (slot) slot.innerHTML = examVideoEmbed(url);
    examShow("exam-video-modal");
}

function closeExamVideo() {
    const slot = document.getElementById("exam-video-slot");
    if (slot) slot.innerHTML = "";
    examHide("exam-video-modal");
}

function toggleExamAccordion(index) {
    const panel = document.getElementById(`exam-acc-${index}`);
    const icon = document.getElementById(`exam-acc-icon-${index}`);
    if (!panel) return;
    const willOpen = panel.classList.contains("ph-hide");
    panel.classList.toggle("ph-hide", !willOpen);
    if (icon) icon.setAttribute("data-lucide", willOpen ? "chevron-up" : "chevron-down");
    if (window.lucide) lucide.createIcons();
}

function closeExamAnalysis() {
    examHide("exam-analysis-modal");
}

function openExamDiagnostics() {
    const data = examState.analysis;
    const body = document.getElementById("exam-diag-body");
    if (!body) return;
    if (!data) {
        body.innerHTML = '<p class="text-xs text-slate-400 text-center py-6">Avval tahlilni oching.</p>';
    } else if (!data.has_submission) {
        body.innerHTML = '<p class="text-xs text-slate-300 text-center py-6 leading-relaxed">Diagnostika sizning javoblaringiz saqlangach ochiladi. Testni elektron yoki skaner rejimida topshiring.</p>';
    } else {
        const rows = data.diagnostics || [];
        body.innerHTML = `
            <table class="w-full text-left text-[10px] border-collapse">
                <thead>
                    <tr class="text-slate-400">
                        <th class="py-2 pr-2 font-bold">Yo'nalish</th>
                        <th class="py-2 pr-2 font-bold">Mavzu</th>
                        <th class="py-2 pr-2 font-bold">Qiyinlik</th>
                        <th class="py-2 pr-2 font-bold">Jami</th>
                        <th class="py-2 font-bold">Xato</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map((row) => `
                        <tr class="border-t border-[#1F2937] ${row.wrong ? "text-rose-200" : "text-slate-200"}">
                            <td class="py-2 pr-2 align-top">${examEsc(row.direction)}</td>
                            <td class="py-2 pr-2 align-top">${examEsc(row.topic)}</td>
                            <td class="py-2 pr-2 align-top">${examEsc(row.difficulty_label)}</td>
                            <td class="py-2 pr-2 align-top">${row.total}</td>
                            <td class="py-2 align-top font-bold">${row.wrong}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
            <p class="text-[10px] text-slate-500 mt-3">Xato qatorlar qizg'ish rangda. O'zlashtirish foizi har bir satr bo'yicha hisoblangan.</p>
            <div class="mt-2 space-y-1">
                ${rows.filter((row) => row.wrong > 0).map((row) => `<p class="text-[10px] text-slate-300">${examEsc(row.direction)} / ${examEsc(row.topic)} / ${examEsc(row.difficulty_label)} — o'zlashtirish ${row.mastery}%</p>`).join("") || '<p class="text-[11px] text-emerald-300">Bu urinishda yo\'nalish bo\'yicha xato qolmagan.</p>'}
            </div>
        `;
    }
    examShow("exam-diag-modal");
}

function closeExamDiagnostics() {
    examHide("exam-diag-modal");
}

async function openExamStudent(telegramId, quizId) {
    const body = document.getElementById("exam-student-body");
    if (body) body.innerHTML = '<p class="text-xs text-slate-400 text-center py-4">Profil yuklanmoqda...</p>';
    examShow("exam-student-modal");
    try {
        const res = await fetch(`/api/exams/student/${telegramId}?quiz_id=${quizId || examState.activeQuizId || ""}`);
        const data = await res.json();
        if (!body) return;
        const avatar = data.avatar_url
            ? `<img src="${examEsc(data.avatar_url)}" alt="" class="w-16 h-16 rounded-full object-cover border border-emerald-500/40">`
            : `<div class="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center text-2xl">👤</div>`;
        body.innerHTML = `
            <div class="flex flex-col items-center text-center -mt-2">
                ${avatar}
                <h3 class="text-sm font-extrabold text-white mt-2">${examEsc(data.full_name)}</h3>
                <p class="text-[11px] text-slate-400 mt-0.5">${examEsc(data.region)}, ${examEsc(data.district)}</p>
                <span class="mt-2 text-[10px] font-bold px-2 py-1 rounded-lg border ${examLevelClass(data.level)}">${examEsc(data.level || "Boshlang'ich")}</span>
                <div class="grid grid-cols-2 gap-2 w-full mt-3 text-left">
                    <div class="bg-[#0A0E17] border border-[#1F2937] rounded-xl p-2">
                        <p class="text-[10px] text-slate-500">Shu testdagi o'rni</p>
                        <p class="text-sm font-extrabold text-amber-300">${data.quiz_rank ? data.quiz_rank + "-o'rin" : "—"}</p>
                    </div>
                    <div class="bg-[#0A0E17] border border-[#1F2937] rounded-xl p-2">
                        <p class="text-[10px] text-slate-500">Ball</p>
                        <p class="text-sm font-extrabold text-white">${data.quiz_score != null ? data.quiz_score + "/" + data.quiz_total : "—"}</p>
                    </div>
                    <div class="bg-[#0A0E17] border border-[#1F2937] rounded-xl p-2">
                        <p class="text-[10px] text-slate-500">Topshirgan testlar</p>
                        <p class="text-sm font-extrabold text-white">${data.exams_taken || 0}</p>
                    </div>
                    <div class="bg-[#0A0E17] border border-[#1F2937] rounded-xl p-2">
                        <p class="text-[10px] text-slate-500">Eng yuqori foiz</p>
                        <p class="text-sm font-extrabold text-emerald-300">${data.best_percent != null ? data.best_percent + "%" : "—"}</p>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        if (body) body.innerHTML = '<p class="text-xs text-rose-400 text-center py-4">Profilni ochib bo\'lmadi.</p>';
    }
}

function closeExamStudent() {
    examHide("exam-student-modal");
}

function closeAllExamOverlays() {
    ["exam-mode-modal", "exam-play-layer", "exam-paper-modal", "exam-scan-modal", "exam-board-modal", "exam-analysis-modal", "exam-diag-modal", "exam-student-modal", "exam-zoom-modal", "exam-video-modal", "exam-share-sheet"].forEach(examHide);
    stopExamCountdown();
    stopExamCamera();
    const videoSlot = document.getElementById("exam-video-slot");
    if (videoSlot) videoSlot.innerHTML = "";
    const frame = document.getElementById("exam-paper-frame");
    if (frame) frame.src = "about:blank";
}
