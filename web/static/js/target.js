// web/static/js/target.js

let currentSelectedInstType = 'otm';
let targetListOffset = 0;
const TARGET_PAGE_SIZE = 24;
let targetListTotal = 0;
let targetReqToken = 0;
let targetExam = null;
let targetExamTimer = null;
let militaryDetailCard = null;
let militaryCountdownTimer = null;
const militaryCardsById = new Map();

const TARGET_ALL_DIRECTION = "";
const TARGET_ALL_BLOCK = "";
const TARGET_ALL_REGION = "";
const TARGET_LITSEY_TYPES = new Set(['litsey', 'litsey_harbiy']);
const TARGET_MILITARY_TYPES = new Set(['litsey_harbiy', 'otm_harbiy']);

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

function isTargetLitsey(card) {
    return TARGET_LITSEY_TYPES.has(card?.inst_type) || card?.is_litsey === true;
}

function isTargetMilitary(card) {
    return TARGET_MILITARY_TYPES.has(card?.inst_type) || card?.is_military === true;
}

function buildSubjectBlockLabel(card) {
    if (card.subject_block) return card.subject_block;
    const bits = [card.subject_main, card.subject_second, card.subject_third].filter(Boolean);
    return bits.join(' - ') || '—';
}

function renderSubjectsSection(card) {
    const block = buildSubjectBlockLabel(card);
    const rows = [
        '<p class="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Fanlar majmuasi</p>',
        `<p class="text-[11px] text-slate-200 font-semibold tracking-wide">${escTarget(block)}</p>`,
        `<p class="text-[10px] text-slate-400">1-fan: <span class="text-slate-200">${escTarget(card.subject_main || '—')}</span> <span class="text-amber-300">[3.1]</span></p>`,
        `<p class="text-[10px] text-slate-400">2-fan: <span class="text-slate-200">${escTarget(card.subject_second || '—')}</span> <span class="text-amber-300">[2.1]</span></p>`,
    ];
    if (isTargetLitsey(card)) {
        if (card.subject_third) {
            rows.push(
                `<p class="text-[10px] text-slate-400">3-fan: <span class="text-slate-200">${escTarget(card.subject_third)}</span> <span class="text-amber-300">[1.1]</span></p>`
            );
        }
    } else {
        const mandatory = card.mandatory_subjects || "Ona tili, Matematika, O'zbekiston tarixi";
        rows.push(
            `<p class="text-[10px] text-slate-400">Majburiy blok: <span class="text-slate-200">${escTarget(mandatory)}</span> <span class="text-amber-300">[1.1]</span></p>`
        );
    }
    return rows.join('');
}

function renderTargetCard(card) {
    militaryCardsById.set(String(card.id), card);
    const formLang = [card.edu_form, card.edu_lang].filter(Boolean).join(' · ') || '—';
    const galleryCount = parseGalleryImages(card).length;
    const showDetail = isTargetMilitary(card) || isTargetLitsey(card)
        || Boolean(card.eligibility_criteria || card.practical_exams?.length || galleryCount);
    const logoHtml = renderMilitaryLogoHtml(card, {
        sizeClass: 'w-10 h-10',
        textClass: 'text-[10px]',
        rounded: 'rounded-xl'
    });
    const el = document.createElement('div');
    el.className = 'bg-[#111827] border border-[#1F2937] hover:border-emerald-500/30 rounded-2xl p-3.5 shadow-md space-y-2.5 transition-all' + (showDetail ? ' cursor-pointer' : '');
    el.setAttribute('role', 'button');
    el.tabIndex = 0;
    el.dataset.directionId = String(card.id);
    el.addEventListener('click', (ev) => {
        if (ev.target.closest('button')) return;
        if (showDetail) openMilitaryDetail(card.id);
    });
    el.innerHTML = `
        <div class="flex items-start gap-2 border-b border-[#1F2937] pb-2">
            ${logoHtml}
            <div class="min-w-0 flex-1">
                <span class="text-[9px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md inline-block mb-1">
                    ${escTarget(card.badge)}
                </span>
                <div class="flex items-start gap-2">
                    <h4 class="text-xs font-extrabold text-white leading-tight min-w-0 flex-1">${escTarget(card.inst_name)}</h4>
                    ${showDetail ? `
                    <button type="button" data-direction-id="${card.id}" onclick="openMilitaryDetail(${card.id})"
                            class="shrink-0 px-2 py-0.5 rounded-lg text-[10px] font-bold bg-violet-500/15 border border-violet-400/40 text-violet-200 hover:bg-violet-500/25 active:scale-95 transition-all cursor-pointer">
                        Batafsil
                    </button>` : ''}
                </div>
                <p class="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                    <i data-lucide="map-pin" class="w-3 h-3 text-emerald-400"></i> ${escTarget(card.region)}
                </p>
            </div>
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
            ${renderSubjectsSection(card)}
        </div>
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
        militaryCardsById.clear();
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

function parseMilitaryDate(raw) {
    if (!raw) return null;
    const text = String(raw).trim();
    if (!text) return null;
    const normalized = text.includes('T') ? text : text.replace(' ', 'T');
    const dt = new Date(normalized);
    if (!Number.isNaN(dt.getTime())) return dt;
    const m = text.match(/^(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
    if (m) {
        return new Date(
            Number(m[3]),
            Number(m[2]) - 1,
            Number(m[1]),
            Number(m[4] || 0),
            Number(m[5] || 0)
        );
    }
    return null;
}

function formatMilitaryDate(raw) {
    const dt = parseMilitaryDate(raw);
    if (!dt) return raw || '—';
    const dd = String(dt.getDate()).padStart(2, '0');
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const yyyy = dt.getFullYear();
    const hh = String(dt.getHours()).padStart(2, '0');
    const min = String(dt.getMinutes()).padStart(2, '0');
    return `${dd}.${mm}.${yyyy} ${hh}:${min}`;
}

function splitCountdown(ms) {
    const safe = Math.max(0, ms);
    const totalSec = Math.floor(safe / 1000);
    return {
        days: Math.floor(totalSec / 86400),
        hours: Math.floor((totalSec % 86400) / 3600),
        mins: Math.floor((totalSec % 3600) / 60),
        secs: totalSec % 60,
        expired: ms <= 0
    };
}

function formatCountdown(ms) {
    const { days, hours, mins, secs, expired } = splitCountdown(ms);
    if (expired) return "Muddat o'tdi";
    return `${days} kun ${String(hours).padStart(2, '0')} soat ${String(mins).padStart(2, '0')} daq ${String(secs).padStart(2, '0')} son`;
}

function renderCountdownBlocks(ms, prefix) {
    const { days, hours, mins, secs, expired } = splitCountdown(ms);
    const vals = expired
        ? ['00', '00', '00', '00']
        : [String(days).padStart(2, '0'), String(hours).padStart(2, '0'), String(mins).padStart(2, '0'), String(secs).padStart(2, '0')];
    const labels = ['Kun', 'Soat', 'Daqiqa', 'Soniya'];
    const colors = ['text-emerald-400', 'text-white', 'text-white', 'text-amber-400'];
    return `
        <div class="grid grid-cols-4 gap-1.5 text-center select-none" data-countdown-for="${escTarget(prefix)}">
            ${vals.map((v, i) => `
                <div class="bg-[#0A0E17]/80 border border-[#283548]/60 rounded-xl px-1 py-1.5">
                    <span data-cd-part="${i}" class="block font-mono text-sm font-bold ${colors[i]}">${v}</span>
                    <span class="text-[8px] uppercase tracking-wider text-slate-500">${labels[i]}</span>
                </div>
            `).join('')}
        </div>`;
}

const TIMER_FAV_KEY = 'tarix_timer_favorites';

function getTimerFavorites() {
    try {
        const raw = JSON.parse(localStorage.getItem(TIMER_FAV_KEY) || '[]');
        return Array.isArray(raw) ? raw : [];
    } catch (_) {
        return [];
    }
}

function saveTimerFavorites(list) {
    localStorage.setItem(TIMER_FAV_KEY, JSON.stringify(list));
    window.dispatchEvent(new CustomEvent('timer-favorites-changed'));
    if (typeof loadExamDeadlines === 'function') {
        try { loadExamDeadlines(); } catch (_) { /* home hali yuklanmagan */ }
    }
}

function timerFavoriteId(directionId, key) {
    return `${directionId}:${key}`;
}

function isTimerFavorite(directionId, key) {
    const id = timerFavoriteId(directionId, key);
    return getTimerFavorites().some((item) => item.id === id);
}

function toggleTimerFavorite(directionId, key, label, dateRaw, badge) {
    const card = militaryDetailCard || militaryCardsById.get(String(directionId));
    const id = timerFavoriteId(directionId, key);
    let list = getTimerFavorites();
    const existing = list.findIndex((item) => item.id === id);
    if (existing >= 0) {
        list.splice(existing, 1);
    } else {
        const dt = parseMilitaryDate(dateRaw);
        list.unshift({
            id,
            direction_id: Number(directionId),
            key,
            label: label || 'Muddat',
            date: dateRaw || '',
            target_iso: dt ? dt.toISOString() : '',
            badge: badge || card?.badge || 'MAQSAD',
            title: `${card?.inst_name || ''} — ${label || 'Muddat'}`.trim(),
            inst_name: card?.inst_name || '',
            favorited_at: Date.now()
        });
    }
    saveTimerFavorites(list);
    // Yulduzcha UI yangilash
    document.querySelectorAll(`[data-fav-btn="${escTarget(id)}"]`).forEach((btn) => {
        const on = existing < 0;
        btn.className = on
            ? 'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-amber-400 fill-amber-400 bg-amber-500/10 border border-amber-400/40 cursor-pointer active:scale-95 transition-all'
            : 'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-slate-500 bg-[#161F30] border border-[#283548] cursor-pointer active:scale-95 transition-all';
        btn.innerHTML = on ? '⭐' : '☆';
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
}

function starButtonHtml(directionId, key, label, dateRaw, badge) {
    const id = timerFavoriteId(directionId, key);
    const on = isTimerFavorite(directionId, key);
    const cls = on
        ? 'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-amber-400 fill-amber-400 bg-amber-500/10 border border-amber-400/40 cursor-pointer active:scale-95 transition-all'
        : 'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-slate-500 bg-[#161F30] border border-[#283548] cursor-pointer active:scale-95 transition-all';
    return `<button type="button" data-fav-btn="${escTarget(id)}"
        data-direction-id="${escTarget(directionId)}" data-fav-key="${escTarget(key)}"
        data-fav-label="${escTarget(label)}" data-fav-date="${escTarget(dateRaw)}" data-fav-badge="${escTarget(badge || '')}"
        onclick="onTimerFavoriteClick(this)"
        class="${cls}" aria-pressed="${on ? 'true' : 'false'}" title="Sevimlilarga qo'shish">${on ? '⭐' : '☆'}</button>`;
}

function onTimerFavoriteClick(btn) {
    if (!btn) return;
    toggleTimerFavorite(
        btn.dataset.directionId,
        btn.dataset.favKey,
        btn.dataset.favLabel,
        btn.dataset.favDate,
        btn.dataset.favBadge
    );
}

function openTargetCatalogCourses(catalogUrl) {
    closeMilitaryDetail();
    if (typeof switchTab === 'function') {
        switchTab('catalog', { catalogUrl: catalogUrl || '' });
    } else if (catalogUrl) {
        window.open(catalogUrl, '_blank');
    }
}

function openMilitaryMockTest(card) {
    const url = card?.mock_test_url;
    if (url) {
        window.open(url, '_blank', 'noopener');
        return;
    }
    if (card?.id) {
        openTargetMock({ direction_id: card.id }).catch(() => {
            alert("Imtihonni ochib bo'lmadi. Qayta urinib ko'ring.");
        });
    }
}

function isMediaUrl(text) {
    return /^https?:\/\//i.test(String(text || '').trim());
}

function isDirectImageUrl(text) {
    return /\.(png|jpe?g|gif|webp|bmp|svg)(\?|$)/i.test(String(text || '').trim());
}

function isTelegramPostUrl(text) {
    return /^https?:\/\/(t\.me|telegram\.me)\//i.test(String(text || '').trim());
}

/** gallery_images: vergul, \\n, \\r bilan ajratilgan yoki massiv */
function parseGalleryImages(item) {
    const raw = item?.gallery_images ?? item?.gallery ?? '';
    const splitOne = (part) =>
        String(part || '').split(/[\n,\r]+/).map((s) => s.trim()).filter(Boolean);
    if (Array.isArray(raw)) {
        return raw.flatMap(splitOne);
    }
    return splitOne(raw);
}

function institutionInitials(card) {
    const short = String(card?.short_name || '').trim();
    if (short) {
        const letters = short.replace(/[^A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ'\s-]/g, '').trim();
        if (letters.length >= 2) return letters.slice(0, 3).toUpperCase();
        return short.slice(0, 3).toUpperCase();
    }
    const name = String(card?.inst_name || 'H').trim();
    const words = name.split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
        return words.slice(0, 2).map((w) => w[0]).join('').toUpperCase();
    }
    return name.slice(0, 2).toUpperCase() || 'H';
}

/** Zangori/oltin gerb nishoni — logotip o'rniga */
function militaryCrestHtml(initials, sizeClass = 'w-14 h-14', textClass = 'text-sm', rounded = 'rounded-2xl') {
    return `
        <div class="${sizeClass} ${rounded} shrink-0 relative overflow-hidden flex items-center justify-center
                    bg-gradient-to-br from-[#0B1F3A] via-[#123A6B] to-[#0A1628]
                    border-2 border-amber-400/80 shadow-[inset_0_0_0_1px_rgba(59,130,246,0.45),0_0_14px_rgba(251,191,36,0.18)]"
             aria-hidden="true">
            <span class="absolute inset-x-2 top-1 h-px bg-gradient-to-r from-transparent via-amber-300/70 to-transparent"></span>
            <span class="absolute inset-x-2 bottom-1 h-px bg-gradient-to-r from-transparent via-blue-400/50 to-transparent"></span>
            <span class="${textClass} font-black tracking-wide text-amber-300 drop-shadow-[0_1px_2px_rgba(0,0,0,0.6)]">${escTarget(initials)}</span>
        </div>`;
}

function militaryGalleryPlaceholderDataUri() {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="352" height="224" viewBox="0 0 352 224" role="img">
        <defs>
            <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#0B1F3A"/>
                <stop offset="55%" stop-color="#123A6B"/>
                <stop offset="100%" stop-color="#0A1628"/>
            </linearGradient>
        </defs>
        <rect width="352" height="224" rx="24" fill="url(#g)"/>
        <rect x="12" y="12" width="328" height="200" rx="18" fill="none" stroke="#FBBF24" stroke-opacity="0.55" stroke-width="2"/>
        <path d="M176 48 L204 78 L188 78 L188 118 L164 118 L164 78 L148 78 Z" fill="#FBBF24" fill-opacity="0.85"/>
        <circle cx="176" cy="148" r="18" fill="none" stroke="#60A5FA" stroke-width="2.5"/>
        <path d="M176 136 L176 160 M164 148 L188 148" stroke="#60A5FA" stroke-width="2" stroke-linecap="round"/>
        <text x="176" y="196" text-anchor="middle" fill="#94A3B8" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700">Harbiy shablon</text>
    </svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function canUseAsImgSrc(url) {
    const u = String(url || '').trim();
    if (!u || !isMediaUrl(u)) return false;
    if (isTelegramPostUrl(u)) return false;
    return true;
}

function militaryImgLoaded(img) {
    if (!img) return;
    img.classList.remove('opacity-0');
    img.classList.add('opacity-100');
    const wrap = img.closest('[data-mil-img-wrap]');
    const loader = wrap?.querySelector('[data-mil-img-loader]');
    if (loader) loader.classList.add('hidden');
}

function militaryImgFallback(img, initials) {
    if (!img || img.dataset.fallbackApplied === '1') return;
    img.dataset.fallbackApplied = '1';
    const wrap = img.closest('[data-mil-img-wrap]');
    const loader = wrap?.querySelector('[data-mil-img-loader]');
    if (loader) loader.classList.add('hidden');
    const role = img.dataset.milRole || 'gallery';
    if (role === 'logo') {
        const crest = document.createElement('div');
        crest.innerHTML = militaryCrestHtml(
            initials || img.dataset.initials || 'H',
            img.dataset.sizeClass || 'w-14 h-14',
            img.dataset.textClass || 'text-sm',
            img.dataset.rounded || 'rounded-2xl'
        ).trim();
        const node = crest.firstElementChild;
        const target = wrap || img;
        if (node && target.parentNode) {
            target.replaceWith(node);
        }
        return;
    }
    img.onerror = null;
    img.src = militaryGalleryPlaceholderDataUri();
    img.classList.remove('opacity-0');
    img.classList.add('opacity-100');
    img.alt = 'Harbiy shablon';
}

function renderMilitaryLogoHtml(card, opts = {}) {
    const sizeClass = opts.sizeClass || 'w-14 h-14';
    const textClass = opts.textClass || 'text-sm';
    const rounded = opts.rounded || 'rounded-2xl';
    const initials = institutionInitials(card);
    const url = String(card?.logo_url || '').trim();
    if (!canUseAsImgSrc(url)) {
        return militaryCrestHtml(initials, sizeClass, textClass, rounded);
    }
    return `
        <div data-mil-img-wrap class="${sizeClass} ${rounded} shrink-0 relative overflow-hidden border border-[#283548] bg-[#0A0E17]">
            <div data-mil-img-loader class="absolute inset-0 animate-pulse bg-gradient-to-br from-[#161F30] to-[#0A0E17]"></div>
            <img src="${escTarget(url)}" alt=""
                 data-mil-role="logo"
                 data-initials="${escTarget(initials)}"
                 data-size-class="${escTarget(sizeClass)}"
                 data-text-class="${escTarget(textClass)}"
                 data-rounded="${escTarget(rounded)}"
                 class="${sizeClass} ${rounded} object-cover opacity-0 transition-opacity duration-300"
                 onload="militaryImgLoaded(this)"
                 onerror="militaryImgFallback(this)">
        </div>`;
}

function renderGalleryTile(url) {
    const safe = escTarget(url);
    const telegram = isTelegramPostUrl(url);
    const usable = canUseAsImgSrc(url);
    const shell = 'snap-start shrink-0 relative h-28 w-44 rounded-xl overflow-hidden border border-[#283548] bg-[#0A0E17]';
    if (!usable) {
        const href = isMediaUrl(url) ? safe : '#';
        const tagOpen = isMediaUrl(url)
            ? `<a href="${href}" target="_blank" rel="noopener" class="${shell} flex flex-col items-center justify-center gap-1.5 cursor-pointer hover:border-amber-400/40 transition-colors"`
            : `<div class="${shell} flex flex-col items-center justify-center gap-1.5"`;
        const tagClose = isMediaUrl(url) ? '</a>' : '</div>';
        return `
            ${tagOpen}>
                <img src="${militaryGalleryPlaceholderDataUri()}" alt="" class="absolute inset-0 w-full h-full object-cover opacity-40 pointer-events-none" aria-hidden="true">
                <span class="relative z-[1] text-[10px] font-bold text-amber-200/90 px-2 text-center leading-tight">
                    ${telegram ? 'Telegram post' : 'Rasm mavjud emas'}
                </span>
                ${telegram ? '<span class="relative z-[1] text-[9px] text-slate-400">Ochish →</span>' : ''}
            ${tagClose}`;
    }
    return `
        <button type="button" onclick="openMilitaryImage('${safe}')"
                class="${shell} cursor-pointer active:scale-[0.98] transition-transform" data-mil-img-wrap>
            <div data-mil-img-loader class="absolute inset-0 flex items-center justify-center bg-[#0A0E17] z-[1]">
                <span class="w-6 h-6 rounded-full border-2 border-amber-400/30 border-t-amber-400 animate-spin"></span>
            </div>
            <img src="${safe}" alt=""
                 data-mil-role="gallery"
                 class="absolute inset-0 w-full h-full object-cover rounded-xl opacity-0 transition-opacity duration-300"
                 onload="militaryImgLoaded(this)"
                 onerror="militaryImgFallback(this)">
        </button>`;
}

function criteriaHtml(criteria) {
    if (!criteria) return '';
    const raw = String(criteria).trim();
    if (isDirectImageUrl(raw) && canUseAsImgSrc(raw)) {
        return `<button type="button" onclick="openMilitaryImage('${escTarget(raw)}')"
                        class="block w-full text-left cursor-pointer relative rounded-xl overflow-hidden border border-[#283548]" data-mil-img-wrap>
            <div data-mil-img-loader class="absolute inset-0 flex items-center justify-center bg-[#0A0E17] z-[1]">
                <span class="w-5 h-5 rounded-full border-2 border-amber-400/30 border-t-amber-400 animate-spin"></span>
            </div>
            <img src="${escTarget(raw)}" alt="Mezon" data-mil-role="gallery"
                 class="w-full max-h-40 object-cover rounded-xl opacity-0 transition-opacity duration-300"
                 onload="militaryImgLoaded(this)" onerror="militaryImgFallback(this)">
            <span class="text-[10px] text-violet-300 mt-1 inline-block px-0.5">Mezon rasmini kattalashtirish</span>
        </button>`;
    }
    if (isMediaUrl(raw)) {
        const label = isTelegramPostUrl(raw) ? '📎 Telegram mezon / material' : '📎 Mezon / materialni ochish';
        return `<a href="${escTarget(raw)}" target="_blank" rel="noopener"
                   class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[10px] font-bold bg-violet-500/10 border border-violet-400/30 text-violet-200">
            ${label}
        </a>`;
    }
    return `<p class="text-[11px] text-slate-400 leading-relaxed">${nl2brEscaped(criteria)}</p>`;
}

function getMilitaryTimeline(card) {
    if (Array.isArray(card.dates_timeline) && card.dates_timeline.length) {
        return card.dates_timeline;
    }
    const items = [];
    if (card.admission_date) {
        items.push({ key: 'admission', label: 'Hujjat topshirish', date: card.admission_date });
    }
    (card.practical_exams || []).forEach((exam) => {
        if (exam.date) items.push({ key: `exam${exam.index}`, label: exam.name || 'Amaliy imtihon', date: exam.date });
    });
    if (card.test_exam_date) {
        items.push({ key: 'test_exam', label: 'Test sinovi', date: card.test_exam_date });
    }
    return items;
}

function nearestMilitaryDeadline(card) {
    const now = Date.now();
    const upcoming = getMilitaryTimeline(card)
        .map((item) => ({ ...item, at: parseMilitaryDate(item.date) }))
        .filter((item) => item.at && item.at.getTime() >= now)
        .sort((a, b) => a.at - b.at);
    return upcoming[0] || null;
}

function nl2brEscaped(text) {
    return escTarget(text || '').replace(/\n/g, '<br>');
}

function toggleMilitaryAccordion(btn) {
    const panel = btn?.nextElementSibling;
    if (!panel) return;
    panel.classList.toggle('hidden');
    const icon = btn.querySelector('[data-acc-icon]');
    if (icon) icon.textContent = panel.classList.contains('hidden') ? '+' : '−';
}

function toggleMilitaryTimelineList() {
    const box = document.getElementById('military-timeline-list');
    if (!box) return;
    box.classList.toggle('hidden');
}

function openMilitaryVideo(url) {
    if (!url) return;
    const layer = document.getElementById('military-video-layer');
    const frame = document.getElementById('military-video-frame');
    if (!layer || !frame) {
        window.open(url, '_blank');
        return;
    }
    let embed = url;
    const yt = url.match(/(?:youtu\.be\/|v=|embed\/)([A-Za-z0-9_-]{6,})/);
    if (yt) embed = `https://www.youtube.com/embed/${yt[1]}?autoplay=1`;
    frame.src = embed;
    layer.classList.remove('hidden');
}

function closeMilitaryVideo() {
    const layer = document.getElementById('military-video-layer');
    const frame = document.getElementById('military-video-frame');
    if (frame) frame.src = '';
    if (layer) layer.classList.add('hidden');
}

function openMilitaryImage(url) {
    if (!url) return;
    if (isTelegramPostUrl(url) || !canUseAsImgSrc(url)) {
        if (isMediaUrl(url)) {
            window.open(url, '_blank', 'noopener');
        }
        return;
    }
    const layer = document.getElementById('military-image-layer');
    const img = document.getElementById('military-image-zoom');
    if (!layer || !img) {
        window.open(url, '_blank');
        return;
    }
    img.onerror = () => {
        img.onerror = null;
        img.src = militaryGalleryPlaceholderDataUri();
    };
    img.src = url;
    layer.classList.remove('hidden');
}

function closeMilitaryImage() {
    const layer = document.getElementById('military-image-layer');
    const img = document.getElementById('military-image-zoom');
    if (img) img.src = '';
    if (layer) layer.classList.add('hidden');
}

function tickMilitaryCountdown() {
    if (!militaryDetailCard) return;
    const now = Date.now();
    document.querySelectorAll('#military-detail-body [data-countdown-for]').forEach((box) => {
        const key = box.getAttribute('data-countdown-for');
        const item = getMilitaryTimeline(militaryDetailCard).find((t) => t.key === key);
        const at = item ? parseMilitaryDate(item.date) : null;
        const parts = splitCountdown(at ? at.getTime() - now : 0);
        const vals = parts.expired
            ? ['00', '00', '00', '00']
            : [
                String(parts.days).padStart(2, '0'),
                String(parts.hours).padStart(2, '0'),
                String(parts.mins).padStart(2, '0'),
                String(parts.secs).padStart(2, '0')
            ];
        box.querySelectorAll('[data-cd-part]').forEach((el) => {
            const idx = Number(el.getAttribute('data-cd-part'));
            if (!Number.isNaN(idx) && vals[idx] != null) el.textContent = vals[idx];
        });
    });
    const nearestLabel = document.getElementById('military-countdown-label');
    const nearestHint = document.getElementById('military-countdown-hint');
    const nearest = nearestMilitaryDeadline(militaryDetailCard);
    if (nearestLabel) {
        nearestLabel.textContent = nearest ? `${nearest.label}gacha` : 'Yaqin muddat';
    }
    if (nearestHint) {
        nearestHint.textContent = nearest
            ? formatMilitaryDate(nearest.date)
            : 'Belgilanmagan';
    }
}

function renderMilitaryDetailBody(card) {
    const body = document.getElementById('military-detail-body');
    if (!body) return;

    const gallery = parseGalleryImages(card);
    const videoUrl = card.review_video_url || card.video_review_url;
    const timeline = getMilitaryTimeline(card);
    const exams = card.practical_exams || [];
    const catalogUrl = card.catalog_courses_url || card.bundle_package_url || '';
    const subjectsImg = card.subjects_table_image;
    const mockUrl = card.mock_test_url;
    const nearest = nearestMilitaryDeadline(card);

    const logoHtml = renderMilitaryLogoHtml(card, {
        sizeClass: 'w-14 h-14',
        textClass: 'text-sm',
        rounded: 'rounded-2xl'
    });

    const galleryHtml = gallery.length
        ? `<div class="flex gap-2 overflow-x-auto pb-1 scrollbar-none snap-x">
            ${gallery.map((url) => renderGalleryTile(url)).join('')}
           </div>`
        : `<p class="text-[11px] text-slate-500">Galereya rasmlari hozircha yo'q.</p>`;

    const accordion = (title, content) => {
        if (!content) return '';
        return `
            <div class="bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden">
                <button type="button" onclick="toggleMilitaryAccordion(this)"
                        class="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left cursor-pointer">
                    <span class="text-xs font-bold text-slate-100">${title}</span>
                    <span data-acc-icon class="text-emerald-400 font-bold">+</span>
                </button>
                <div class="hidden px-3 pb-3 text-[11px] text-slate-300 leading-relaxed border-t border-[#1F2937] pt-2">
                    ${nl2brEscaped(content)}
                </div>
            </div>`;
    };

    const timerRow = (item) => {
        const at = parseMilitaryDate(item.date);
        const ms = at ? at.getTime() - Date.now() : 0;
        return `
            <div class="bg-[#0A0E17]/80 border border-[#283548]/70 rounded-2xl p-3 space-y-2">
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <p class="text-xs font-bold text-white">${escTarget(item.label)}</p>
                        <p class="text-[10px] text-amber-300 mt-0.5 font-mono">${escTarget(formatMilitaryDate(item.date))}</p>
                    </div>
                    ${starButtonHtml(card.id, item.key, item.label, item.date, card.badge)}
                </div>
                ${renderCountdownBlocks(ms, item.key)}
            </div>`;
    };

    const examsHtml = exams.length
        ? exams.map((exam) => {
            const key = `exam${exam.index || ''}`;
            const at = parseMilitaryDate(exam.date);
            const ms = at ? at.getTime() - Date.now() : 0;
            return `
            <div class="bg-[#0A0E17] border border-[#283548]/70 rounded-2xl p-3 space-y-2">
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <p class="text-xs font-bold text-white">${escTarget(exam.name || 'Amaliy sinov')}</p>
                        <p class="text-[10px] text-amber-300 mt-0.5">${escTarget(formatMilitaryDate(exam.date))}</p>
                    </div>
                    ${exam.date ? starButtonHtml(card.id, key, exam.name || 'Amaliy sinov', exam.date, card.badge) : ''}
                </div>
                ${exam.date ? renderCountdownBlocks(ms, key) : ''}
                ${criteriaHtml(exam.criteria)}
                <div class="flex flex-wrap gap-2">
                    ${(exam.practical_mock_id || exam.practical_mock_url || mockUrl) ? `
                        <a href="${escTarget(exam.practical_mock_url || mockUrl || '#')}" target="_blank" rel="noopener"
                           class="px-2.5 py-1.5 rounded-xl text-[10px] font-bold bg-amber-500/10 border border-amber-400/30 text-amber-200">Sinov testi 🎯</a>` : ''}
                    ${exam.practical_course_url ? `
                        <a href="${escTarget(exam.practical_course_url)}" target="_blank" rel="noopener"
                           class="px-2.5 py-1.5 rounded-xl text-[10px] font-bold bg-violet-500/10 border border-violet-400/30 text-violet-200">Tayyorgarlik kursi 📚</a>` : ''}
                </div>
            </div>`;
        }).join('')
        : `<p class="text-[11px] text-slate-500">Amaliy imtihonlar ma'lumoti yo'q.</p>`;

    body.innerHTML = `
        <section class="space-y-3">
            <div class="flex items-start gap-3">
                ${logoHtml}
                <div class="min-w-0 flex-1">
                    <p class="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">${escTarget(card.badge || '')}</p>
                    <h3 class="text-sm font-extrabold text-white leading-snug mt-0.5">${escTarget(card.inst_name)}</h3>
                    <p class="text-[11px] text-slate-400 mt-0.5">${escTarget(card.direction_title || '')}</p>
                    <span class="inline-flex mt-1.5 px-2 py-0.5 rounded-lg border border-[#283548] bg-[#161F30] text-[10px] font-bold text-slate-300">
                        ${escTarget(card.short_name || '—')}
                    </span>
                </div>
            </div>
            ${galleryHtml}
            ${videoUrl ? `
                <button type="button" onclick="openMilitaryVideo('${escTarget(videoUrl)}')"
                        class="w-full py-2.5 rounded-2xl bg-rose-500/10 border border-rose-400/30 text-rose-200 text-xs font-bold cursor-pointer">
                    ▶️ Bizning video sharh
                </button>` : ''}
            ${card.overview_text ? `
                <div class="bg-[#111827] border border-[#1F2937] rounded-2xl p-3 text-[11px] text-slate-300 leading-relaxed">
                    ${nl2brEscaped(card.overview_text)}
                </div>` : ''}
        </section>

        <section class="bg-gradient-to-br from-emerald-500/10 to-violet-500/10 border border-emerald-500/20 rounded-2xl p-3 space-y-3">
            <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                    <p id="military-countdown-label" class="text-[10px] uppercase tracking-wider text-emerald-300 font-bold">
                        ${nearest ? escTarget(nearest.label) + 'gacha' : 'Yaqin muddat'}
                    </p>
                    <p id="military-countdown-hint" class="text-[10px] text-slate-400 mt-0.5 font-mono">
                        ${nearest ? escTarget(formatMilitaryDate(nearest.date)) : 'Belgilanmagan'}
                    </p>
                </div>
                ${nearest ? starButtonHtml(card.id, nearest.key, nearest.label, nearest.date, card.badge) : ''}
            </div>
            ${nearest ? renderCountdownBlocks(nearest.at.getTime() - Date.now(), nearest.key) : ''}
            <button type="button" onclick="toggleMilitaryTimelineList()"
                    class="text-[11px] font-semibold text-violet-200 underline underline-offset-2 cursor-pointer">
                Barcha muddatlar va taymerlar
            </button>
            <div id="military-timeline-list" class="hidden space-y-2 pt-1">
                ${timeline.length ? timeline.map(timerRow).join('') : '<p class="text-[11px] text-slate-500">Muddatlar kiritilmagan.</p>'}
            </div>
        </section>

        <section class="space-y-2">
            <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Qabul talablari va mezonlar</p>
            ${accordion('📋 Kimlar qabul qilinadi', card.eligibility_criteria)}
            ${accordion('🎖 Imkoniyatlar va imtiyozlar', card.career_opportunities || card.opportunities)}
            ${accordion('📍 Qabul tartibi va joyi', card.admission_info || card.admission_requirements)}
        </section>

        <section class="space-y-2">
            <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Amaliy imtihonlar</p>
            ${examsHtml}
        </section>

        <section class="space-y-2">
            <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Test sinovi va fanlar</p>
            <div class="bg-[#161F30] border border-[#283548] rounded-2xl p-3 space-y-1">
                ${renderSubjectsSection(card)}
            </div>
            ${subjectsImg && canUseAsImgSrc(subjectsImg) ? `
                <button type="button" onclick="openMilitaryImage('${escTarget(subjectsImg)}')"
                        class="w-full text-left bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden cursor-pointer" data-mil-img-wrap>
                    <div class="px-3 py-2 text-xs font-bold text-slate-100">📊 Fanlar va kvota jadvali</div>
                    <div class="relative border-t border-[#1F2937]">
                        <div data-mil-img-loader class="absolute inset-0 flex items-center justify-center bg-[#0A0E17] z-[1]">
                            <span class="w-6 h-6 rounded-full border-2 border-amber-400/30 border-t-amber-400 animate-spin"></span>
                        </div>
                        <img src="${escTarget(subjectsImg)}" alt="Fanlar jadvali"
                             data-mil-role="gallery"
                             class="w-full max-h-48 object-cover opacity-0 transition-opacity duration-300"
                             onload="militaryImgLoaded(this)"
                             onerror="militaryImgFallback(this)">
                    </div>
                </button>` : subjectsImg && isMediaUrl(subjectsImg) ? `
                <a href="${escTarget(subjectsImg)}" target="_blank" rel="noopener"
                   class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[10px] font-bold bg-violet-500/10 border border-violet-400/30 text-violet-200">
                    📎 Fanlar jadvalini ochish
                </a>` : ''}
        </section>

    `;

    const catalogBtn = document.getElementById('military-btn-catalog');
    if (catalogBtn) {
        catalogBtn.onclick = () => openTargetCatalogCourses(catalogUrl);
    }
}

function openMilitaryDetail(directionId) {
    const card = militaryCardsById.get(String(directionId));
    if (!card) return;
    militaryDetailCard = card;
    const modal = document.getElementById('military-detail-modal');
    if (!modal) return;
    renderMilitaryDetailBody(card);
    tickMilitaryCountdown();
    if (militaryCountdownTimer) clearInterval(militaryCountdownTimer);
    militaryCountdownTimer = setInterval(tickMilitaryCountdown, 1000);
    modal.classList.remove('hidden');
    modal.scrollTop = 0;
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons();
}

function closeMilitaryDetail() {
    const modal = document.getElementById('military-detail-modal');
    if (modal) modal.classList.add('hidden');
    if (militaryCountdownTimer) {
        clearInterval(militaryCountdownTimer);
        militaryCountdownTimer = null;
    }
    closeMilitaryVideo();
    closeMilitaryImage();
    militaryDetailCard = null;
    document.body.style.overflow = '';
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
window.openMilitaryDetail = openMilitaryDetail;
window.closeMilitaryDetail = closeMilitaryDetail;
window.toggleMilitaryAccordion = toggleMilitaryAccordion;
window.toggleMilitaryTimelineList = toggleMilitaryTimelineList;
window.openMilitaryVideo = openMilitaryVideo;
window.closeMilitaryVideo = closeMilitaryVideo;
window.openMilitaryImage = openMilitaryImage;
window.closeMilitaryImage = closeMilitaryImage;
window.toggleTimerFavorite = toggleTimerFavorite;
window.onTimerFavoriteClick = onTimerFavoriteClick;
window.getTimerFavorites = getTimerFavorites;
window.openTargetCatalogCourses = openTargetCatalogCourses;
window.openMilitaryMockTest = openMilitaryMockTest;
window.militaryImgLoaded = militaryImgLoaded;
window.militaryImgFallback = militaryImgFallback;
window.parseGalleryImages = parseGalleryImages;
