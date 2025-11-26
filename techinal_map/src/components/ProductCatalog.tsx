import React, { useEffect, useMemo, useState } from 'react';
import { PRODUCTS, type Product } from '../data/products';
import type { Payload } from '../types/types';
import { onStateEvent, offStateEvent, startWebSocket } from '../ws';

export default function ProductCatalog({
  onSelectProduct,
  searchTerm = '',
  category = '',
}: {
  onSelectProduct: (p: Product) => void;
  searchTerm?: string;
  category?: string;
}) {
  const [remoteProducts, setRemoteProducts] = useState<Product[]>([]);
  const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8001';

  function resolveImageUrl(u?: string | null): string | null {
    if (!u) return null;
    const s = String(u);
    if (s.startsWith('http://') || s.startsWith('https://')) return s;
    if (s.startsWith('/')) {
      // If it's the backend placeholder, fetch from API; otherwise use local static assets
      if (s.startsWith('/product-placeholder/')) return `${apiBase}${s}`;
      // e.g. "/products/water-pack-6x1.5l.svg" should be served by techinal_map static
      return s;
    }
    // fallback to local static assets in techinal_map
    return `/products/${s}`;
  }

  function nameBasedFallback(name?: string): string | null {
    const n = (name ?? '').toLowerCase();
    const rules: Array<{ kw: string[]; file: string }> = [
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
      if (r.kw.every((k) => n.includes(k))) return `/products/${r.file}`;
    }
    return null;
  }

  function svgCardFor(p: Product): string {
    const name = (p.name ?? 'Produit').trim();
    const category = (p.category ?? 'produit').toLowerCase();
    const colorMap: Record<string, string> = {
      munitions: '#F97316',
      attachments: '#22C55E',
      medicaments: '#EF4444',
      communication: '#0EA5E9',
      logistique: '#8B5CF6',
    };
    const base = colorMap[category] ?? '#64748B';
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
    const encoded = encodeURIComponent(svg);
    return `data:image/svg+xml;charset=utf-8,${encoded}`;
  }

  function imageFor(p: Product): string {
    // 1) explicit image_url
    const resolved = resolveImageUrl((p as any).image_url);
    if (resolved) return resolved;
    // 2) backend dynamic placeholder by id
    // Only use backend placeholder for numeric IDs; otherwise fall back to local generator
    if (p.id && /^\d+$/.test(String(p.id))) return `${apiBase}/product-placeholder/${p.id}.svg`;
    // 3) name-based local asset
    const byName = nameBasedFallback(p.name);
    if (byName) return byName;
    // 4) dynamic SVG with product name
    return svgCardFor(p);
  }

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${apiBase}/products`);
        const data = await res.json();
        // Map API fields to local Product type if needed
        if (Array.isArray(data)) {
          setRemoteProducts(data.map((p: any) => ({
            id: String(p.id),
            name: p.name,
            description: p.description,
            category: p.category,
            weight_kg: p.weight_kg,
            image_url: p.image_url,
          })) as Product[]);
        }
      } catch (_) {
        // ignore fetch errors; fallback to local PRODUCTS
      }
    })();

    // Ensure realtime socket started
    startWebSocket();

    // Subscribe to realtime product events
    const handler = (msg: any) => {
      const t = msg?.data?.type;
      if (t === 'product_delete') {
        const pid = msg?.data?.product_id;
        if (typeof pid === 'number' || typeof pid === 'string') {
          const pidStr = String(pid);
          setRemoteProducts((prev) => prev.filter((p) => String(p.id) !== pidStr));
        }
      } else if (t === 'product_upsert') {
        const p = msg?.data?.product;
        if (p && (typeof p.id === 'number' || typeof p.id === 'string')) {
          setRemoteProducts((prev) => {
            const key = String(p.id);
            const idx = prev.findIndex((x) => String(x.id) === key);
            const mapped: Product = {
              id: key,
              name: p.name,
              description: p.description,
              category: p.category,
              weight_kg: p.weight_kg,
              image_url: p.image_url,
            };
            if (idx >= 0) {
              const copy = prev.slice();
              copy[idx] = mapped;
              return copy;
            }
            return [mapped, ...prev];
          });
        }
      }
    };
    onStateEvent(handler);
    return () => offStateEvent(handler);
  }, []);

  const items = useMemo(() => {
    const all = remoteProducts.length > 0 ? remoteProducts : PRODUCTS;
    const term = searchTerm.trim().toLowerCase();
    return all.filter((p) =>
      (!category || p.category === category) &&
      (!term || p.name.toLowerCase().includes(term) || (p.description ?? '').toLowerCase().includes(term))
    );
  }, [searchTerm, category, remoteProducts]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
        {items.map((p) => (
            <div
              key={p.id}
              style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', background: 'var(--glass)', cursor: 'pointer' }}
              onClick={() => onSelectProduct(p)}
            >
            <img
              src={imageFor(p)}
              alt={p.name}
              style={{ width: '100%', height: 140, objectFit: 'cover', backgroundColor: 'rgba(0,0,0,0.25)' }}
              onError={(e) => {
                // Fallback robuste: générer une carte SVG avec le nom du produit
                const fallback = svgCardFor(p);
                if (e.currentTarget.src !== fallback) {
                  e.currentTarget.src = fallback;
                }
              }}
            />
            <div style={{ padding: 12 }}>
              <div style={{ fontWeight: 600 }}>{p.name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{p.description}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--text)' }}> {p.weight_kg ?? '-'} kg </span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}> {p.category}</span>
                <button
                  type="button"
                  className="btn btn-icon"
                  onClick={(e) => { e.stopPropagation(); onSelectProduct(p); }}
                  aria-label="Ajouter à la mission"
                  title="Ajouter à la mission"
                  style={{ marginLeft: 'auto' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
