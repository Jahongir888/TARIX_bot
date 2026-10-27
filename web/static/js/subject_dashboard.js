/**
 * PHAROS — Fan tizimi va o'quv paneli (Subject Hub & Study Dashboard)
 * Export: openSubjectHub, initSubjectHub, shSwitchPanel, shBackToSubjects
 */

let shState = {
    subjectId: null,
    panel: 'wiki',
    communityTag: 'all',
    wikiTimer: null,
    scheduleVideoUrl: null,
    overview: null,
    masterGrade: null,
    masterTopic: null,
    masterGradesLoaded: false,
    masterFacts: [],
    masterVoice: {
        active: false,
        idx: 0,
        listening: false,
        recognition: null,
        mediaRecorder: null,
        mediaChunks: [],
        mediaStream: null,
    },
};

function _shTgId() {
    if (typeof getRequestTelegramId === 'function') return getRequestTelegramId();
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 12345678;
}

function _shEscape(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function _shHaptic(type) {
    try {
        const hf = window.Telegram?.WebApp?.HapticFeedback;
        if (!hf) return;
        if (type === 'success') hf.notificationOccurred('success');
        else if (type === 'error') hf.notificationOccurred('error');
        else hf.impactOccurred(type || 'light');
    } catch (e) {}
}

function _shPaceLabel(status) {
    return {
        ahead: 'Oldinda',
        on_track: 'Rejada',
        slightly_behind: 'Ozgina kechikkan',
        behind: 'Ortda',
    }[status] || 'Rejada';
}

function _shRankClass(rank) {
    if (rank === 'Grossmeyster') return 'border-violet-500/40 text-violet-300 bg-violet-500/10';
    if (rank === 'Ustoz') return 'border-amber-500/30 text-amber-400 bg-amber-500/10';
    if (rank === 'Bilimdon') return 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10';
    return 'border-slate-500/30 text-slate-300 bg-slate-500/10';
}

// ==========================================================
// PUBLIC API
// ==========================================================
function openSubjectHub(subjectId, opts) {
    opts = opts || {};
    if (typeof switchTab === 'function') {
        switchTab('subject-hub', {
            backTo: opts.backTo || 'cabinet',
            subjectId: subjectId || null,
        });
    } else {
        initSubjectHub(subjectId || null);
    }
}

async function initSubjectHub(subjectId) {
    const listWrap = document.getElementById('sh-subjects-list-wrap');
    const dash = document.getElementById('sh-dashboard');
    if (!listWrap || !dash) return;

    if (subjectId) {
        await shSelectSubject(subjectId);
        return;
    }

    listWrap.classList.remove('hidden');
    dash.classList.add('hidden');
    await shLoadMySubjects();
    if (window.lucide) lucide.createIcons();
}

function shBackToSubjects() {
    shState.subjectId = null;
    shState.overview = null;
    document.getElementById('sh-subjects-list-wrap')?.classList.remove('hidden');
    document.getElementById('sh-dashboard')?.classList.add('hidden');
    shLoadMySubjects();
}

// ==========================================================
// FANLAR RO'YXATI
// ==========================================================
async function shLoadMySubjects() {
    const box = document.getElementById('sh-subjects-list');
    if (!box) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/my-subjects?telegram_id=${_shTgId()}`);
        const data = await res.json();
        const items = data.subjects || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-8">Hali fanlar yo\'q. Kabinetdan kurs qo\'shing.</p>';
            return;
        }

        box.innerHTML = '';
        items.forEach((s) => {
            const actual = Math.min(100, Math.max(0, s.actual_progress || 0));
            const color = s.pace_color || '#10B981';
            const card = document.createElement('div');
            card.className = 'bg-[#111827] border border-[#1F2937] hover:border-emerald-500/40 rounded-2xl p-3 flex gap-3 cursor-pointer transition-all active:scale-[0.99]';
            card.onclick = () => shSelectSubject(s.subject_id);
            card.innerHTML = `
                <div class="w-16 h-16 rounded-xl overflow-hidden bg-[#161F30] border border-[#283548] shrink-0">
                    <img src="${_shEscape(s.image_url || '')}" alt="" class="w-full h-full object-cover" onerror="this.style.display='none'">
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between gap-2 mb-1">
                        <h4 class="text-xs font-bold text-white truncate">${_shEscape(s.title)}</h4>
                        <span class="text-[8px] uppercase font-bold px-1.5 py-0.5 rounded border ${_shRankClass(s.rank_label)}">${_shEscape(s.rank_label)}</span>
                    </div>
                    <p class="text-[10px] text-slate-400 mb-1.5">
                        ${s.enrollment_status === 'completed' ? 'Yakunlangan' : 'Faol'} · ${_shPaceLabel(s.pace_status)}
                    </p>
                    <div class="flex items-center gap-2">
                        <div class="flex-1 h-1.5 rounded-full overflow-hidden bg-[#161F30]">
                            <div class="h-full rounded-full" style="width:${actual}%;background:${color}"></div>
                        </div>
                        <span class="text-[10px] font-mono font-bold" style="color:${color}">${actual}%</span>
                    </div>
                </div>
            `;
            box.appendChild(card);
        });
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-6">Yuklashda xatolik</p>';
    }
}

async function shSelectSubject(subjectId) {
    shState.subjectId = subjectId;
    document.getElementById('sh-subjects-list-wrap')?.classList.add('hidden');
    document.getElementById('sh-dashboard')?.classList.remove('hidden');

    try {
        const res = await fetch(`/api/subject-dashboard/overview?subject_id=${subjectId}&telegram_id=${_shTgId()}`);
        const ov = await res.json();
        shState.overview = ov;
        shRenderHeader(ov);
        shSwitchPanel(shState.panel || 'wiki');
    } catch (e) {
        console.error('Subject overview error', e);
    }
    if (window.lucide) lucide.createIcons();
}

function shRenderHeader(ov) {
    const title = document.getElementById('sh-subject-title');
    const desc = document.getElementById('sh-subject-desc');
    const badge = document.getElementById('sh-rank-badge');
    const paceLabel = document.getElementById('sh-pace-label');
    const bar = document.getElementById('sh-progress-bar');
    const marker = document.getElementById('sh-expected-marker');
    const pct = document.getElementById('sh-progress-pct');

    if (title) title.textContent = ov.title || 'Fan';
    if (desc) desc.textContent = ov.description || '';
    if (badge) {
        badge.textContent = ov.rank_label || 'Shogird';
        badge.className = `shrink-0 text-[9px] uppercase font-bold tracking-wider px-2 py-1 rounded-lg border ${_shRankClass(ov.rank_label)}`;
    }
    const actual = Math.min(100, Math.max(0, ov.actual_progress || 0));
    const expected = Math.min(100, Math.max(0, ov.expected_progress || 0));
    const color = ov.pace_color || '#10B981';
    if (paceLabel) {
        paceLabel.textContent = _shPaceLabel(ov.pace_status);
        paceLabel.style.color = color;
    }
    if (bar) {
        bar.style.width = `${actual}%`;
        bar.style.background = color;
    }
    if (marker) marker.style.left = `${expected}%`;
    if (pct) {
        pct.textContent = `${actual}%`;
        pct.style.color = color;
    }
}

// ==========================================================
// PANEL NAVIGATSIYA
// ==========================================================
function shSwitchPanel(panel) {
    shState.panel = panel;
    document.querySelectorAll('.sh-panel').forEach((el) => el.classList.add('hidden'));
    const target = document.getElementById(`sh-panel-${panel}`);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.sh-nav-chip').forEach((btn) => {
        const active = btn.getAttribute('data-sh-panel') === panel;
        btn.className = active
            ? 'sh-nav-chip snap-start px-3 py-1.5 rounded-xl text-[10px] font-bold whitespace-nowrap bg-emerald-500 text-slate-950 shadow-md cursor-pointer'
            : 'sh-nav-chip snap-start px-3 py-1.5 rounded-xl text-[10px] font-semibold whitespace-nowrap bg-[#161F30] border border-[#283548] text-slate-300 cursor-pointer';
    });

    const loaders = {
        wiki: shLoadWiki,
        master: shLoadMasterPanel,
        battle: shLoadBattle,
        schedule: shLoadSchedule,
        mistakes: shLoadMistakes,
        community: shLoadCommunity,
        books: shLoadBooks,
        modules: shLoadModules,
        quizzes: () => shLoadQuizzes('all'),
        diagnostics: shLoadDiagnostics,
    };
    // Master baza fan ID ga bog'liq emas — har doim yuklanadi
    if (loaders[panel] && (panel === 'master' || shState.subjectId)) loaders[panel]();
    if (window.lucide) lucide.createIcons();
}

// ==========================================================
// MASTER BAZA — SAVOL-JAVOB
// ==========================================================
async function shLoadMasterPanel() {
    const box = document.getElementById('sh-master-results');
    const gradeSel = document.getElementById('sh-master-grade');
    if (!box || !gradeSel) return;

    gradeSel.innerHTML = '<option value="">Yuklanmoqda...</option>';
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Sinflar yuklanmoqda...</p>';
    try {
        const res = await fetch('/api/master/grades');
        const data = await res.json().catch(() => ({}));
        const grades = data.grades || [];
        if (!res.ok) {
            gradeSel.innerHTML = '<option value="">Xatolik</option>';
            box.innerHTML = `<p class="text-[11px] text-rose-400 text-center py-4">API xato: ${_shEscape(data.detail || data.error || res.status)}</p>`;
            return;
        }
        if (!grades.length) {
            gradeSel.innerHTML = '<option value="">Sinf yo\'q</option>';
            box.innerHTML = `<p class="text-[11px] text-amber-400 text-center py-6 leading-relaxed">Master baza bo'sh.<br>Serverda <code class="text-emerald-400">import_master_baza.py</code> ishga tushirilishi kerak.${data.error ? '<br>' + _shEscape(data.error) : ''}</p>`;
            shState.masterGradesLoaded = false;
            return;
        }
        gradeSel.innerHTML = grades.map((g) =>
            `<option value="${g.grade}">${_shEscape(g.title)} · ${g.questions_count} savol</option>`
        ).join('');
        shState.masterGradesLoaded = true;
        if (!shState.masterGrade || !grades.some((g) => g.grade === shState.masterGrade)) {
            shState.masterGrade = grades[0].grade;
        }
        gradeSel.value = String(shState.masterGrade);
    } catch (e) {
        gradeSel.innerHTML = '<option value="">Xatolik</option>';
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Sinflarni yuklab bo\'lmadi (tarmoq)</p>';
        return;
    }

    await shLoadMasterTopics(shState.masterGrade || Number(gradeSel.value));
}

async function shOnMasterGradeChange() {
    const gradeSel = document.getElementById('sh-master-grade');
    const grade = Number(gradeSel?.value || 0);
    shState.masterGrade = grade || null;
    shState.masterTopic = null;
    await shLoadMasterTopics(grade);
}

async function shLoadMasterTopics(grade) {
    const topicSel = document.getElementById('sh-master-topic');
    const chips = document.getElementById('sh-master-topics');
    const box = document.getElementById('sh-master-results');
    const countEl = document.getElementById('sh-master-count');
    if (!topicSel || !box) return;

    if (!grade) {
        topicSel.disabled = true;
        topicSel.innerHTML = '<option value="">Mavzu</option>';
        if (chips) chips.innerHTML = '';
        box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Sinf tanlang</p>';
        return;
    }

    topicSel.disabled = true;
    topicSel.innerHTML = '<option value="">Yuklanmoqda...</option>';
    if (chips) chips.innerHTML = '';
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Mavzular yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/master/topics/${grade}`);
        const data = await res.json();
        const topics = data.topics || [];
        if (countEl) countEl.textContent = topics.length ? `${topics.length} mavzu` : '';

        if (!topics.length) {
            topicSel.innerHTML = '<option value="">Mavzu yo\'q</option>';
            box.innerHTML = `<p class="text-[11px] text-slate-500 text-center py-6">${grade}-sinf uchun mavzu topilmadi</p>`;
            return;
        }

        topicSel.disabled = false;
        topicSel.innerHTML = topics.map((t) =>
            `<option value="${t.topic_num}">${_shEscape(t.title)} · ${t.questions_count} savol</option>`
        ).join('');

        if (chips) {
            chips.innerHTML = topics.map((t) => `
                <button type="button" data-master-topic="${t.topic_num}"
                        onclick="shSelectMasterTopic(${t.topic_num})"
                        class="sh-master-topic-chip shrink-0 px-2.5 py-1 rounded-lg text-[10px] font-semibold border border-[#283548] bg-[#161F30] text-slate-300 cursor-pointer">
                    ${_shEscape(t.title)} · ${t.facts_count}
                </button>
            `).join('');
        }

        const preferred = shState.masterTopic && topics.some((t) => t.topic_num === shState.masterTopic)
            ? shState.masterTopic
            : topics[0].topic_num;
        topicSel.value = String(preferred);
        await shSelectMasterTopic(preferred);
    } catch (e) {
        topicSel.innerHTML = '<option value="">Xatolik</option>';
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Mavzular yuklanmadi</p>';
    }
}

async function shOnMasterTopicChange() {
    const topicSel = document.getElementById('sh-master-topic');
    const topicNum = Number(topicSel?.value || 0);
    await shSelectMasterTopic(topicNum);
}

async function shSelectMasterTopic(topicNum) {
    const grade = shState.masterGrade || Number(document.getElementById('sh-master-grade')?.value || 0);
    const box = document.getElementById('sh-master-results');
    const topicSel = document.getElementById('sh-master-topic');
    const countEl = document.getElementById('sh-master-count');
    if (!box || !grade || !topicNum) return;

    shState.masterTopic = topicNum;
    if (topicSel) topicSel.value = String(topicNum);

    document.querySelectorAll('.sh-master-topic-chip').forEach((btn) => {
        const active = Number(btn.getAttribute('data-master-topic')) === topicNum;
        btn.className = active
            ? 'sh-master-topic-chip shrink-0 px-2.5 py-1 rounded-lg text-[10px] font-bold border border-emerald-500/40 bg-emerald-500 text-slate-950 cursor-pointer'
            : 'sh-master-topic-chip shrink-0 px-2.5 py-1 rounded-lg text-[10px] font-semibold border border-[#283548] bg-[#161F30] text-slate-300 cursor-pointer';
    });

    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Savollar yuklanmoqda...</p>';
    try {
        const res = await fetch(`/api/master/facts/${grade}/${topicNum}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            box.innerHTML = `<p class="text-[11px] text-rose-400 text-center py-4">${_shEscape(err.detail || 'Topilmadi')}</p>`;
            return;
        }
        const data = await res.json();
        const facts = data.facts || [];
        if (countEl) countEl.textContent = `${facts.length} savol`;

        if (!facts.length) {
            shState.masterFacts = [];
            document.getElementById('sh-master-voice-start')?.classList.add('hidden');
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Bu mavzuda savol yo\'q</p>';
            return;
        }

        shState.masterFacts = facts;
        const startBtn = document.getElementById('sh-master-voice-start');
        if (startBtn) startBtn.classList.remove('hidden');

        box.innerHTML = facts.map((f, idx) => {
            const variants = [f.variant_b, f.variant_c, f.variant_d]
                .filter(Boolean)
                .map((v, i) => `<li class="text-[10px] text-slate-400">${['B', 'C', 'D'][i]}) ${_shEscape(v)}</li>`)
                .join('');
            return `
            <div class="master-fact-card bg-[#161F30] border border-[#283548] rounded-xl p-3 space-y-2" data-idx="${idx}">
                <div class="flex items-center justify-between gap-2">
                    <span class="text-[9px] font-mono text-emerald-400/90">${_shEscape(f.fakt_id || '')}${f.test_id ? ' · ' + _shEscape(f.test_id) : ''}</span>
                    <span class="text-[8px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">#${idx + 1}</span>
                </div>
                ${f.asl_gap ? `<p class="text-[11px] text-slate-300 leading-relaxed"><span class="text-[9px] text-slate-500 uppercase tracking-wide">Fakt · </span>${_shEscape(f.asl_gap)}</p>` : ''}
                ${f.fakt_kontekst ? `<p class="text-[10px] text-slate-500 italic leading-relaxed">${_shEscape(f.fakt_kontekst)}</p>` : ''}
                <div class="rounded-lg bg-[#0A0E17]/60 border border-[#283548]/80 px-2.5 py-2">
                    <p class="text-[9px] text-slate-500 mb-0.5 uppercase tracking-wide">Savol</p>
                    <p class="text-xs font-semibold text-white leading-snug">${_shEscape(f.savol_matni)}</p>
                </div>
                <div class="grid grid-cols-2 gap-1.5">
                    <button type="button" onclick="shSpeakMasterCard(${idx})"
                            class="py-1.5 rounded-lg text-[10px] font-bold bg-[#0A0E17] border border-[#283548] text-sky-300 active:scale-[0.98] cursor-pointer flex items-center justify-center gap-1">
                        <i data-lucide="volume-2" class="w-3 h-3"></i> O'qib ber
                    </button>
                    <button type="button" onclick="shListenMasterCard(${idx})"
                            class="py-1.5 rounded-lg text-[10px] font-bold bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 active:scale-[0.98] cursor-pointer flex items-center justify-center gap-1">
                        <i data-lucide="mic" class="w-3 h-3"></i> Ovozli javob
                    </button>
                </div>
                <p id="master-card-heard-${idx}" class="text-[10px] text-slate-500 min-h-[0.75rem]"></p>
                <div id="master-card-result-${idx}" class="hidden rounded-lg px-2.5 py-2 text-[11px]"></div>
                <button type="button" onclick="shToggleMasterAnswer(this)"
                        class="w-full py-1.5 rounded-lg text-[10px] font-bold bg-[#0A0E17] border border-[#283548] text-slate-300 active:scale-[0.98] cursor-pointer">
                    Javobni ko'rsatish
                </button>
                <div class="hidden master-answer space-y-1.5">
                    <div class="rounded-lg bg-emerald-500/10 border border-emerald-500/25 px-2.5 py-2">
                        <p class="text-[9px] text-emerald-400/80 mb-0.5 uppercase tracking-wide">Etalon javob</p>
                        <p class="text-[11px] font-semibold text-emerald-300 leading-snug">${_shEscape(f.etalon_javob)}</p>
                    </div>
                    ${variants ? `<ul class="space-y-0.5 pl-0.5">${variants}</ul>` : ''}
                    <p class="text-[9px] text-slate-500">
                        ${[f.klass, f.yonalish, f.tematik_teg, f.mavzu_reja].filter(Boolean).map(_shEscape).join(' · ')}
                    </p>
                </div>
            </div>`;
        }).join('');
        _shHaptic('light');
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Savollar yuklanmadi</p>';
    }
    if (window.lucide) lucide.createIcons();
}

function shToggleMasterAnswer(btn) {
    const wrap = btn?.parentElement?.querySelector('.master-answer');
    if (!wrap) return;
    const open = wrap.classList.contains('hidden');
    wrap.classList.toggle('hidden', !open);
    btn.textContent = open ? 'Javobni yashirish' : 'Javobni ko\'rsatish';
    if (open) _shHaptic('success');
}

// ==========================================================
// OVOZLI SAVOL-JAVOB (TTS + STT + etalon tekshiruv)
// ==========================================================
function _shSpeechRecognition() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    return Ctor ? new Ctor() : null;
}

function _shSpeakText(text) {
    if (!text || !window.speechSynthesis) return;
    try {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(String(text));
        const voices = window.speechSynthesis.getVoices?.() || [];
        const prefer = voices.find((v) => /uz/i.test(v.lang))
            || voices.find((v) => /ru|tr|en/i.test(v.lang))
            || null;
        if (prefer) utter.voice = prefer;
        utter.lang = prefer?.lang || 'ru-RU';
        utter.rate = 0.95;
        window.speechSynthesis.speak(utter);
    } catch (e) {}
}

function _shStopAllVoice() {
    const v = shState.masterVoice;
    try { window.speechSynthesis?.cancel(); } catch (e) {}
    try { v.recognition?.stop(); } catch (e) {}
    try { v.recognition?.abort(); } catch (e) {}
    v.recognition = null;
    if (v.mediaRecorder && v.mediaRecorder.state !== 'inactive') {
        try { v.mediaRecorder.stop(); } catch (e) {}
    }
    v.mediaRecorder = null;
    v.mediaChunks = [];
    if (v.mediaStream) {
        v.mediaStream.getTracks().forEach((t) => t.stop());
        v.mediaStream = null;
    }
    v.listening = false;
    const mic = document.getElementById('sh-master-mic-btn');
    if (mic) {
        mic.classList.remove('animate-pulse', 'bg-rose-500');
        mic.classList.add('bg-emerald-500');
        mic.innerHTML = '<i data-lucide="mic" class="w-3.5 h-3.5"></i> Javob aytish';
        if (window.lucide) lucide.createIcons();
    }
}

async function _shCheckAnswerText(userAnswer, fact) {
    try {
        const res = await fetch('/api/master/check-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_answer: userAnswer,
                etalon_javob: fact.etalon_javob,
                savol_matni: fact.savol_matni,
            }),
        });
        return await res.json();
    } catch (e) {
        return { transcript: userAnswer, is_correct: false, score: 0, feedback: 'Tekshiruv xatosi' };
    }
}

function _shShowVoiceResult(el, data, etalon) {
    if (!el) return;
    el.classList.remove('hidden');
    const ok = !!data.is_correct;
    el.className = `rounded-lg px-2.5 py-2 text-[11px] border ${ok
        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        : 'bg-rose-500/10 border-rose-500/30 text-rose-300'}`;
    el.innerHTML = `
        <p class="font-bold mb-0.5">${ok ? 'To\'g\'ri!' : 'Noto\'g\'ri'} · ${Number(data.score || 0)}%</p>
        <p class="text-[10px] opacity-90">${_shEscape(data.feedback || '')}</p>
        ${!ok ? `<p class="text-[10px] mt-1 text-slate-400">Etalon: <span class="text-emerald-300">${_shEscape(etalon)}</span></p>` : ''}
    `;
    _shHaptic(ok ? 'success' : 'error');
}

function shSpeakMasterCard(idx) {
    const fact = shState.masterFacts[idx];
    if (!fact) return;
    _shSpeakText(`${fact.savol_matni || ''}.`);
}

function shSpeakMasterDrill() {
    const fact = shState.masterFacts[shState.masterVoice.idx];
    if (!fact) return;
    _shSpeakText(`${fact.asl_gap ? fact.asl_gap + '. ' : ''}${fact.savol_matni || ''}`);
}

function shStartMasterVoiceDrill() {
    if (!shState.masterFacts.length) return;
    shState.masterVoice.active = true;
    shState.masterVoice.idx = 0;
    document.getElementById('sh-master-voice-drill')?.classList.remove('hidden');
    document.getElementById('sh-master-voice-start')?.classList.add('hidden');
    document.getElementById('sh-master-results')?.classList.add('hidden');
    shRenderMasterVoiceDrill();
    _shHaptic('light');
}

function shStopMasterVoiceDrill() {
    _shStopAllVoice();
    shState.masterVoice.active = false;
    document.getElementById('sh-master-voice-drill')?.classList.add('hidden');
    document.getElementById('sh-master-results')?.classList.remove('hidden');
    if (shState.masterFacts.length) {
        document.getElementById('sh-master-voice-start')?.classList.remove('hidden');
    }
}

function shRenderMasterVoiceDrill() {
    const facts = shState.masterFacts;
    const idx = shState.masterVoice.idx;
    const fact = facts[idx];
    if (!fact) return;
    const prog = document.getElementById('sh-master-voice-progress');
    const factEl = document.getElementById('sh-master-voice-fact');
    const qEl = document.getElementById('sh-master-voice-question');
    const heard = document.getElementById('sh-master-voice-heard');
    const result = document.getElementById('sh-master-voice-result');
    const textIn = document.getElementById('sh-master-text-answer');
    if (prog) prog.textContent = `${idx + 1} / ${facts.length}`;
    if (factEl) factEl.textContent = fact.asl_gap || '';
    if (qEl) qEl.textContent = fact.savol_matni || '';
    if (heard) heard.textContent = '';
    if (textIn) textIn.value = '';
    if (result) {
        result.classList.add('hidden');
        result.innerHTML = '';
    }
    if (window.lucide) lucide.createIcons();
}

async function shSubmitMasterTextAnswer() {
    const fact = shState.masterFacts[shState.masterVoice.idx];
    const input = document.getElementById('sh-master-text-answer');
    const heard = document.getElementById('sh-master-voice-heard');
    const result = document.getElementById('sh-master-voice-result');
    if (!fact || !input) return;
    const text = (input.value || '').trim();
    if (!text) {
        if (heard) heard.textContent = 'Avval javob yozing yoki mikrofon bilan ayting.';
        return;
    }
    if (heard) heard.textContent = `Siz: ${text}`;
    const data = await _shCheckAnswerText(text, fact);
    _shShowVoiceResult(result, data, fact.etalon_javob);
}

function shRevealMasterDrillAnswer() {
    const fact = shState.masterFacts[shState.masterVoice.idx];
    const result = document.getElementById('sh-master-voice-result');
    if (!fact || !result) return;
    result.classList.remove('hidden');
    result.className = 'rounded-lg px-2.5 py-2 text-[11px] bg-emerald-500/10 border border-emerald-500/25 text-emerald-300';
    result.innerHTML = `<p class="text-[9px] text-emerald-400/80 mb-0.5 uppercase">Etalon javob</p><p class="font-semibold">${_shEscape(fact.etalon_javob)}</p>`;
}

function shMasterVoiceNext() {
    _shStopAllVoice();
    if (shState.masterVoice.idx >= shState.masterFacts.length - 1) {
        shStopMasterVoiceDrill();
        _shHaptic('success');
        return;
    }
    shState.masterVoice.idx += 1;
    shRenderMasterVoiceDrill();
}

function _shSetMicButton(listening) {
    const mic = document.getElementById('sh-master-mic-btn');
    if (!mic) return;
    if (listening) {
        mic.classList.add('animate-pulse', 'bg-rose-500');
        mic.classList.remove('bg-emerald-500');
        mic.innerHTML = '<i data-lucide="square" class="w-3.5 h-3.5"></i> To\'xtatish';
    } else {
        mic.classList.remove('animate-pulse', 'bg-rose-500');
        mic.classList.add('bg-emerald-500');
        mic.innerHTML = '<i data-lucide="mic" class="w-3.5 h-3.5"></i> Javob aytish';
    }
    if (window.lucide) lucide.createIcons();
}

async function shToggleMasterMic() {
    const fact = shState.masterFacts[shState.masterVoice.idx];
    if (!fact) return;
    const heard = document.getElementById('sh-master-voice-heard');
    const result = document.getElementById('sh-master-voice-result');

    // 2-bosish: yozuvni to'xtatib tekshirish
    if (shState.masterVoice.listening) {
        if (heard) heard.textContent = 'Yozuv yakunlanmoqda...';
        const captured = await _shStopPushToTalk(fact, (msg) => {
            if (heard && msg) heard.textContent = msg;
        });
        shState.masterVoice.listening = false;
        _shSetMicButton(false);
        if (!captured.transcript) {
            if (heard) {
                heard.textContent = captured.error
                    || 'Javob eshitilmadi. Mikrofon ruxsatini tekshiring yoki pastda yozib tekshiring.';
            }
            return;
        }
        if (heard) heard.textContent = `Siz: ${captured.transcript}`;
        const data = captured.check || await _shCheckAnswerText(captured.transcript, fact);
        _shShowVoiceResult(result, data, fact.etalon_javob);
        return;
    }

    // 1-bosish: yozuvni boshlash
    if (result) result.classList.add('hidden');
    if (heard) heard.textContent = 'Gapiring... tayyor bo\'lgach yana «To\'xtatish» ni bosing';
    try {
        await _shStartPushToTalk((msg) => { if (heard && msg) heard.textContent = msg; });
        shState.masterVoice.listening = true;
        _shSetMicButton(true);
        _shHaptic('light');
    } catch (e) {
        shState.masterVoice.listening = false;
        _shSetMicButton(false);
        if (heard) {
            heard.textContent = 'Mikrofon ochilmadi. Telegram sozlamalarida mikrofon ruxsatini yoqing yoki javobni yozing.';
        }
    }
}

async function shListenMasterCard(idx) {
    const fact = shState.masterFacts[idx];
    if (!fact) return;
    const heardEl = document.getElementById(`master-card-heard-${idx}`);
    const resultEl = document.getElementById(`master-card-result-${idx}`);
    if (heardEl) heardEl.textContent = 'Tinglanmoqda... 5 soniya gapiring';
    if (resultEl) resultEl.classList.add('hidden');

    const captured = await _shCaptureVoiceAnswer((partial) => {
        if (heardEl && partial) heardEl.textContent = partial;
    }, fact);

    if (!captured.transcript) {
        if (heardEl) {
            heardEl.textContent = captured.error
                || 'Javob eshitilmadi. Qayta urinib ko\'ring yoki ovozli mashqda yozib tekshiring.';
        }
        return;
    }
    if (heardEl) heardEl.textContent = `Siz: ${captured.transcript}`;
    const data = captured.check || await _shCheckAnswerText(captured.transcript, fact);
    _shShowVoiceResult(resultEl, data, fact.etalon_javob);
}

async function _shStartPushToTalk(onPartial) {
    if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('getUserMedia yo\'q');
    }
    _shStopAllVoice();
    const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
    });
    shState.masterVoice.mediaStream = stream;
    const chunks = [];
    shState.masterVoice.mediaChunks = chunks;
    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
            : (MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : ''));
    const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    shState.masterVoice.mediaRecorder = recorder;
    recorder.ondataavailable = (ev) => { if (ev.data?.size) chunks.push(ev.data); };
    recorder.start(250);
    if (onPartial) onPartial('Yozilmoqda... gapiring, keyin To\'xtatish');

    // Parallel: brauzer STT (Telegramda uz-UZ ko'pincha ishlamaydi → ru-RU)
    const rec = _shSpeechRecognition();
    if (rec) {
        try {
            let live = '';
            const langs = ['uz-UZ', 'ru-RU', 'tr-TR', 'en-US'];
            rec.lang = langs[0];
            rec.interimResults = true;
            rec.continuous = true;
            rec.maxAlternatives = 3;
            rec.onresult = (event) => {
                let interim = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const t = event.results[i][0].transcript;
                    if (event.results[i].isFinal) live += `${t} `;
                    else interim += t;
                }
                shState.masterVoice._liveTranscript = (live || interim).trim();
                if (onPartial && shState.masterVoice._liveTranscript) {
                    onPartial(`Eshitildi: ${shState.masterVoice._liveTranscript}`);
                }
            };
            rec.onerror = (ev) => {
                // language-not-supported bo'lsa keyingi tilga o'tamiz
                const err = String(ev?.error || '');
                const idx = langs.indexOf(rec.lang);
                if ((err === 'language-not-supported' || err === 'service-not-allowed') && idx >= 0 && idx < langs.length - 1) {
                    try {
                        rec.lang = langs[idx + 1];
                        rec.start();
                    } catch (e2) {}
                }
            };
            shState.masterVoice.recognition = rec;
            rec.start();
        } catch (e) {
            shState.masterVoice.recognition = null;
        }
    }
}

async function _shStopPushToTalk(fact, onPartial) {
    const v = shState.masterVoice;
    const live = (v._liveTranscript || '').trim();
    v._liveTranscript = '';

    // STT to'xtatish
    try { v.recognition?.stop(); } catch (e) {}
    try { v.recognition?.abort(); } catch (e) {}
    v.recognition = null;

    const recorder = v.mediaRecorder;
    const stream = v.mediaStream;
    const chunks = v.mediaChunks || [];

    if (recorder && recorder.state !== 'inactive') {
        const stopped = new Promise((res) => {
            recorder.onstop = () => res();
            setTimeout(res, 1500);
        });
        try { recorder.requestData?.(); } catch (e) {}
        try { recorder.stop(); } catch (e) {}
        await stopped;
    }
    if (stream) stream.getTracks().forEach((t) => t.stop());
    v.mediaRecorder = null;
    v.mediaStream = null;

    // Brauzer STT matn bersa — darhol tekshiramiz (Telegramda ko'pincha bo'sh)
    if (live) {
        return { transcript: live, check: null, error: null };
    }

    if (!chunks.length) {
        return {
            transcript: '',
            check: null,
            error: 'Audio yozilmadi. Mikrofon ruxsatini tekshiring yoki javobni yozing.',
        };
    }

    const blob = new Blob(chunks, { type: (recorder && recorder.mimeType) || 'audio/webm' });
    if (blob.size < 800) {
        return {
            transcript: '',
            check: null,
            error: 'Yozuv juda qisqa. Uzunroq gapiring, keyin To\'xtatishni bosing.',
        };
    }

    if (onPartial) onPartial('Ovoz tekshirilmoqda...');
    try {
        const b64 = await _shBlobToBase64(blob);
        const res = await fetch('/api/master/voice-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                audio_base64: b64,
                mime_type: blob.type || 'audio/webm',
                etalon_javob: fact.etalon_javob,
                savol_matni: fact.savol_matni,
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            return {
                transcript: '',
                check: null,
                error: data.detail || `Server xatosi (${res.status}). Javobni yozib tekshiring.`,
            };
        }
        const transcript = (data.transcript || '').trim();
        if (!transcript) {
            return {
                transcript: '',
                check: data,
                error: data.feedback || 'Ovozni matnga aylantirib bo\'lmadi. Javobni yozib tekshiring.',
            };
        }
        return { transcript, check: data, error: null };
    } catch (e) {
        return {
            transcript: '',
            check: null,
            error: 'Tarmoq xatosi. Javobni pastda yozib tekshiring.',
        };
    }
}

/**
 * Kartalar uchun: qisqa avtomatik yozuv + Gemini / STT.
 * @returns {Promise<{transcript: string, check?: object, error?: string}>}
 */
function _shCaptureVoiceAnswer(onPartial, factForGemini) {
    return new Promise(async (resolve) => {
        try {
            await _shStartPushToTalk(onPartial);
            // Kartada avtomatik 6 soniya
            await new Promise((r) => setTimeout(r, 6000));
            resolve(await _shStopPushToTalk(factForGemini, onPartial));
        } catch (e) {
            resolve({
                transcript: '',
                check: null,
                error: 'Mikrofon ochilmadi. Ruxsat bering yoki ovozli mashqda yozib tekshiring.',
            });
        }
    });
}

function _shBlobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const result = String(reader.result || '');
            const idx = result.indexOf(',');
            resolve(idx >= 0 ? result.slice(idx + 1) : result);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// ==========================================================
// WIKI
// ==========================================================
function shOnWikiSearch() {
    clearTimeout(shState.wikiTimer);
    shState.wikiTimer = setTimeout(() => shLoadWiki(), 320);
}

async function shLoadWiki() {
    const box = document.getElementById('sh-wiki-results');
    if (!box || !shState.subjectId) return;
    const q = document.getElementById('sh-wiki-search')?.value || '';
    const ctype = document.getElementById('sh-wiki-type')?.value || 'all';
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Qidirilmoqda...</p>';

    try {
        const url = `/api/subject-dashboard/wiki?subject_id=${shState.subjectId}&q=${encodeURIComponent(q)}&concept_type=${encodeURIComponent(ctype)}`;
        const res = await fetch(url);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Hech narsa topilmadi</p>';
            return;
        }

        box.innerHTML = items.map((it) => `
            <div class="bg-[#161F30] border border-[#283548] rounded-xl p-3">
                <div class="flex items-center justify-between gap-2 mb-1">
                    <h4 class="text-xs font-bold text-white">${_shEscape(it.term)}</h4>
                    <span class="text-[8px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${_shEscape(it.concept_type)}</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed mb-2">${_shEscape(it.definition)}</p>
                <p class="text-[9px] text-slate-500">
                    ${_shEscape(it.source_book || 'Manba noma\'lum')}
                    ${it.grade_level ? ' · ' + _shEscape(it.grade_level) : ''}
                    ${it.topic_title ? ' · ' + _shEscape(it.topic_title) : ''}
                </p>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

// ==========================================================
// BATTLE
// ==========================================================
async function shLoadBattle() {
    if (!shState.subjectId) return;
    const sel = document.getElementById('sh-battle-module');
    const games = document.getElementById('sh-battle-games');
    try {
        const res = await fetch(`/api/subject-dashboard/battle-modules?subject_id=${shState.subjectId}`);
        const data = await res.json();
        if (sel) {
            sel.innerHTML = (data.modules || []).map((m) =>
                `<option value="${m.id}">${_shEscape(m.title)}${m.grade_level ? ' (' + _shEscape(m.grade_level) + ')' : ''}</option>`
            ).join('') || '<option value="">Modul yo\'q</option>';
        }
        if (games) {
            games.innerHTML = (data.game_types || []).map((g) => `
                <div class="flex items-center justify-between px-3 py-2 rounded-xl bg-[#161F30] border border-[#283548]">
                    <span class="text-[11px] text-slate-200 font-semibold">${_shEscape(g.title)}</span>
                    <span class="text-[9px] font-bold ${g.available ? 'text-emerald-400' : 'text-slate-500'}">${g.available ? 'Faol' : 'Tez orada'}</span>
                </div>
            `).join('');
        }
    } catch (e) {
        if (games) games.innerHTML = '<p class="text-[11px] text-rose-400">Yuklash xatosi</p>';
    }
}

async function shSendCommunityChallenge() {
    if (!shState.subjectId) return;
    const status = document.getElementById('sh-battle-status');
    const moduleId = document.getElementById('sh-battle-module')?.value;
    const level = document.getElementById('sh-battle-level')?.value || 'orta';
    const moduleTitle = document.getElementById('sh-battle-module')?.selectedOptions?.[0]?.text || '';

    try {
        const res = await fetch('/api/subject-dashboard/battle-challenge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _shTgId(),
                subject_id: shState.subjectId,
                module_id: moduleId ? Number(moduleId) : null,
                level,
                topic: moduleTitle || null,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Xato');

        if (status) {
            status.classList.remove('hidden');
            status.innerHTML = data.community_sent
                ? `Community ga yuborildi · <span class="text-emerald-400 break-all">${_shEscape(data.invite_link)}</span>`
                : `Havola tayyor · <span class="text-emerald-400 break-all">${_shEscape(data.invite_link)}</span>`;
        }

        if (window.Telegram?.WebApp?.openTelegramLink && data.invite_link) {
            // Share via Telegram if available
            try {
                window.Telegram.WebApp.openTelegramLink(
                    `https://t.me/share/url?url=${encodeURIComponent(data.invite_link)}&text=${encodeURIComponent(data.share_text || '')}`
                );
            } catch (e) {}
        }
        _shHaptic('success');
    } catch (e) {
        if (status) {
            status.classList.remove('hidden');
            status.textContent = 'Chaqiriq yuborilmadi';
            status.classList.add('text-rose-400');
        }
        _shHaptic('error');
    }
}

// ==========================================================
// JADVAL
// ==========================================================
async function shLoadSchedule() {
    const box = document.getElementById('sh-schedule-list');
    if (!box || !shState.subjectId) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/schedule?subject_id=${shState.subjectId}&telegram_id=${_shTgId()}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Jadval bo\'sh</p>';
            return;
        }

        box.innerHTML = '';
        items.forEach((it) => {
            let border = 'border-[#1F2937]';
            let badge = 'text-slate-400 bg-slate-500/10';
            let badgeText = 'Kutilmoqda';
            if (it.status === 'done') {
                border = 'border-emerald-500/20';
                badge = 'text-emerald-400 bg-emerald-500/10';
                badgeText = 'O\'tilgan';
            } else if (it.status === 'current') {
                border = 'border-amber-500/40';
                badge = 'text-amber-400 bg-amber-500/10';
                badgeText = 'Joriy';
            }

            const card = document.createElement('div');
            card.className = `bg-[#111827] border ${border} rounded-2xl p-3 cursor-pointer active:scale-[0.99] transition-all`;
            card.onclick = () => shOpenScheduleItem(it);
            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <p class="text-[9px] text-slate-500 font-mono mb-0.5">#${it.order_num}</p>
                        <h4 class="text-xs font-bold text-white">${_shEscape(it.topic_title)}</h4>
                        <p class="text-[10px] text-slate-400 mt-1">${it.planned_date || 'Sana belgilanmagan'}</p>
                    </div>
                    <span class="text-[8px] uppercase font-bold px-1.5 py-0.5 rounded ${badge}">${badgeText}</span>
                </div>
                ${it.test_score_avg != null ? `<p class="text-[10px] text-emerald-400 mt-2 font-semibold">Test: ${it.test_score_avg}%</p>` : ''}
            `;
            box.appendChild(card);
        });
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

function shOpenScheduleItem(it) {
    shState.scheduleVideoUrl = it.video_url || null;
    const modal = document.getElementById('sh-schedule-modal');
    const title = document.getElementById('sh-sched-modal-title');
    const meta = document.getElementById('sh-sched-modal-meta');
    const score = document.getElementById('sh-sched-modal-score');
    if (title) title.textContent = it.topic_title;
    if (meta) meta.textContent = `Tartib: #${it.order_num} · ${it.planned_date || 'Sana yo\'q'} · Holat: ${it.status}`;
    if (score) {
        score.textContent = it.test_score_avg != null
            ? `O'tgan mavzu test natijasi: ${it.test_score_avg}%`
            : 'Bu mavzu bo\'yicha test hali topshirilmagan';
    }
    modal?.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function shCloseScheduleModal() {
    document.getElementById('sh-schedule-modal')?.classList.add('hidden');
}

function shPlayScheduleVideo() {
    if (!shState.scheduleVideoUrl) return;
    shCloseScheduleModal();
    shOpenViewer('Dars videosi', shState.scheduleVideoUrl);
}

// ==========================================================
// XATOLAR BANKI
// ==========================================================
async function shLoadMistakes() {
    const box = document.getElementById('sh-mistakes-list');
    if (!box || !shState.subjectId) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/mistakes?subject_id=${shState.subjectId}&telegram_id=${_shTgId()}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = `
                <div class="py-10 text-center">
                    <div class="w-12 h-12 mx-auto mb-2 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                        <i data-lucide="check-circle-2" class="w-6 h-6"></i>
                    </div>
                    <p class="text-xs font-bold text-slate-300">Xatolar banki bo'sh</p>
                    <p class="text-[10px] text-slate-500 mt-1">Barcha savollar to'g'ri ishlangan</p>
                </div>`;
            if (window.lucide) lucide.createIcons();
            return;
        }

        box.innerHTML = '';
        items.forEach((m) => {
            const card = document.createElement('div');
            card.id = `sh-mistake-${m.id}`;
            card.className = 'bg-[#111827] border border-[#1F2937] rounded-2xl p-3 space-y-2 transition-all duration-500';
            const opts = (m.options || []).map((o) => {
                const isCorrect = o === m.correct_answer;
                const isWrong = o === m.user_wrong_answer;
                let cls = 'bg-[#161F30] border-[#283548] text-slate-300';
                if (isCorrect) cls = 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300';
                if (isWrong) cls = 'bg-rose-500/10 border-rose-500/40 text-rose-300';
                return `<button type="button" onclick="shResolveMistake(${m.id}, ${isCorrect})"
                    class="w-full text-left px-2.5 py-2 rounded-xl border text-[11px] ${cls} active:scale-[0.98] transition-all cursor-pointer">${_shEscape(o)}</button>`;
            }).join('');

            card.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="text-[9px] text-rose-400 font-bold">${m.mistake_count}× xato</span>
                </div>
                <p class="text-xs font-semibold text-white leading-snug">${_shEscape(m.question_text)}</p>
                <div class="space-y-1.5">${opts}</div>
                ${m.explanation ? `<p class="text-[10px] text-slate-400 leading-relaxed">${_shEscape(m.explanation)}</p>` : ''}
            `;
            box.appendChild(card);
        });
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

async function shResolveMistake(mistakeId, isCorrect) {
    try {
        const res = await fetch('/api/subject-dashboard/resolve-mistake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _shTgId(),
                mistake_id: mistakeId,
                is_correct: !!isCorrect,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Xato');

        if (data.is_resolved) {
            const el = document.getElementById(`sh-mistake-${mistakeId}`);
            if (el) {
                el.style.opacity = '0';
                el.style.transform = 'translateX(24px) scale(0.96)';
                setTimeout(() => {
                    el.remove();
                    const box = document.getElementById('sh-mistakes-list');
                    if (box && !box.children.length) shLoadMistakes();
                }, 420);
            }
            _shHaptic('success');
        } else {
            _shHaptic('error');
            shLoadMistakes();
        }
    } catch (e) {
        _shHaptic('error');
    }
}

// ==========================================================
// HAMJAMIYAT
// ==========================================================
function shFilterCommunity(tag) {
    shState.communityTag = tag;
    document.querySelectorAll('.sh-tag-chip').forEach((btn) => {
        const active = btn.getAttribute('data-sh-tag') === tag;
        btn.className = active
            ? 'sh-tag-chip px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-500 text-slate-950 cursor-pointer'
            : 'sh-tag-chip px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-[#161F30] border border-[#283548] text-slate-300 cursor-pointer';
    });
    shLoadCommunity();
}

async function shLoadCommunity() {
    const box = document.getElementById('sh-community-list');
    if (!box || !shState.subjectId) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';

    try {
        const tag = shState.communityTag === 'all' ? '' : shState.communityTag;
        const res = await fetch(`/api/subject-dashboard/community?subject_id=${shState.subjectId}&hashtag=${encodeURIComponent(tag)}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Hali xabarlar yo\'q</p>';
            return;
        }

        box.innerHTML = items.map((p) => `
            <div class="bg-[#111827] border border-[#1F2937] rounded-2xl p-3">
                <div class="flex items-center justify-between mb-1.5">
                    <span class="text-[11px] font-bold text-white">${_shEscape(p.user_name)}</span>
                    <span class="text-[9px] text-emerald-400 font-semibold">${_shEscape(p.hashtags)}</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed">${_shEscape(p.content)}</p>
                <p class="text-[9px] text-slate-600 mt-1.5">${p.created_at ? new Date(p.created_at).toLocaleString('uz-UZ') : ''}</p>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

async function shAskQuestion() {
    const contentEl = document.getElementById('sh-ask-content');
    const tagEl = document.getElementById('sh-ask-tag');
    const content = (contentEl?.value || '').trim();
    if (!content || !shState.subjectId) return;

    try {
        const res = await fetch('/api/subject-dashboard/ask-question', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _shTgId(),
                subject_id: shState.subjectId,
                content,
                hashtags: tagEl?.value || '#savol',
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Xato');
        if (contentEl) contentEl.value = '';
        _shHaptic('success');
        shLoadCommunity();
    } catch (e) {
        _shHaptic('error');
        alert('Xabar yuborilmadi');
    }
}

// ==========================================================
// KITOBLAR (IN-APP, NO DOWNLOAD)
// ==========================================================
async function shLoadBooks() {
    const box = document.getElementById('sh-books-list');
    if (!box || !shState.subjectId) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4 col-span-2">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/books?subject_id=${shState.subjectId}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6 col-span-2">Kitoblar yo\'q</p>';
            return;
        }

        box.innerHTML = '';
        items.forEach((b) => {
            const card = document.createElement('div');
            card.className = 'bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden cursor-pointer active:scale-[0.98] transition-all';
            card.onclick = () => shOpenViewer(b.title, b.viewer_url);
            card.innerHTML = `
                <div class="aspect-[3/4] bg-[#161F30] relative">
                    <img src="${_shEscape(b.cover_url || '')}" alt="" class="w-full h-full object-cover" onerror="this.style.opacity=0.2">
                    <span class="absolute top-1.5 left-1.5 text-[8px] font-bold uppercase px-1.5 py-0.5 rounded bg-[#0A0E17]/80 text-emerald-400 border border-emerald-500/30">${_shEscape(b.book_type)}</span>
                </div>
                <div class="p-2">
                    <p class="text-[10px] font-bold text-white line-clamp-2 leading-tight">${_shEscape(b.title)}</p>
                    <p class="text-[8px] text-slate-500 mt-1">Faqat platformada</p>
                </div>
            `;
            box.appendChild(card);
        });
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4 col-span-2">Xatolik</p>';
    }
}

function shOpenViewer(title, url) {
    const modal = document.getElementById('sh-viewer-modal');
    const titleEl = document.getElementById('sh-viewer-title');
    const video = document.getElementById('sh-viewer-video');
    if (!modal || !video) return;
    if (titleEl) titleEl.textContent = title || 'Ko\'rish';
    video.src = url || '';
    video.setAttribute('controlsList', 'nodownload noremoteplayback');
    modal.classList.remove('hidden');
    // Download / context menu bloklash
    video.oncontextmenu = () => false;
    if (window.lucide) lucide.createIcons();
}

function shCloseViewer() {
    const modal = document.getElementById('sh-viewer-modal');
    const video = document.getElementById('sh-viewer-video');
    if (video) {
        video.pause();
        video.removeAttribute('src');
        video.load();
    }
    modal?.classList.add('hidden');
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        shCloseViewer();
        shCloseScheduleModal();
    }
});

// ==========================================================
// MODULLAR
// ==========================================================
async function shLoadModules() {
    const box = document.getElementById('sh-modules-list');
    if (!box || !shState.subjectId) return;
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/modules?subject_id=${shState.subjectId}&telegram_id=${_shTgId()}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Modullar yo\'q</p>';
            return;
        }

        box.innerHTML = items.map((m) => `
            <div class="bg-[#111827] border border-[#1F2937] rounded-2xl p-3 flex gap-3">
                <div class="w-14 h-14 rounded-xl overflow-hidden bg-[#161F30] shrink-0 border border-[#283548]">
                    <img src="${_shEscape(m.image_url || '')}" class="w-full h-full object-cover" alt="" onerror="this.style.display='none'">
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between gap-2">
                        <h4 class="text-xs font-bold text-white truncate">${_shEscape(m.title)}</h4>
                        ${m.owned ? '<span class="text-[8px] font-bold text-emerald-400">Sizniki</span>' : ''}
                    </div>
                    <p class="text-[10px] text-slate-400 line-clamp-2 mt-0.5">${_shEscape(m.description || '')}</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-[10px] text-slate-500">${_shEscape(m.grade_level || '')}</span>
                        <span class="text-[11px] font-bold text-amber-400 font-mono">${Number(m.price_coin || 0).toLocaleString('uz-UZ')} so'm</span>
                    </div>
                    ${!m.owned && m.is_standalone ? `
                        <button type="button" onclick="typeof switchTab==='function'&&switchTab('books')"
                            class="mt-2 w-full py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold cursor-pointer">
                            Alohida sotib olish
                        </button>` : ''}
                </div>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

// ==========================================================
// TESTLAR
// ==========================================================
async function shLoadQuizzes(filter) {
    const box = document.getElementById('sh-quizzes-list');
    if (!box || !shState.subjectId) return;

    ['all', 'free', 'paid'].forEach((f) => {
        const btn = document.getElementById(`sh-quiz-filter-${f}`);
        if (!btn) return;
        const active = f === filter;
        btn.className = active
            ? 'px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-500 text-slate-950 cursor-pointer'
            : 'px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-[#161F30] border border-[#283548] text-slate-300 cursor-pointer';
    });

    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';
    let paidParam = '';
    if (filter === 'paid') paidParam = '&paid=true';
    if (filter === 'free') paidParam = '&paid=false';

    try {
        const res = await fetch(`/api/subject-dashboard/quizzes?subject_id=${shState.subjectId}${paidParam}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Testlar yo\'q</p>';
            return;
        }

        box.innerHTML = items.map((q) => `
            <div class="bg-[#111827] border border-[#1F2937] rounded-2xl p-3 flex items-center justify-between gap-2">
                <div class="min-w-0">
                    <h4 class="text-xs font-bold text-white truncate">${_shEscape(q.title)}</h4>
                    <p class="text-[10px] text-slate-400 mt-0.5">
                        ${_shEscape(q.scope)} · ${q.is_paid ? (Number(q.price_coin || 0).toLocaleString('uz-UZ') + ' so\'m') : 'Bepul'}
                    </p>
                </div>
                <button type="button" onclick="shGoToQuiz(${q.quiz_id || 1})"
                    class="shrink-0 px-3 py-1.5 rounded-xl bg-emerald-500 text-slate-950 text-[10px] font-bold cursor-pointer active:scale-95">
                    Ochish
                </button>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

function shGoToQuiz(quizId) {
    if (typeof switchTab === 'function') {
        switchTab('tests');
    }
    // Kelajakda quiz_id bilan to'g'ridan-to'g'ri ochish
    window.__pendingQuizId = quizId;
}

// ==========================================================
// DIAGNOSTIKA
// ==========================================================
async function shLoadDiagnostics() {
    const box = document.getElementById('sh-diagnostics-body');
    if (!box || !shState.subjectId) return;
    const quizId = Number(document.getElementById('sh-diag-quiz-id')?.value || 1);
    box.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Yuklanmoqda...</p>';

    try {
        const res = await fetch(`/api/subject-dashboard/diagnostics/${quizId}?subject_id=${shState.subjectId}&telegram_id=${_shTgId()}`);
        const d = await res.json();

        const sources = (d.sources || []).map((s) =>
            `<a href="${_shEscape(s.url)}" target="_blank" rel="noopener"
                class="block text-[11px] text-sky-400 hover:underline truncate">${_shEscape(s.title || s.url)}</a>`
        ).join('') || '<p class="text-[10px] text-slate-500">Manbalar yo\'q</p>';

        box.innerHTML = `
            <div class="bg-[#111827] border border-[#1F2937] rounded-2xl p-3 space-y-3">
                <h3 class="text-xs font-bold text-white">${_shEscape(d.quiz_title || 'Diagnostika')}</h3>
                ${d.video_review_url ? `
                    <div oncontextmenu="return false;">
                        <p class="text-[9px] text-slate-500 mb-1 uppercase tracking-wider">Videosharh</p>
                        <video controls controlsList="nodownload noremoteplayback" disablePictureInPicture
                               oncontextmenu="return false;" playsinline
                               class="w-full rounded-xl bg-black aspect-video"
                               src="${_shEscape(d.video_review_url)}"></video>
                    </div>` : ''}
                <div>
                    <p class="text-[9px] text-slate-500 mb-1 uppercase tracking-wider">Rasmiy manbalar</p>
                    <div class="space-y-1">${sources}</div>
                </div>
                <div>
                    <p class="text-[9px] text-slate-500 mb-1 uppercase tracking-wider">Umumiy tahlil</p>
                    <p class="text-[11px] text-slate-300 leading-relaxed">${_shEscape(d.analysis_text || '')}</p>
                </div>
                <div class="grid grid-cols-1 gap-2">
                    <div class="rounded-xl bg-emerald-500/5 border border-emerald-500/20 p-2.5">
                        <p class="text-[9px] font-bold text-emerald-400 uppercase mb-1">Kuchli tomonlar</p>
                        <p class="text-[11px] text-slate-300 whitespace-pre-line">${_shEscape(d.strengths_text || '—')}</p>
                    </div>
                    <div class="rounded-xl bg-rose-500/5 border border-rose-500/20 p-2.5">
                        <p class="text-[9px] font-bold text-rose-400 uppercase mb-1">Ojiz tomonlar</p>
                        <p class="text-[11px] text-slate-300 whitespace-pre-line">${_shEscape(d.weaknesses_text || '—')}</p>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        box.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-4">Xatolik</p>';
    }
}

// Global export (switchTab / Cabinet dan chaqirish uchun)
window.openSubjectHub = openSubjectHub;
window.initSubjectHub = initSubjectHub;
window.shSwitchPanel = shSwitchPanel;
window.shBackToSubjects = shBackToSubjects;
window.shOnWikiSearch = shOnWikiSearch;
window.shLoadWiki = shLoadWiki;
window.shLoadMasterPanel = shLoadMasterPanel;
window.shOnMasterGradeChange = shOnMasterGradeChange;
window.shOnMasterTopicChange = shOnMasterTopicChange;
window.shSelectMasterTopic = shSelectMasterTopic;
window.shToggleMasterAnswer = shToggleMasterAnswer;
window.shSpeakMasterCard = shSpeakMasterCard;
window.shListenMasterCard = shListenMasterCard;
window.shStartMasterVoiceDrill = shStartMasterVoiceDrill;
window.shStopMasterVoiceDrill = shStopMasterVoiceDrill;
window.shSpeakMasterDrill = shSpeakMasterDrill;
window.shToggleMasterMic = shToggleMasterMic;
window.shSubmitMasterTextAnswer = shSubmitMasterTextAnswer;
window.shRevealMasterDrillAnswer = shRevealMasterDrillAnswer;
window.shMasterVoiceNext = shMasterVoiceNext;
window.shSendCommunityChallenge = shSendCommunityChallenge;
window.shResolveMistake = shResolveMistake;
window.shFilterCommunity = shFilterCommunity;
window.shAskQuestion = shAskQuestion;
window.shCloseViewer = shCloseViewer;
window.shCloseScheduleModal = shCloseScheduleModal;
window.shPlayScheduleVideo = shPlayScheduleVideo;
window.shLoadQuizzes = shLoadQuizzes;
window.shGoToQuiz = shGoToQuiz;
window.shLoadDiagnostics = shLoadDiagnostics;
