// web/static/js/home.js
let currentOpenNewsId = null;

// 1. Yangiliklar kartochkalarini yuklash va render qilish
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
    try {
        const res = await fetch(`/api/news/${newsId}`);
        const data = await res.json();

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

function renderComments(comments) {
    const list = document.getElementById('nd-comments-list');
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

// 3. Yangi komment yozish
async function postComment() {
    const input = document.getElementById('nd-comment-input');
    const text = input.value.trim();
    if (!text || !currentOpenNewsId) return;

    const user = window.Telegram?.WebApp?.initDataUnsafe?.user || { id: 1206236612, first_name: "O'quvchi" };

    try {
        await fetch('/api/news/comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                news_id: currentOpenNewsId,
                user_id: user.id,
                user_name: user.first_name,
                text: text
            })
        });
        input.value = '';
        openNewsDetail(currentOpenNewsId);
    } catch (e) {
        console.error("Izoh yuborishda xatolik:", e);
    }
}

function closeNewsDetail() {
    document.getElementById('news-detail-modal').classList.add('hidden');
    loadNews(); // Ko'rishlar soni 1 taga oshgani uchun ro'yxatni yangilab qo'yamiz
}