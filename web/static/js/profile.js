// ==========================================================
// PHAROS MINI APP — YANGILANGAN PROFIL BOSHQARUVI (profile.js)
// ==========================================================

const REGION_DISTRICTS = {
    "Toshkent": ["Yunusobod", "Chilonzor", "Mirzo Ulug'bek", "Yashnobod", "Yakkasaroy", "Shayxontohur", "Mirobod"],
    "Xorazm": ["Urganch sh.", "Xiva sh.", "Shovot", "Gurlan", "Bog'ot", "Hazorasp", "Xonqa", "Yangiariq"],
    "Samarqand": ["Samarqand sh.", "Pastdarg'om", "Urgut", "Bulung'ur", "Kattaqo'rg'on", "Toyloq"],
    "Farg'ona": ["Farg'ona sh.", "Marg'ilon", "Qo'qon", "Oltiariq", "Rishton", "Quva"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon", "Xo'jaobod", "Baliqchi"],
    "Namangan": ["Namangan sh.", "Chust", "Pop", "Uychi", "Yangiqo'rg'on"],
    "Buxoro": ["Buxoro sh.", "G'ijduvon", "Kogon", "Jondor", "Vobkent"],
    "Qashqadaryo": ["Qarshi sh.", "Shahrisabz", "Kitob", "G'uzor", "Koson"],
    "Surxondaryo": ["Termiz sh.", "Denov", "Sherobod", "Boysun", "Sho'rchi"],
    "Jizzax": ["Jizzax sh.", "Zomin", "G'allaorol", "Do'stlik"],
    "Sirdaryo": ["Guliston sh.", "Boyovut", "Sayxunobod", "Sardoba"],
    "Navoiy": ["Navoiy sh.", "Zarafshon", "Karmana", "Qiziltepa"],
    "Qoraqalpog'iston": ["Nukus sh.", "Xo'jayli", "Beruniy", "To'rtko'l", "Qo'ng'irot"]
};

function getCurrentTelegramId() {
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 84920194;
}

// Profil ma'lumotlarini Backenddan tortib kelish
async function fetchUserProfile() {
    const tgId = getCurrentTelegramId();
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user || {};
    const firstName = encodeURIComponent(tgUser.first_name || "Jahongir");
    const username = encodeURIComponent(tgUser.username || "Jahongir_Qadamov");

    try {
        const res = await fetch(`/api/profile?telegram_id=${tgId}&first_name=${firstName}&username=${username}`);
        if (!res.ok) throw new Error("Profilni yuklab bo'lmadi");
        const data = await res.json();
        renderUserProfile(data);
    } catch (e) {
        console.error("Profil yuklashda xatolik:", e);
    }
}

// Ma'lumotlarni HTML birkalariga yozish
function renderUserProfile(u) {
    // Sarlavha qismi
    const nameTop = document.getElementById('profile-fullname-top');
    if (nameTop) nameTop.innerText = u.full_name;

    const tgIdEl = document.getElementById('profile-tg-id');
    if (tgIdEl) tgIdEl.innerText = u.telegram_id;

    const avatarEl = document.getElementById('profile-avatar-icon');
    if (avatarEl) avatarEl.innerText = u.avatar_url || "👤";

    // 1-bo'lim: Ma'lumotlarim
    const infoName = document.getElementById('info-fullname');
    if (infoName) infoName.innerText = u.full_name;

    const infoDist = document.getElementById('info-district');
    if (infoDist) infoDist.innerText = u.district || "Tanlanmagan";

    const infoPhone = document.getElementById('info-phone');
    if (infoPhone) infoPhone.innerText = u.phone_number || "Kiritilmagan";

    const infoBday = document.getElementById('info-birthday');
    if (infoBday) infoBday.innerText = u.birth_date || "Tanlanmagan";

    // 2-bo'lim: Hisobim
    const coinBal = document.getElementById('coin-balance');
    if (coinBal) coinBal.innerText = u.coins || 0;

    const refCount = document.getElementById('referral-count');
    if (refCount) refCount.innerText = u.invited_friends || 0;

    // Faollik diagrammasi
    const chartName = document.getElementById('chart-user-name');
    if (chartName) chartName.innerText = u.full_name;

    const chartXp = document.getElementById('chart-xp-label');
    if (chartXp) chartXp.innerText = Math.round((u.total_hours || 0) * 10);

    // Referal havola
    const refLink = `https://t.me/pharos_talim_bot?start=ref${u.telegram_id}`;
    const refText = document.getElementById('referral-link-text');
    if (refText) refText.innerText = refLink;

    // Oferta holati
    const ofertaTag = document.getElementById('oferta-bonus-tag');
    if (ofertaTag && u.oferta_accepted) {
        ofertaTag.innerText = "(Imzolangan ✔)";
        ofertaTag.className = "text-slate-400 font-semibold";
    }

    // Kurslar dropdownini shakllantirish
    renderCoursesDropdown(u.courses || []);

    // Tranzaksiyalar ro'yxatini shakllantirish
    renderTransactions(u.transactions || []);
}

// Kurslar dropdowni
function renderCoursesDropdown(courses) {
    const container = document.getElementById('course-dropdown-items');
    if (!container) return;
    container.innerHTML = '';

    courses.forEach((c) => {
        const item = document.createElement('div');
        item.className = "px-3 py-2 hover:bg-[#161F30] cursor-pointer flex justify-between items-center text-xs";
        item.innerHTML = `
            <span class="text-slate-200">${c.name}</span>
            <span class="text-amber-400 font-bold">${c.level}</span>
        `;
        item.onclick = () => {
            document.getElementById('selected-course-title').innerText = c.name;
            document.getElementById('selected-course-level').innerText = c.level;
            toggleCourseDropdown();
        };
        container.appendChild(item);
    });
}

function toggleCourseDropdown() {
    document.getElementById('course-dropdown')?.classList.toggle('hidden');
}

// Tranzaksiyalar tarixi
function renderTransactions(txs) {
    const container = document.getElementById('transactions-list');
    if (!container) return;

    if (txs.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-center py-4">Hozircha tranzaksiyalar mavjud emas.</p>';
        return;
    }

    container.innerHTML = txs.map(t => {
        const isPlus = t.amount > 0;
        return `
            <div class="bg-[#161F30] border border-[#283548] p-2.5 rounded-xl flex items-center justify-between">
                <div>
                    <p class="text-slate-200 font-medium">${t.description}</p>
                    <span class="text-[10px] text-slate-500">${t.date}</span>
                </div>
                <span class="font-bold font-mono ${isPlus ? 'text-emerald-400' : 'text-rose-400'}">
                    ${isPlus ? '+' : ''}${t.amount} Coin
                </span>
            </div>
        `;
    }).join('');
}

// Ichki modallarni ochish va yopish
function openModal(id) { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }

// Ismni tahrirlash
async function editFieldPrompt(field) {
    const newVal = prompt("Ism-familiyangizni kiriting:");
    if (!newVal || !newVal.trim()) return;

    const tgId = getCurrentTelegramId();
    await fetch(`/api/user/profile/${tgId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: newVal.trim() })
    });
    fetchUserProfile();
}

// Manzil (Viloyat va tuman) tanlash mantiqi
function onRegionChange() {
    const reg = document.getElementById('select-region').value;
    const distSelect = document.getElementById('select-district');
    distSelect.innerHTML = '<option value="">Tumanni tanlang</option>';

    const districts = REGION_DISTRICTS[reg] || ["Markaziy tuman", "Shahar"];
    districts.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.innerText = d;
        distSelect.appendChild(opt);
    });
}

async function saveRegionSelection() {
    const reg = document.getElementById('select-region').value;
    const dist = document.getElementById('select-district').value;
    if (!reg || !dist) return alert("Viloyat va tumanni tanlang!");

    const tgId = getCurrentTelegramId();
    await fetch(`/api/user/profile/${tgId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ district: `${reg}, ${dist}` })
    });
    closeModal('edit-region-modal');
    fetchUserProfile();
}

// Tug'ilgan kunni saqlash
async function saveBirthdaySelection() {
    const bday = document.getElementById('input-birthday').value;
    if (!bday) return alert("Sanani tanlang!");

    const tgId = getCurrentTelegramId();
    await fetch(`/api/user/profile/${tgId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ birth_date: bday })
    });
    closeModal('edit-birthday-modal');
    fetchUserProfile();
}

// Referal havolasini nusxalash va ulashish
function copyReferralLink() {
    const link = document.getElementById('referral-link-text').innerText;
    navigator.clipboard.writeText(link);
    alert("Havola nusxalandi! Do'stlaringizga yuboring.");
}

function shareReferralLink() {
    const link = document.getElementById('referral-link-text').innerText;
    const shareText = encodeURIComponent(`PHAROS ta'lim platformasida birga tayyorlanamiz! Havola: ${link}`);
    window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${shareText}`, '_blank');
}

// Oferta bonusini olish (+20 Coin)
async function claimOfertaBonus() {
    const tgId = getCurrentTelegramId();
    try {
        const res = await fetch(`/api/user/oferta/${tgId}`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        if (data.status === 'success') {
            fetchUserProfile();
        }
    } catch (e) {
        alert("Ulanishda xatolik yuz berdi.");
    }
}

// Murojaat yo'llash
function submitFeedback() {
    const type = document.getElementById('feedback-type').value;
    const text = document.getElementById('feedback-text').value;
    if (!text.trim()) return alert("Iltimos, xabar matnini yozing.");

    alert(`Rahmat! ${type.toUpperCase()} turidagi murojaatingiz adminga yuborildi.`);
    closeModal('feedback-modal');
    document.getElementById('feedback-text').value = '';
}

// "Biz" bo'limi axborot darchalari
function openAboutModal() {
    alert("PHAROS — Tarix va boshqa fanlardan milliy sertifikat hamda attestatsiyaga tayyorlovchi zamonaviy LMS platforma.\n\n(Ushbu matn admin paneldan boshqariladi)");
}

function openManualModal() {
    alert("Foydalanish qo'llanmasi:\n1. Bosh sahifada imtihon sanalarini kuzating.\n2. Do'kondan kerakli kursni xarid qiling.\n3. Testlar bo'limida bilimingizni sinang.\n\n(Admin tomonidan yangilanadi)");
}

function openSocialsModal() {
    alert("Rasmiy sahifalarimiz:\nTelegram: @pharos_talim\nInstagram: @pharos_edu");
}

// Ilovada o'tkazilgan vaqtni har 30 soniyada backendga yuborish
setInterval(async () => {
    const tgId = getCurrentTelegramId();
    try {
        await fetch(`/api/user/activity/${tgId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ seconds: 30 })
        });
    } catch (e) {}
}, 30000);

// ==========================================================
// HEADER PROFIL KO'RSATKICHLARINI YANGILASH FUNKSIYASI
// ==========================================================
function updateHeaderProfileWidgets(data) {
    if (!data) return;

    // 1. Ism (faqat birinchi so'zi, masalan: "Jahongir")
    const nameEl = document.getElementById('hdr-name');
    if (nameEl) {
        const rawName = data.full_name || "O'quvchi";
        nameEl.innerText = rawName.split(' ')[0];
    }

    // 2. Status (Target yoki ABC darajasi)
    const statusEl = document.getElementById('hdr-status');
    if (statusEl) {
        statusEl.innerText = data.target || "Bilimdon";
    }

    // 3. Balans (Coins)
    const coinsEl = document.getElementById('hdr-coins');
    if (coinsEl) {
        coinsEl.innerText = data.coins || 0;
    }

    // 4. Aylana shakldagi Avatar (Rasm yoki Emoji)
    const avatarBox = document.getElementById('hdr-avatar-box');
    const avatarEl = document.getElementById('hdr-avatar');
    if (avatarBox && data.avatar_url) {
        if (data.avatar_url.startsWith('http')) {
            avatarBox.innerHTML = `<img src="${data.avatar_url}" class="w-full h-full object-cover">`;
        } else if (avatarEl) {
            avatarEl.innerText = data.avatar_url;
        }
    }
}

// Mini App yuklanganda Header profil ma'lumotlarini darhol chaqirish
window.addEventListener('DOMContentLoaded', () => {
    if (typeof fetchUserProfile === 'function') {
        fetchUserProfile();
    }
});