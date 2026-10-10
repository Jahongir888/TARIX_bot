// web/static/js/home.js
async function loadNews() {
    const container = document.getElementById('news-container');
    if (!container) return;

    try {
        const res = await fetch('/api/news');
        const newsList = await res.json();
        container.innerHTML = '';

        newsList.forEach(item => {
            const card = document.createElement('div');
            card.className = "min-w-[270px] max-w-[280px] bg-[#111827] border border-[#1F2937] p-3.5 rounded-2xl shrink-0 snap-start shadow-sm flex flex-col justify-between";

            const badgeClass = item.tag_color === 'amber'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : item.tag_color === 'blue'
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

            card.innerHTML = `
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="px-2 py-0.5 rounded-md ${badgeClass} border text-[10px] font-bold">${item.tag}</span>
                        <span class="text-[10px] text-slate-400 font-mono">${item.date}</span>
                    </div>
                    <h4 class="text-xs font-bold text-slate-100 leading-snug line-clamp-2">${item.title}</h4>
                    <p class="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">${item.desc}</p>
                </div>
                <button onclick="switchTab('${item.action_tab}')" class="mt-3 w-full py-1.5 bg-[#161F30] hover:bg-[#1F2937] border border-[#283548] text-emerald-400 text-[11px] font-semibold rounded-xl text-center active:scale-95 transition-all">
                    ${item.action_text}
                </button>
            `;
            container.appendChild(card);
        });
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        container.innerHTML = '<p class="text-xs text-slate-500">Yangiliklarni yuklab bo\'lmadi.</p>';
    }
}