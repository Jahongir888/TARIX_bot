// web/static/js/catalog.js

let selectedSubject = 'all';
let selectedCategory = 'all';

// Fanga qarab ochiladigan ikkinchi qator toifalari lug'ati
const categoryMatrix = {
    all: [
        { id: 'all', title: 'Barchasi' }
    ],
    tarix: [
        { id: 'all', title: 'Hammasi' },
        { id: 'ms', title: 'Milliy Sertifikat (MS)' },
        { id: 'attestatsiya', title: 'Attestatsiya' },
        { id: 'bmba_asosiy', title: 'BMBA (Asosiy blok)' },
        { id: 'bmba_majburiy', title: 'BMBA (Majburiy blok)' },
        { id: 'litsey', title: 'Akademik litsey' },
        { id: 'olimpiada', title: 'Olimpiada' },
        { id: 'kitoblar', title: 'Kitoblar' },
        { id: 'paketlar', title: 'Paketlar (Bundle)' }
    ],
    huquq: [
        { id: 'all', title: 'Hammasi' },
        { id: 'ms', title: 'Milliy Sertifikat (MS)' },
        { id: 'attestatsiya', title: 'Attestatsiya' },
        { id: 'bmba_asosiy', title: 'BMBA (Asosiy blok)' },
        { id: 'litsey', title: 'Akademik litsey' },
        { id: 'olimpiada', title: 'Olimpiada' },
        { id: 'kitoblar', title: 'Kitoblar' },
        { id: 'paketlar', title: 'Paketlar (Bundle)' }
    ],
    psixologiya: [
        { id: 'all', title: 'Hammasi' },
        { id: 'litsey', title: 'Litsey saralash' },
        { id: 'otm', title: 'OTM / Harbiy' },
        { id: 'ish', title: 'Ishga qabul testlari' },
        { id: 'paketlar', title: 'Paketlar' }
    ],
    ona_tili: [
        { id: 'all', title: 'Hammasi' },
        { id: 'ms', title: 'Milliy sertifikat' },
        { id: 'attestatsiya', title: 'Attestatsiya' },
        { id: 'bmba_asosiy', title: 'BMBA (Asosiy blok)' },
        { id: 'bmba_majburiy', title: 'BMBA (Majburiy blok)' },
        { id: 'litsey', title: 'Akademik litsey' },
        { id: 'olimpiada', title: 'Olimpiada' },
        { id: 'kitoblar', title: 'Kitoblar' },
        { id: 'paketlar', title: 'Paketlar' }
    ]
};

// 1. Fan tanlanganda
function selectCatalogSubject(sub) {
    selectedSubject = sub;
    selectedCategory = 'all';

    // 1-qator chiplari stillari
    document.querySelectorAll('.cat-chip-sub').forEach(btn => {
        btn.className = "cat-chip-sub px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap bg-[#161F30] border border-[#283548] text-slate-300 hover:border-emerald-500/50 transition-all active:scale-95 cursor-pointer";
    });
    const activeSubBtn = document.getElementById(`sub-chip-${sub}`);
    if (activeSubBtn) {
        activeSubBtn.className = "cat-chip-sub px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap bg-emerald-500 text-slate-950 shadow-md transition-all active:scale-95 cursor-pointer";
    }

    renderCategoryChips();
    loadCatalogProducts();
}

// 2. Ikkinchi qator toifalarini chizish
function renderCategoryChips() {
    const container = document.getElementById('catalog-category-chips');
    if (!container) return;

    const list = categoryMatrix[selectedSubject] || categoryMatrix['all'];
    container.innerHTML = '';

    list.forEach(cat => {
        const btn = document.createElement('button');
        const isActive = cat.id === selectedCategory;
        btn.className = isActive
            ? "cat-chip-cat px-3 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap bg-amber-500 text-slate-950 shadow transition-all active:scale-95 cursor-pointer"
            : "cat-chip-cat px-3 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap bg-[#111827] border border-[#1F2937] text-slate-400 hover:text-slate-200 transition-all active:scale-95 cursor-pointer";
        btn.innerText = cat.title;
        btn.onclick = () => selectCatalogCategory(cat.id);
        container.appendChild(btn);
    });
}

// 3. Imtihon/Toifa tanlanganda
function selectCatalogCategory(catId) {
    selectedCategory = catId;
    renderCategoryChips();
    loadCatalogProducts();
}

// 4. Mahsulotlarni API dan yuklash va 50/50 kartalarni render qilish
async function loadCatalogProducts() {
    const container = document.getElementById('catalog-cards-container');
    if (!container) return;

    container.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Mahsulotlar saralanmoqda...</p>';

    try {
        const res = await fetch(`/api/catalog/products?subject=${selectedSubject}&category=${selectedCategory}`);
        const products = await res.json();

        container.innerHTML = '';

        if (!products || products.length === 0) {
            container.innerHTML = `
                <div class="py-10 text-center bg-[#111827] border border-[#1F2937] rounded-2xl p-6">
                    <span class="text-3xl block mb-2">🔍</span>
                    <p class="text-xs text-slate-400">Bu yo'nalish bo'yicha hozircha kurs yoki kitoblar mavjud emas.</p>
                </div>
            `;
            return;
        }

        products.forEach(p => {
            const card = document.createElement('div');
            card.className = "bg-[#111827] border border-[#1F2937] hover:border-[#283548] rounded-2xl p-3 shadow-md flex gap-3 transition-all";

            // Yulduzchalarni chizish
            const stars = '⭐'.repeat(Math.round(p.rating || 5));

            card.innerHTML = `
                <!-- CHAP YARMI (50%): Rasm va Kurs nomi -->
                <div class="w-5/12 flex flex-col shrink-0">
                    <div class="w-full aspect-[4/3] rounded-xl overflow-hidden bg-[#161F30] border border-[#283548]/60 relative mb-2">
                        <img src="${p.image_url || 'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=300'}" alt="${p.title}" class="w-full h-full object-cover">
                    </div>
                    <h4 class="text-xs font-bold text-white leading-tight line-clamp-2">${p.title}</h4>
                </div>

                <!-- O'NG YARMI (50%): Reyting, Narx, Reklama matni, Tugmalar -->
                <div class="w-7/12 flex flex-col justify-between">
                    <div>
                        <!-- Reyting va Xaridorlar soni -->
                        <div class="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                            <span class="font-bold text-amber-400 flex items-center gap-0.5">
                                ★ ${p.rating}
                            </span>
                            <span class="text-slate-400 text-[9px] bg-[#161F30] px-1.5 py-0.5 rounded border border-[#283548]">
                                👥 ${p.buyers_count}+ o'quvchi
                            </span>
                        </div>

                        <!-- Narx (Hozirgi va chizilgan) -->
                        <div class="flex items-baseline gap-1.5 my-1">
                            <span class="text-xs font-black text-emerald-400 font-mono">${Number(p.price_coin || 0).toLocaleString('uz-UZ')} so'm</span>
                            ${p.old_price_coin > p.price_coin ? `<span class="text-[9px] text-slate-500 line-through font-mono">${Number(p.old_price_coin || 0).toLocaleString('uz-UZ')} so'm</span>` : ''}
                        </div>

                        <!-- 1-2 ta tavsiflovchi jumla -->
                        <p class="text-[10px] text-slate-300 line-clamp-2 leading-relaxed mb-2 font-normal">
                            ${p.short_desc || 'Mukammal tayyorgarlik uchun mo\'ljallangan maxsus o\'quv dasturi.'}
                        </p>
                    </div>

                    <!-- 2 TA TUGMA: Batafsil va Sotib olish -->
                    <div class="grid grid-cols-2 gap-1.5 pt-1 border-t border-[#1F2937]">
                        <button onclick="openProductDetailModal(${p.id}, '${p.title.replace(/'/g, "\\'")}')" class="py-1.5 bg-[#161F30] hover:bg-[#1F2937] border border-[#283548] text-[10px] font-bold text-slate-300 rounded-lg active:scale-95 transition-all text-center cursor-pointer">
                            Batafsil
                        </button>
                        <button onclick="handleProductBuy(${p.id}, ${p.price_coin}, '${p.title.replace(/'/g, "\\'")}')" class="py-1.5 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-[10px] font-black text-slate-950 rounded-lg shadow active:scale-95 transition-all text-center cursor-pointer">
                            Sotib olish
                        </button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-400 text-center py-6">Katalogni yuklashda xatolik yuz berdi.</p>';
    }
}

// 5. "Batafsil" tugmasi modali (qolip)
function openProductDetailModal(id, title) {
    alert(`«${title}» kursi bo'yicha batafsil mundarija va namuna darslar oynasi keyingi bosqichda to'liq ulanadi.`);
}

// 6. "Sotib olish" tugmasi mantig'i
async function handleProductBuy(productId, priceCoin, title) {
    const tgId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 12345678;
    const priceLabel = Number(priceCoin || 0).toLocaleString('uz-UZ');

    if (!confirm(`«${title}» mahsulotini ${priceLabel} so'm evaziga xarid qilasizmi?`)) {
        return;
    }

    try {
        const res = await fetch('/api/catalog/buy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: tgId, product_id: productId })
        });
        const data = await res.json();

        if (data.success) {
            alert(data.message);
            const hdrBalance = document.getElementById('hdr-balance') || document.getElementById('hdr-coins');
            if (hdrBalance) hdrBalance.innerText = Number(data.new_balance || 0).toLocaleString('uz-UZ');
        } else {
            const need = Number(data.needed_amount != null ? data.needed_amount : data.needed_coins) || 0;
            const current = Number(data.current_balance) || 0;
            alert(`⚠️ Balansingizda mablag' yetarli emas!\n\nUshbu kurs uchun yana ${need.toLocaleString('uz-UZ')} so'm kerak.\n(Joriy balansingiz: ${current.toLocaleString('uz-UZ')} so'm).`);
        }
    } catch (err) {
        alert("Server bilan aloqa uzildi. Iltimos qayta urinib ko'ring.");
    }
}

// Sahifa yuklanganda yoki tabga o'tganda ishga tushirish
document.addEventListener('DOMContentLoaded', () => {
    selectCatalogSubject('all');
});