/**
 * PHAROS Admin Panel — API, jadvallar, modallar
 */
const AdminApp = (() => {
    const state = {
        token: null,
        initData: null,
        currentTab: 'dashboard',
        currentQuizId: null,
        quizTimer: null,
        newsTimer: null,
        dbTimer: null,
        quizzesById: {},
        newsById: {},
        questionsById: {},
        pricingQuizzes: [],
        pricingProducts: [],
        dbTables: [],
        dbTable: null,
        dbColumns: [],
        dbPk: 'id',
        dbRows: [],
        dbTotal: 0,
        dbOffset: 0,
        dbLimit: 30,
    };

    function esc(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function money(n) {
        return Number(n || 0).toLocaleString('uz-UZ');
    }

    function toast(msg, isError) {
        const el = document.getElementById('toast');
        if (!el) return;
        el.textContent = msg;
        el.classList.remove('ph-hide');
        el.style.background = isError ? '#ef4444' : '#10B981';
        el.style.color = isError ? '#fff' : '#0A0E17';
        clearTimeout(el._t);
        el._t = setTimeout(() => el.classList.add('ph-hide'), 2600);
    }

    function authHeaders() {
        const h = { 'Content-Type': 'application/json' };
        if (state.initData) h['X-Telegram-Init-Data'] = state.initData;
        if (state.token) h['X-Admin-Token'] = state.token;
        return h;
    }

    function authQuery() {
        if (state.token) return `?token=${encodeURIComponent(state.token)}`;
        return '';
    }

    async function api(path, options = {}) {
        const sep = path.includes('?') ? '&' : '?';
        let url = path;
        if (state.token && !path.includes('token=')) {
            url = `${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(state.token)}`;
        }
        const res = await fetch(url, {
            ...options,
            headers: { ...authHeaders(), ...(options.headers || {}) },
        });
        let data = null;
        try {
            data = await res.json();
        } catch (_) {
            data = null;
        }
        if (!res.ok) {
            const detail = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
            const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
            err.status = res.status;
            throw err;
        }
        return data;
    }

    function closeModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.add('ph-hide');
    }

    function openModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove('ph-hide');
        if (window.lucide) lucide.createIcons();
    }

    function switchTab(tab) {
        state.currentTab = tab;
        ['dashboard', 'quizzes', 'news', 'pricing', 'db'].forEach((name) => {
            const section = document.getElementById(`tab-${name}`);
            if (section) section.classList.toggle('ph-hide', name !== tab);
        });
        document.querySelectorAll('.admin-tab').forEach((btn) => {
            const active = btn.dataset.tab === tab;
            btn.classList.toggle('admin-tab-active', active);
            btn.classList.toggle('text-slate-300', !active);
        });
        if (tab === 'dashboard') loadStats();
        if (tab === 'quizzes') loadQuizzes();
        if (tab === 'news') loadNews();
        if (tab === 'pricing') loadPricing();
        if (tab === 'db') loadDbTables();
        if (window.lucide) lucide.createIcons();
    }

    function openStudentMode() {
        window.location.href = '/';
    }

    function reloadCurrent() {
        switchTab(state.currentTab);
        toast('Yangilandi');
    }

    // ---------- AUTH ----------
    async function tryAuth() {
        const params = new URLSearchParams(window.location.search);
        const urlToken = params.get('token');
        if (urlToken) {
            state.token = urlToken;
            sessionStorage.setItem('pharos_admin_token', urlToken);
        } else {
            state.token = sessionStorage.getItem('pharos_admin_token');
        }

        try {
            const tg = window.Telegram?.WebApp;
            if (tg) {
                tg.ready();
                tg.expand();
                if (tg.initData) state.initData = tg.initData;
            }
        } catch (_) { /* brauzer */ }

        const status = document.getElementById('auth-status');
        const tokenForm = document.getElementById('token-form');

        try {
            await api('/api/admin/me');
            document.getElementById('auth-gate')?.classList.add('ph-hide');
            switchTab('dashboard');
            return;
        } catch (e) {
            if (status) {
                status.textContent = state.initData
                    ? 'Telegram ID admin emas yoki initData yaroqsiz. Token bilan kiring.'
                    : 'Mini App tashqarisida token kerak.';
            }
            tokenForm?.classList.remove('ph-hide');
            if (state.token) {
                document.getElementById('token-input').value = state.token;
            }
        }
    }

    async function loginWithToken() {
        const input = document.getElementById('token-input');
        const value = (input?.value || '').trim();
        if (!value) {
            toast('Token kiriting', true);
            return;
        }
        state.token = value;
        state.initData = null;
        try {
            await api('/api/admin/me');
            sessionStorage.setItem('pharos_admin_token', value);
            document.getElementById('auth-gate')?.classList.add('ph-hide');
            switchTab('dashboard');
            toast('Kirish muvaffaqiyatli');
        } catch (e) {
            toast(e.message || 'Token noto\'g\'ri', true);
        }
    }

    // ---------- DASHBOARD ----------
    async function loadStats() {
        const grid = document.getElementById('stats-grid');
        if (!grid) return;
        try {
            const s = await api('/api/admin/stats');
            const cards = [
                { label: "O'quvchilar", value: money(s.students_count), icon: 'users', color: 'emerald' },
                { label: 'Bugungi faollik', value: money(s.today_active), icon: 'activity', color: 'sky' },
                { label: 'Kurs / mahsulot', value: money(s.products_count), icon: 'package', color: 'amber' },
                { label: 'Testlar', value: money(s.quizzes_count), icon: 'clipboard-list', color: 'violet' },
                { label: 'Savollar', value: money(s.questions_count), icon: 'help-circle', color: 'rose' },
                { label: 'Aylanma', value: money(s.turnover_balance), icon: 'wallet', color: 'emerald' },
            ];
            grid.innerHTML = cards.map((c) => `
                <div class="rounded-2xl border border-[#283548] bg-[#111827]/85 p-3.5">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] uppercase tracking-wider text-slate-400 font-bold">${esc(c.label)}</span>
                        <i data-lucide="${c.icon}" class="w-4 h-4 text-emerald-400"></i>
                    </div>
                    <div class="text-xl font-extrabold text-white font-mono">${esc(c.value)}</div>
                </div>
            `).join('');
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            toast(e.message, true);
        }
    }

    // ---------- QUIZZES ----------
    function debounceQuizzes() {
        clearTimeout(state.quizTimer);
        state.quizTimer = setTimeout(loadQuizzes, 320);
    }

    async function loadQuizzes() {
        const tbody = document.getElementById('quizzes-tbody');
        if (!tbody) return;
        const q = document.getElementById('quiz-search')?.value?.trim() || '';
        const subject = document.getElementById('quiz-subject-filter')?.value || '';
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (subject) params.set('subject', subject);
        try {
            const list = await api(`/api/admin/quizzes?${params.toString()}`);
            state.quizzesById = {};
            list.forEach((item) => { state.quizzesById[item.id] = item; });
            if (!list.length) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-3 py-6 text-center text-slate-500">Test topilmadi</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map((item) => `
                <tr class="hover:bg-[#161F30]/60">
                    <td class="px-3 py-2.5 font-mono text-slate-400">${item.id}</td>
                    <td class="px-3 py-2.5">
                        <div class="font-semibold text-slate-100 max-w-[220px] truncate">${esc(item.title)}</div>
                        <div class="text-[10px] text-slate-500 truncate">${esc(item.command_path || '—')}</div>
                    </td>
                    <td class="px-3 py-2.5">
                        <div>${esc(item.subject)}</div>
                        <div class="text-[10px] text-slate-500">${esc(item.exam_type)}</div>
                    </td>
                    <td class="px-3 py-2.5 font-mono">
                        ${money(item.base_price || item.price)}
                        ${item.share_discount_percent ? `<span class="text-emerald-400 text-[10px]">-${item.share_discount_percent}%</span>` : ''}
                    </td>
                    <td class="px-3 py-2.5 text-[10px] text-slate-400">${esc(item.visible_at || 'darhol')}</td>
                    <td class="px-3 py-2.5 font-mono">${item.questions_count}</td>
                    <td class="px-3 py-2.5">
                        <div class="flex flex-wrap gap-1">
                            <button onclick="AdminApp.openQuizEdit(${item.id})" class="px-2 py-1 rounded-lg bg-[#161F30] border border-[#283548] text-[10px] font-bold hover:border-emerald-500/40">Tahrir</button>
                            <button onclick="AdminApp.openQuestions(${item.id})" class="px-2 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold">Savollar</button>
                            <button onclick="AdminApp.deleteQuiz(${item.id})" class="px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[10px] font-bold">O'chirish</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            toast(e.message, true);
        }
    }

    function openQuizCreate() {
        document.getElementById('modal-quiz-title').textContent = 'Yangi test';
        document.getElementById('quiz-edit-id').value = '';
        document.getElementById('quiz-f-title').value = '';
        document.getElementById('quiz-f-subject').value = 'tarix';
        document.getElementById('quiz-f-exam_type').value = 'namunaviy';
        document.getElementById('quiz-f-price').value = '0';
        document.getElementById('quiz-f-base_price').value = '0';
        document.getElementById('quiz-f-discount').value = '0';
        document.getElementById('quiz-f-path').value = '';
        document.getElementById('quiz-f-visible').value = '';
        document.getElementById('quiz-f-starts').value = '';
        document.getElementById('quiz-f-video').value = '';
        document.getElementById('quiz-f-analysis').value = '';
        document.getElementById('quiz-f-active').checked = true;
        openModal('modal-quiz');
    }

    function openQuizEdit(idOrItem) {
        const item = typeof idOrItem === 'object' ? idOrItem : state.quizzesById[idOrItem];
        if (!item) {
            toast('Test topilmadi', true);
            return;
        }
        document.getElementById('modal-quiz-title').textContent = `Test #${item.id}`;
        document.getElementById('quiz-edit-id').value = item.id;
        document.getElementById('quiz-f-title').value = item.title || '';
        document.getElementById('quiz-f-subject').value = item.subject || '';
        document.getElementById('quiz-f-exam_type').value = item.exam_type || '';
        document.getElementById('quiz-f-price').value = item.price ?? 0;
        document.getElementById('quiz-f-base_price').value = item.base_price ?? 0;
        document.getElementById('quiz-f-discount').value = item.share_discount_percent ?? 0;
        document.getElementById('quiz-f-path').value = item.command_path || '';
        document.getElementById('quiz-f-visible').value = item.visible_at || '';
        document.getElementById('quiz-f-starts').value = item.starts_at || '';
        document.getElementById('quiz-f-video').value = item.full_analysis_video || '';
        document.getElementById('quiz-f-analysis').value = item.analysis_text || '';
        document.getElementById('quiz-f-active').checked = item.is_active !== false;
        openModal('modal-quiz');
    }

    async function saveQuiz() {
        const id = document.getElementById('quiz-edit-id').value;
        const payload = {
            title: document.getElementById('quiz-f-title').value.trim(),
            subject: document.getElementById('quiz-f-subject').value.trim(),
            exam_type: document.getElementById('quiz-f-exam_type').value.trim(),
            price: Number(document.getElementById('quiz-f-price').value || 0),
            base_price: Number(document.getElementById('quiz-f-base_price').value || 0),
            share_discount_percent: Number(document.getElementById('quiz-f-discount').value || 0),
            command_path: document.getElementById('quiz-f-path').value.trim() || null,
            visible_at: document.getElementById('quiz-f-visible').value.trim() || null,
            starts_at: document.getElementById('quiz-f-starts').value.trim() || null,
            full_analysis_video: document.getElementById('quiz-f-video').value.trim() || null,
            analysis_text: document.getElementById('quiz-f-analysis').value.trim() || null,
            is_active: document.getElementById('quiz-f-active').checked,
        };
        if (!payload.title) {
            toast('Sarlavha majburiy', true);
            return;
        }
        try {
            if (id) {
                await api(`/api/admin/quizzes/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            } else {
                await api('/api/admin/quizzes', { method: 'POST', body: JSON.stringify(payload) });
            }
            closeModal('modal-quiz');
            toast('Saqlandi');
            loadQuizzes();
        } catch (e) {
            toast(e.message, true);
        }
    }

    async function deleteQuiz(id) {
        if (!confirm(`Test #${id} ni o'chirish (faolsizlantirish)?`)) return;
        try {
            await api(`/api/admin/quizzes/${id}`, { method: 'DELETE' });
            toast("O'chirildi");
            loadQuizzes();
        } catch (e) {
            toast(e.message, true);
        }
    }

    // ---------- QUESTIONS ----------
    async function openQuestions(quizId) {
        state.currentQuizId = quizId;
        try {
            const data = await api(`/api/admin/questions/${quizId}`);
            document.getElementById('questions-quiz-name').textContent = data.quiz?.title || `Test #${quizId}`;
            document.getElementById('questions-quiz-meta').textContent =
                `${data.quiz?.subject || ''} · ${data.questions?.length || 0} ta savol`;
            renderQuestions(data.questions || []);
            openModal('modal-questions');
        } catch (e) {
            toast(e.message, true);
        }
    }

    function renderQuestions(list) {
        const box = document.getElementById('questions-list');
        if (!list.length) {
            box.innerHTML = '<p class="text-xs text-slate-500 py-4 text-center">Savollar yo\'q</p>';
            return;
        }
        state.questionsById = {};
        list.forEach((q) => { state.questionsById[q.id] = q; });
        const letters = ['A', 'B', 'C', 'D'];
        box.innerHTML = list.map((q) => `
            <div class="rounded-xl border border-[#283548] bg-[#0A0E17]/80 p-3">
                <div class="flex items-start justify-between gap-2 mb-1.5">
                    <div class="text-[11px] font-bold text-emerald-400">#${q.order_num} · β ${q.difficulty_beta ?? 2}</div>
                    <div class="flex gap-1">
                        <button onclick="AdminApp.openQuestionEdit(${q.id})" class="px-2 py-0.5 rounded-md border border-[#283548] text-[10px] font-bold">Tahrir</button>
                        <button onclick="AdminApp.deleteQuestion(${q.id})" class="px-2 py-0.5 rounded-md border border-rose-500/30 text-rose-300 text-[10px] font-bold">×</button>
                    </div>
                </div>
                <p class="text-xs text-slate-200 leading-snug mb-1.5">${esc(q.question_text)}</p>
                <div class="grid grid-cols-2 gap-1 text-[10px] text-slate-400">
                    ${['option_a','option_b','option_c','option_d'].map((k, i) =>
                        `<span class="${q.correct_option === i ? 'text-emerald-400 font-bold' : ''}">${letters[i]}) ${esc(q[k])}</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');
    }

    function openQuestionCreate() {
        if (!state.currentQuizId) return;
        document.getElementById('modal-q-title').textContent = 'Yangi savol';
        document.getElementById('q-edit-id').value = '';
        document.getElementById('q-edit-quiz-id').value = state.currentQuizId;
        document.getElementById('q-f-order').value = '1';
        document.getElementById('q-f-text').value = '';
        document.getElementById('q-f-a').value = '';
        document.getElementById('q-f-b').value = '';
        document.getElementById('q-f-c').value = '';
        document.getElementById('q-f-d').value = '';
        document.getElementById('q-f-correct').value = '0';
        document.getElementById('q-f-beta').value = '2.0';
        document.getElementById('q-f-video').value = '';
        document.getElementById('q-f-solution').value = '';
        document.getElementById('q-f-topic').value = '';
        openModal('modal-question-edit');
    }

    function openQuestionEdit(idOrItem) {
        const q = typeof idOrItem === 'object' ? idOrItem : state.questionsById[idOrItem];
        if (!q) {
            toast('Savol topilmadi', true);
            return;
        }
        document.getElementById('modal-q-title').textContent = `Savol #${q.id}`;
        document.getElementById('q-edit-id').value = q.id;
        document.getElementById('q-edit-quiz-id').value = q.quiz_id;
        document.getElementById('q-f-order').value = q.order_num ?? 1;
        document.getElementById('q-f-text').value = q.question_text || '';
        document.getElementById('q-f-a').value = q.option_a || '';
        document.getElementById('q-f-b').value = q.option_b || '';
        document.getElementById('q-f-c').value = q.option_c || '';
        document.getElementById('q-f-d').value = q.option_d || '';
        document.getElementById('q-f-correct').value = String(q.correct_option ?? 0);
        document.getElementById('q-f-beta').value = q.difficulty_beta ?? 2;
        document.getElementById('q-f-video').value = q.video_solution_url || '';
        document.getElementById('q-f-solution').value = q.solution_text || '';
        document.getElementById('q-f-topic').value = q.topic || '';
        openModal('modal-question-edit');
    }

    async function saveQuestion() {
        const id = document.getElementById('q-edit-id').value;
        const quizId = Number(document.getElementById('q-edit-quiz-id').value);
        const payload = {
            order_num: Number(document.getElementById('q-f-order').value || 1),
            question_text: document.getElementById('q-f-text').value.trim(),
            option_a: document.getElementById('q-f-a').value.trim(),
            option_b: document.getElementById('q-f-b').value.trim(),
            option_c: document.getElementById('q-f-c').value.trim(),
            option_d: document.getElementById('q-f-d').value.trim(),
            correct_option: Number(document.getElementById('q-f-correct').value),
            difficulty_beta: Number(document.getElementById('q-f-beta').value || 2),
            video_solution_url: document.getElementById('q-f-video').value.trim() || null,
            solution_text: document.getElementById('q-f-solution').value.trim() || null,
            topic: document.getElementById('q-f-topic').value.trim() || null,
        };
        if (!payload.question_text || !payload.option_a) {
            toast("Savol va variantlar to'ldirilsin", true);
            return;
        }
        try {
            if (id) {
                await api(`/api/admin/questions/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            } else {
                await api('/api/admin/questions', {
                    method: 'POST',
                    body: JSON.stringify({ ...payload, quiz_id: quizId }),
                });
            }
            closeModal('modal-question-edit');
            toast('Savol saqlandi');
            openQuestions(quizId);
        } catch (e) {
            toast(e.message, true);
        }
    }

    async function deleteQuestion(id) {
        if (!confirm('Savolni o\'chirish?')) return;
        try {
            await api(`/api/admin/questions/${id}`, { method: 'DELETE' });
            toast("O'chirildi");
            if (state.currentQuizId) openQuestions(state.currentQuizId);
        } catch (e) {
            toast(e.message, true);
        }
    }

    // ---------- NEWS ----------
    function debounceNews() {
        clearTimeout(state.newsTimer);
        state.newsTimer = setTimeout(loadNews, 320);
    }

    async function loadNews() {
        const tbody = document.getElementById('news-tbody');
        if (!tbody) return;
        const q = document.getElementById('news-search')?.value?.trim() || '';
        const params = q ? `?q=${encodeURIComponent(q)}` : '';
        try {
            const list = await api(`/api/admin/news${params}`);
            state.newsById = {};
            list.forEach((n) => { state.newsById[n.id] = n; });
            if (!list.length) {
                tbody.innerHTML = `<tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">Yangilik yo'q</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map((n) => `
                <tr class="hover:bg-[#161F30]/60">
                    <td class="px-3 py-2.5 font-mono text-slate-400">${n.id}</td>
                    <td class="px-3 py-2.5 font-semibold max-w-[240px] truncate">${esc(n.title)}</td>
                    <td class="px-3 py-2.5 text-slate-400">${esc(n.category)}</td>
                    <td class="px-3 py-2.5 font-mono text-emerald-400">${money(n.views_count)}</td>
                    <td class="px-3 py-2.5 text-[10px] text-slate-500">${esc((n.created_at || '').slice(0, 16))}</td>
                    <td class="px-3 py-2.5">
                        <div class="flex gap-1">
                            <button onclick="AdminApp.openNewsEdit(${n.id})" class="px-2 py-1 rounded-lg bg-[#161F30] border border-[#283548] text-[10px] font-bold">Tahrir</button>
                            <button onclick="AdminApp.deleteNews(${n.id})" class="px-2 py-1 rounded-lg border border-rose-500/30 text-rose-300 text-[10px] font-bold">O'chirish</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            toast(e.message, true);
        }
    }

    function openNewsCreate() {
        document.getElementById('modal-news-title').textContent = 'Yangi yangilik';
        document.getElementById('news-edit-id').value = '';
        document.getElementById('news-f-title').value = '';
        document.getElementById('news-f-hashtags').value = '';
        document.getElementById('news-f-category').value = 'umumiy';
        document.getElementById('news-f-summary').value = '';
        document.getElementById('news-f-content').value = '';
        document.getElementById('news-f-image').value = '';
        document.getElementById('news-f-source').value = '';
        openModal('modal-news');
    }

    function openNewsEdit(idOrItem) {
        const n = typeof idOrItem === 'object' ? idOrItem : state.newsById[idOrItem];
        if (!n) {
            toast('Yangilik topilmadi', true);
            return;
        }
        document.getElementById('modal-news-title').textContent = `Yangilik #${n.id}`;
        document.getElementById('news-edit-id').value = n.id;
        document.getElementById('news-f-title').value = n.title || '';
        document.getElementById('news-f-hashtags').value = n.hashtags || '';
        document.getElementById('news-f-category').value = n.category || 'umumiy';
        document.getElementById('news-f-summary').value = n.summary || '';
        document.getElementById('news-f-content').value = n.content || '';
        document.getElementById('news-f-image').value = n.image_url || '';
        document.getElementById('news-f-source').value = n.source_url || '';
        openModal('modal-news');
    }

    async function saveNews() {
        const id = document.getElementById('news-edit-id').value;
        const payload = {
            title: document.getElementById('news-f-title').value.trim(),
            hashtags: document.getElementById('news-f-hashtags').value.trim(),
            category: document.getElementById('news-f-category').value.trim() || 'umumiy',
            summary: document.getElementById('news-f-summary').value.trim() || null,
            content: document.getElementById('news-f-content').value.trim(),
            image_url: document.getElementById('news-f-image').value.trim() || '',
            source_url: document.getElementById('news-f-source').value.trim() || null,
        };
        if (!payload.title || !payload.content) {
            toast('Sarlavha va matn majburiy', true);
            return;
        }
        try {
            if (id) {
                await api(`/api/admin/news/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            } else {
                await api('/api/admin/news', { method: 'POST', body: JSON.stringify(payload) });
            }
            closeModal('modal-news');
            toast('Saqlandi');
            loadNews();
        } catch (e) {
            toast(e.message, true);
        }
    }

    async function deleteNews(id) {
        if (!confirm(`Yangilik #${id} ni o'chirish?`)) return;
        try {
            await api(`/api/admin/news/${id}`, { method: 'DELETE' });
            toast("O'chirildi");
            loadNews();
        } catch (e) {
            toast(e.message, true);
        }
    }

    // ---------- PRICING ----------
    async function loadPricing() {
        try {
            const data = await api('/api/admin/pricing');
            state.pricingQuizzes = data.quizzes || [];
            state.pricingProducts = data.products || [];
            const qBody = document.getElementById('pricing-quizzes-tbody');
            const pBody = document.getElementById('pricing-products-tbody');
            qBody.innerHTML = state.pricingQuizzes.map((q) => `
                <tr>
                    <td class="px-3 py-2">
                        <div class="font-semibold max-w-[200px] truncate">${esc(q.title)}</div>
                        <div class="text-[10px] text-slate-500">#${q.id} · ${esc(q.subject)}</div>
                    </td>
                    <td class="px-3 py-2"><input data-entity="quiz" data-id="${q.id}" data-field="price" type="number" min="0" value="${q.price}" class="w-24"></td>
                    <td class="px-3 py-2"><input data-entity="quiz" data-id="${q.id}" data-field="base_price" type="number" min="0" value="${q.base_price}" class="w-24"></td>
                    <td class="px-3 py-2"><input data-entity="quiz" data-id="${q.id}" data-field="share_discount_percent" type="number" min="0" max="100" value="${q.share_discount_percent}" class="w-20"></td>
                </tr>
            `).join('') || `<tr><td colspan="4" class="px-3 py-4 text-center text-slate-500">Bo'sh</td></tr>`;

            pBody.innerHTML = state.pricingProducts.map((p) => `
                <tr>
                    <td class="px-3 py-2">
                        <div class="font-semibold max-w-[220px] truncate">${esc(p.title)}</div>
                        <div class="text-[10px] text-slate-500">#${p.id} · ${esc(p.category)}</div>
                    </td>
                    <td class="px-3 py-2"><input data-entity="product" data-id="${p.id}" data-field="price_coin" type="number" min="0" value="${p.price_coin}" class="w-24"></td>
                    <td class="px-3 py-2"><input data-entity="product" data-id="${p.id}" data-field="old_price_coin" type="number" min="0" value="${p.old_price_coin}" class="w-24"></td>
                </tr>
            `).join('') || `<tr><td colspan="3" class="px-3 py-4 text-center text-slate-500">Bo'sh</td></tr>`;
        } catch (e) {
            toast(e.message, true);
        }
    }

    async function saveAllPricing() {
        const inputs = document.querySelectorAll('#tab-pricing input[data-entity]');
        const map = {};
        inputs.forEach((inp) => {
            const entity = inp.dataset.entity;
            const id = Number(inp.dataset.id);
            const field = inp.dataset.field;
            const key = `${entity}:${id}`;
            if (!map[key]) map[key] = { entity, id };
            map[key][field] = Number(inp.value || 0);
        });
        const items = Object.values(map);
        if (!items.length) {
            toast("O'zgarish yo'q");
            return;
        }
        try {
            const res = await api('/api/admin/update-pricing', {
                method: 'POST',
                body: JSON.stringify({ items }),
            });
            toast(`Saqlandi: ${res.updated} ta`);
            loadPricing();
        } catch (e) {
            toast(e.message, true);
        }
    }

    // ---------- DB MANAGER ----------
    function truncateCell(val, max = 48) {
        const s = val == null ? '' : String(val);
        if (s.length <= max) return esc(s);
        return `<span title="${esc(s)}">${esc(s.slice(0, max))}…</span>`;
    }

    function renderDbTableChips() {
        const box = document.getElementById('db-tables-list');
        const countEl = document.getElementById('db-table-count');
        if (countEl) countEl.textContent = `${state.dbTables.length} jadval`;
        if (!box) return;
        if (!state.dbTables.length) {
            box.innerHTML = `<span class="text-xs text-slate-500">Jadvallar topilmadi</span>`;
            return;
        }
        box.innerHTML = state.dbTables.map((t) => {
            const active = t.name === state.dbTable;
            return `
                <button
                    onclick="AdminApp.selectDbTable('${esc(t.name)}')"
                    class="px-2.5 py-1 rounded-lg border text-[10px] font-bold transition ${
                        active
                            ? 'bg-emerald-500/15 border-emerald-500/45 text-emerald-300'
                            : 'bg-[#161F30] border-[#283548] text-slate-300 hover:border-emerald-500/30'
                    }"
                    title="${esc(t.model)}"
                >${esc(t.name)}</button>
            `;
        }).join('');
    }

    async function loadDbTables() {
        try {
            const data = await api('/api/admin/db/tables');
            state.dbTables = data.tables || [];
            if (!state.dbTable && state.dbTables.length) {
                state.dbTable = state.dbTables[0].name;
            }
            renderDbTableChips();
            if (state.dbTable) await loadDbRows(true);
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            toast(e.message, true);
        }
    }

    function selectDbTable(name) {
        state.dbTable = name;
        state.dbOffset = 0;
        renderDbTableChips();
        loadDbRows(true);
    }

    function debounceDbRows() {
        clearTimeout(state.dbTimer);
        state.dbTimer = setTimeout(() => loadDbRows(true), 320);
    }

    function dbPrevPage() {
        if (state.dbOffset <= 0) return;
        state.dbOffset = Math.max(0, state.dbOffset - state.dbLimit);
        loadDbRows(false);
    }

    function dbNextPage() {
        if (state.dbOffset + state.dbLimit >= state.dbTotal) return;
        state.dbOffset += state.dbLimit;
        loadDbRows(false);
    }

    async function loadDbRows(resetOffset) {
        if (!state.dbTable) return;
        if (resetOffset) state.dbOffset = 0;
        const q = document.getElementById('db-search')?.value?.trim() || '';
        const size = Number(document.getElementById('db-page-size')?.value || 30);
        state.dbLimit = size;
        const params = new URLSearchParams({
            limit: String(state.dbLimit),
            offset: String(state.dbOffset),
        });
        if (q) params.set('q', q);

        const thead = document.getElementById('db-thead-row');
        const tbody = document.getElementById('db-tbody');
        const meta = document.getElementById('db-meta');
        const pageLabel = document.getElementById('db-page-label');

        try {
            const data = await api(`/api/admin/db/${encodeURIComponent(state.dbTable)}?${params}`);
            state.dbColumns = data.columns || [];
            state.dbPk = data.pk || 'id';
            state.dbRows = data.rows || [];
            state.dbTotal = data.total || 0;

            const page = Math.floor(state.dbOffset / state.dbLimit) + 1;
            const pages = Math.max(1, Math.ceil(state.dbTotal / state.dbLimit));
            if (meta) {
                meta.textContent = `${data.model || state.dbTable} · ${state.dbTotal} ta yozuv`;
            }
            if (pageLabel) pageLabel.textContent = `${page} / ${pages}`;

            if (thead) {
                thead.innerHTML = state.dbColumns
                    .map((c) => `<th class="px-3 py-2.5">${esc(c.name)}</th>`)
                    .join('') + `<th class="px-3 py-2.5">Amallar</th>`;
            }

            if (!tbody) return;
            if (!state.dbRows.length) {
                tbody.innerHTML = `<tr><td colspan="${state.dbColumns.length + 1}" class="px-3 py-6 text-center text-slate-500">Ma'lumot yo'q</td></tr>`;
                return;
            }

            tbody.innerHTML = state.dbRows.map((row) => {
                const pkVal = row[state.dbPk];
                const cells = state.dbColumns.map((c) => {
                    const v = row[c.name];
                    if (c.type === 'boolean') {
                        return `<td class="px-3 py-2.5">${v ? '<span class="text-emerald-400">✓</span>' : '<span class="text-slate-600">—</span>'}</td>`;
                    }
                    if (c.type === 'text' || (typeof v === 'string' && v.length > 48)) {
                        return `<td class="px-3 py-2.5 max-w-[220px]">${truncateCell(v, 48)}</td>`;
                    }
                    return `<td class="px-3 py-2.5 font-mono text-[11px] text-slate-300">${truncateCell(v, 40)}</td>`;
                }).join('');
                return `
                    <tr class="hover:bg-[#161F30]/60" data-pk="${esc(pkVal)}">
                        ${cells}
                        <td class="px-3 py-2.5">
                            <div class="flex gap-1 whitespace-nowrap">
                                <button onclick="AdminApp.openDbEdit(${JSON.stringify(String(pkVal))})" class="px-2 py-1 rounded-lg bg-[#161F30] border border-[#283548] text-[10px] font-bold hover:border-emerald-500/40">✏️ Tahrirlash</button>
                                <button onclick="AdminApp.deleteDbRow(${JSON.stringify(String(pkVal))})" class="px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[10px] font-bold">🗑️ O'chirish</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            toast(e.message, true);
        }
    }

    function buildDbForm(row, creating) {
        const box = document.getElementById('db-form-fields');
        if (!box) return;
        box.innerHTML = state.dbColumns.map((c) => {
            const val = row && row[c.name] != null ? row[c.name] : '';
            const isPk = c.primary_key;
            const disabled = !creating && isPk ? 'disabled' : '';
            const hint = [
                c.type,
                c.nullable ? 'nullable' : 'required',
                isPk ? 'PK' : '',
            ].filter(Boolean).join(' · ');

            if (c.type === 'boolean') {
                const checked = val === true || val === 1 || val === '1' || val === 'true' ? 'checked' : '';
                return `
                    <label class="flex items-center gap-2 text-slate-300">
                        <input type="checkbox" data-db-field="${esc(c.name)}" data-db-type="boolean" class="w-4 h-4" ${checked} ${disabled}>
                        <span>${esc(c.name)} <span class="text-slate-500">(${esc(hint)})</span></span>
                    </label>
                `;
            }

            if (c.type === 'text') {
                return `
                    <label class="block text-slate-400">${esc(c.name)}
                        <span class="text-slate-600">(${esc(hint)})</span>
                        <textarea data-db-field="${esc(c.name)}" data-db-type="text" rows="3" ${disabled}>${esc(val)}</textarea>
                    </label>
                `;
            }

            let inputType = 'text';
            if (c.type === 'integer' || c.type === 'float') inputType = 'number';
            if (c.type === 'date') inputType = 'date';
            if (c.type === 'datetime') inputType = 'text';
            const step = c.type === 'float' ? 'step="any"' : (c.type === 'integer' ? 'step="1"' : '');
            const placeholder = c.type === 'datetime' ? 'YYYY-MM-DD HH:MM:SS' : '';

            return `
                <label class="block text-slate-400">${esc(c.name)}
                    <span class="text-slate-600">(${esc(hint)})</span>
                    <input data-db-field="${esc(c.name)}" data-db-type="${esc(c.type)}" type="${inputType}" ${step} value="${esc(val)}" placeholder="${esc(placeholder)}" ${disabled}>
                </label>
            `;
        }).join('');
    }

    function collectDbFormPayload(creating) {
        const payload = {};
        document.querySelectorAll('#db-form-fields [data-db-field]').forEach((el) => {
            const name = el.dataset.dbField;
            const type = el.dataset.dbType;
            const col = state.dbColumns.find((c) => c.name === name);
            if (!creating && col?.primary_key) return;
            if (el.disabled) return;

            if (type === 'boolean') {
                payload[name] = !!el.checked;
                return;
            }
            let v = el.value;
            if (v === '' || v == null) {
                payload[name] = null;
                return;
            }
            if (type === 'integer') {
                payload[name] = Number(v);
                return;
            }
            if (type === 'float') {
                payload[name] = Number(v);
                return;
            }
            payload[name] = v;
        });
        return payload;
    }

    function openDbCreate() {
        if (!state.dbTable) {
            toast('Avval jadval tanlang', true);
            return;
        }
        document.getElementById('modal-db-title').textContent = `➕ Yangi · ${state.dbTable}`;
        document.getElementById('db-edit-id').value = '';
        buildDbForm({}, true);
        openModal('modal-db');
    }

    function openDbEdit(pkVal) {
        const row = state.dbRows.find((r) => String(r[state.dbPk]) === String(pkVal));
        if (!row) {
            toast('Yozuv topilmadi', true);
            return;
        }
        document.getElementById('modal-db-title').textContent = `✏️ ${state.dbTable} #${pkVal}`;
        document.getElementById('db-edit-id').value = String(pkVal);
        buildDbForm(row, false);
        openModal('modal-db');
    }

    async function saveDbRow() {
        if (!state.dbTable) return;
        const id = document.getElementById('db-edit-id').value;
        const creating = !id;
        const payload = collectDbFormPayload(creating);
        try {
            if (creating) {
                await api(`/api/admin/db/${encodeURIComponent(state.dbTable)}`, {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
                toast("Qo'shildi");
            } else {
                const res = await api(
                    `/api/admin/db/${encodeURIComponent(state.dbTable)}/${encodeURIComponent(id)}`,
                    { method: 'PUT', body: JSON.stringify(payload) },
                );
                // Sahifa yangilanmasdan qatorni yangilash
                const idx = state.dbRows.findIndex((r) => String(r[state.dbPk]) === String(id));
                if (idx >= 0 && res.row) state.dbRows[idx] = res.row;
                toast('Saqlandi');
            }
            closeModal('modal-db');
            await loadDbRows(false);
        } catch (e) {
            toast(e.message, true);
        }
    }

    async function deleteDbRow(pkVal) {
        if (!state.dbTable) return;
        if (!confirm(`"${state.dbTable}" jadvalidan #${pkVal} ni o'chirishni tasdiqlaysizmi?`)) return;
        try {
            await api(
                `/api/admin/db/${encodeURIComponent(state.dbTable)}/${encodeURIComponent(pkVal)}`,
                { method: 'DELETE' },
            );
            toast("O'chirildi");
            await loadDbRows(false);
        } catch (e) {
            toast(e.message, true);
        }
    }

    function init() {
        tryAuth();
    }

    return {
        init,
        switchTab,
        openStudentMode,
        reloadCurrent,
        loginWithToken,
        closeModal,
        debounceQuizzes,
        loadQuizzes,
        openQuizCreate,
        openQuizEdit,
        saveQuiz,
        deleteQuiz,
        openQuestions,
        openQuestionCreate,
        openQuestionEdit,
        saveQuestion,
        deleteQuestion,
        debounceNews,
        loadNews,
        openNewsCreate,
        openNewsEdit,
        saveNews,
        deleteNews,
        loadPricing,
        saveAllPricing,
        loadDbTables,
        selectDbTable,
        debounceDbRows,
        loadDbRows,
        dbPrevPage,
        dbNextPage,
        openDbCreate,
        openDbEdit,
        saveDbRow,
        deleteDbRow,
    };
})();
