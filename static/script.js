function renderGrid(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (viewMode === 'grid') {
        container.className = 'grid grid-cols-2 gap-3 pb-24';
    } else {
        container.className = 'flex flex-col gap-3 pb-24';
    }

    data.forEach(item => {
        const el = document.createElement('div');
        el.className = `card p-0 relative active:scale-95 transition-transform overflow-hidden ${viewMode === 'list' ? 'flex flex-row h-24' : 'flex flex-col'}`;
        el.onclick = () => openDetail(item);
        
        const opacity = item.status === 0 ? 'opacity-60 grayscale' : '';
        const colors = ['bg-blue-50', 'bg-green-50', 'bg-orange-50', 'bg-purple-50'];
        const rndColor = colors[item.id % colors.length];

        el.innerHTML = `
            <div class="${rndColor} flex items-center justify-center ${viewMode === 'list' ? 'w-24 h-full' : 'h-32 w-full'} ${opacity}">
                <i class="fas fa-layer-group text-3xl text-gray-400"></i>
            </div>
            <div class="p-3 flex-1 flex flex-col justify-between ${opacity}">
                <div>
                    <span class="text-[10px] text-blue-600 font-bold uppercase tracking-wider bg-blue-50 px-1 rounded">${item.category || 'MDF'}</span>
                    <h3 class="font-bold text-sm text-gray-800 leading-tight mt-1 line-clamp-2">${item.material || 'Nomsiz'}</h3>
                </div>
                <div class="mt-2">
                     <div class="font-extrabold text-lg text-gray-900">
                        ${item.width || 0} <span class="text-xs text-gray-400 font-normal">x</span> ${item.height || 0}
                     </div>
                     <div class="flex justify-between items-end mt-1">
                        <span class="text-xs text-gray-500 font-bold">${item.qty || 0} dona</span>
                        ${item.location ? `<span class="text-[10px] text-gray-400 truncate max-w-[70px]"><i class="fas fa-map-marker-alt"></i> ${item.location}</span>` : ''}
                     </div>
                </div>
            </div>
        `;
        container.appendChild(el);
    });
}
