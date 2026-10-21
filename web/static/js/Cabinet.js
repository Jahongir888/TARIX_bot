let currentCabinetFilter = 'active';

// 1. Filtr chiplarini almashtirish
function switchCabinetFilter(filterType) {
    currentCabinetFilter = filterType;

    document.querySelectorAll('.cab-chip').forEach(btn => {
        btn.className = "cab-chip px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap bg-[#161F30] border border-[#283548] text-slate-300 hover:border-emerald-500/50 transition-all active:scale-95 cursor-pointer";
    });

    const activeBtn = document.getElementById(`cab-chip-${filterType}`);
    if (activeBtn) {
        activeBtn.className = "cab-chip px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap bg-emerald-500 text-slate-950 shadow-md transition-all active:scale-95 cursor-pointer";
    }

    loadCabinetItems();
}

// 2. Ma'lumotlarni yuklash va render qilish
async function loadCabinetItems() {
    const container = document.getElementById('cabinet-cards-container');
    if (!container) return;

    container.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Yuklanmoqda...</p>';

    try {
        const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 12345678;
        const res = await fetch(`/api/cabinet/items?telegram_id=${tgId}&filter_type=${currentCabinetFilter}`);
        const data = await res.json();
        const items = data.items || [];

        container.innerHTML = '';

        // 3. AGAR BO'SH BO'LSA: O'rgimchak to'ri va kitob javoni grafik tasviri
        if (items.length === 0) {
            container.innerHTML = `
                <div class="py-12 flex flex-col items-center justify-center text-center">
                    <div class="relative w-28 h-28 mb-3 flex items-center justify-center bg-[#111827] border border-[#1F2937] rounded-3xl p-4 shadow-inner">
                        <!-- O'rgimchak to'ri SVG -->
                        <svg class="absolute -top-1 -right-1 w-10 h-10 text-slate-600/60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
                            <path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M4.93 19.07L19.07 4.93"/>
                            <path d="M12 6a6 6 0 0 1 6 6M12 18a6 6 0 0 0-6-6M6 12a6 6 0 0 1 6-6M18 12a6 6 0 0 1-6 6"/>
                        </svg>
                        <!-- Kitob javoni SVG -->
                        <svg class="w-14 h-14 text-slate-500 stroke-1" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="1.5"/>
                            <line x1="3" y1="9" x2="21" y2="9" stroke-width="1.5"/>
                            <line x1="3" y1="15" x2="21" y2="15" stroke-width="1.5"/>
                            <path d="M6 9V5M9 9V5M15 9l2-4M6 15v-3M9 15v-3M16 15v-3" stroke-width="1.5"/>
                        </svg>
                    </div>
                    <span class="text-sm font-bold text-slate-400">Bo'sh</span>
                    <p class="text-[11px] text-slate-500 mt-1">Ushbu bo'limda hozircha hech narsa yo'q</p>
                </div>
            `;
            return;
        }

        // 4. KARTOCHKALARNI RENDER QILISH (50/50 KO'RINISH)
        items.forEach(item => {
            const actual = Math.min(100, Math.max(0, item.actual_progress || 0));
            const expected = Math.min(100, Math.max(0, item.expected_progress || 0));

            // Status rangi
            let rankBadge = "border-slate-500/30 text-slate-300 bg-slate-500/10";
            if (item.user_rank === 'Bilimdon') {
                rankBadge = "border-emerald-500/30 text-emerald-400 bg-emerald-500/10";
            } else if (item.user_rank === 'Ustoz') {
                rankBadge = "border-amber-500/30 text-amber-400 bg-amber-500/10";
            }

            // 3 xil rangli progress chizig'i
            let progressGradient = '';
            if (actual >= expected) {
                // O'z vaqtida: Yashil qism qizilni yopib ketadi, qolgani sariq
                progressGradient = `linear-gradient(to right, #10B981 0%, #10B981 ${actual}%, #F59E0B ${actual}%, #F59E0B 100%)`;
            } else {
                // Kechikmoqda: Yashil -> Qizil (kechikish) -> Sariq (qolgan davomiylik)
                progressGradient = `linear-gradient(to right, #10B981 0%, #10B981 ${actual}%, #EF4444 ${actual}%, #EF4444 ${expected}%, #F59E0B ${expected}%, #F59E0B 100%)`;
            }

            const card = document.createElement('div');
            card.className = "bg-[#111827] border border-[#1F2937] hover:border-[#283548] rounded-2xl p-3 shadow-md flex gap-3 transition-all cursor-pointer";
            card.onclick = () => openSubjectFromCabinet(item);

            card.innerHTML = `
                <!-- CHAP YARMI (50%): Rasm, g'ubor (backdrop-blur) va nom -->
                <div class="w-1/2 flex flex-col shrink-0">
                    <div class="relative w-full aspect-[4/3] rounded-xl overflow-hidden bg-[#161F30] border border-[#283548]/60 flex flex-col justify-end">
                        <img src="${item.image_url || 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=400'}" alt="${item.title}" class="absolute inset-0 w-full h-full object-cover">
                        <!-- G'ubor bilan qoplangan nom bloki -->
                        <div class="relative z-10 bg-[#0A0E17]/75 backdrop-blur-md p-2 border-t border-white/10">
                            <h4 class="text-xs font-bold text-white leading-tight line-clamp-2">${item.title}</h4>
                        </div>
                    </div>
                </div>

                <!-- O'NG YARMI (50%): Status, Taymer, 3 rangli chiziq, Reyting, Tugma -->
                <div class="w-1/2 flex flex-col justify-between py-0.5">
                    <div>
                        <!-- Status darajasi (Shogird, Bilimdon, Ustoz) -->
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${rankBadge}">
                                ${item.user_rank}
                            </span>
                        </div>

                        <!-- Obuna qolgan kun va sana -->
                        <p class="text-[10px] text-slate-400 font-mono mb-2 flex items-center justify-between">
                            <span>Qoldi: <strong class="text-amber-400">${item.days_left} kun</strong></span>
                            <span class="text-slate-500">${item.expire_date}</span>
                        </p>

                        <!-- 3 xil rangdagi yagona chiziq va Foiz -->
                        <div class="flex items-center gap-2 mb-2">
                            <div class="relative flex-1 h-2 rounded-full overflow-hidden shadow-inner" style="background: ${progressGradient};"></div>
                            <span class="text-[10px] font-mono font-bold text-emerald-400 shrink-0">${actual}%</span>
                        </div>
                    </div>

                    <!-- Reyting o'rni va Davom etish tugmasi -->
                    <div class="flex items-center justify-between pt-1 border-t border-[#1F2937] mt-1">
                        <div class="text-[10px] text-slate-400">
                            Reyting: <strong class="text-white font-mono">${item.course_rank}-o'rin</strong>
                        </div>
                        <button type="button" data-cab-id="${item.id}" class="cab-open-hub-btn px-2.5 py-1 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-[10px] font-black text-slate-950 rounded-lg shadow active:scale-95 transition-all cursor-pointer">
                            Fan paneli
                        </button>
                    </div>
                </div>
            `;
            const hubBtn = card.querySelector('.cab-open-hub-btn');
            if (hubBtn) {
                hubBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openSubjectFromCabinet(item);
                });
            }
            container.appendChild(card);
        });

        if (window.lucide) lucide.createIcons();
    } catch (err) {
        container.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Yuklashda xatolik yuz berdi.</p>';
    }
}

// 5. Fan paneli (Subject Hub) ochish
async function openSubjectFromCabinet(item) {
    const payload = typeof item === 'string' ? (() => { try { return JSON.parse(item); } catch (e) { return { id: item }; } })() : item;
    window.headerBackContext = 'cabinet';

    if (typeof openSubjectHub !== 'function') {
        resumeCourse(payload?.id, payload?.last_lesson_id);
        return;
    }

    let subjectId = payload?.subject_id || null;
    if (!subjectId) {
        try {
            const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 12345678;
            const res = await fetch(`/api/subject-dashboard/my-subjects?telegram_id=${tgId}`);
            const data = await res.json();
            const subjects = data.subjects || [];
            const match = subjects.find((s) =>
                payload?.title && s.title && s.title.toLowerCase().includes(String(payload.title).toLowerCase().slice(0, 12))
            ) || subjects.find((s) => s.is_primary) || subjects[0];
            subjectId = match?.subject_id || null;
        } catch (e) {}
    }

    openSubjectHub(subjectId, { backTo: 'cabinet', cabinetItem: payload });
}

// 5b. Eski yo'l: darslarga o'tish (fallback)
function resumeCourse(courseId, lessonId) {
    window.headerBackContext = 'cabinet';
    if (typeof switchTab === 'function') {
        switchTab('lessons', { backTo: 'cabinet' });
    }
    window.headerBackContext = 'cabinet';
    if (typeof updateHeaderLeftButton === 'function') {
        updateHeaderLeftButton();
    }
    if (typeof selectClass === 'function' && lessonId) {
        console.log(`Kurs: ${courseId}, Dars: ${lessonId} davom ettirilmoqda.`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    switchCabinetFilter('active');
});