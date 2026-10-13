// web/static/js/home.js
let currentOpenNewsId = null;

// Foydalanuvchi Telegram ID sini aniqlash
function getCurrentUserId() {
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 84920194;
}

// 1. Yangiliklar kartochkalarini yuklash va render qilish (Xira fonli suzuvchi kartochka)
async function loadNews(selectedTag = '') {
    const container = document.getElementById('news-container');
    if (!container) return;

    const url = selectedTag ? `/api/news?tag=${encodeURIComponent(selectedTag)}` : '/api/news';
    try {
        const res = await fetch(url);
        const list = await res.json();
        container.innerHTML = '';

        if (!list || list.length === 0) {
            container.innerHTML = '<p class="text-xs text-slate-500 py-3 px-1">Hozircha yangiliklar mavjud emas.</p>';
            return;
        }

        list.forEach(item => {
            const card = document.createElement('div');
            // Butun yuzani qoplagan xira fon, tepada heshteglar, pastda sarlavha va ko'rishlar soni
            card.className = "relative min-w-[270px] max-w-[270px] h-44 rounded-2xl overflow-hidden shrink-0 snap-start shadow-lg border border-[#1F2937] p-3.5 flex flex-col justify-between cursor-pointer active:scale-95 transition-all select-none";

            const tagsHtml = (item.hashtags || []).map(t =>
                `<span onclick="event.stopPropagation(); loadNews('${t}')" class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold backdrop-blur-md">${t}</span>`
            ).join('');

            card.innerHTML = `
                <!-- Butun kartochka yuzasi bo'ylab xira fon rasmi -->
                <div class="absolute inset-0 bg-cover bg-center filter blur-[1.5px] brightness-[0.35] -z-10 scale-105" style="background-image: url('${item.image_url || ''}');"></div>
                <div class="absolute inset-0 bg-gradient-to-t from-[#0A0E17] via-[#0A0E17]/60 to-transparent -z-10"></div>

                <!-- Tepa qismi: Heshteglar -->
                <div class="flex flex-wrap gap-1">
                    ${tagsHtml}
                </div>

                <!-- O'rta va Past qismi: Sarlavha hamda Ko'rishlar soni -->
                <div onclick="openNewsDetail(${item.id})">
                    <h4 class="text-xs font-bold text-white leading-snug line-clamp-2 drop-shadow-md">${item.title}</h4>
                    <div class="flex items-center justify-between mt-2 pt-2 border-t border-white/10 text-[10px] text-slate-300">
                        <span>${item.date}</span>
                        <span class="flex items-center gap-1 font-mono text-emerald-400">
                            👁 ${item.views_count}
                        </span>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-400 py-3 px-1">Yangiliklarni yuklashda xatolik yuz berdi.</p>';
    }
}

// 2. Yangilik tafsilotini ochish (Sayt uslubidagi to'liq ekran modal)
async function openNewsDetail(newsId) {
    currentOpenNewsId = newsId;
    const userId = getCurrentUserId();

    try {
        const res = await fetch(`/api/news/${newsId}?user_id=${userId}`);
        const data = await res.json();
        if (data.error) return;

        document.getElementById('nd-image').src = data.image_url || '';
        document.getElementById('nd-date').innerText = `📅 ${data.date} • 👁 ${data.views_count} marta ko'rildi`;
        document.getElementById('nd-title').innerText = data.title;
        document.getElementById('nd-content').innerText = data.content;

        // Manba havolasi
        const srcLink = document.getElementById('nd-source');
        if (data.source_url) {
            srcLink.href = data.source_url;
            srcLink.innerText = data.source_name || 'Manba havolasi';
            document.getElementById('nd-source-box').classList.remove('hidden');
        } else {
            document.getElementById('nd-source-box').classList.add('hidden');
        }

        // Heshteglar
        const tagBox = document.getElementById('nd-hashtags');
        tagBox.innerHTML = (data.hashtags || []).map(t =>
            `<span onclick="closeNewsDetail(); loadNews('${t}')" class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold cursor-pointer">${t}</span>`
        ).join('');

        // Reaksiyalar hisoblagichlarini va faol holatini ekranga chiqarish
        updateReactionUI({
            likes: data.likes_count,
            hearts: data.hearts_count,
            fires: data.fires_count,
            ideas: data.ideas_count,
            user_reaction: data.user_reaction
        });

        // O'xshash xabarlar
        const relBox = document.getElementById('nd-related');
        relBox.innerHTML = (data.related && data.related.length > 0) ? data.related.map(r => `
            <div onclick="openNewsDetail(${r.id})" class="flex items-center gap-2.5 p-2 bg-[#111827] rounded-xl border border-[#1F2937] hover:border-slate-700 cursor-pointer transition-all">
                <img src="${r.image_url}" class="w-12 h-12 object-cover rounded-lg">
                <span class="text-xs font-medium text-slate-200 line-clamp-2">${r.title}</span>
            </div>
        `).join('') : '<p class="text-[11px] text-slate-500">Boshqa o\'xshash xabarlar yo\'q</p>';

        // Kommentlar ro'yxati
        renderComments(data.comments || []);

        // Modalni ko'rsatish
        document.getElementById('news-detail-modal').classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Yangilik tafsilotini yuklashda xatolik:", e);
    }
}

// 3. Reaksiya tugmalari holatini chizish
function updateReactionUI(data) {
    const likeCount = document.getElementById('count-react-like');
    const heartCount = document.getElementById('count-react-heart');
    const fireCount = document.getElementById('count-react-fire');
    const ideaCount = document.getElementById('count-react-idea');

    if (likeCount) likeCount.innerText = data.likes || 0;
    if (heartCount) heartCount.innerText = data.hearts || 0;
    if (fireCount) fireCount.innerText = data.fires || 0;
    if (ideaCount) ideaCount.innerText = data.ideas || 0;

    // Tugma chegaralarini faollashtirish/tozalash
    ['like', 'heart', 'fire', 'idea'].forEach(type => {
        const btn = document.getElementById(`btn-react-${type}`);
        if (!btn) return;
        if (data.user_reaction === type) {
            btn.classList.add('border-emerald-500', 'bg-emerald-500/15');
            btn.classList.remove('border-[#1F2937]', 'bg-[#111827]');
        } else {
            btn.classList.remove('border-emerald-500', 'bg-emerald-500/15');
            btn.classList.add('border-[#1F2937]', 'bg-[#111827]');
        }
    });
}

// 4. Reaksiya bosish va serverga yuborish
async function sendReaction(type) {
    if (!currentOpenNewsId) return;
    const userId = getCurrentUserId();

    try {
        const res = await fetch('/api/news/react', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                news_id: currentOpenNewsId,
                user_id: userId,
                reaction_type: type
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            updateReactionUI({
                likes: data.likes,
                hearts: data.hearts,
                fires: data.fires,
                ideas: data.ideas,
                user_reaction: data.reaction
            });
        } else if (data.status === 'removed') {
            // Bekor qilinganda sonini kamaytirish
            const countEl = document.getElementById(`count-react-${type}`);
            if (countEl) {
                const curVal = parseInt(countEl.innerText) || 0;
                countEl.innerText = Math.max(0, curVal - 1);
            }
            const btn = document.getElementById(`btn-react-${type}`);
            btn?.classList.remove('border-emerald-500', 'bg-emerald-500/15');
            btn?.classList.add('border-[#1F2937]', 'bg-[#111827]');
        }
    } catch (e) {
        console.error("Reaksiya yuborishda xatolik:", e);
    }
}

// 5. Izohlar ro'yxatini chiqarish
function renderComments(comments) {
    const list = document.getElementById('nd-comments-list');
    if (!list) return;

    list.innerHTML = (comments && comments.length > 0) ? comments.map(c => `
        <div class="bg-[#111827] p-2.5 rounded-xl border border-[#1F2937]">
            <div class="flex justify-between items-center mb-1">
                <span class="text-[11px] font-bold text-emerald-400">${c.user}</span>
                <span class="text-[9px] text-slate-500">${c.time}</span>
            </div>
            <p class="text-xs text-slate-300">${c.text}</p>
        </div>
    `).join('') : '<p class="text-[11px] text-slate-500 py-2">Hozircha izohlar mavjud emas.</p>';
}

// 6. Yangi izoh yozish
async function postComment() {
    const input = document.getElementById('nd-comment-input');
    const text = input?.value.trim();
    if (!text || !currentOpenNewsId) return;

    const user = window.Telegram?.WebApp?.initDataUnsafe?.user || { id: getCurrentUserId(), first_name: "O'quvchi" };

    try {
        const res = await fetch('/api/news/comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                news_id: currentOpenNewsId,
                user_id: user.id,
                user_name: user.first_name || "O'quvchi",
                text: text
            })
        });

        if (res.ok) {
            input.value = '';
            openNewsDetail(currentOpenNewsId);
        }
    } catch (e) {
        console.error("Izoh yuborishda xatolik:", e);
    }
}

// 7. Modalni yopish
function closeNewsDetail() {
    document.getElementById('news-detail-modal')?.classList.add('hidden');
    currentOpenNewsId = null;
    loadNews(); // Ko'rishlar soni yangilanishi uchun
}

// ==========================================================
// IMTIHON TAYMERLARI VA DEDLAYNLAR MANTIQI (EXAM DEADLINES)
// ==========================================================
let deadlineCountdownInterval = null;
let allExamDeadlinesList = [];

/**
 * 1. API dan imtihon sanalarini yuklab olish va bosh sahifa vidjetiga chiqarish
 */
async function loadExamDeadlines() {
    try {
        const res = await fetch('/api/deadlines');
        if (!res.ok) throw new Error("Dedlaynlarni yuklab bo'lmadi");
        const data = await res.json();
        if (!data || !data.nearest) return;

        // Barcha sanalarni xotirada saqlaymiz (modal uchun)
        allExamDeadlinesList = data.all || [];

        const nearest = data.nearest;
        const badgeEl = document.getElementById('timer-badge');
        const titleEl = document.getElementById('timer-exam-title');

        if (badgeEl) badgeEl.innerText = nearest.badge || 'IMTIHON';
        if (titleEl) titleEl.innerText = nearest.title || 'Rasmiy Imtihon';

        // Aniq nishon vaqti (target ISO)
        const targetTime = new Date(nearest.target_iso).getTime();

        // Oldingi interval bo'lsa tozalaymiz
        if (deadlineCountdownInterval) clearInterval(deadlineCountdownInterval);

        function updateCountdown() {
            const now = new Date().getTime();
            const diff = targetTime - now;

            const daysEl = document.getElementById('timer-days');
            const hoursEl = document.getElementById('timer-hours');
            const minutesEl = document.getElementById('timer-minutes');
            const secondsEl = document.getElementById('timer-seconds');

            if (diff <= 0) {
                if (daysEl) daysEl.innerText = "00";
                if (hoursEl) hoursEl.innerText = "00";
                if (minutesEl) minutesEl.innerText = "00";
                if (secondsEl) secondsEl.innerText = "00";
                clearInterval(deadlineCountdownInterval);
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            if (daysEl) daysEl.innerText = String(days).padStart(2, '0');
            if (hoursEl) hoursEl.innerText = String(hours).padStart(2, '0');
            if (minutesEl) minutesEl.innerText = String(minutes).padStart(2, '0');
            if (secondsEl) secondsEl.innerText = String(seconds).padStart(2, '0');
        }

        updateCountdown();
        deadlineCountdownInterval = setInterval(updateCountdown, 1000);

    } catch (err) {
        console.error("Dedlayn taymerini yuklashda xatolik:", err);
    }
}

/**
 * 2. "Barchasi" bosilganda ochiluvchi Taqvim Modali mantiqi
 */
function openAllDeadlinesModal() {
    const modal = document.getElementById('deadlines-modal');
    const container = document.getElementById('deadlines-list-container');
    if (!modal || !container) return;

    if (allExamDeadlinesList.length === 0) {
        container.innerHTML = `
            <div class="p-6 text-center text-slate-500 text-xs">
                Rejadagi boshqa rasmiy imtihonlar mavjud emas yoki yuklanmoqda.
            </div>
        `;
    } else {
        container.innerHTML = allExamDeadlinesList.map(item => `
            <div class="bg-[#161F30] border border-[#283548] p-3 rounded-2xl flex items-center justify-between gap-3">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 mb-1">
                        <span class="text-[9px] uppercase font-bold bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">
                            ${item.badge || 'IMTIHON'}
                        </span>
                        <span class="text-[10px] text-slate-400 font-mono">📅 ${item.date}</span>
                    </div>
                    <h4 class="text-xs font-bold text-white truncate">${item.title}</h4>
                </div>
                ${item.action_url ? `
                    <a href="${item.action_url}" target="_blank" class="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-semibold rounded-xl shrink-0 active:scale-95 transition">
                        Batafsil
                    </a>
                ` : ''}
            </div>
        `).join('');
    }

    modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeAllDeadlinesModal() {
    const modal = document.getElementById('deadlines-modal');
    if (modal) modal.classList.add('hidden');
}

// Bosh sahifa ochilganda yoki tab almashganda chaqiriladi
if (typeof document !== 'undefined') {
    loadExamDeadlines();
}

// ==========================================================
// BILDIRISHNOMALAR (NOTIFICATIONS) MANTIQI
// ==========================================================
let notificationsData = [];

// Har bir bo'lim uchun belgilangan ranglar va nishonlar
const NOTIF_SOURCE_CONFIG = {
    oktagon:    { label: "Oktagon", bg: "bg-rose-500/10", border: "border-rose-500/30", text: "text-rose-400" },
    testlar:    { label: "Testlar", bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400" },
    elonlar:    { label: "E'lonlar", bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" },
    kurslar:    { label: "Mening kurslarim", bg: "bg-indigo-500/10", border: "border-indigo-500/30", text: "text-indigo-400" },
    tolov:      { label: "To'lovlar", bg: "bg-teal-500/10", border: "border-teal-500/30", text: "text-teal-400" },
    qurilmalar: { label: "Qurilmalar", bg: "bg-slate-500/10", border: "border-slate-500/30", text: "text-slate-300" }
};

/**
 * 1. Backenddan bildirishnomalarni yuklash
 */
async function loadNotifications() {
    try {
        const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '';
        const res = await fetch(`/api/notifications?telegram_id=${tgId}`);
        if (!res.ok) return;
        const data = await res.json();

        notificationsData = data.items || [];
        const unreadCount = data.unread_count || 0;

        // Yangi xabarlar bo'lsa qizil nuqtani ko'rsatish
        const dot = document.getElementById('notif-badge-dot');
        if (dot) {
            if (unreadCount > 0) dot.classList.remove('hidden');
            else dot.classList.add('hidden');
        }
    } catch (e) {
        console.error("Bildirishnomalarni yuklashda xatolik:", e);
    }
}

/**
 * 2. Bildirishnomalar kartochkalarini chizish
 */
function renderNotifications() {
    const container = document.getElementById('notif-list-container');
    if (!container) return;

    if (!notificationsData || notificationsData.length === 0) {
        container.innerHTML = '<p class="text-xs text-slate-500 text-center py-8">Yangi bildirishnomalar mavjud emas.</p>';
        return;
    }

    container.innerHTML = notificationsData.map(item => {
        const conf = NOTIF_SOURCE_CONFIG[item.source] || {
            label: "Tizim", bg: "bg-slate-800", border: "border-slate-700", text: "text-slate-300"
        };

        return `
            <div onclick="handleNotificationClick(${item.id}, '${item.target_tab}')" 
                 class="relative bg-[#161F30] hover:bg-[#1a253a] border border-[#283548] p-3 rounded-2xl cursor-pointer active:scale-95 transition-all">
                
                <!-- O'qilmagan bo'lsa ko'k nuqta -->
                ${!item.is_read ? '<span class="absolute top-3 right-3 w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></span>' : ''}
                
                <!-- Bo'lim nishoni (manbaga qarab alohida rangda) -->
                <div class="flex items-center gap-1.5 mb-1.5">
                    <span class="text-[9px] font-bold uppercase px-2 py-0.5 rounded-md border ${conf.bg} ${conf.border} ${conf.text}">
                        ${conf.label}
                    </span>
                    <span class="text-[9px] text-slate-500 font-mono">${item.created_at}</span>
                </div>

                <!-- Xabar sarlavhasi va mazmuni -->
                <h4 class="text-xs font-bold text-white mb-1 pr-3 leading-snug">${item.title}</h4>
                <p class="text-[11px] text-slate-300 leading-relaxed font-normal">${item.message}</p>
            </div>
        `;
    }).join('');
}

/**
 * 3. Xabarga bosilganda o'qilgan deb belgilash va kerakli bo'limga o'tish
 */
async function handleNotificationClick(id, targetTab) {
    const item = notificationsData.find(n => n.id === id);
    if (item && !item.is_read) {
        item.is_read = true;
        fetch(`/api/notifications/${id}/read`, { method: 'POST' });
        loadNotifications();
    }

    // Oynani yopish
    closeNotificationDrawer();

    // Tegishli bo'limga o'tkazish
    if (typeof switchTab === 'function' && targetTab) {
        switchTab(targetTab);
    }
}

/**
 * 4. O'ng tomondan panelni ochish
 */
function openNotificationDrawer() {
    renderNotifications();
    const drawer = document.getElementById('notif-drawer');
    const backdrop = document.getElementById('notif-drawer-backdrop');
    if (drawer && backdrop) {
        backdrop.classList.remove('hidden');
        setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
        drawer.classList.remove('translate-x-full');
    }
}

/**
 * 5. Panelni yopish (asosiy menyu ochiq qoladi)
 */
function closeNotificationDrawer() {
    const drawer = document.getElementById('notif-drawer');
    const backdrop = document.getElementById('notif-drawer-backdrop');
    if (drawer && backdrop) {
        drawer.classList.add('translate-x-full');
        backdrop.classList.add('opacity-0');
        setTimeout(() => backdrop.classList.add('hidden'), 300);
    }
}

// Boshlang'ich tekshirish
if (typeof document !== 'undefined') {
    loadNotifications();
}

// ==========================================================
// O'QUV SUR'ATI VA REJA (COURSE PACE) MANTIQI
// ==========================================================
async function loadCoursePace() {
    const container = document.getElementById('course-pace-container');
    if (!container) return;

    try {
        const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '';
        const res = await fetch(`/api/user/course-pace?telegram_id=${tgId}`);
        if (!res.ok) return;
        const data = await res.json();
        const items = data.items || [];

        if (items.length === 0) {
            container.innerHTML = '<p class="text-xs text-slate-500 text-center py-2">Faol kurslar mavjud emas.</p>';
            return;
        }

        container.innerHTML = items.map(item => {
            const actual = Math.min(100, Math.max(0, item.actual || 0));
            const expected = Math.min(100, Math.max(0, item.expected || 0));

            // Status ranglari
            let statusBadge = "border-slate-500/30 text-slate-300 bg-slate-500/10";
            if (item.status === 'Bilimdon') {
                statusBadge = "border-emerald-500/30 text-emerald-400 bg-emerald-500/10";
            } else if (item.status === 'Ustoz') {
                statusBadge = "border-amber-500/30 text-amber-400 bg-amber-500/10";
            }

            // 1 ta qatlamli chiziq: Yashil -> Qizil (agar kechikayotgan bo'lsa) -> Sariq (qolgan qism)
            let progressBackground = '';
            if (actual >= expected) {
                // O'z vaqtida ketmoqda: yashil chiziq qizilni to'liq bosib ketadi
                progressBackground = `linear-gradient(to right, #10B981 0%, #10B981 ${actual}%, #F59E0B ${actual}%, #F59E0B 100%)`;
            } else {
                // Orqada qolmoqda: kelgan joyigacha yashil, reja bo'lgan joyigacha qizil, qolgani sariq
                progressBackground = `linear-gradient(to right, #10B981 0%, #10B981 ${actual}%, #EF4444 ${actual}%, #EF4444 ${expected}%, #F59E0B ${expected}%, #F59E0B 100%)`;
            }

            return `
                <div onclick="switchTab('${item.target_tab || 'lessons'}')" 
                     class="bg-[#0A0E17]/90 border border-[#283548]/70 hover:border-emerald-500/40 p-3 rounded-xl cursor-pointer active:scale-98 transition-all">
                    
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-xs font-bold text-white truncate max-w-[210px]">${item.title}</h4>
                        <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${statusBadge}">
                            ${item.status}
                        </span>
                    </div>

                    <!-- Yagona 3 rangli davomiylik chizig'i -->
                    <div class="relative w-full h-2.5 rounded-full overflow-hidden shadow-inner" style="background: ${progressBackground};">
                    </div>

                    <div class="flex justify-between items-center mt-1.5 text-[10px] font-mono text-slate-400">
                        <span>O'zlashtirish: <strong class="text-emerald-400 font-bold">${actual}%</strong></span>
                        <span>Reja: <strong class="${actual < expected ? 'text-rose-400' : 'text-slate-300'} font-bold">${expected}%</strong></span>
                    </div>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Course pace yuklashda xatolik:", e);
    }
}

// Bosh sahifa yuklanganda chaqirish
if (typeof document !== 'undefined') {
    loadCoursePace();
}


// ==========================================================
// OKTAGON VIDJETI MANTIQI
// ==========================================================
async function loadOctagonWidget() {
    try {
        const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '';
        const res = await fetch(`/api/octagon/user-rank?telegram_id=${tgId}`);
        if (!res.ok) return;
        const data = await res.json();

        const courseTitleEl = document.getElementById('oct-course-title');
        const rankEl = document.getElementById('oct-rank-num');

        if (courseTitleEl && data.course_title) {
            courseTitleEl.innerText = data.course_title;
        }
        if (rankEl && data.rank) {
            rankEl.innerText = data.rank;
        }
    } catch (e) {
        console.error("Oktagon ma'lumotlarini yuklashda xatolik:", e);
    }
}

function startOctagonBattle() {
    // Agar umumiy reyting/oktagon turlariga o'tish lozim bo'lsa:
    if (typeof switchTab === 'function') {
        switchTab('rating'); // Hozirgi Reyting/Oktagon tabiga o'tkazadi
    }
    // Telegram haptic feedback (agar mavjud bo'lsa)
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
    }
}

// Bosh sahifa yuklanganda chaqirish
if (typeof document !== 'undefined') {
    loadOctagonWidget();
}


// ==========================================================
// REKLAMA VA AKSIYALAR (PROMOTIONS) MANTIQI
// ==========================================================
let promoTargetTab = 'books';
let promoInterval = null;

async function loadPromotions() {
    try {
        const res = await fetch('/api/promotions');
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !data.promo) return;

        const promo = data.promo;
        promoTargetTab = promo.target_tab || 'books';

        const titleEl = document.getElementById('promo-title');
        const subtitleEl = document.getElementById('promo-subtitle');
        const badgeEl = document.getElementById('promo-badge');
        const discountEl = document.getElementById('promo-discount-price');
        const originalEl = document.getElementById('promo-original-price');
        const btnTextEl = document.getElementById('promo-btn-text');

        if (titleEl) titleEl.innerText = promo.title;
        if (subtitleEl) subtitleEl.innerText = promo.subtitle || '';
        if (badgeEl) badgeEl.innerText = promo.badge || 'AKSIYA';
        if (discountEl) discountEl.innerText = `${promo.discount_price} so'm`;

        if (originalEl) {
            if (promo.original_price) {
                originalEl.innerText = `${promo.original_price} so'm`;
                originalEl.classList.remove('hidden');
            } else {
                originalEl.classList.add('hidden');
            }
        }
        if (btnTextEl && promo.action_text) btnTextEl.innerText = promo.action_text;

        // Aksiya teskari hisoblagichi
        const targetTime = new Date(promo.end_iso).getTime();
        if (promoInterval) clearInterval(promoInterval);

        function updatePromoTimer() {
            const now = new Date().getTime();
            const diff = targetTime - now;
            const timerEl = document.getElementById('promo-timer');
            if (!timerEl) return;

            if (diff <= 0) {
                timerEl.innerText = "Tugadi";
                clearInterval(promoInterval);
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            if (days > 0) {
                timerEl.innerText = `${days}k ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
            } else {
                timerEl.innerText = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            }
        }

        updatePromoTimer();
        promoInterval = setInterval(updatePromoTimer, 1000);

    } catch (e) {
        console.error("Aksiyalarni yuklashda xatolik:", e);
    }
}

function handlePromoClick() {
    if (typeof switchTab === 'function') {
        switchTab(promoTargetTab);
    }
}

// Bosh sahifa yuklanganda chaqirish
if (typeof document !== 'undefined') {
    loadPromotions();
}

// ==========================================================
// PLATFORMA STATISTIKASI (PLATFORM STATS) MANTIQI
// ==========================================================
async function loadPlatformStats() {
    try {
        const res = await fetch('/api/platform-stats');
        if (!res.ok) return;
        const data = await res.json();

        const stEl = document.getElementById('stat-students');
        const lsEl = document.getElementById('stat-lessons');
        const qeEl = document.getElementById('stat-questions');
        const bkEl = document.getElementById('stat-books');

        if (stEl && data.students) stEl.innerText = data.students;
        if (lsEl && data.lessons) lsEl.innerText = data.lessons;
        if (qeEl && data.questions) qeEl.innerText = data.questions;
        if (bkEl && data.books) bkEl.innerText = data.books;

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Platforma statistikasini yuklashda xatolik:", e);
    }
}

// Bosh sahifa yuklanganda chaqirish
if (typeof document !== 'undefined') {
    loadPlatformStats();
}