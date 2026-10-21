// web/static/js/octagon.js — OKTAGON (PvP jang zali va diagnostika)

let octagonPresenceTimer = null;
let octagonInviteTimer = null;
let octagonActiveBattleId = null;
let octagonUnlockedStickers = ['🔥', '😤', '😮', '💪'];
let octagonRegionsLoaded = false;

function _octTgId() {
    if (typeof getRequestTelegramId === 'function') return getRequestTelegramId();
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 123456789;
}

function _octHaptic(type) {
    try {
        const hf = window.Telegram?.WebApp?.HapticFeedback;
        if (!hf) return;
        if (type === 'success') hf.notificationOccurred('success');
        else if (type === 'error') hf.notificationOccurred('error');
        else hf.impactOccurred(type || 'light');
    } catch (e) {}
}

function _octBattleSettings() {
    const subject = document.getElementById('oct-battle-subject')?.value || 'tarix';
    const level = document.getElementById('oct-battle-level')?.value || 'orta';
    const topic = (document.getElementById('oct-battle-topic')?.value || '').trim();
    return { subject, level, topic: topic || null };
}

function _setInviteStatus(text, show) {
    const el = document.getElementById('oct-invite-status');
    if (!el) return;
    if (!show) {
        el.classList.add('hidden');
        el.innerText = '';
        return;
    }
    el.classList.remove('hidden');
    el.innerText = text;
}

function _levelLabel(level) {
    const map = { oson: 'Oson', orta: "O'rta", qiyin: 'Qiyin' };
    return map[level] || level || '—';
}

function _escapeHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ==========================================================
// BO'LIM INIT / PRESENCE
// ==========================================================
async function initOctagonSection() {
    await Promise.all([
        octagonSendPresence(),
        loadOctagonLeaderboard(),
        loadOctagonHistory(),
        loadOctagonMyRank(),
    ]);

    if (octagonPresenceTimer) clearInterval(octagonPresenceTimer);
    octagonPresenceTimer = setInterval(() => {
        if (typeof currentTab !== 'undefined' && currentTab === 'octagon') {
            octagonSendPresence();
        }
    }, 45000);

    // Telegram start_param orqali kelgan duel havolasini qabul qilish
    const startParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
    if (startParam && String(startParam).startsWith('oct_')) {
        await acceptOctagonInviteFromStart(String(startParam).slice(4));
    }

    if (window.lucide) lucide.createIcons();
}

async function octagonSendPresence() {
    try {
        const settings = _octBattleSettings();
        const res = await fetch('/api/octagon/presence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _octTgId(),
                subject: settings.subject,
            }),
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.stickers?.unlocked) {
            octagonUnlockedStickers = data.stickers.unlocked;
            renderBattleReactionBar(data.stickers);
        }
    } catch (e) {
        console.error('Octagon presence xatosi:', e);
    }
}

async function loadOctagonMyRank() {
    try {
        const res = await fetch(`/api/octagon/user-rank?telegram_id=${_octTgId()}`);
        if (!res.ok) return;
        const data = await res.json();
        const el = document.getElementById('octagon-my-rank');
        if (el && data.rank) el.innerText = data.rank;
    } catch (e) {}
}

// ==========================================================
// REYTING / PESHQADAMLAR
// ==========================================================
async function loadOctagonLeaderboard() {
    const container = document.getElementById('octagon-leaderboard');
    if (!container) return;

    const region = document.getElementById('oct-filter-region')?.value || 'all';
    const subject = document.getElementById('oct-filter-subject')?.value || '';

    const params = new URLSearchParams({ limit: '15' });
    if (region && region !== 'all') params.set('region', region);
    if (subject) params.set('subject', subject);

    try {
        const res = await fetch(`/api/octagon/leaderboard?${params}`);
        const data = await res.json();
        const items = data.items || [];

        if (!octagonRegionsLoaded) {
            await _populateRegionFilter();
            octagonRegionsLoaded = true;
        }

        if (!items.length) {
            container.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-3">Peshqadamlar topilmadi</p>';
            return;
        }

        container.innerHTML = items.map((row, idx) => {
            const onlineDot = row.is_online
                ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]"></span>'
                : '<span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span>';
            const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${row.rank || idx + 1}`;
            return `
                <div class="flex items-center gap-2 px-2 py-1.5 rounded-xl bg-[#0A0E17]/70 border border-[#1F2937]/80">
                    <span class="w-7 text-center text-[11px] font-bold text-amber-400/90 shrink-0">${medal}</span>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5">
                            ${onlineDot}
                            <p class="text-[11px] font-bold text-white truncate">${_escapeHtml(row.full_name)}</p>
                        </div>
                        <p class="text-[9px] text-slate-500 truncate">${_escapeHtml(row.region)} · ${row.victories || 0} g'alaba</p>
                    </div>
                    <span class="text-[11px] font-black text-amber-400 font-mono shrink-0">${row.rating}</span>
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-3">Reyting yuklanmadi</p>';
    }
}

async function _populateRegionFilter() {
    const select = document.getElementById('oct-filter-region');
    if (!select || select.options.length > 1) return;
    try {
        const res = await fetch(`/api/octagon/history?telegram_id=${_octTgId()}`);
        const data = await res.json();
        const regions = (data.filters && data.filters.regions) || [];
        regions.forEach((r) => {
            if (r === 'all') return;
            const opt = document.createElement('option');
            opt.value = r;
            opt.textContent = r;
            select.appendChild(opt);
        });
    } catch (e) {}
}

// ==========================================================
// DUEL HAVOLASI (60 SEKUND)
// ==========================================================
async function generateDuelInviteLink(opponentId) {
    const settings = _octBattleSettings();
    _setInviteStatus('Havola yaratilmoqda...', true);
    _octHaptic('medium');

    try {
        const body = {
            telegram_id: _octTgId(),
            subject: settings.subject,
            level: settings.level,
            topic: settings.topic,
        };
        if (opponentId) body.opponent_id = opponentId;

        const res = await fetch('/api/octagon/create-invite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Havola yaratilmadi');

        const link = data.invite_link;
        let left = data.expires_in || 60;

        if (octagonInviteTimer) clearInterval(octagonInviteTimer);
        _setInviteStatus(`Havola faol: ${left}s · do'stingiz ulashing`, true);

        octagonInviteTimer = setInterval(async () => {
            left -= 1;
            if (left <= 0) {
                clearInterval(octagonInviteTimer);
                octagonInviteTimer = null;
                _setInviteStatus('Havola muddati tugadi (60s)', true);
                try {
                    await fetch(`/api/octagon/check-invite/${data.room_code}?telegram_id=${_octTgId()}`);
                } catch (e) {}
                return;
            }
            _setInviteStatus(`Havola faol: ${left}s · ${data.room_code}`, true);
        }, 1000);

        // Raqib a'zo bo'lsa onlayn holatini ko'rsatish
        if (data.opponent && data.opponent.is_member) {
            const online = data.opponent.is_online ? '🟢 Onlayn' : '⚪ Oflayn';
            _setInviteStatus(`${online} · ${data.opponent.full_name} · ${left}s`, true);
        }

        const tg = window.Telegram?.WebApp;
        if (tg?.openTelegramLink) {
            const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(
                `⚔️ Oktagon jangiga chaqiruv!\nFan: ${settings.subject} · ${_levelLabel(settings.level)}` +
                (settings.topic ? `\nMavzu: ${settings.topic}` : '') +
                `\n\n60 soniya ichida qabul qiling:`
            )}`;
            tg.openTelegramLink(shareUrl);
        } else if (navigator.clipboard) {
            await navigator.clipboard.writeText(link);
            _setInviteStatus(`Havola nusxalandi · ${left}s`, true);
        } else {
            prompt('Duel havolasi:', link);
        }

        _octHaptic('success');
        return data;
    } catch (e) {
        console.error(e);
        _setInviteStatus(e.message || 'Xatolik yuz berdi', true);
        _octHaptic('error');
        return null;
    }
}

async function acceptOctagonInviteFromStart(roomCode) {
    if (!roomCode) return;
    try {
        const check = await fetch(`/api/octagon/check-invite/${roomCode}?telegram_id=${_octTgId()}`);
        const info = await check.json();
        if (!info.valid) {
            _setInviteStatus(info.message || 'Taklif yaroqsiz', true);
            return;
        }

        const res = await fetch('/api/octagon/accept-invite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: _octTgId(), room_code: roomCode }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Qabul qilinmadi');

        if (data.battle_id) {
            showBattleReactionBar(data.battle_id);
            await showBattleDiagnostic(data.battle_id);
            await loadOctagonHistory();
        }
    } catch (e) {
        _setInviteStatus(e.message || 'Taklifni qabul qilib bo\'lmadi', true);
    }
}

// ==========================================================
// BOT / JONLI RAQIB
// ==========================================================
async function startDuelWithBot() {
    const settings = _octBattleSettings();
    _setInviteStatus('Bot bilan jang boshlanmoqda...', true);
    _octHaptic('medium');

    try {
        // Avvalgi kutishdagi havolalarni bekor qilish (server ham qiladi)
        await fetch('/api/octagon/cancel-invites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: _octTgId() }),
        });

        if (octagonInviteTimer) {
            clearInterval(octagonInviteTimer);
            octagonInviteTimer = null;
        }

        const res = await fetch('/api/octagon/start-bot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _octTgId(),
                subject: settings.subject,
                level: settings.level,
                topic: settings.topic || 'Umumiy mashq',
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Bot jangi boshlanmadi');

        _setInviteStatus('Bot jangi yakunlandi', true);
        showBattleReactionBar(data.battle_id);
        await showBattleDiagnostic(data.battle_id);
        await loadOctagonHistory();
        await loadOctagonMyRank();
        _octHaptic('success');
    } catch (e) {
        _setInviteStatus(e.message || 'Xatolik', true);
        _octHaptic('error');
    }
}

async function findRandomOnlineOpponent() {
    const settings = _octBattleSettings();
    _setInviteStatus('Onlayn raqib qidirilmoqda...', true);
    _octHaptic('medium');

    try {
        await fetch('/api/octagon/cancel-invites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: _octTgId() }),
        });

        if (octagonInviteTimer) {
            clearInterval(octagonInviteTimer);
            octagonInviteTimer = null;
        }

        const res = await fetch('/api/octagon/find-opponent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _octTgId(),
                subject: settings.subject,
                level: settings.level,
                topic: settings.topic,
            }),
        });
        const data = await res.json();

        if (data.status === 'not_found') {
            _setInviteStatus(data.message || 'Onlayn raqib yo\'q', true);
            _octHaptic('error');
            return;
        }
        if (!res.ok) throw new Error(data.detail || 'Raqib topilmadi');

        const name = data.opponent?.full_name || 'Raqib';
        _setInviteStatus(`Topildi: ${name}`, true);
        showBattleReactionBar(data.battle_id);
        await showBattleDiagnostic(data.battle_id);
        await loadOctagonHistory();
        await loadOctagonMyRank();
        _octHaptic('success');
    } catch (e) {
        _setInviteStatus(e.message || 'Xatolik', true);
        _octHaptic('error');
    }
}

// ==========================================================
// JANG TARIXI VA REVANSH
// ==========================================================
async function loadOctagonHistory() {
    const container = document.getElementById('octagon-history-list');
    if (!container) return;

    const subject = document.getElementById('oct-filter-subject')?.value || '';
    const level = document.getElementById('oct-filter-level')?.value || '';
    const region = document.getElementById('oct-filter-region')?.value || 'all';

    const params = new URLSearchParams({ telegram_id: String(_octTgId()) });
    if (subject) params.set('subject', subject);
    if (level) params.set('level', level);
    if (region && region !== 'all') params.set('region', region);

    try {
        const res = await fetch(`/api/octagon/history?${params}`);
        const data = await res.json();
        const items = data.items || [];

        if (!items.length) {
            container.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-4">Hali janglar yo\'q. Birinchi duelni boshlang!</p>';
            return;
        }

        container.innerHTML = items.map((item) => {
            const isWin = item.outcome === 'win';
            const isLoss = item.outcome === 'loss';
            const border = isWin
                ? 'border-emerald-500/40 bg-emerald-500/5'
                : isLoss
                    ? 'border-rose-500/40 bg-rose-500/5'
                    : 'border-[#283548] bg-[#0A0E17]/60';
            const badge = isWin
                ? '<span class="text-[9px] font-bold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-1.5 py-0.5 rounded">G\'alaba</span>'
                : isLoss
                    ? '<span class="text-[9px] font-bold text-rose-400 bg-rose-500/15 border border-rose-500/30 px-1.5 py-0.5 rounded">Mag\'lubiyat</span>'
                    : '<span class="text-[9px] font-bold text-slate-400 bg-slate-500/15 border border-slate-500/30 px-1.5 py-0.5 rounded">Durang</span>';

            const opp = item.opponent || {};
            const online = opp.is_online
                ? '<span class="text-emerald-400">●</span>'
                : '<span class="text-slate-600">●</span>';

            const rematchBtn = (isLoss && item.can_rematch)
                ? `<button type="button" onclick="requestOctagonRematch(${item.battle_id})" class="px-2 py-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-[9px] font-bold rounded-lg active:scale-95 cursor-pointer">Revansh</button>`
                : '';

            const challengeBtn = item.can_rematch
                ? `<button type="button" onclick="challengeFromHistory(${opp.telegram_id || 'null'}, '${_escapeHtml(item.subject)}', '${_escapeHtml(item.level)}', '${_escapeHtml(item.topic || '')}')" class="px-2 py-1 bg-[#161F30] hover:bg-[#1F2937] border border-[#283548] text-slate-300 text-[9px] font-bold rounded-lg active:scale-95 cursor-pointer">Chaqirish</button>`
                : '';

            return `
                <div class="rounded-xl border ${border} p-2.5 space-y-2">
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="flex items-center gap-1.5 mb-0.5">
                                ${online}
                                <p class="text-[11px] font-bold text-white truncate">${_escapeHtml(opp.full_name || 'Raqib')}</p>
                            </div>
                            <p class="text-[9px] text-slate-500">${_escapeHtml(opp.region || '—')} · ⭐ ${opp.rating || '—'}</p>
                        </div>
                        ${badge}
                    </div>
                    <div class="flex items-center justify-between text-[9px] text-slate-400">
                        <span>${_escapeHtml(item.subject)} · ${_levelLabel(item.level)}${item.topic ? ' · ' + _escapeHtml(item.topic) : ''}</span>
                        <span class="font-mono text-slate-300">${item.my_score}:${item.opponent_score}</span>
                    </div>
                    <div class="flex items-center justify-between gap-2">
                        <button type="button" onclick="showBattleDiagnostic(${item.battle_id})" class="text-[9px] text-amber-400/90 font-semibold hover:text-amber-300 cursor-pointer">Diagnostika ›</button>
                        <div class="flex gap-1.5">
                            ${challengeBtn}
                            ${rematchBtn}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = '<p class="text-[11px] text-rose-400 text-center py-3">Tarix yuklanmadi</p>';
    }
}

async function challengeFromHistory(opponentId, subject, level, topic) {
    if (subject) {
        const sEl = document.getElementById('oct-battle-subject');
        if (sEl) sEl.value = subject;
    }
    if (level) {
        const lEl = document.getElementById('oct-battle-level');
        if (lEl) lEl.value = level;
    }
    if (topic) {
        const tEl = document.getElementById('oct-battle-topic');
        if (tEl) tEl.value = topic;
    }
    await generateDuelInviteLink(opponentId || undefined);
}

async function requestOctagonRematch(battleId) {
    _octHaptic('medium');
    _setInviteStatus('Revansh tayyorlanmoqda...', true);

    try {
        const res = await fetch('/api/octagon/rematch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: _octTgId(), battle_id: battleId }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Revansh yuborilmadi');

        if (data.notified && data.opponent_online) {
            _setInviteStatus(`Revansh xabari yuborildi · ${data.opponent?.full_name || 'raqib'} onlayn`, true);
            _octHaptic('success');
            return;
        }

        // Oflayn — ulashish havolasini ochish
        const link = data.invite_link;
        const tg = window.Telegram?.WebApp;
        if (tg?.openTelegramLink) {
            const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent('🔁 Oktagon revansh chaqiruvi (60 soniya)!')}`;
            tg.openTelegramLink(shareUrl);
        } else if (navigator.clipboard) {
            await navigator.clipboard.writeText(link);
        }
        _setInviteStatus('Revansh havolasi ochildi (60s)', true);
        _octHaptic('success');
    } catch (e) {
        _setInviteStatus(e.message || 'Revansh xatosi', true);
        _octHaptic('error');
    }
}

// ==========================================================
// STIKERLAR / REAKSIYALAR
// ==========================================================
function renderBattleReactionBar(stickers) {
    const bar = document.getElementById('battle-reaction-bar');
    const buttons = document.getElementById('battle-reaction-buttons');
    const tierEl = document.getElementById('oct-sticker-tier');
    if (!buttons) return;

    const unlocked = stickers?.unlocked || octagonUnlockedStickers;
    const all = [
        ...(stickers?.basic || ['🔥', '😤', '😮', '💪']),
        ...(stickers?.pro || ['🏆', '⚡']),
        ...(stickers?.premium || ['👑', '💎']),
    ];
    const unique = [...new Set(all)];

    if (tierEl) {
        const tier = (stickers?.tier || 'free').toUpperCase();
        tierEl.innerText = tier;
    }

    buttons.innerHTML = unique.map((emoji) => {
        const locked = !unlocked.includes(emoji);
        return `
            <button type="button"
                onclick="sendBattleSticker('${emoji}')"
                class="w-10 h-10 rounded-xl text-lg flex items-center justify-center border transition-all active:scale-90 cursor-pointer ${
                    locked
                        ? 'bg-[#0A0E17] border-[#283548] opacity-40 grayscale'
                        : 'bg-[#161F30] border-amber-500/30 hover:border-amber-400 hover:bg-amber-500/10'
                }"
                title="${locked ? 'Pro/Premium kerak' : emoji}">
                ${emoji}
            </button>
        `;
    }).join('');
}

function showBattleReactionBar(battleId) {
    octagonActiveBattleId = battleId;
    const bar = document.getElementById('battle-reaction-bar');
    if (bar) bar.classList.remove('hidden');
    renderBattleReactionBar({ unlocked: octagonUnlockedStickers, tier: 'free', basic: ['🔥', '😤', '😮', '💪'], pro: ['🏆', '⚡'], premium: ['👑', '💎'] });
    octagonSendPresence();
}

function hideBattleReactionBar() {
    const bar = document.getElementById('battle-reaction-bar');
    if (bar) bar.classList.add('hidden');
    octagonActiveBattleId = null;
}

async function sendBattleSticker(emoji) {
    if (!octagonActiveBattleId) {
        _setInviteStatus('Avval jangni boshlang', true);
        return;
    }
    if (!octagonUnlockedStickers.includes(emoji)) {
        _setInviteStatus('Bu stiker Pro/Premium obuna uchun', true);
        _octHaptic('error');
        return;
    }

    try {
        const res = await fetch('/api/octagon/send-reaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: _octTgId(),
                battle_id: octagonActiveBattleId,
                emoji,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Yuborilmadi');
        _octHaptic('success');
        _setInviteStatus(`Reaksiya yuborildi: ${emoji}`, true);
    } catch (e) {
        _setInviteStatus(e.message || 'Stiker xatosi', true);
        _octHaptic('error');
    }
}

// ==========================================================
// NATIJA VA DIAGNOSTIKA
// ==========================================================
async function showBattleDiagnostic(battleId) {
    const modal = document.getElementById('battle-result-modal');
    if (!modal) return;

    try {
        const res = await fetch(`/api/octagon/battle-result/${battleId}?telegram_id=${_octTgId()}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Natija yuklanmadi');

        octagonActiveBattleId = battleId;
        showBattleReactionBar(battleId);

        const summary = document.getElementById('battle-result-summary');
        const outcomeColor = data.outcome === 'win'
            ? 'text-emerald-400'
            : data.outcome === 'loss'
                ? 'text-rose-400'
                : 'text-amber-400';

        if (summary) {
            summary.innerHTML = `
                <p class="text-base font-extrabold ${outcomeColor}">${_escapeHtml(data.winner_label || 'Natija')}</p>
                <p class="text-[11px] text-slate-400 mt-1">
                    vs ${_escapeHtml(data.opponent?.full_name || 'Raqib')}
                    · ${_escapeHtml(data.subject)} · ${_levelLabel(data.level)}
                </p>
                <p class="text-[10px] text-slate-500 mt-0.5">${_escapeHtml(data.finished_at || '')}</p>
            `;
        }

        const scoreEl = document.getElementById('br-my-score');
        const correctEl = document.getElementById('br-my-correct');
        const wrongEl = document.getElementById('br-my-wrong');
        if (scoreEl) scoreEl.innerText = `${data.my_score}:${data.opponent_score}`;
        if (correctEl) correctEl.innerText = data.my_correct ?? 0;
        if (wrongEl) wrongEl.innerText = data.my_wrong ?? 0;

        const tbody = document.getElementById('battle-gaps-tbody');
        const empty = document.getElementById('battle-gaps-empty');
        const gaps = data.gaps || [];

        if (tbody) {
            if (!gaps.length) {
                tbody.innerHTML = '';
                if (empty) empty.classList.remove('hidden');
            } else {
                if (empty) empty.classList.add('hidden');
                tbody.innerHTML = gaps.map((g) => `
                    <tr class="bg-[#0A0E17]/40">
                        <td class="px-2.5 py-2 text-slate-200 font-medium">${_escapeHtml(g.topic)}</td>
                        <td class="px-2 py-2 text-center text-rose-400 font-mono">${g.mistakes_count}/${g.questions_total}</td>
                        <td class="px-2 py-2 text-center text-amber-400 font-mono">${g.mastery_percent}%</td>
                        <td class="px-2.5 py-2 text-right">
                            <button type="button"
                                onclick="goToRecommendedCourse('${_escapeHtml(g.course_link || 'lessons')}')"
                                class="text-[9px] font-bold text-emerald-400 hover:text-emerald-300 underline cursor-pointer">
                                Kursga o'tish
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }

        modal.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
        _octHaptic('success');
    } catch (e) {
        console.error(e);
        _setInviteStatus(e.message || 'Diagnostika xatosi', true);
        _octHaptic('error');
    }
}

function closeBattleResultModal() {
    const modal = document.getElementById('battle-result-modal');
    if (modal) modal.classList.add('hidden');
    hideBattleReactionBar();
}

function goToRecommendedCourse(targetTab) {
    closeBattleResultModal();
    const tab = targetTab || 'lessons';
    if (typeof switchTab === 'function') {
        switchTab(tab);
    }
}

// Global eksport (inline onclick uchun)
window.initOctagonSection = initOctagonSection;
window.generateDuelInviteLink = generateDuelInviteLink;
window.loadOctagonHistory = loadOctagonHistory;
window.loadOctagonLeaderboard = loadOctagonLeaderboard;
window.startDuelWithBot = startDuelWithBot;
window.findRandomOnlineOpponent = findRandomOnlineOpponent;
window.sendBattleSticker = sendBattleSticker;
window.showBattleDiagnostic = showBattleDiagnostic;
window.closeBattleResultModal = closeBattleResultModal;
window.requestOctagonRematch = requestOctagonRematch;
window.challengeFromHistory = challengeFromHistory;
window.goToRecommendedCourse = goToRecommendedCourse;
