const API = 'http://localhost:8001';

// Simple PIN login (aligné sur le client carto)
let authenticated = (() => {
  try { return localStorage.getItem('session_auth') === '1'; } catch { return false; }
})();
let pin = '';
const DEFAULT_PIN = '123123123';
const PIN_LENGTH = DEFAULT_PIN.length;
let wrongAttempts = (() => {
  try { return parseInt(localStorage.getItem('pin_fail_count') || '0'); } catch { return 0; }
})();
let locked = wrongAttempts >= 3;

function handleAccess() {
  if (pin === DEFAULT_PIN) {
    authenticated = true;
    try { localStorage.setItem('session_auth', '1'); } catch {}
    pin = '';
    wrongAttempts = 0;
    try { localStorage.setItem('pin_fail_count', '0'); } catch {}
    const ov = document.getElementById('login-overlay');
    if (ov) ov.remove();
    const loginEl = document.getElementById('login');
    if (loginEl) loginEl.style.display = 'none';
    destroyLoginGlobe();
    init();
    return;
  }
  const next = wrongAttempts + 1;
  wrongAttempts = next;
  try { localStorage.setItem('pin_fail_count', String(next)); } catch {}
  const errEl = document.getElementById('pin-error');
  if (errEl) errEl.textContent = `PIN incorrect — tentative ${next}/3`;
  const errEl2 = document.getElementById('login-pin-error');
  if (errEl2) errEl2.textContent = `PIN incorrect — tentative ${next}/3`;
  if (next >= 3) {
    locked = true;
    const box = document.getElementById('login-box');
    if (box) {
      box.innerHTML = `<div style="text-align:center; font-weight:600;">Verrouillé — réessayez plus tard</div>`;
    }
    const card = document.getElementById('login-card');
    if (card) {
      card.innerHTML = `<div style="text-align:center; font-weight:600;">Verrouillé — réessayez plus tard</div>`;
    }
  }
}

function renderLogin() {
  if (document.getElementById('login-overlay')) return;
  const overlay = document.createElement('div');
  overlay.id = 'login-overlay';
  overlay.style.position = 'fixed';
  overlay.style.inset = '0';
  overlay.style.zIndex = '3000';
  overlay.style.background = 'rgba(0,0,0,0.35)';
  const box = document.createElement('div');
  box.id = 'login-box';
  box.style.position = 'absolute';
  box.style.left = '50%';
  box.style.top = '50%';
  box.style.transform = 'translate(-50%, -50%)';
  box.style.width = 'min(360px, 92vw)';
  box.style.background = 'rgba(12,16,22,0.85)';
  box.style.border = '1px solid var(--border)';
  box.style.borderRadius = '12px';
  box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.25)';
  box.style.backdropFilter = 'saturate(180%) blur(8px)';
  box.style.padding = '16px';
  box.innerHTML = `
    <div style="text-align: center; font-weight: 600; margin-bottom: 6px">Entrer le PIN</div>
    <input
      id="pin-input"
      type="password"
      inputmode="numeric"
      pattern="[0-9]*"
      maxlength="${PIN_LENGTH}"
      class="input"
      placeholder="${'•'.repeat(PIN_LENGTH)}"
      style="display:block; margin:0 auto; width:min(260px, 100%); text-align:center; font-size:24px; letter-spacing:6px; color:#fff; border:1px solid var(--border)"
      aria-label="PIN agent"
    />
    <div id="pin-error" style="color:#f44336; text-align:center; margin-top:8px; font-size:13px"></div>
    <div style="display:flex; margin-top:12px">
      <button type="button" class="btn" style="margin-left:auto" id="btn-access">Accéder</button>
    </div>
  `;
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  const inp = document.getElementById('pin-input');
  const btn = document.getElementById('btn-access');
  if (inp) {
    inp.addEventListener('input', (e) => {
      const v = String(e.target.value || '');
      pin = v.replace(/[^0-9]/g, '').slice(0, PIN_LENGTH);
      e.target.value = pin;
    });
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleAccess(); });
    inp.focus();
  }
  if (btn) btn.addEventListener('click', () => handleAccess());
}

let sections = ['login','warehouses','products','inventory','stocks','drones','missions'];

function forceLogin() {
  authenticated = false;
  try { localStorage.setItem('session_auth', '0'); } catch {}
  window.location.href = './login.html';
}

let loginGlobeInit = false;
let loginGlobeRenderer = null;
let loginGlobeScene = null;
let loginGlobeCamera = null;
let loginGlobeSphere = null;
let loginGlobeAnimId = null;

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Criticité automatique par catégorie (sans configuration manuelle)
function severityFor(qty, product, warehouse) {
  const cat = String(product?.category || '').toLowerCase();
  const thresholds = {
    'medicaments': { low: 10, medium: 20 },
    'communication': { low: 8, medium: 16 },
    'attachments': { low: 6, medium: 12 },
    'logistique': { low: 8, medium: 16 },
    'munitions': { low: 20, medium: 40 },
    'default': { low: 5, medium: 12 },
  };
  const t = thresholds[cat] || thresholds['default'];
  if (qty <= t.low) return 2; // bas
  if (qty <= t.medium) return 1; // moyen
  return 0;
}

// Couleur par niveau
function severityColor(sev) {
  return sev === 2 ? '#e53935' : sev === 1 ? '#ffca28' : 'var(--border)';
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
    card.className = 'card warehouse-card';
    const status = (w.status || '').trim().toLowerCase();
    const note = w.note || '';
    let mgrsStr = '';
    try {
      if (typeof window.mgrs !== 'undefined' && window.mgrs && typeof window.mgrs.forward === 'function') {
        mgrsStr = window.mgrs.forward([Number(w.longitude), Number(w.latitude)]);
      }
    } catch {}
    card.innerHTML = `
      <div style="display:flex; align-items:flex-start; gap:8px;">
        <div class="warehouse-title"><strong>${w.name}</strong></div>
        <div class="muted" style="margin-left:auto">Lat/Lon: ${Number(w.latitude).toFixed(5)}, ${Number(w.longitude).toFixed(5)}</div>
        <button class="btn-delete-warehouse" data-id="${w.id}" title="Supprimer" aria-label="Supprimer" style="background:transparent; color:#e53935; border:none; font-weight:700; font-size:18px; cursor:pointer; line-height:1">×</button>
      </div>
      ${status ? `<div class="muted"> ${status}${note ? ` — ${note}` : ''}</div>` : ''}
      <div class="row" style="gap:8px;">
        <label class="muted">
          <select data-id="${w.id}" class="input warehouse-status">
            <option value="operational" ${status === 'operational' ? 'selected' : ''}>Opérationnel</option>
            <option value="maintenance" ${status === 'maintenance' ? 'selected' : ''}>Maintenance</option>
            <option value="inactive" ${status === 'inactive' ? 'selected' : ''}>Inactif</option>
            <option value="moving" ${status === 'moving' ? 'selected' : ''}>En déplacement</option>
          </select>
        </label>
        <input type="text" class="input warehouse-note" data-id="${w.id}" placeholder="Message (si déplacement)" value="${note}" />
      </div>
      <div class="row" style="gap:8px;">
        <input type="number" step="any" class="input warehouse-lat" data-id="${w.id}" placeholder="Latitude (optionnel)" />
        <input type="number" step="any" class="input warehouse-lon" data-id="${w.id}" placeholder="Longitude (optionnel)" />
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start;">
        <div style="font-weight: 600;">Coordonnées — format MGRS</div>
        <div class="mgrs-grid" style="display: grid; grid-template-columns: 80px 80px 160px 1fr 1fr auto; gap: 8px; justify-items: start; align-items: start;">
          <label style="display: flex; flex-direction: column; gap: 4px;">Zone
            <select class="input input-sm warehouse-mgrs-zone" aria-label="Zone (menu)" data-id="${w.id}">
              <option value="" disabled selected>Choisir</option>
              ${Array.from({length: 60}, (_, i) => `<option value="${i+1}">${i+1}</option>`).join('')}
            </select>
          </label>
          <label style="display: flex; flex-direction: column; gap: 4px;">Bande
            <select class="input input-sm warehouse-mgrs-band" aria-label="Bande (menu)" data-id="${w.id}">
              <option value="" disabled selected>Choisir</option>
              ${['C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X'].map(l => `<option value="${l}">${l}</option>`).join('')}
            </select>
          </label>
          <label style="display: flex; flex-direction: column; gap: 4px;">Grille
            <input type="text" placeholder="YT" class="input input-sm warehouse-mgrs-grid" data-id="${w.id}" />
          </label>
          <label style="display: flex; flex-direction: column; gap: 4px;">Est (m)
            <input type="text" inputmode="numeric" placeholder="26398" class="input input-sm warehouse-mgrs-east" data-id="${w.id}" />
          </label>
          <label style="display: flex; flex-direction: column; gap: 4px;">Nord (m)
            <input type="text" inputmode="numeric" placeholder="28974" class="input input-sm warehouse-mgrs-north" data-id="${w.id}" />
          </label>
          <button data-id="${w.id}" class="btn btn primary btn-update-warehouse" style="justify-self:end; align-self:end;">Mettre à jour</button>
        </div>

      </div>
    `;
    container.appendChild(card);
  }
  listEl.appendChild(container);

  // populate inventory form warehouse select
  const sel = document.querySelector('#inventory-form select[name="warehouse_id"]');
  const prev = sel ? sel.value : '';
  // Toujours proposer tous les entrepôts dans le sélecteur d'inventaire (indépendant du filtre FR)
  sel.innerHTML = items.map(w => `<option value="${w.id}">${w.name}</option>`).join('');
  if (prev && Array.isArray(items) && items.some((w) => String(w.id) === String(prev))) {
    sel.value = prev;
  }
  if (!sel.value && items.length > 0) {
    sel.value = String(items[0].id);
  }
  try { await loadInventoryView(); } catch {}

  // Bind update warehouse buttons
  listEl.querySelectorAll('.btn-update-warehouse').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(e.target.getAttribute('data-id'), 10);
      if (!id) return;
      const statusSel = listEl.querySelector(`select.warehouse-status[data-id="${id}"]`);
      const noteInput = listEl.querySelector(`input.warehouse-note[data-id="${id}"]`);
      const latInput = listEl.querySelector(`input.warehouse-lat[data-id="${id}"]`);
      const lonInput = listEl.querySelector(`input.warehouse-lon[data-id="${id}"]`);
      const zoneSel = listEl.querySelector(`select.warehouse-mgrs-zone[data-id="${id}"]`);
      const bandSel = listEl.querySelector(`select.warehouse-mgrs-band[data-id="${id}"]`);
      const gridInput = listEl.querySelector(`input.warehouse-mgrs-grid[data-id="${id}"]`);
      const eastInput = listEl.querySelector(`input.warehouse-mgrs-east[data-id="${id}"]`);
      const northInput = listEl.querySelector(`input.warehouse-mgrs-north[data-id="${id}"]`);
      const payload = {};
      const statusVal = statusSel?.value || '';
      const noteVal = noteInput?.value || '';
      const latVal = latInput?.value || '';
      const lonVal = lonInput?.value || '';
      const zoneVal = zoneSel?.value || '';
      const bandVal = bandSel?.value || '';
      const gridVal = gridInput?.value || '';
      const eastVal = eastInput?.value || '';
      const northVal = northInput?.value || '';
      if (statusVal) payload.status = statusVal;
      if (statusVal === 'moving' && noteVal) payload.note = noteVal;
      // Prefer MGRS if provided, otherwise use lat/lon inputs
      if (zoneVal && bandVal && gridVal && eastVal && northVal && typeof window.mgrs !== 'undefined' && window.mgrs && typeof window.mgrs.toPoint === 'function') {
        try {
          const mgrsStr2 = `${zoneVal}${bandVal} ${gridVal.trim()} ${eastVal.trim()} ${northVal.trim()}`;
          const pt = window.mgrs.toPoint(mgrsStr2);
          if (Array.isArray(pt) && pt.length === 2) {
            payload.longitude = parseFloat(pt[0]);
            payload.latitude = parseFloat(pt[1]);
          }
        } catch {}
      } else {
        if (latVal !== '') payload.latitude = parseFloat(latVal);
        if (lonVal !== '') payload.longitude = parseFloat(lonVal);
      }
      try {
        await fetchJSON(`${API}/warehouses/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        await loadWarehouses();
      } catch (err) { alert(err.message); }
    });
  });

  listEl.querySelectorAll('.btn-delete-warehouse').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(e.target.getAttribute('data-id'), 10);
      if (!id) return;
      const ok = confirm(`Supprimer l'entrepôt #${id} ? Les stocks associés seront supprimés.`);
      if (!ok) return;
      try {
        await fetchJSON(`${API}/warehouses/${id}`, { method: 'DELETE' });
        await loadWarehouses();
        try { await loadInventoryView(); } catch {}
      } catch (err) { alert(err.message); }
    });
  });
}

document.getElementById('warehouse-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  payload.latitude = parseFloat(payload.latitude);
  payload.longitude = parseFloat(payload.longitude);
  // If MGRS components provided, compose and convert to lat/lon
  try {
    const zone = (payload.mgrs_zone || '').trim();
    const band = (payload.mgrs_band || '').trim();
    const grid = (payload.mgrs_grid || '').trim();
    const east = (payload.mgrs_east || '').trim();
    const north = (payload.mgrs_north || '').trim();
    if (zone && band && grid && east && north && typeof window.mgrs !== 'undefined' && window.mgrs && typeof window.mgrs.toPoint === 'function') {
      const mgrsStr = `${zone}${band} ${grid} ${east} ${north}`;
      const pt = window.mgrs.toPoint(mgrsStr);
      if (Array.isArray(pt) && pt.length === 2) {
        payload.longitude = parseFloat(pt[0]);
        payload.latitude = parseFloat(pt[1]);
      }
    }
  } catch {}
  if (payload.capacity) payload.capacity = parseInt(payload.capacity, 10);
  delete payload.mgrs_zone; delete payload.mgrs_band; delete payload.mgrs_grid; delete payload.mgrs_east; delete payload.mgrs_north;
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
      try {
        await fetchJSON(`${API}/products/${id}`, { method: 'DELETE' });
        await loadProducts();
        await loadInventoryView();
      } catch (err) { console.warn(err); }
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

const imageFileInput = document.querySelector('#product-form input[name="image_file"]');
const imageUrlInput = document.querySelector('#product-form input[name="image_url"]');
const previewBox = document.getElementById('product-image-preview');
const previewImg = document.getElementById('product-image-preview-img');
if (imageFileInput) {
  imageFileInput.addEventListener('change', () => {
    const f = imageFileInput.files && imageFileInput.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result || '');
      if (imageUrlInput) imageUrlInput.value = dataUrl;
      if (previewImg) previewImg.src = dataUrl;
      if (previewBox) previewBox.style.display = 'block';
    };
    reader.readAsDataURL(f);
  });
}

// Inventory
async function loadInventoryView() {
  const sel = document.querySelector('#inventory-form select[name="warehouse_id"]');
  const warehouseId = sel.value;
  const view = document.getElementById('inventory-view');
  view.innerHTML = '';
  if (!warehouseId) return;
  const items = await fetchJSON(`${API}/warehouses/${warehouseId}/inventory`);
  window.inventoryCache = items;
  renderInventoryView(items);
}

function renderInventoryView(items) {
  const view = document.getElementById('inventory-view');
  const filterInput = document.getElementById('inventory-filter');
  const term = String(filterInput?.value || '').trim().toLowerCase();
  const filtered = items.filter(it => {
    const n = String(it.product?.name || '').toLowerCase();
    const c = String(it.product?.category || '').toLowerCase();
    return !term || n.includes(term) || c.includes(term);
  }).sort((a,b) => String(a.product?.name||'').localeCompare(String(b.product?.name||'')));
  const container = document.createElement('div');
  container.className = 'list';
  let totalQty = 0;
  let totalWeight = 0;
  for (const it of filtered) {
    const p = it.product || {};
    const w = typeof p.weight_kg === 'number' ? p.weight_kg : null;
    const qty = parseInt(it.quantity, 10) || 0;
    totalQty += qty;
    if (w !== null) totalWeight += w * qty;
    const img = productImageFor(p);
    const card = document.createElement('div');
    card.className = 'card product-card';
    card.style.position = 'relative';
    card.style.paddingLeft = '28px';
    card.style.paddingRight = '28px';
    card.innerHTML = `
      <button class="btn btn-icon btn-inv-minus" data-pid="${p.id}" data-q="${qty}" title="Retirer" aria-label="Retirer"
        style="position:absolute; left:-14px; top:50%; transform:translateY(-50%); width:28px; height:28px; font-weight:700">−</button>
      ${img ? `<img class="product-image" src="${img}" alt="${p.name||''}" style="background-color:rgba(0,0,0,0.25)" />` : `<img class="product-image" src="${svgCardFor(p)}" alt="${p.name||''}" style="background-color:rgba(0,0,0,0.25)" />`}
      <div style="flex:1;">
        <div class="product-title">${p.name||''}</div>
        <div class="muted">${p.category||''}${w!==null?` · ${w} kg/unité`:''}</div>
      </div>
      <div style="margin-left:auto; text-align:right">
        <div style="font-weight:600">x ${qty}</div>
        ${w!==null?`<div class="muted">${(w*qty).toFixed(2)} kg</div>`:''}
      </div>
      <button class="btn btn-icon btn-inv-plus" data-pid="${p.id}" data-q="${qty}" title="Ajouter" aria-label="Ajouter"
        style="position:absolute; right:-14px; top:50%; transform:translateY(-50%); width:28px; height:28px; font-weight:700">+</button>
    `;
    const imgEl = card.querySelector('img.product-image');
    if (imgEl) {
      imgEl.addEventListener('error', () => { imgEl.src = svgCardFor(p); });
    }
    const minusBtn = card.querySelector('.btn-inv-minus');
    const plusBtn = card.querySelector('.btn-inv-plus');
    const selWh = document.querySelector('#inventory-form select[name="warehouse_id"]');
    const wid = selWh && selWh.value;
    if (minusBtn && wid) {
      minusBtn.addEventListener('click', async (e) => {
        e.preventDefault(); e.stopPropagation();
        const pid = parseInt(minusBtn.getAttribute('data-pid'), 10);
        const current = parseInt(minusBtn.getAttribute('data-q'), 10) || 0;
        const next = Math.max(0, current - 1);
        try {
          await fetchJSON(`${API}/warehouses/${wid}/inventory`, { method: 'POST', body: JSON.stringify({ product_id: pid, quantity: next }) });
          await loadInventoryView();
        } catch (err) { alert(err.message); }
      });
    }
    if (plusBtn && wid) {
      plusBtn.addEventListener('click', async (e) => {
        e.preventDefault(); e.stopPropagation();
        const pid = parseInt(plusBtn.getAttribute('data-pid'), 10);
        const current = parseInt(plusBtn.getAttribute('data-q'), 10) || 0;
        const next = current + 1;
        try {
          await fetchJSON(`${API}/warehouses/${wid}/inventory`, { method: 'POST', body: JSON.stringify({ product_id: pid, quantity: next }) });
          await loadInventoryView();
        } catch (err) { alert(err.message); }
      });
    }
    container.appendChild(card);
  }
  view.innerHTML = '';
  view.appendChild(container);
  const summaryEl = document.getElementById('inventory-summary');
  if (summaryEl) {
    const lines = filtered.length;
    summaryEl.textContent = `${lines} lignes · ${totalQty} unités${totalWeight?` · ${totalWeight.toFixed(2)} kg`:''}`;
  }
}

const inventoryFilterEl = document.getElementById('inventory-filter');
if (inventoryFilterEl) {
  inventoryFilterEl.addEventListener('input', () => {
    const items = window.inventoryCache || [];
    renderInventoryView(items);
  });
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
      <div class="muted"> ${d.name ?? '-'}</div>`;
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
    if (!authenticated) { window.location.href = './login.html'; return; }
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

// Simple tabs routing: show one section at a time
function showSection(id) {
  if (!authenticated && id !== 'login') id = 'login';
  sections.forEach((s) => {
    const el = document.getElementById(s);
    if (!el) return;
    el.style.display = (s === id) ? 'block' : 'none';
  });
}
document.querySelectorAll('button[data-nav]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const id = btn.getAttribute('data-nav');
    if (sections.includes(id)) showSection(id);
  });
});
const logo = document.querySelector('header .logo');
if (logo) {
  logo.style.cursor = 'pointer';
  logo.addEventListener('click', () => { forceLogin(); });
}
// Default section: warehouses
showSection('warehouses');

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
    function statusColor(s) {
      if (!s) return '#b0b0b8';
      const k = String(s).trim().toLowerCase().replace(/[_-]+/g, ' ');
      const colors = {
        'assigned': '#64b5f6',
        'en cours': '#ffca28',
        'in progress': '#ffca28',
        'en route': '#4fc3f7',
        'in transit': '#4fc3f7',
        'completed': '#4caf50',
        'delivered': '#4caf50',
        'livré': '#4caf50',
        'cancelled': '#e57373',
        'canceled': '#e57373',
        'failed': '#f44336',
        'error': '#e53935',
        'queued': '#90a4ae',
        'scheduled': '#9575cd',
        'pending': '#ff9800',
        'en attente': '#ff9800',
        'mission': '#ff7043',
        'returning': '#29b6f6',
        'armed': '#81c784',
        'idle': '#9e9e9e',
        'blocked': '#f44336',
      };
      return colors[k] || '#b0b0b8';
    }
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
        <label style="flex:2;">
          <textarea id="${noteInputId}" placeholder="Ajouter une note" rows="3">${m.note ?? ''}</textarea>
        </label>
      </div>
      <div class="row" style="margin-top:8px;">
        <button data-id="${m.id}" class="btn btn primary btn-update-note" style="margin-left:auto">Enregistrer note</button>
      </div>
      <div class="row" style="margin-top:8px;">
        <label>
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
    try {
      const bc = statusColor(m.status);
      card.style.border = `2px solid ${bc}`;
    } catch {}
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
function initLoginGlobe() {
  if (loginGlobeInit) return;
  const canvas = document.getElementById('login-globe');
  if (!canvas || typeof THREE === 'undefined') return;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(w, h, false);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0f14);
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
  camera.position.set(0, 0, 3.2);
  const ambient = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(ambient);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(3, 2, 2);
  scene.add(dir);
  const geom = new THREE.SphereGeometry(1, 64, 64);
  const mat = new THREE.MeshStandardMaterial({ color: 0x1f3a68, roughness: 0.65, metalness: 0.05 });
  const sphere = new THREE.Mesh(geom, mat);
  scene.add(sphere);
  function onResize() {
    const ww = canvas.clientWidth;
    const hh = canvas.clientHeight;
    renderer.setSize(ww, hh, false);
    camera.aspect = ww / hh;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', onResize, { passive: true });
  function animate() {
    sphere.rotation.y += 0.0025;
    renderer.render(scene, camera);
    loginGlobeAnimId = requestAnimationFrame(animate);
  }
  animate();
  loginGlobeInit = true;
  loginGlobeRenderer = renderer;
  loginGlobeScene = scene;
  loginGlobeCamera = camera;
  loginGlobeSphere = sphere;
}
function destroyLoginGlobe() {
  if (!loginGlobeInit) return;
  try { cancelAnimationFrame(loginGlobeAnimId); } catch {}
  try { loginGlobeRenderer.dispose(); } catch {}
  loginGlobeInit = false; loginGlobeRenderer = null; loginGlobeScene = null; loginGlobeCamera = null; loginGlobeSphere = null; loginGlobeAnimId = null;
}
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
  if (u.startsWith('data:image/')) return u;
  if (u.startsWith('/product-placeholder/')) return `${API}${u}`;
  if (u.startsWith('/product-icons/')) return `${API}${u}`;
  if (/^\d+$/.test(u)) return `${API}/product-placeholder/${p.id}.svg`;
  if (/^\d+\.svg$/.test(u)) return `${API}/product-placeholder/${p.id}.svg`;
  if (u.startsWith('/products/')) {
    const tail = u.split('/').pop() || '';
    const m = tail.match(/^(\d+)(\.svg)?$/);
    if (m) return `${API}/product-placeholder/${m[1]}.svg`;
    if (u.includes('/placeholder/')) {
      const n = parseInt(tail.replace(/\.svg$/,''), 10);
      if (!isNaN(n)) return `${API}/product-placeholder/${n}.svg`;
    }
    return `${API}${u.replace('/products/', '/product-icons/')}`;
  }
  if (u.endsWith('.svg')) return `${API}/product-icons/${u}`;
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
    if (r.kw.every(k => name.includes(k))) return `${API}/product-icons/${r.file}`;
  }
  return svgCardFor(p);
}
// Stocks — page dédiée
async function loadStocks() {
  const warehouses = await fetchJSON(`${API}/warehouses?skip=0&limit=1000`);
  const productMap = new Map();
  const warehouseEntries = {};
  for (const w of warehouses) {
    try {
      const items = await fetchJSON(`${API}/warehouses/${w.id}/inventory`);
      warehouseEntries[w.id] = items.map(it => ({ product: it.product, product_id: it.product_id, quantity: parseInt(it.quantity, 10) || 0 }));
      for (const it of items) {
        const key = it.product_id;
        let rec = productMap.get(key);
        if (!rec) {
          rec = { product: it.product, quantities: {}, total: 0, weight_total: 0 };
          productMap.set(key, rec);
        }
        const qty = parseInt(it.quantity, 10) || 0;
        rec.quantities[w.id] = qty;
        rec.total += qty;
        const wkg = typeof it.product.weight_kg === 'number' ? it.product.weight_kg : null;
        if (wkg !== null) rec.weight_total += wkg * qty;
      }
    } catch {}
  }
  window.stocksCache = { productMap, warehouses, warehouseEntries };
  renderStocks();
}

function renderStocks() {
  const stocksView = document.getElementById('stocks-view');
  const stocksSummary = document.getElementById('stocks-summary');
  const filterInput = document.getElementById('stocks-filter');
  const groupingSel = document.getElementById('stocks-grouping');
  const grouping = groupingSel ? groupingSel.value : 'produits';
  const { productMap, warehouses, warehouseEntries } = window.stocksCache || { productMap: new Map(), warehouses: [], warehouseEntries: {} };
  const wid2name = new Map();
  for (const w of warehouses) wid2name.set(w.id, w.name);
  const term = String(filterInput?.value || '').trim().toLowerCase();
  const container = document.createElement('div');
  container.className = 'list';
  let totalQty = 0, totalWeight = 0, lowCount = 0;

  if (grouping === 'produits') {
    const rows = Array.from(productMap.values()).filter(r => {
      const n = String(r.product?.name || '').toLowerCase();
      const c = String(r.product?.category || '').toLowerCase();
      return !term || n.includes(term) || c.includes(term);
    }).sort((a,b)=>{
      const sevA = Math.max(...Object.entries(a.quantities).map(([wid,q]) => {
        const ww = warehouses.find(x => x.id === parseInt(wid,10));
        return severityFor(q, a.product, ww);
      }));
      const sevB = Math.max(...Object.entries(b.quantities).map(([wid,q]) => {
        const ww = warehouses.find(x => x.id === parseInt(wid,10));
        return severityFor(q, b.product, ww);
      }));
      if (sevA !== sevB) return sevB - sevA;
      return String(a.product?.name||'').localeCompare(String(b.product?.name||''));
    });
    for (const r of rows) {
      totalQty += r.total; totalWeight += r.weight_total;
      const p = r.product;
      const img = productImageFor(p);
      const card = document.createElement('div');
      card.className = 'card';
      const badgeParts = [];
      let cardSev = 0;
      for (const [wid, q] of Object.entries(r.quantities)) {
        const wnum = parseInt(wid,10);
        const ww = warehouses.find(x => x.id === wnum);
        const sev = severityFor(q, p, ww);
        cardSev = Math.max(cardSev, sev);
        if (sev === 2) lowCount++;
        const nm = wid2name.get(wnum) || `Entrepôt ${wid}`;
        badgeParts.push(`
          <span style="display:inline-flex; align-items:center; gap:6px; border:2px solid ${severityColor(sev)}; border-radius:6px; padding:2px 6px">
            <span class="muted">${nm}: ${q}</span>
          </span>`);
      }
      const badges = badgeParts.join(' ');
      try { card.style.border = `2px solid ${severityColor(cardSev)}`; } catch {}
      card.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px">
          ${img ? `<img class="product-image" src="${img}" alt="${p.name||''}" style="background-color:rgba(0,0,0,0.25)" />` : `<img class="product-image" src="${svgCardFor(p)}" alt="${p.name||''}" style="background-color:rgba(0,0,0,0.25)" />`}
          <div style="flex:1">
            <div class="product-title">${p.name||''}</div>
            <div class="muted">${p.category||''}${typeof p.weight_kg==='number'?` · ${p.weight_kg} kg/unité`:''}</div>
          </div>
          <div style="margin-left:auto; text-align:right">
            <div style="font-weight:600"> ${r.total}</div>
            ${r.weight_total?`<div class="muted">${r.weight_total.toFixed(2)} kg</div>`:''}
          </div>
        </div>
        <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap">${badges}</div>
      `;
      const imgEl = card.querySelector('img.product-image');
      if (imgEl) { imgEl.addEventListener('error', () => { imgEl.src = svgCardFor(p); }); }
      container.appendChild(card);
    }
  } else {
    const whs = warehouses.filter(w => {
      const nm = String(w.name || '').toLowerCase();
      return !term || nm.includes(term);
    });
    for (const w of whs) {
      let list = (warehouseEntries[w.id] || []).filter(it => {
        const n = String(it.product?.name || '').toLowerCase();
        const c = String(it.product?.category || '').toLowerCase();
        return !term || n.includes(term) || c.includes(term);
      });
      list = list.map(it => {
        const sev = severityFor(it.quantity, it.product, w);
        return { ...it, _sev: sev };
      }).sort((a,b)=>{
        if (a._sev !== b._sev) return b._sev - a._sev; // bas > moyen > normal
        return String(a.product?.name||'').localeCompare(String(b.product?.name||''));
      });
      const card = document.createElement('div');
      card.className = 'card';
      const rows = list.map(it => {
        const p = it.product;
        const sev = severityFor(it.quantity, p, w);
        if (sev === 2) lowCount++;
        totalQty += it.quantity;
        const wkg = typeof p.weight_kg === 'number' ? p.weight_kg : null;
        if (wkg !== null) totalWeight += wkg * it.quantity;
        return `
          <div style="display:flex; align-items:center; gap:8px; padding:6px; border:2px solid ${severityColor(sev)}; border-radius:6px;">
            <div style="flex:1">
              <div class="product-title">${p.name||''}</div>
              <div class="muted">${p.category||''}${wkg!==null?` · ${wkg} kg/unité`:''}</div>
            </div>
            <div style="text-align:right; width:120px">
              <div style="font-weight:600">x ${it.quantity}</div>
              ${wkg!==null?`<div class="muted">${(wkg*it.quantity).toFixed(2)} kg</div>`:''}
            </div>
          </div>`;
      }).join('');
      card.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px">
          <div style="font-weight:600">${w.name}</div>
          <div class="muted" style="margin-left:auto">${list.length} produits</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px">${rows}</div>
      `;
      container.appendChild(card);
    }
  }

  if (stocksView) { stocksView.innerHTML = ''; stocksView.appendChild(container); }
  if (stocksSummary) stocksSummary.textContent = `${grouping==='produits'?`${productMap.size} produits`:`${container.childElementCount} entrepôts`} · ${totalQty} unités${totalWeight?` · ${totalWeight.toFixed(2)} kg`:''}${lowCount?` · ${lowCount} critiques`:''}`;
}

const stocksFilterEl = document.getElementById('stocks-filter');
if (stocksFilterEl) {
  stocksFilterEl.addEventListener('input', () => { renderStocks(); });
}

const stocksGroupingEl = document.getElementById('stocks-grouping');
if (stocksGroupingEl) {
  stocksGroupingEl.addEventListener('change', () => { renderStocks(); });
}

(async function initStocks() { try { await loadStocks(); } catch {} })();

async function seedInventoryAllWarehouses() {
  const btn = document.getElementById('seed-inventory');
  try { if (btn) { btn.disabled = true; btn.textContent = 'Remplissage…'; } } catch {}
  try {
    const warehouses = await fetchJSON(`${API}/warehouses?skip=0&limit=1000`);
    let products = await fetchJSON(`${API}/products`);
    if (!Array.isArray(products) || products.length === 0) {
      try { await seedProducts(); products = await fetchJSON(`${API}/products`); } catch {}
    }
    const pick = (arr, pct) => arr.filter((_, i) => (i % Math.round(100/pct)) === 0);
    for (const w of warehouses) {
      const subset = products.length > 12 ? pick(products, 35) : products;
      for (const p of subset) {
        const base = 8 + (w.id % 5) * 4;
        const qty = base + Math.floor(Math.random() * 12);
        try {
          await fetchJSON(`${API}/warehouses/${w.id}/inventory`, { method: 'POST', body: JSON.stringify({ product_id: p.id, quantity: qty }) });
        } catch (e) {}
      }
    }
    await loadStocks();
    alert('Stocks démo remplis dans tous les entrepôts');
  } catch (err) {
    alert(err.message || 'Erreur lors du remplissage des stocks');
  } finally {
    try { if (btn) { btn.disabled = false; btn.textContent = 'Remplir stocks démo'; } } catch {}
  }
}

document.getElementById('seed-inventory')?.addEventListener('click', seedInventoryAllWarehouses);
