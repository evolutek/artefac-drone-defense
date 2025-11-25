const API = 'http://localhost:8001';

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Warehouses
function isInFrance(lat, lon) {
  return lat >= 41.0 && lat <= 51.5 && lon >= -5.5 && lon <= 9.5;
}

async function loadWarehouses() {
  const listEl = document.getElementById('warehouse-list');
  listEl.innerHTML = '';
  const items = await fetchJSON(`${API}/warehouses`);
  const frOnly = document.getElementById('warehouse-filter-fr')?.checked;
  const renderItems = frOnly ? items.filter(w => isInFrance(w.latitude, w.longitude)) : items;
  const container = document.createElement('div');
  container.className = 'list';
  for (const w of renderItems) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<div><strong>${w.name}</strong></div>
      <div class="muted">Lat/Lon: ${w.latitude.toFixed(5)}, ${w.longitude.toFixed(5)}</div>
      <div class="row"><button data-id="${w.id}" class="btn btn primary btn-inventory">Voir inventaire</button></div>`;
    container.appendChild(card);
  }
  listEl.appendChild(container);

  // populate inventory form warehouse select
  const sel = document.querySelector('#inventory-form select[name="warehouse_id"]');
  sel.innerHTML = renderItems.map(w => `<option value="${w.id}">${w.name}</option>`).join('');
}

document.getElementById('warehouse-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  payload.latitude = parseFloat(payload.latitude);
  payload.longitude = parseFloat(payload.longitude);
  if (payload.capacity) payload.capacity = parseInt(payload.capacity, 10);
  try {
    await fetchJSON(`${API}/warehouses`, { method: 'POST', body: JSON.stringify(payload) });
    e.target.reset();
    await loadWarehouses();
  } catch (err) { alert(err.message); }
});

// Products
async function loadProducts() {
  const listEl = document.getElementById('product-list');
  listEl.innerHTML = '';
  const items = await fetchJSON(`${API}/products`);
  function svgCardFor(p) {
    const name = (p.name || 'Produit').trim();
    const category = (p.category || 'produit').toLowerCase();
    const colorMap = {
      'munitions': '#F97316',
      'attachments': '#22C55E',
      'medicaments': '#EF4444',
      'communication': '#0EA5E9',
      'logistique': '#8B5CF6',
    };
    const base = colorMap[category] || '#64748B';
    const svg = `
<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0' stop-color='${base}' stop-opacity='0.9'/>
      <stop offset='1' stop-color='#111827' stop-opacity='0.9'/>
    </linearGradient>
  </defs>
  <rect x='0' y='0' width='512' height='512' fill='url(#g)'/>
  <rect x='24' y='24' width='464' height='464' rx='28' ry='28' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.2)'/>
  <text x='256' y='256' font-size='36' fill='#FFFFFF' text-anchor='middle' font-family='Inter, system-ui, sans-serif'>${name}</text>
  <text x='256' y='300' font-size='16' fill='rgba(255,255,255,0.75)' text-anchor='middle' font-family='Inter, system-ui, sans-serif'>${category || 'produit'}</text>
</svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }
  function productImageFor(p) {
    const u = p.image_url ? String(p.image_url) : '';
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    if (u.startsWith('/product-placeholder/')) return `${API}${u}`; // served by backend
    // Legacy numeric-only values or numeric .svg should resolve to backend placeholder
    if (/^\d+$/.test(u)) return `${API}/product-placeholder/${p.id}.svg`;
    if (/^\d+\.svg$/.test(u)) return `${API}/product-placeholder/${p.id}.svg`;
    // Absolute local asset path
    // Old absolute local asset path under /products -> rewrite to /product-icons
    if (u.startsWith('/products/')) {
      const tail = u.split('/').pop() || '';
      if (/^\d+$/.test(tail)) return `${API}/product-placeholder/${p.id}.svg`;
      return u.replace('/products/', '/product-icons/'); // served by backend static mount
    }
    // Relative file name under product-icons
    if (u.endsWith('.svg')) return `/product-icons/${u}`; // e.g., 'med-kit.svg'
    // No explicit image: try name-based mapping or dynamic SVG
    const name = (p.name || '').toLowerCase();
    const rules = [
      { kw: ['mre', 'ration'], file: 'food-mre-box.svg' },
      { kw: ['eau', 'water', 'pack'], file: 'water-pack-6x1.5l.svg' },
      { kw: ['jerrican', 'carburant', 'fuel'], file: 'fuel-jerrycan-20l.svg' },
      { kw: ['hygi'], file: 'hygiene-kit.svg' },
      { kw: ['secours', 'médical', 'medical'], file: 'med-kit.svg' },
      { kw: ['batterie', 'énergie', 'energie', 'power'], file: 'power-pack.svg' },
      { kw: ['caméra', 'camera', 'optique', 'viseur'], file: 'optic-x.svg' },
      { kw: ['radio', 'gps', 'communication'], file: 'radio-secure.svg' },
      { kw: ['hélice'], file: 'propeller-reinforced.svg' },
      { kw: ['moteur'], file: 'motor-brushless.svg' },
      { kw: ['esc'], file: 'esc-30a.svg' },
      { kw: ['vis', 'visserie'], file: 'screw-kit.svg' },
      { kw: ['extincteur', 'co2'], file: 'extinguisher-co2-2kg.svg' },
      { kw: ['extincteur', 'poudre'], file: 'extinguisher-powder-6kg.svg' },
      { kw: ['aérosol', 'aerosol'], file: 'extinguisher-aerosol-1l.svg' },
    ];
    for (const r of rules) {
      if (r.kw.every(k => name.includes(k))) return `/product-icons/${r.file}`;
    }
    return svgCardFor(p);
  }
  const container = document.createElement('div');
  container.className = 'list';
  for (const p of items) {
    const card = document.createElement('div');
    card.className = 'card product-card';
    const img = productImageFor(p);
    card.innerHTML = `
      ${img ? `<img class="product-image" src="${img}" alt="${p.name}" style="background-color:rgba(0,0,0,0.25)" />` : `<img class="product-image" src="${svgCardFor(p)}" alt="${p.name}" style="background-color:rgba(0,0,0,0.25)" />`}
      <div style="flex:1;">
        <div class="product-title">${p.name}</div>
        <div class="muted">${p.category ?? ''} · ${p.weight_kg ?? '-'} kg</div>
      </div>
      <div style="margin-left:auto">
        <button class="btn danger btn-delete-product" data-id="${p.id}">Supprimer</button>
      </div>
    `;
    // Robust onError fallback to dynamic SVG with product name
    const imgEl = card.querySelector('img.product-image');
    if (imgEl) {
      imgEl.addEventListener('error', () => {
        imgEl.src = svgCardFor(p);
      });
    }
    container.appendChild(card);
  }
  listEl.appendChild(container);

  // populate inventory form product select
  const sel = document.querySelector('#inventory-form select[name="product_id"]');
  sel.innerHTML = items.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

  // Bind delete buttons
  listEl.querySelectorAll('.btn-delete-product').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(e.target.getAttribute('data-id'), 10);
      if (!id) return;
      const ok = confirm('Supprimer ce produit ? Cette action est définitive.');
      if (!ok) return;
      try {
        await fetchJSON(`${API}/products/${id}`, { method: 'DELETE' });
        await loadProducts();
        await loadInventoryView();
      } catch (err) { alert(err.message); }
    });
  });
}

document.getElementById('product-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  if (payload.weight_kg) payload.weight_kg = parseFloat(payload.weight_kg);
  try {
    await fetchJSON(`${API}/products`, { method: 'POST', body: JSON.stringify(payload) });
    e.target.reset();
    await loadProducts();
  } catch (err) { alert(err.message); }
});

// Inventory
async function loadInventoryView() {
  const sel = document.querySelector('#inventory-form select[name="warehouse_id"]');
  const warehouseId = sel.value;
  const view = document.getElementById('inventory-view');
  view.innerHTML = '';
  if (!warehouseId) return;
  const items = await fetchJSON(`${API}/warehouses/${warehouseId}/inventory`);
  const container = document.createElement('div');
  container.className = 'list';
  for (const it of items) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<div><strong>${it.product.name}</strong> <span class="muted">x ${it.quantity}</span></div>`;
    container.appendChild(card);
  }
  view.appendChild(container);
}

document.getElementById('inventory-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  payload.quantity = parseInt(payload.quantity, 10);
  try {
    await fetchJSON(`${API}/warehouses/${payload.warehouse_id}/inventory`, { method: 'POST', body: JSON.stringify({ product_id: parseInt(payload.product_id, 10), quantity: payload.quantity }) });
    await loadInventoryView();
  } catch (err) { alert(err.message); }
});

document.querySelector('#inventory-form select[name="warehouse_id"]').addEventListener('change', loadInventoryView);

// Drones
async function loadDrones() {
  const listEl = document.getElementById('drone-list');
  listEl.innerHTML = '';
  const items = await fetchJSON(`${API}/drones`);
  const container = document.createElement('div');
  container.className = 'list';
  for (const d of items) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<div><strong>${d.drone_id}</strong> <span class="muted">${d.model ?? ''}</span></div>
      <div class="muted">Nom: ${d.name ?? '-'}</div>`;
    container.appendChild(card);
  }
  listEl.appendChild(container);
}

document.getElementById('drone-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  try {
    await fetchJSON(`${API}/drones`, { method: 'POST', body: JSON.stringify(payload) });
    e.target.reset();
    await loadDrones();
  } catch (err) { alert(err.message); }
});

// Initial load
(async function init() {
  try {
    await loadWarehouses();
    await loadProducts();
    await loadDrones();
    await loadInventoryView();
  } catch (err) {
    console.error(err);
  }
})();

// Seed demo products
async function seedProducts() {
  const btn = document.getElementById('seed-products');
  if (btn) { btn.disabled = true; btn.textContent = 'Ajout…'; }
  const demo = [
    { name: 'Ration MRE Lot x12', description: 'Rations de campagne', category: 'logistique', weight_kg: 9.6 },
    { name: 'Pack Eau 6x1.5L', description: 'Eau potable en pack', category: 'logistique', weight_kg: 9.0 },
    { name: 'Jerrican Carburant 20L', description: 'Carburant pour équipements', category: 'logistique', weight_kg: 16.0 },
    { name: 'Kit Hygiène', description: 'Hygiène personnelle de base', category: 'logistique', weight_kg: 2.0 },
    { name: 'Kit Médical', description: 'Premiers secours', category: 'medicaments', weight_kg: 3.5 },
    { name: 'Batterie LiPo 4S 5000mAh', description: 'Alimentation drone', category: 'attachments', weight_kg: 0.45 },
    { name: 'Caméra HD Stabilisée', description: 'Observation stabilisée', category: 'communication', weight_kg: 0.32 },
    { name: 'Radio Secure VHF', description: 'Communication sécurisée', category: 'communication', weight_kg: 0.58 },
    { name: 'Hélice Renforcée 10"', description: 'Hélice composite', category: 'attachments', weight_kg: 0.12 },
    { name: 'Moteur Brushless 2207', description: 'Propulsion drone', category: 'attachments', weight_kg: 0.09 },
    { name: 'ESC 30A', description: 'Contrôleur moteur', category: 'attachments', weight_kg: 0.06 },
    { name: 'Kit Visserie Inox', description: 'Assortiment de vis', category: 'attachments', weight_kg: 0.4 },
    { name: 'Extincteur CO2 2kg', description: 'Sécurité incendie', category: 'logistique', weight_kg: 2.0 },
    { name: 'Extincteur Poudre 6kg', description: 'Sécurité incendie', category: 'logistique', weight_kg: 6.0 },
    { name: 'Aérosol Extincteur 1L', description: 'Sécurité incendie', category: 'logistique', weight_kg: 1.0 },
  ];
  let created = 0, skipped = 0, failed = 0;
  for (const p of demo) {
    try {
      await fetchJSON(`${API}/products`, { method: 'POST', body: JSON.stringify(p) });
      created++;
    } catch (err) {
      if (String(err.message || '').toLowerCase().includes('already exists')) skipped++;
      else failed++;
    }
  }
  try { await loadProducts(); } catch {}
  if (btn) { btn.disabled = false; btn.textContent = 'Ajouter articles de test'; }
  alert(`Ajout terminé: ${created} créés, ${skipped} existants, ${failed} erreurs.`);
}

document.getElementById('seed-products')?.addEventListener('click', seedProducts);

// Real-time updates via WebSocket
function connectRealtime() {
  try {
    const ws = new WebSocket('ws://localhost:8001/ws/telemetry');
    ws.onopen = () => console.log('[RT] connecté');
    ws.onmessage = async (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'state') {
          const t = msg.data?.type;
          if (t === 'warehouse_upsert') {
            await loadWarehouses();
          } else if (t === 'product_upsert') {
            await loadProducts();
          } else if (t === 'product_delete') {
            await loadProducts();
            await loadInventoryView();
          } else if (t === 'inventory_update') {
            // Refresh inventory view if current warehouse matches
            await loadInventoryView();
      } else if (t === 'drone_upsert') {
        await loadDrones();
      } else if (t === 'mission_upsert' || t === 'mission_status_update' || t === 'mission_note_update') {
        const current = document.getElementById('mission-status-filter').value;
        await loadMissions(current);
      }
        }
      } catch (e) {
        console.warn('[RT] message invalide', e);
      }
    };
    ws.onerror = (e) => console.warn('[RT] erreur', e);
    ws.onclose = () => {
      console.warn('[RT] déconnecté, reconnexion dans 3s...');
      setTimeout(connectRealtime, 3000);
    };
  } catch (e) {
    console.warn('[RT] WebSocket indisponible', e);
  }
}

connectRealtime();

// Reload warehouses list when FR filter toggled
document.getElementById('warehouse-filter-fr')?.addEventListener('change', async () => {
  await loadWarehouses();
});

// Missions (Suivi des livraisons)
async function loadMissions(filter = '') {
  const listEl = document.getElementById('mission-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  const url = new URL(`${API}/missions`);
  if (filter) url.searchParams.set('status', filter);
  const items = await fetchJSON(url.toString());
  const container = document.createElement('div');
  container.className = 'list';
  for (const m of items) {
    const card = document.createElement('div');
    card.className = 'card';
    const waypoints = (() => {
      try { const arr = JSON.parse(m.waypoints ?? '[]'); return Array.isArray(arr) ? arr : []; } catch { return []; }
    })();
    const payloadOne = (() => {
      try { return m.payload ? JSON.parse(m.payload) : null; } catch { return null; }
    })();
    const payloadMany = (() => {
      try { const arr = m.payloads ? JSON.parse(m.payloads) : null; return Array.isArray(arr) ? arr : null; } catch { return null; }
    })();
    const statusSelectId = `mission-status-${m.id}`;
    const noteInputId = `mission-note-${m.id}`;
    const statusPct = (s) => ({
      'pending': 10,
      'assigned': 25,
      'in_progress': 70,
      'blocked': 50,
      'completed': 100,
      'failed': 0,
    }[s] ?? 0);
    card.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px;">
        <div><strong>#${m.id}</strong> • ${m.drone_id}</div>
        <div style="margin-left:auto" class="muted">WP: ${waypoints.length}</div>
      </div>
      <div class="progress" style="margin-top:6px"><div class="progress-bar" style="width:${statusPct(m.status)}%"></div></div>
      ${payloadMany ? `
        <div class="muted" style="margin-top:6px">Commande: ${payloadMany.map(p => `${p.item_name} x${p.quantity}`).join(', ')}</div>
      ` : payloadOne ? `
        <div class="muted" style="margin-top:6px">Commande: ${payloadOne.item_name} x${payloadOne.quantity} (${payloadOne.weight_kg}kg)</div>
      ` : ''}
      <div class="row" style="margin-top:8px;">
        <label style="flex:1;">Note opérateur
          <input type="text" id="${noteInputId}" placeholder="Ajouter une note" value="${m.note ?? ''}" />
        </label>
        <button data-id="${m.id}" class="btn btn primary btn-update-note">Enregistrer note</button>
      </div>
      <div class="row" style="margin-top:8px;">
        <label>État
          <select id="${statusSelectId}">
            <option value="pending" ${m.status === 'pending' ? 'selected' : ''}>Préparation</option>
            <option value="assigned" ${m.status === 'assigned' ? 'selected' : ''}>Assignée</option>
            <option value="in_progress" ${m.status === 'in_progress' ? 'selected' : ''}>En vol</option>
            <option value="blocked" ${m.status === 'blocked' ? 'selected' : ''}>Bloqué</option>
            <option value="completed" ${m.status === 'completed' ? 'selected' : ''}>Livré</option>
            <option value="failed" ${m.status === 'failed' ? 'selected' : ''}>Annulé</option>
          </select>
        </label>
        <button data-id="${m.id}" class="btn btn primary btn-update-status">Mettre à jour</button>
      </div>
    `;
    container.appendChild(card);
  }
  listEl.appendChild(container);

  // Bind update buttons
  listEl.querySelectorAll('.btn-update-status').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(e.target.getAttribute('data-id'), 10);
      const sel = document.getElementById(`mission-status-${id}`);
      const status = sel.value;
      try {
        const key = (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : `k-${Date.now()}-${id}-${Math.random().toString(16).slice(2)}`;
        await fetchJSON(`${API}/missions/${id}/status?status=${encodeURIComponent(status)}`, { method: 'PUT', headers: { 'X-Idempotency-Key': key } });
        // Reload list preserving filter
        const current = document.getElementById('mission-status-filter').value;
        await loadMissions(current);
      } catch (err) { alert(err.message); }
    });
  });

  // Bind note update buttons
  listEl.querySelectorAll('.btn-update-note').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(e.target.getAttribute('data-id'), 10);
      const input = document.getElementById(`mission-note-${id}`);
      const note = input.value || '';
      try {
        await fetchJSON(`${API}/missions/${id}/note?note=${encodeURIComponent(note)}`, { method: 'PUT' });
        const current = document.getElementById('mission-status-filter').value;
        await loadMissions(current);
      } catch (err) { alert(err.message); }
    });
  });
}

document.getElementById('mission-refresh')?.addEventListener('click', async () => {
  const filter = document.getElementById('mission-status-filter').value;
  await loadMissions(filter);
});

document.getElementById('mission-status-filter')?.addEventListener('change', async (e) => {
  const filter = e.target.value;
  await loadMissions(filter);
});

// Load missions once on boot
(async function initMissions() {
  try { await loadMissions(''); } catch (err) { console.error(err); }
})();
