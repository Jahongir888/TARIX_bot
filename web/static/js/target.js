// web/static/js/target.js

let currentSelectedInstType = 'otm';
let targetListOffset = 0;
const TARGET_PAGE_SIZE = 24;
let targetListTotal = 0;
let targetReqToken = 0;
let targetExam = null;
let targetExamTimer = null;

const TARGET_ALL_DIRECTION = "";
const TARGET_ALL_BLOCK = "";
const TARGET_ALL_REGION = "";

function escTarget(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[ch]));
}

function fmtTargetScore(value) {
    if (value === null || value === undefined || value === '') return '—';
    const num = Number(value);
    if (Number.isNaN(num)) return '—';
    return Number.isInteger(num) ? String(num) : num.toFixed(1);
}

function fillTargetSelect(select, values, placeholder) {
    if (!select) return;
    const previous = select.value;
    const options = [`<option value="">${escTarget(placeholder)}</option>`]
        .concat(values.map((item) => `<option value="${escTarget(item)}">${escTarget(item)}</option>`));
    select.innerHTML = options.join('');
    if (previous && values.includes(previous)) {
        select.value = previous;
    }
}

async function initTargetSection() {
    await loadFilterDropdowns(false);
    targetListOffset = 0;
    await loadTargetCards(false);
}

async function loadFilterDropdowns(resetValues) {
    const dirSelect = document.getElementById('target-filter-direction');
    const blockSelect = document.getElementById('target-filter-subject-block');
    const regSelect = document.getElementById('target-filter-region');
    if (resetValues) {
        if (dirSelect) dirSelect.value = '';
        if (blockSelect) blockSelect.value = '';
        if (regSelect) regSelect.value = '';
    }
    try {
        const res = await fetch(`/api/target/filter-options?inst_type=${encodeURIComponent(currentSelectedInstType)}`);
        const data = await res.json();
        fillTargetSelect(dirSelect, data.directions || [], "Barcha yo'nalishlar");
        fillTargetSelect(blockSelect, data.subject_blocks || [], 'Barcha fanlar majmuasi');
        fillTargetSelect(regSelect, data.regions || [], 'Barcha viloyatlar');
    } catch (e) {
        console.error("Filtr ma'lumotlarini yuklashda xatolik:", e);
    }
}

function selectTargetInstType(type) {
    currentSelectedInstType = type;
    document.querySelectorAll('.target-type-chip').forEach((btn) => {
        btn.className = "target-type-chip py-2 px-2.5 rounded-xl text-xs font-semibold bg-[#161F30] border border-[#283548] text-slate-300 hover:border-emerald-500/50 transition-all active:scale-95 cursor-pointer text-center truncate";
    });
    const activeBtn = document.getElementById(`target-chip-${type}`);
    if (activeBtn) {
        activeBtn.className = "target-type-chip py-2 px-2.5 rounded-xl text-xs font-bold bg-emerald-500 text-slate-950 shadow-md transition-all active:scale-95 cursor-pointer text-center truncate";
    }
    targetListOffset = 0;
    loadFilterDropdowns(true).then(() => loadTargetCards(false));
}

function onTargetFilterChange() {
    targetListOffset = 0;
    loadTargetCards(false);
}

function targetFilterParams() {
    return {
        direction: document.getElementById('target-filter-direction')?.value || TARGET_ALL_DIRECTION,
        subject_block: document.getElementById('target-filter-subject-block')?.value || TARGET_ALL_BLOCK,
        region: document.getElementById('target-filter-region')?.value || TARGET_ALL_REGION
    };
}

function renderTargetCard(card) {
    const formLang = [card.edu_form, card.edu_lang].filter(Boolean).join(' · ') || '—';
    const mandatory = card.mandatory_subjects || "Ona tili, Matematika, O'zbekiston tarixi";
    const el = document.createElement('div');
    el.className = "bg-[#111827] border border-[#1F2937] hover:border-[#283548] rounded-2xl p-3.5 shadow-md space-y-2.5 transition-all";
    el.innerHTML = `
        <div class="flex items-start justify-between gap-2 border-b border-[#1F2937] pb-2">
            <div class="min-w-0">
                <span class="text-[9px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md inline-block mb-1">
                    ${escTarget(card.badge)}
                </span>
                <h4 class="text-xs font-extrabold text-white leading-tight">${escTarget(card.inst_name)}</h4>
                <p class="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                    <i data-lucide="map-pin" class="w-3 h-3 text-emerald-400"></i> ${escTarget(card.region)}
                </p>
            </div>
            <span class="text-[10px] font-mono font-bold bg-[#161F30] text-slate-300 border border-[#283548] px-2 py-1 rounded-lg shrink-0">
                ${escTarget(card.cipher || '—')}
            </span>
        </div>
        <div class="bg-[#0A0E17]/80 border border-[#283548]/50 rounded-xl p-2.5 text-xs space-y-1.5">
            <p class="font-bold text-slate-200 text-xs leading-snug">${escTarget(card.direction_title)}</p>
            <p class="text-[10px] text-slate-400">${escTarget(formLang)}</p>
            <div class="flex justify-between items-center pt-1.5 border-t border-[#1F2937] text-[10px] font-mono">
                <span class="text-amber-400">Grant: <b>${fmtTargetScore(card.grant_score)}</b></span>
                <span class="text-slate-300">Kontrakt: <b>${fmtTargetScore(card.contract_score)}</b></span>
            </div>
        </div>
        <div class="bg-[#161F30] border border-[#283548] rounded-xl p-2.5 space-y-1">
            <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Fanlar majmuasi</p>
            <p class="text-[11px] text-slate-200 font-semibold">${escTarget(card.subject_block || '—')}</p>
            <p class="text-[10px] text-slate-400">1-fan: <span class="text-slate-200">${escTarget(card.subject_main)}</span> <span class="text-amber-300">[3.1]</span></p>
            <p class="text-[10px] text-slate-400">2-fan: <span class="text-slate-200">${escTarget(card.subject_second || '—')}</span> <span class="text-amber-300">[2.1]</span></p>
            <p class="text-[10px] text-slate-400">Majburiy blok: <span class="text-slate-200">${escTarget(mandatory)}</span> <span class="text-amber-300">[1.1]</span></p>
        </div>
        <button type="button" data-direction-id="${card.id}" onclick="startTargetDirectionExam(this)"
                class="w-full py-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold rounded-xl active:scale-95 transition-all cursor-pointer">
            Shu yo'nalish bo'yicha test topshirish
        </button>
    `;
    return el;
}

async function loadTargetCards(append) {
    const container = document.getElementById('target-cards-container');
    if (!container) return;
    const token = ++targetReqToken;
    const filters = targetFilterParams();
    if (!append) {
        targetListOffset = 0;
        container.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Yo\'nalishlar saralanmoqda...</p>';
    }

    try {
        const query = new URLSearchParams({
            inst_type: currentSelectedInstType,
            direction: filters.direction,
            subject_block: filters.subject_block,
            region: filters.region,
            limit: String(TARGET_PAGE_SIZE),
            offset: String(append ? targetListOffset : 0)
        });
        const res = await fetch(`/api/target/directions?${query.toString()}`);
        const data = await res.json();
        if (token !== targetReqToken) return;

        const items = data.items || [];
        targetListTotal = data.total || 0;
        targetListOffset = (append ? targetListOffset : 0) + items.length;

        if (!append) container.innerHTML = '';
        const oldMore = document.getElementById('target-load-more-wrap');
        if (oldMore) oldMore.remove();

        if (!items.length && !append) {
            container.innerHTML = `
                <div class="py-10 text-center bg-[#111827] border border-[#1F2937] rounded-2xl p-6">
                    <span class="text-3xl block mb-2">🔍</span>
                    <p class="text-xs text-slate-400">Tanlangan filtrlarga mos yo'nalishlar topilmadi.</p>
                </div>
            `;
            return;
        }

        items.forEach((card) => container.appendChild(renderTargetCard(card)));

        const meta = document.createElement('div');
        meta.id = 'target-load-more-wrap';
        meta.className = 'pt-1 space-y-2';
        meta.innerHTML = `<p class="text-[10px] text-center text-slate-500">${targetListOffset} / ${targetListTotal} ta yo'nalish</p>`;
        if (data.has_more) {
            meta.innerHTML += `
                <button type="button" onclick="loadMoreTargetCards()"
                        class="w-full py-2.5 bg-[#161F30] border border-[#283548] text-xs font-semibold text-slate-200 rounded-xl cursor-pointer">
                    Yana yuklash
                </button>`;
        }
        container.appendChild(meta);
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        if (token !== targetReqToken) return;
        container.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Ma\'lumotlarni yuklashda xatolik yuz berdi.</p>';
    }
}

function loadMoreTargetCards() {
    loadTargetCards(true);
}

function selectedSubjectBlock() {
    return document.getElementById('target-filter-subject-block')?.value || '';
}

function selectedDirectionTitle() {
    return document.getElementById('target-filter-direction')?.value || '';
}

async function openTargetMock(params) {
    const query = new URLSearchParams({ inst_type: currentSelectedInstType });
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && String(value) !== '') {
            query.set(key, value);
        }
    });
    const res = await fetch(`/api/target/start-mock?${query.toString()}`);
    if (!res.ok) {
        let message = "Iltimos, avval Fanlar majmuasini tanlang!";
        try {
            const err = await res.json();
            if (err.detail) message = err.detail;
        } catch (_) { /* server matni yo'q */ }
        alert(message);
        return;
    }
    const exam = await res.json();
    beginTargetExam(exam);
}

async function startTargetHeroExam() {
    const block = selectedSubjectBlock();
    const direction = selectedDirectionTitle();
    if (!block && !direction) {
        alert("Iltimos, avval Fanlar majmuasini tanlang!");
        return;
    }
    try {
        await openTargetMock({ subject_block: block, direction });
    } catch (e) {
        alert("Imtihonni ochib bo'lmadi. Qayta urinib ko'ring.");
    }
}

async function startTargetDirectionExam(button) {
    const directionId = button?.dataset?.directionId;
    if (!directionId) return;
    try {
        await openTargetMock({ direction_id: directionId });
    } catch (e) {
        alert("Imtihonni ochib bo'lmadi. Qayta urinib ko'ring.");
    }
}

function flatExamQuestions() {
    if (!targetExam) return [];
    const flat = [];
    targetExam.blocks.forEach((block, blockIndex) => {
        block.questions.forEach((question, questionIndex) => {
            flat.push({ block, blockIndex, question, questionIndex });
        });
    });
    return flat;
}

function beginTargetExam(exam) {
    targetExam = {
        ...exam,
        cursor: 0,
        answers: {},
        finished: false,
        endsAt: Date.now() + (Number(exam.duration_minutes) || 180) * 60 * 1000
    };
    const modal = document.getElementById('target-exam-modal');
    const play = document.getElementById('target-exam-play');
    const result = document.getElementById('target-exam-result');
    const footer = document.getElementById('target-exam-footer');
    if (!modal || !play || !result) return;
    play.classList.remove('hidden');
    result.classList.add('hidden');
    if (footer) footer.classList.remove('hidden');
    document.getElementById('target-exam-title').textContent = exam.title || 'Namunaviy imtihon';
    const bits = [exam.inst_name, exam.subject_block].filter(Boolean);
    document.getElementById('target-exam-subtitle').textContent = bits.join(' · ');
    modal.classList.remove('hidden');
    renderTargetExam();
    startTargetExamTimer();
}

function startTargetExamTimer() {
    if (targetExamTimer) clearInterval(targetExamTimer);
    const tick = () => {
        const label = document.getElementById('target-exam-timer');
        if (!label || !targetExam) return;
        const left = Math.max(0, targetExam.endsAt - Date.now());
        const totalSec = Math.floor(left / 1000);
        const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
        const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
        const s = String(totalSec % 60).padStart(2, '0');
        label.textContent = `${h}:${m}:${s}`;
        if (left <= 0 && !targetExam.finished) finishTargetExam();
    };
    tick();
    targetExamTimer = setInterval(tick, 1000);
}

function closeTargetExam() {
    const modal = document.getElementById('target-exam-modal');
    if (modal) modal.classList.add('hidden');
    if (targetExamTimer) {
        clearInterval(targetExamTimer);
        targetExamTimer = null;
    }
    targetExam = null;
}

function renderTargetExam() {
    if (!targetExam) return;
    const flat = flatExamQuestions();
    const current = flat[targetExam.cursor];
    if (!current) return;
    const blocksBox = document.getElementById('target-exam-blocks');
    blocksBox.innerHTML = targetExam.blocks.map((block, index) => {
        const active = index === current.blockIndex;
        const cls = active
            ? 'bg-emerald-500 text-slate-950 border-emerald-400'
            : 'bg-[#161F30] text-slate-300 border-[#283548]';
        return `<button type="button" onclick="jumpTargetExamBlock(${index})" class="shrink-0 px-2 py-1 rounded-lg border text-[10px] font-bold ${cls}">${escTarget(block.title)} · ${block.count}</button>`;
    }).join('');
    document.getElementById('target-exam-progress').textContent = `Savol ${targetExam.cursor + 1} / ${flat.length}`;
    document.getElementById('target-exam-block-label').textContent =
        `${current.block.kind} · ${current.block.title} [${current.block.coeff}]`;
    document.getElementById('target-exam-qtext').textContent =
        `${current.questionIndex + 1}. ${current.question.text}`;
    const chosen = targetExam.answers[current.question.id];
    document.getElementById('target-exam-options').innerHTML = current.question.options.map((option, index) => {
        const active = chosen === index;
        const cls = active
            ? 'border-emerald-400 bg-emerald-500/15 text-white'
            : 'border-[#283548] bg-[#111827] text-slate-200';
        return `<button type="button" onclick="answerTargetExam(${index})" class="w-full text-left px-3 py-2.5 rounded-xl border text-xs font-medium ${cls}">${escTarget(option)}</button>`;
    }).join('');
}

function answerTargetExam(optionIndex) {
    if (!targetExam || targetExam.finished) return;
    const current = flatExamQuestions()[targetExam.cursor];
    if (!current) return;
    targetExam.answers[current.question.id] = optionIndex;
    renderTargetExam();
}

function targetExamPrev() {
    if (!targetExam || targetExam.cursor <= 0) return;
    targetExam.cursor -= 1;
    renderTargetExam();
}

function targetExamNext() {
    if (!targetExam) return;
    const flat = flatExamQuestions();
    if (targetExam.cursor >= flat.length - 1) return;
    targetExam.cursor += 1;
    renderTargetExam();
}

function jumpTargetExamBlock(blockIndex) {
    if (!targetExam) return;
    const flat = flatExamQuestions();
    const idx = flat.findIndex((item) => item.blockIndex === blockIndex);
    if (idx >= 0) {
        targetExam.cursor = idx;
        renderTargetExam();
    }
}

function finishTargetExam() {
    if (!targetExam || targetExam.finished) return;
    targetExam.finished = true;
    if (targetExamTimer) {
        clearInterval(targetExamTimer);
        targetExamTimer = null;
    }
    let score = 0;
    const rows = targetExam.blocks.map((block) => {
        let correct = 0;
        block.questions.forEach((question) => {
            if (targetExam.answers[question.id] === question.correct) correct += 1;
        });
        const points = correct * block.coeff;
        score += points;
        return { block, correct, points };
    });
    const maxScore = Number(targetExam.max_score) || rows.reduce((sum, row) => sum + row.block.count * row.block.coeff, 0);
    const percent = maxScore ? Math.round((score / maxScore) * 100) : 0;
    const play = document.getElementById('target-exam-play');
    const result = document.getElementById('target-exam-result');
    const footer = document.getElementById('target-exam-footer');
    if (play) play.classList.add('hidden');
    if (footer) footer.classList.add('hidden');
    if (!result) return;
    result.classList.remove('hidden');
    result.innerHTML = `
        <div class="bg-[#111827] border border-emerald-500/30 rounded-2xl p-3 text-center">
            <p class="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">Natija</p>
            <p class="text-2xl font-black text-white mt-1">${score.toFixed(1)} <span class="text-sm text-slate-400">/ ${maxScore.toFixed(1)}</span></p>
            <p class="text-xs text-slate-400 mt-1">${percent}%</p>
        </div>
        ${rows.map((row) => `
            <div class="bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 flex items-center justify-between gap-2">
                <div>
                    <p class="text-xs font-bold text-slate-100">${escTarget(row.block.title)}</p>
                    <p class="text-[10px] text-slate-500">${escTarget(row.block.kind)} · ×${row.block.coeff}</p>
                </div>
                <p class="text-xs font-mono text-amber-300">${row.correct}/${row.block.count} · ${row.points.toFixed(1)}</p>
            </div>
        `).join('')}
        <button type="button" onclick="closeTargetExam()" class="w-full bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-bold py-3 rounded-2xl text-sm">Yopish</button>
    `;
    document.getElementById('target-exam-progress').textContent = 'Yakunlandi';
}

window.initTargetSection = initTargetSection;
window.selectTargetInstType = selectTargetInstType;
window.onTargetFilterChange = onTargetFilterChange;
window.loadMoreTargetCards = loadMoreTargetCards;
window.startTargetHeroExam = startTargetHeroExam;
window.startTargetDirectionExam = startTargetDirectionExam;
window.closeTargetExam = closeTargetExam;
window.targetExamPrev = targetExamPrev;
window.targetExamNext = targetExamNext;
window.answerTargetExam = answerTargetExam;
window.jumpTargetExamBlock = jumpTargetExamBlock;
window.finishTargetExam = finishTargetExam;
