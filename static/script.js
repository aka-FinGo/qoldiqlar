const tg = window.Telegram.WebApp;
tg.expand(); 

// Fallback (Test)
const user = tg.initDataUnsafe?.user || { id: 380004653, first_name: "Test User" };
const userId = user.id;

let itemsData = [];
let selectedItem = null;
let isAdmin = false;
let viewMode = 'grid'; 

document.addEventListener('DOMContentLoaded', async () => {
    if(document.getElementById('userName')) {
        document.getElementById('userName').innerText = user.first_name;
        document.getElementById('userIdDisp').innerText = `ID: ${user.id}`;
    }

    try {
        const res = await fetch(`/api/check_admin?user_id=${userId}`);
        const data = await res.json();
        isAdmin = data.is_admin;
        if(isAdmin && document.getElementById('adminPanel')) {
            document.getElementById('adminPanel').classList.remove('hidden');
        }
    } catch(e) {}

    await loadCategories();
    await fetchData('all');
});

// --- DATA ---
async function fetchData(type = 'all') {
    const loader = document.getElementById('loader');
    const list = document.getElementById(type === 'all' ? 'remnantsList' : 'profileList');
    const empty = document.getElementById('emptyState');
    
    if(loader) loader.classList.remove('hidden');
    if(list) list.innerHTML = '';
    if(empty) empty.classList.add('hidden');

    try {
        let url = `/api/remnants?user_id=${userId}&type=${type}`;
        if (type === 'all') {
            const activeCat = document.querySelector('.cat-pill.active');
            if (activeCat && activeCat.innerText !== 'Barchasi') {
                url += `&category=${encodeURIComponent(activeCat.innerText)}`;
            }
        }

        const res = await fetch(url);
        const data = await res.json();

        if (data.error) {
            alert("Xatolik: " + data.error);
            return; 
        }

        itemsData = Array.isArray(data) ? data : [];
        const containerId = (type === 'all') ? 'remnantsList' : 'profileList';
        renderGrid(itemsData, containerId);

        if (itemsData.length === 0 && empty) empty.classList.remove('hidden');

    } catch (e) {
        alert("Aloqa xatosi: " + e.message);
    } finally {
        if(loader) loader.classList.add('hidden');
    }
}

async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        const cats = await res.json();
        if (!Array.isArray(cats)) return;

        const cont = document.getElementById('categoryFilter');
        while (cont.children.length > 1) {
            cont.removeChild(cont.lastChild);
        }

        cats.forEach(c => {
            const btn = document.createElement('button');
            btn.className = "cat-pill px-4 py-1.5 rounded-full text-sm border bg-white whitespace-nowrap transition ml-2";
            btn.innerText = c;
            btn.onclick = function() { filterCat(this, c); };
            cont.appendChild(btn);
        });
    } catch(e) {}
}

// --- RENDER ---
// renderGrid funksiyasini shunga almashtiring
function renderGrid(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="text-center p-10 text-gray-400">Ma\'lumot yo\'q</p>';
        return;
    }

    data.forEach(item => {
        const el = document.createElement('div');
        el.className = `card p-0 active:scale-95 transition-transform overflow-hidden flex flex-col`;
        el.onclick = () => openDetail(item);
        
        // Ma'lumotlarni o'qishda xatolikdan qochamiz
        const material = item.material || 'Nomaʼlum';
        const category = item.category || 'Qoldiq';
        const size = `${item.width || 0} x ${item.height || 0}`;

        el.innerHTML = `
            <div class="bg-blue-50 h-32 flex items-center justify-center text-blue-200">
                <i class="fas fa-layer-group text-4xl"></i>
            </div>
            <div class="p-3">
                <span class="text-[10px] text-blue-600 font-bold uppercase border px-1 rounded">${category}</span>
                <h3 class="font-bold text-sm text-gray-800 mt-1 line-clamp-1">${material}</h3>
                <div class="font-extrabold text-lg mt-1 text-gray-900">${size}</div>
                <div class="text-xs text-gray-500 font-bold">${item.qty || 0} dona</div>
            </div>
        `;
        container.appendChild(el);
    });
}



function filterCat(btn, cat) {
    document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active', 'bg-blue-600', 'text-white'));
    btn.classList.add('active', 'bg-blue-600', 'text-white');
    fetchData('all');
}

function toggleView() {
    viewMode = viewMode === 'grid' ? 'list' : 'grid';
    document.getElementById('viewIcon').className = viewMode === 'grid' ? 'fas fa-th-large text-xl' : 'fas fa-list text-xl';
    const isProfile = !document.getElementById('profilePage').classList.contains('hidden');
    renderGrid(itemsData, isProfile ? 'profileList' : 'remnantsList');
}

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.remove('active', 'text-blue-600');
        el.classList.add('text-gray-400');
    });
    const activeBtn = document.getElementById(`nav-${tab}`);
    if(activeBtn) {
        activeBtn.classList.add('active', 'text-blue-600');
        activeBtn.classList.remove('text-gray-400');
    }

    if (tab === 'home') {
        document.getElementById('mainContainer').classList.remove('hidden');
        document.getElementById('profilePage').classList.add('hidden');
        document.querySelector('header').classList.remove('hidden');
        fetchData('all');
    } else if (tab === 'profile') {
        document.getElementById('mainContainer').classList.add('hidden');
        document.getElementById('profilePage').classList.remove('hidden');
        document.querySelector('header').classList.add('hidden');
        switchProfileTab('mine');
    }
}

function switchProfileTab(ptab) {
    const btnMine = document.getElementById('ptab-mine');
    const btnUsed = document.getElementById('ptab-used');
    const activeClass = "flex-1 py-2 text-sm font-bold rounded-lg bg-white shadow text-gray-800 transition";
    const inactiveClass = "flex-1 py-2 text-sm font-bold rounded-lg text-gray-500 hover:bg-gray-200 transition";

    if (ptab === 'mine') { btnMine.className = activeClass; btnUsed.className = inactiveClass; } 
    else { btnMine.className = inactiveClass; btnUsed.className = activeClass; }
    fetchData(ptab);
}

// --- MODALS ---
function openDetail(item) {
    selectedItem = item;
    document.getElementById('d-material').innerText = item.material;
    document.getElementById('d-cat').innerText = item.category;
    document.getElementById('d-size').innerText = `${item.width} x ${item.height}`;
    document.getElementById('d-qty').innerText = `${item.qty} ta`;
    document.getElementById('d-order').innerText = item.origin_order || '-';
    document.getElementById('d-location').innerText = item.location || '-';
    
    const adminActions = document.getElementById('adminActions');
    // API endi user_id ni to'g'ri qaytaradi, shuning uchun solishtirish ishlaydi
    if (isAdmin || String(item.user_id) === String(userId)) {
        adminActions.classList.remove('hidden');
    } else {
        adminActions.classList.add('hidden');
    }

    const btnUse = document.getElementById('btnUse');
    if (item.status === 0) btnUse.classList.add('hidden');
    else btnUse.classList.remove('hidden');
    
    document.getElementById('detailModal').classList.remove('hidden');
}

async function useItem() {
    if(!selectedItem) return;
    if(!confirm("Ishlatishni tasdiqlaysizmi?")) return;
    await fetch('/api/use', { method: 'POST', body: JSON.stringify({id: selectedItem.id, user_id: userId}) });
    closeModal('detailModal');
    tg.HapticFeedback.notificationOccurred('success');
    const isProfile = !document.getElementById('profilePage').classList.contains('hidden');
    fetchData(isProfile ? (document.getElementById('ptab-used').classList.contains('shadow') ? 'used' : 'mine') : 'all');
}

function editItem() {
    closeModal('detailModal');
    document.getElementById('editId').value = selectedItem.id;
    document.getElementById('inpCat').value = selectedItem.category;
    document.getElementById('inpMat').value = selectedItem.material;
    document.getElementById('inpW').value = selectedItem.width;
    document.getElementById('inpH').value = selectedItem.height;
    document.getElementById('inpQty').value = selectedItem.qty;
    document.getElementById('inpOrd').value = selectedItem.origin_order || '';
    document.getElementById('inpLoc').value = selectedItem.location || '';
    document.getElementById('btnSave').innerText = "Yangilash";
    openModal('addModal');
}

async function deleteItem() {
    if(!selectedItem || !confirm("O'chirib yuborilsinmi?")) return;
    await fetch('/api/delete', { method: 'POST', body: JSON.stringify({id: selectedItem.id}) });
    closeModal('detailModal');
    fetchData('all');
}

async function submitAdd(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    data.user_id = userId;
    
    const url = data.id ? '/api/edit' : '/api/add';
    
    try {
        const res = await fetch(url, { method: 'POST', body: JSON.stringify(data) });
        const result = await res.json();
        if(result.error) alert("Xatolik: " + result.error);
        else {
            e.target.reset();
            document.getElementById('editId').value = ''; 
            document.getElementById('btnSave').innerText = "Saqlash";
            closeModal('addModal');
            tg.HapticFeedback.notificationOccurred('success');
            if(data.id) fetchData('all'); 
            else switchTab('profile');
        }
    } catch(err) { alert("Server xatosi!"); }
}

function openModal(id) { 
    if(id==='addModal' && document.getElementById('btnSave').innerText !== "Yangilash") {
        document.getElementById('addForm').reset(); 
        document.getElementById('editId').value = '';
    }
    document.getElementById(id).classList.remove('hidden'); 
}
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }


async function testAPIDirectly() {
    const debugBox = document.getElementById('debugResult');
    debugBox.classList.remove('hidden');
    debugBox.innerText = "So'rov yuborilmoqda...";

    try {
        // user_id ni qo'lda yozib tekshiramiz (bazangizda bor ID)
        const testId = 380004653; 
        const response = await fetch(`/api/remnants?user_id=${testId}&type=all`);
        
        if (!response.ok) {
            throw new Error(`Server xatosi: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            debugBox.innerText = "❌ API Xatosi: " + data.error;
        } else if (Array.isArray(data)) {
            debugBox.innerText = `✅ Muvaffaqiyatli!\nTopilgan qoldiqlar soni: ${data.length}\n\nBirinchi ma'lumot:\n` + JSON.stringify(data[0], null, 2);
            console.log("To'liq ma'lumot:", data);
        } else {
            debugBox.innerText = "⚠️ Noma'lum format: " + JSON.stringify(data);
        }
    } catch (err) {
        debugBox.innerText = "❌ Tarmoq xatosi: " + err.message;
    }
}

