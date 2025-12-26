const tg = window.Telegram.WebApp;
tg.expand(); 

// Telegramdan foydalanuvchi ma'lumotlarini olish (Test uchun fallback)
const user = tg.initDataUnsafe?.user || { id: 380004653, first_name: "Test User" };
const userId = user.id;

let itemsData = [];
let selectedItem = null;
let isAdmin = false;
let viewMode = 'grid'; 

// --- INIT ---
document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('userName').innerText = user.first_name;
    document.getElementById('userIdDisp').innerText = `ID: ${user.id}`;

    // Adminligini tekshirish
    try {
        const res = await fetch(`/api/check_admin?user_id=${userId}`);
        const data = await res.json();
        isAdmin = data.is_admin;
        if(isAdmin) document.getElementById('adminPanel').classList.remove('hidden');
    } catch(e) { console.log("Admin check fail"); }

    await loadCategories();
    await fetchData();
});

// --- FETCHING ---
async function fetchData(type = 'all') {
    document.getElementById('loader').classList.remove('hidden');
    document.getElementById('remnantsList').innerHTML = '';
    document.getElementById('emptyState').classList.add('hidden');

    try {
        let url = `/api/remnants?user_id=${userId}&type=${type}`;
        const res = await fetch(url);
        itemsData = await res.json();
        
        if (type === 'all') renderGrid(itemsData, 'remnantsList');
        else renderGrid(itemsData, 'profileList');

        if(itemsData.length === 0) document.getElementById('emptyState').classList.remove('hidden');

    } catch (e) {
        tg.showAlert("Xato: " + e.message);
    } finally {
        document.getElementById('loader').classList.add('hidden');
    }
}

async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        const cats = await res.json();
        const cont = document.getElementById('categoryFilter');
        cats.forEach(c => {
            cont.innerHTML += `<button onclick="filterCat(this, '${c}')" class="cat-pill px-4 py-1.5 rounded-full text-sm border bg-white whitespace-nowrap transition ml-2">${c}</button>`;
        });
    } catch(e){}
}

// --- RENDERING ---
function renderGrid(data, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    // Grid/List rejimi
    if (viewMode === 'grid') {
        container.className = 'grid grid-cols-2 gap-3 pb-24';
    } else {
        container.className = 'flex flex-col gap-3 pb-24';
    }

    data.forEach(item => {
        const el = document.createElement('div');
        el.className = `card p-0 relative active:scale-95 transition-transform overflow-hidden ${viewMode === 'list' ? 'flex flex-row' : 'flex flex-col'}`;
        el.onclick = () => openDetail(item);
        
        // Rasm o'rniga rangli icon
        const iconHtml = `
            <div class="bg-gray-100 flex items-center justify-center text-gray-300 ${viewMode === 'list' ? 'w-24 h-full' : 'h-28 w-full'}">
                <i class="fas fa-layer-group text-3xl"></i>
            </div>
        `;

        // Matn qismi
        const contentHtml = `
            <div class="p-3 flex-1 flex flex-col justify-between">
                <div>
                    <span class="text-[10px] text-blue-500 font-bold uppercase tracking-wider bg-blue-50 px-1 rounded">${item.category}</span>
                    <h3 class="font-bold text-sm text-gray-800 leading-tight mt-1 line-clamp-2">${item.material}</h3>
                </div>
                <div class="mt-2">
                        <div class="font-extrabold text-lg text-gray-900">${item.width} <span class="text-xs text-gray-400 font-normal">x</span> ${item.height}</div>
                        <div class="flex justify-between items-end mt-1">
                        <span class="text-xs text-gray-500">${item.qty} dona</span>
                        ${item.location ? '<i class="fas fa-map-marker-alt text-xs text-gray-400"></i>' : ''}
                        </div>
                </div>
            </div>
        `;

        el.innerHTML = iconHtml + contentHtml;
        container.appendChild(el);
    });
}

// --- ACTIONS ---
function filterCat(btn, cat) {
    document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
    if(btn) btn.classList.add('active');
    
    if (cat === 'all') {
        renderGrid(itemsData, 'remnantsList');
    } else {
        const filtered = itemsData.filter(i => i.category === cat);
        renderGrid(filtered, 'remnantsList');
    }
}

function filterItems() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const filtered = itemsData.filter(i => 
        i.material.toLowerCase().includes(query) || 
        i.category.toLowerCase().includes(query) ||
        (i.origin_order && i.origin_order.toLowerCase().includes(query))
    );
    renderGrid(filtered, 'remnantsList');
}

function toggleView() {
    viewMode = viewMode === 'grid' ? 'list' : 'grid';
    document.getElementById('viewIcon').className = viewMode === 'grid' ? 'fas fa-th-large text-xl' : 'fas fa-list text-xl';
    renderGrid(itemsData, 'remnantsList');
}

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active', 'text-blue-600'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.add('text-gray-400'));
    
    document.getElementById(`nav-${tab}`).classList.add('active', 'text-blue-600');
    document.getElementById(`nav-${tab}`).classList.remove('text-gray-400');

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
    document.getElementById('ptab-mine').className = ptab === 'mine' ? 'flex-1 py-2 text-sm font-bold rounded-lg bg-gray-100 text-gray-800' : 'flex-1 py-2 text-sm font-bold rounded-lg text-gray-500';
    document.getElementById('ptab-used').className = ptab === 'used' ? 'flex-1 py-2 text-sm font-bold rounded-lg bg-gray-100 text-gray-800' : 'flex-1 py-2 text-sm font-bold rounded-lg text-gray-500';
    fetchData(ptab);
}

// --- DETAILS & ADMIN ---
function openDetail(item) {
    selectedItem = item;
    document.getElementById('d-material').innerText = item.material;
    document.getElementById('d-cat').innerText = item.category;
    document.getElementById('d-size').innerText = `${item.width} x ${item.height}`;
    document.getElementById('d-qty').innerText = `${item.qty} ta`;
    document.getElementById('d-order').innerText = item.origin_order || '-';
    document.getElementById('d-location').innerText = item.location || '-';
    
    // Admin buttons
    if (isAdmin || item.user_id == userId) {
        document.getElementById('adminActions').classList.remove('hidden');
    } else {
        document.getElementById('adminActions').classList.add('hidden');
    }
    
    document.getElementById('detailModal').classList.remove('hidden');
}

async function useItem() {
    if(!confirm("Ishlatishni tasdiqlaysizmi?")) return;
    await fetch('/api/use', {
        method: 'POST',
        body: JSON.stringify({id: selectedItem.id, user_id: userId})
    });
    closeModal('detailModal');
    tg.HapticFeedback.notificationOccurred('success');
    fetchData();
}

// --- ADD / EDIT ---
function editItem() {
    closeModal('detailModal');
    // Formani to'ldirish
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
    if(!confirm("O'chirib yuborilsinmi?")) return;
    await fetch('/api/delete', { method: 'POST', body: JSON.stringify({id: selectedItem.id}) });
    closeModal('detailModal');
    fetchData();
}

async function submitAdd(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    data.user_id = userId;
    
    // Agar ID bor bo'lsa -> Edit, bo'lmasa -> Add
    const url = data.id ? '/api/edit' : '/api/add';
    
    await fetch(url, { method: 'POST', body: JSON.stringify(data) });
    
    e.target.reset();
    document.getElementById('editId').value = ''; 
    document.getElementById('btnSave').innerText = "Saqlash";
    
    closeModal('addModal');
    tg.HapticFeedback.notificationOccurred('success');
    fetchData();
}

function openModal(id) { 
    if(id==='addModal') { 
        document.getElementById('addForm').reset(); 
        document.getElementById('editId').value = '';
        document.getElementById('btnSave').innerText = "Saqlash";
    }
    document.getElementById(id).classList.remove('hidden'); 
}
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
