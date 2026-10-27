// ==========================================================
// PHAROS MINI APP — YANGILANGAN PROFIL BOSHQARUVI (profile.js)
// ==========================================================

const REGION_DISTRICTS = {
    "Toshkent shahri": [
        "Bektemir tumani", "Chilonzor tumani", "Mirobod tumani", "Mirzo Ulug‘bek tumani",
        "Olmazor tumani", "Sergeli tumani", "Shayxontohur tumani", "Uchtepa tumani",
        "Yakkasaroy tumani", "Yashnobod tumani", "Yangihayot tumani", "Yunusobod tumani"
    ],
    "Qoraqalpog‘iston Respublikasi": [
        "Nukus shahri", "Amudaryo tumani", "Beruniy tumani", "Bo‘zatov tumani",
        "Chimboy tumani", "Ellikqala tumani", "Kegeyli tumani", "Mo‘ynoq tumani",
        "Nukus tumani", "Qanliko‘l tumani", "Qorao‘zak tumani", "Qo‘ng‘irot tumani",
        "Shumanay tumani", "Taxtako‘pir tumani", "To‘rtko‘l tumani", "Xo‘jayli tumani", "Taxiatosh tumani"
    ],
    "Andijon viloyati": [
        "Andijon shahri", "Xonobod shahri", "Andijon tumani", "Asaka tumani",
        "Baliqchi tumani", "Bo‘ston tumani", "Buloqboshi tumani", "Izboskan tumani",
        "Jalaquduq tumani", "Marhamat tumani", "Oltinko‘l tumani", "Paxtaobod tumani",
        "Qo‘rg‘ontepa tumani", "Shahrixon tumani", "Ulug‘nor tumani", "Xo‘jaobod tumani"
    ],
    "Buxoro viloyati": [
        "Buxoro shahri", "Kogon shahri", "Buxoro tumani", "G‘ijduvon tumani",
        "Jondor tumani", "Kogon tumani", "Olot tumani", "Peshku tumani",
        "Qorako‘l tumani", "Qorovulbozor tumani", "Romitan tumani", "Shofirkon tumani", "Vobkent tumani"
    ],
    "Farg‘ona viloyati": [
        "Farg‘ona shahri", "Marg‘ilon shahri", "Qo‘qon shahri", "Quvasoy shahri",
        "Bag‘dod tumani", "Beshariq tumani", "Buvayda tumani", "Dang‘ara tumani",
        "Farg‘ona tumani", "Furqat tumani", "Oltiariq tumani", "Qo‘shtepa tumani",
        "Quva tumani", "Rishton tumani", "So‘x tumani", "Toshloq tumani",
        "Uchko‘prik tumani", "O‘zbekiston tumani", "Yozyovon tumani"
    ],
    "Jizzax viloyati": [
        "Jizzax shahri", "Arnasoy tumani", "Baxmal tumani", "Do‘stlik tumani",
        "Forish tumani", "G‘allaorol tumani", "Sharof Rashidov tumani", "Mirzacho‘l tumani",
        "Paxtakor tumani", "Yangiobod tumani", "Zomin tumani", "Zafarobod tumani", "Zarbdor tumani"
    ],
    "Xorazm viloyati": [
        "Urganch shahri", "Xiva shahri", "Pitnak shahri", "Bog‘ot tumani",
        "Gurlan tumani", "Hazorasp tumani", "Tuproqqal’a tumani", "Shovot tumani",
        "Urganch tumani", "Xiva tumani", "Xonqa tumani", "Yangiariq tumani",
        "Yangibozor tumani", "Qo‘shko‘pir tumani"
    ],
    "Namangan viloyati": [
        "Namangan shahri", "Chortoq tumani", "Chust tumani", "Kosonsoy tumani",
        "Mingbuloq tumani", "Namangan tumani", "Norin tumani", "Pop tumani",
        "To‘raqo‘rg‘on tumani", "Uchqo‘rg‘on tumani", "Uychi tumani", "Yangiqo‘rg‘on tumani",
        "Davlatobod tumani", "Yangi Namangan tumani"
    ],
    "Navoiy viloyati": [
        "Navoiy shahri", "Zarafshon shahri", "Karmana tumani", "Konimex tumani",
        "Qiziltepa tumani", "Xatirchi tumani", "Navbahor tumani", "Nurota tumani",
        "Tomdi tumani", "Uchquduq tumani"
    ],
    "Qashqadaryo viloyati": [
        "Qarshi shahri", "Shahrisabz shahri", "Chiroqchi tumani", "Dehqonobod tumani",
        "G‘uzor tumani", "Kasbi tumani", "Kitob tumani", "Koson tumani",
        "Ko‘kdala tumani", "Mirishkor tumani", "Muborak tumani", "Nishon tumani",
        "Qamashi tumani", "Qarshi tumani", "Shahrisabz tumani", "Yakkabog‘ tumani"
    ],
    "Samarqand viloyati": [
        "Samarqand shahri", "Kattaqo‘rg‘on shahri", "Bulung‘ur tumani", "Ishtixon tumani",
        "Jomboy tumani", "Kattaqo‘rg‘on tumani", "Narpay tumani", "Nurobod tumani",
        "Oqdaryo tumani", "Pastdarg‘om tumani", "Paxtachi tumani", "Payariq tumani",
        "Qo‘shrabot tumani", "Samarqand tumani", "Toyloq tumani", "Urgut tumani"
    ],
    "Sirdaryo viloyati": [
        "Guliston shahri", "Shirin shahri", "Yangiyer shahri", "Boyovut tumani",
        "Guliston tumani", "Xovos tumani", "Mirzaobod tumani", "Oqoltin tumani",
        "Sardoba tumani", "Sayxunobod tumani", "Sirdaryo tumani"
    ],
    "Surxondaryo viloyati": [
        "Termiz shahri", "Angor tumani", "Bandixon tumani", "Boysun tumani",
        "Denov tumani", "Jarqo‘rg‘on tumani", "Qiziriq tumani", "Qumqo‘rg‘on tumani",
        "Muzrabot tumani", "Oltinsoy tumani", "Sariosiyo tumani", "Sherobod tumani",
        "Sho‘rchi tumani", "Termiz tumani", "Uzun tumani"
    ],
    "Toshkent viloyati": [
        "Nurafshon shahri", "Olmaliq shahri", "Angren shahri", "Bekobod shahri",
        "Chirchiq shahri", "Ohangaron shahri", "Yangiyo‘l shahri", "Bekobod tumani",
        "Bo‘stonliq tumani", "Bo‘ka tumani", "Chinoz tumani", "Qibray tumani",
        "Parkent tumani", "Piskent tumani", "Quyi Chirchiq tumani", "O‘rta Chirchiq tumani",
        "Yangiyo‘l tumani", "Yuqori Chirchiq tumani", "Zangiota tumani", "Toshkent tumani", "Ohangaron tumani"
    ]
};

let currentSupervisorLink = "";

function getCurrentTelegramId() {
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    return (tgUser && tgUser.id) ? tgUser.id : 84920194;
}

function setElText(id, value, fallback) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerText = (value === 0 || value) ? String(value) : (fallback ?? "");
}

function isSubscribedFlag(value) {
    return value === true || value === 1 || value === "1" || value === "true";
}

function populateRegionSelect() {
    const regSelect = document.getElementById("select-region");
    if (!regSelect) return;
    const current = regSelect.value;
    const keys = Object.keys(REGION_DISTRICTS);
    regSelect.innerHTML = '<option value="">Viloyatni tanlang</option>';
    keys.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.innerText = name;
        if (name === current) opt.selected = true;
        regSelect.appendChild(opt);
    });
}

// 1. Profil ma'lumotlarini Backenddan tortib kelish
async function fetchUserProfile() {
    const tgId = getCurrentTelegramId();
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user || {};
    const firstName = encodeURIComponent(tgUser.first_name || "O'quvchi");
    const username = encodeURIComponent(tgUser.username || "");

    try {
        const res = await fetch(`/api/profile?telegram_id=${tgId}&first_name=${firstName}&username=${username}`);
        if (!res.ok) throw new Error("Profilni yuklab bo'lmadi");
        const data = await res.json();
        if (!data || typeof data !== "object" || Array.isArray(data)) return;
        renderUserProfile(data);
        updateHeaderProfileWidgets(data);
    } catch (e) {
        console.error("Profil yuklashda xatolik:", e);
    }
}

// 2. Ma'lumotlarni HTML birkalariga yozish
function renderUserProfile(u) {
    if (!u || typeof u !== "object") return;

    const displayName = u.full_name || "O'quvchi";
    setElText("profile-fullname-top", displayName, "O'quvchi");
    setElText("profile-tg-id", u.telegram_id, "---");

    const subBadge = document.getElementById("profile-sub-badge");
    if (subBadge) {
        if (isSubscribedFlag(u.is_subscribed)) {
            subBadge.classList.remove("hidden");
        } else {
            subBadge.classList.add("hidden");
        }
    }

    setElText("profile-knowledge-level", u.knowledge_level, "Mehmon");

    // Avatar (Rasm yoki Emoji)
    const avatarContainer = document.getElementById("profile-avatar-container");
    const avatarUrl = typeof u.avatar_url === "string" ? u.avatar_url : "";
    if (avatarContainer && avatarUrl) {
        if (avatarUrl.startsWith("http") || avatarUrl.startsWith("data:image")) {
            avatarContainer.innerHTML = `<img src="${avatarUrl}" class="w-full h-full object-cover">`;
        } else {
            avatarContainer.innerHTML = `<span id="profile-avatar-icon" class="text-3xl select-none">${avatarUrl}</span>`;
        }
    }

    // Shaxsiy ma'lumotlar bloki
    const infoName = document.getElementById("info-fullname");
    if (infoName) infoName.innerText = displayName;

    const inputFn = document.getElementById("input-fullname");
    if (inputFn) inputFn.value = u.full_name || "";

    const infoPhone = document.getElementById('info-phone');
    if (infoPhone) infoPhone.innerText = u.phone_number || "Kiritilmagan";

    const infoSecPhone = document.getElementById('info-secondary-phone');
    if (infoSecPhone) infoSecPhone.innerText = u.secondary_phone || "Kiritilmagan";

    const inputSecPhone = document.getElementById('input-secondary-phone');
    if (inputSecPhone) inputSecPhone.value = (u.secondary_phone && u.secondary_phone !== "Kiritilmagan") ? u.secondary_phone : '';

    const infoDist = document.getElementById('info-district');
    if (infoDist) infoDist.innerText = u.district || "Tanlanmagan";

    const infoBday = document.getElementById('info-birthday');
    if (infoBday) infoBday.innerText = u.birth_date || "Tanlanmagan";

    // Ulangan qurilmalar
    renderDevices(u.devices || []);

    // Nazoratchi bloki
    renderSupervisor(u.supervisor);

    // Hamyon va faollik (so'm)
    const wallet = Number(u.balance != null ? u.balance : u.coins) || 0;
    const balanceEl = document.getElementById("coin-balance");
    if (balanceEl) balanceEl.innerText = wallet.toLocaleString("uz-UZ");
    setElText("referral-count", u.invited_friends || 0, "0");

    const refLink = document.getElementById("referral-link-text");
    if (refLink && u.telegram_id) {
        refLink.innerText = `https://t.me/pharos_talim_bot?start=ref${u.telegram_id}`;
    }

    const chartName = document.getElementById('chart-user-name');
    if (chartName) chartName.innerText = u.full_name || "O'quvchi";

    const chartXp = document.getElementById('chart-xp-label');
    if (chartXp) chartXp.innerText = Math.round((u.total_hours || 0) * 10);

    // Oferta holati
    const ofertaTag = document.getElementById('oferta-bonus-tag');
    if (ofertaTag && u.oferta_accepted) {
        ofertaTag.innerText = "(Imzolangan ✔)";
        ofertaTag.className = "text-slate-400 font-semibold";
    }

    // Tranzaksiyalar
    renderTransactions(u.transactions || []);
}

// 3. Galereyadan rasm tanlash va saqlash
function handleAvatarUpload(event) {
    const input = event?.target || document.getElementById("avatar-file-input");
    const file = input?.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        alert("Rasm hajmi 5MB dan oshmasligi kerak!");
        return;
    }

    const reader = new FileReader();
    reader.onload = async function(e) {
        const base64Data = e.target.result;

        const avatarContainer = document.getElementById('profile-avatar-container');
        if (avatarContainer) {
            avatarContainer.innerHTML = `<img src="${base64Data}" class="w-full h-full object-cover">`;
        }

        const tgId = getCurrentTelegramId();
        try {
            await fetch(`/api/user/profile/${tgId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ avatar_url: base64Data })
            });
            fetchUserProfile();
        } catch (err) {
            console.error("Avatar saqlashda xatolik:", err);
        }
    };
    reader.readAsDataURL(file);
}

// 4. Qo'shimcha telefon raqamini saqlash
async function saveSecondaryPhone() {
    const inputEl = document.getElementById('input-secondary-phone');
    const val = inputEl ? inputEl.value.trim() : '';

    if (!val) {
        alert("Iltimos, telefon raqamingizni kiriting!");
        return;
    }

    const tgId = getCurrentTelegramId();
    try {
        const res = await fetch(`/api/user/profile/${tgId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ secondary_phone: val })
        });

        if (res.ok) {
            closeModal('edit-phone-modal');
            fetchUserProfile();
        } else {
            alert("Xatolik: Raqam saqlanmadi.");
        }
    } catch (e) {
        alert("Server bilan aloqa uzildi.");
    }
}

// 5. Ulangan qurilmalar
function renderDevices(devices) {
    const container = document.getElementById("devices-container");
    if (!container) return;
    container.innerHTML = "";

    (Array.isArray(devices) ? devices : []).forEach(d => {
        const item = document.createElement('div');
        item.className = "bg-[#161F30] p-2 rounded-xl flex justify-between items-center text-[11px] border border-slate-800/40";
        item.innerHTML = `
            <div>
                <p class="text-white font-medium">${d.device_name || "Mobil qurilma"}</p>
                <p class="text-slate-400 text-[9px]">${d.device_ip || "IP"} • ${d.last_login || "Faol"}</p>
            </div>
            <span class="text-[10px] text-emerald-400 font-semibold">Ushbu sessiya</span>
        `;
        container.appendChild(item);
    });
}

function disconnectAllOtherDevices() {
    alert("Boshqa barcha faol sessiyalar muvaffaqiyatli uzildi!");
}

// 6. Nazoratchi boshqaruvi
function renderSupervisor(sup) {
    const emptyState = document.getElementById('supervisor-empty-state');
    const activeState = document.getElementById('supervisor-active-state');
    const nameEl = document.getElementById('supervisor-display-name');
    const badgeEl = document.getElementById('supervisor-status-badge');

    if (sup && sup.is_connected) {
        emptyState?.classList.add('hidden');
        activeState?.classList.remove('hidden');
        if (nameEl) nameEl.innerText = sup.name;
        if (badgeEl) {
            badgeEl.innerText = sup.terms_accepted ? "Ulangan (Faol)" : "Kutilmoqda";
        }
    } else {
        emptyState?.classList.remove('hidden');
        activeState?.classList.add('hidden');
    }
}

async function generateSupervisorInviteLink() {
    const nameInput = document.getElementById('input-supervisor-name');
    const supName = nameInput ? nameInput.value.trim() : '';

    if (!supName) {
        alert("Iltimos, nazoratchi kim bo'lishini yozing (Masalan: Dadam, Onam)");
        return;
    }

    const tgId = getCurrentTelegramId();
    try {
        const res = await fetch('/api/supervisor/invite-link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_tg_id: tgId, supervisor_name: supName })
        });
        let data = {};
        try {
            data = await res.json();
        } catch (parseErr) {
            data = {};
        }

        if (res.ok && data.status === "ok" && data.invite_link) {
            currentSupervisorLink = data.invite_link;
            document.getElementById('supervisor-input-group')?.classList.add('hidden');
            const linkGroup = document.getElementById('supervisor-link-group');
            if (linkGroup) linkGroup.classList.remove('hidden');

            const linkText = document.getElementById('supervisor-generated-link');
            if (linkText) linkText.innerText = data.invite_link;
        } else {
            alert("Havola yaratishda xatolik yuz berdi.");
        }
    } catch (e) {
        alert("Server bilan aloqa yo'q.");
    }
}

function copySupervisorLink() {
    if (!currentSupervisorLink) return;
    navigator.clipboard.writeText(currentSupervisorLink);
    alert("Nazoratchi taklif havolasi nusxalandi!");
}

function shareSupervisorLink() {
    if (!currentSupervisorLink) return;
    const text = encodeURIComponent("Assalomu alaykum! PHAROS platformasidagi ta'lim natijalarimni kuzatib borish uchun ushbu havolani tasdiqlang:");
    window.open(`https://t.me/share/url?url=${encodeURIComponent(currentSupervisorLink)}&text=${text}`, '_blank');
}

// 7. Ism-familiyani tahrirlash (kamida 2 ta so'z)
async function saveFullNameSelection() {
    const inputEl = document.getElementById('input-fullname');
    const errorEl = document.getElementById('fullname-error');
    const val = inputEl ? inputEl.value.trim() : '';

    const words = val.split(/\s+/).filter(w => w.length > 0);
    if (words.length < 2) {
        if (errorEl) errorEl.classList.remove('hidden');
        return;
    }
    if (errorEl) errorEl.classList.add('hidden');

    const tgId = getCurrentTelegramId();
    try {
        const res = await fetch(`/api/user/profile/${tgId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: val })
        });

        if (res.ok) {
            closeModal('edit-fullname-modal');
            fetchUserProfile();
        } else {
            alert("Xatolik: Ma'lumot saqlanmadi.");
        }
    } catch (e) {
        alert("Server bilan bog'lanishda xatolik yuz berdi.");
    }
}

// Manzil (Viloyat va tuman) tanlash mantiqi
function onRegionChange() {
    const regSelect = document.getElementById("select-region");
    const distSelect = document.getElementById("select-district");
    if (!distSelect) return;
    const reg = regSelect ? regSelect.value.trim() : "";

    distSelect.innerHTML = '<option value="">Tumanni tanlang</option>';
    if (!reg) return;

    let districts = REGION_DISTRICTS[reg];
    if (!districts) {
        const matchedKey = Object.keys(REGION_DISTRICTS).find(k => k.startsWith(reg) || reg.startsWith(k.split(' ')[0]));
        if (matchedKey) districts = REGION_DISTRICTS[matchedKey];
    }

    if (districts && districts.length > 0) {
        districts.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.innerText = d;
            distSelect.appendChild(opt);
        });
    }
}

async function saveRegionSelection() {
    const reg = document.getElementById("select-region")?.value;
    const dist = document.getElementById("select-district")?.value;
    if (!reg || !dist) return alert("Viloyat va tumanni tanlang!");

    const tgId = getCurrentTelegramId();
    await fetch(`/api/user/profile/${tgId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ region: reg, district: `${reg}, ${dist}` })
    });
    closeModal('edit-region-modal');
    fetchUserProfile();
}

// Tug'ilgan kunni saqlash
async function saveBirthdaySelection() {
    const bday = document.getElementById("input-birthday")?.value;
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

// Tranzaksiyalar tarixi
function renderTransactions(txs) {
    const container = document.getElementById("transactions-list");
    if (!container) return;
    const list = Array.isArray(txs) ? txs : [];

    if (list.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-center py-4">Hozircha tranzaksiyalar mavjud emas.</p>';
        return;
    }

    container.innerHTML = list.map(t => {
        const isPlus = t.amount > 0;
        const title = t.title || t.description || "Tranzaksiya";
        return `
            <div class="bg-[#161F30] border border-[#283548] p-2.5 rounded-xl flex items-center justify-between">
                <div>
                    <p class="text-slate-200 font-medium">${title}</p>
                    <span class="text-[10px] text-slate-500">${t.date || ""}</span>
                </div>
                <span class="font-bold font-mono ${isPlus ? 'text-emerald-400' : 'text-rose-400'}">
                    ${isPlus ? '+' : ''}${Number(t.amount || 0).toLocaleString('uz-UZ')} so'm
                </span>
            </div>
        `;
    }).join('');
}

// Modallar
function openModal(id) { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }

// Hisobni Click orqali to'ldirish
function openTopUpModal() {
    const input = document.getElementById("topup-amount-input");
    if (input) input.value = "50000";
    selectTopUpAmount(50000);
    openModal("topup-modal");
}

function selectTopUpAmount(amount) {
    const input = document.getElementById("topup-amount-input");
    if (input) input.value = String(amount);
    document.querySelectorAll(".topup-amt-btn").forEach((btn) => {
        const active = Number(btn.getAttribute("data-amt")) === Number(amount);
        btn.classList.toggle("border-emerald-500", active);
        btn.classList.toggle("bg-emerald-500/15", active);
        btn.classList.toggle("text-emerald-400", active);
    });
}

async function startClickTopUp() {
    const tgId = getCurrentTelegramId();
    const raw = document.getElementById("topup-amount-input")?.value;
    const amount = Number(raw);
    if (!tgId) {
        alert("Telegram ID aniqlanmadi. Mini Appni bot orqali oching.");
        return;
    }
    if (!amount || amount < 1000) {
        alert("Minimal summa 1 000 so'm.");
        return;
    }

    const btn = document.getElementById("topup-pay-btn");
    if (btn) {
        btn.disabled = true;
        btn.innerText = "Tayyorlanmoqda...";
    }
    try {
        const res = await fetch("/api/payments/click/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ telegram_id: tgId, amount: Math.round(amount) })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(data.detail || "Click to'lovi yaratilmadi. Sozlamalarni tekshiring.");
            return;
        }
        if (data.pay_url) {
            closeModal("topup-modal");
            if (window.Telegram?.WebApp?.openLink) {
                window.Telegram.WebApp.openLink(data.pay_url);
            } else {
                window.open(data.pay_url, "_blank");
            }
        } else {
            alert("To'lov havolasi olinmadi.");
        }
    } catch (e) {
        alert("Server bilan aloqa uzildi.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Click orqali to'lash";
        }
    }
}

// Oferta bonusi
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

// Axborot oynalari
function openAboutModal() {
    alert("PHAROS — Tarix va boshqa fanlardan milliy sertifikat hamda attestatsiyaga tayyorlovchi zamonaviy LMS platforma.");
}

function openManualModal() {
    alert("Foydalanish qo'llanmasi:\n1. Bosh sahifada imtihon sanalarini kuzating.\n2. Do'kondan kerakli kursni xarid qiling.\n3. Testlar bo'limida bilimingizni sinang.");
}

function openSocialsModal() {
    alert("Rasmiy sahifalarimiz:\nTelegram: @pharos_talim\nInstagram: @pharos_edu");
}

// Header ma'lumotlarini yangilash
function updateHeaderProfileWidgets(data) {
    if (!data) return;

    const nameEl = document.getElementById('hdr-name');
    if (nameEl) {
        const rawName = data.full_name || "O'quvchi";
        nameEl.innerText = rawName.split(' ')[0];
    }

    const statusEl = document.getElementById('hdr-status');
    if (statusEl) {
        statusEl.innerText = data.knowledge_level || data.target || "Mehmon";
    }

    const balanceEl = document.getElementById('hdr-balance') || document.getElementById('hdr-coins');
    if (balanceEl) {
        const wallet = Number(data.balance != null ? data.balance : data.coins) || 0;
        balanceEl.innerText = wallet.toLocaleString('uz-UZ');
    }

    const avatarBox = document.getElementById("hdr-avatar-box");
    const avatarEl = document.getElementById("hdr-avatar");
    const hdrAvatar = typeof data.avatar_url === "string" ? data.avatar_url : "";
    if (avatarBox && hdrAvatar) {
        if (hdrAvatar.startsWith("http") || hdrAvatar.startsWith("data:image")) {
            avatarBox.innerHTML = `<img src="${hdrAvatar}" class="w-full h-full object-cover">`;
        } else if (avatarEl) {
            avatarEl.innerText = hdrAvatar;
        }
    }
}

// Har 30 soniyada faollik hisoblash
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

function copyReferralLink() {
    const el = document.getElementById("referral-link-text");
    const link = el ? el.innerText.trim() : "";
    if (!link) return;
    navigator.clipboard.writeText(link);
    alert("Taklif havolasi nusxalandi!");
}

function shareReferralLink() {
    const el = document.getElementById("referral-link-text");
    const link = el ? el.innerText.trim() : "";
    if (!link) return;
    const text = encodeURIComponent("PHAROS platformasiga qo'shiling:");
    window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${text}`, "_blank");
}

async function submitFeedback() {
    const typeEl = document.getElementById("feedback-type");
    const textEl = document.getElementById("feedback-text");
    const message = textEl ? textEl.value.trim() : "";
    if (!message) {
        alert("Iltimos, xabaringizni yozing!");
        return;
    }
    const tgId = getCurrentTelegramId();
    try {
        const res = await fetch("/api/user/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                telegram_id: tgId,
                category: typeEl ? typeEl.value : "taklif",
                message
            })
        });
        if (res.ok) {
            closeModal("feedback-modal");
            if (textEl) textEl.value = "";
            alert("Murojaatingiz yuborildi. Rahmat!");
        } else {
            alert("Murojaat yuborilmadi. Qayta urinib ko'ring.");
        }
    } catch (e) {
        alert("Server bilan aloqa uzildi.");
    }
}

// Sahifa yuklanganda ishga tushirish
window.addEventListener("DOMContentLoaded", () => {
    populateRegionSelect();
    fetchUserProfile();
});