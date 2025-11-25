import React, { useMemo } from 'react';
import { PRODUCTS, type Product } from '../data/products';
import type { Payload } from '../types';

export default function ProductCatalog({
  onSelectProduct,
  searchTerm = '',
  category = '',
}: {
  onSelectProduct: (p: Product) => void;
  searchTerm?: string;
  category?: string;
}) {
  const items = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return PRODUCTS.filter((p) =>
      (!category || p.category === category) &&
      (!term || p.name.toLowerCase().includes(term) || (p.description ?? '').toLowerCase().includes(term))
    );
  }, [searchTerm, category]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
        {items.map((p) => (
            <div
              key={p.id}
              style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', background: 'var(--glass)', cursor: 'pointer' }}
              onClick={() => onSelectProduct(p)}
            >
            {p.image_url && (
              <img src={p.image_url} alt={p.name} style={{ width: '100%', height: 140, objectFit: 'cover' }} />
            )}
            <div style={{ padding: 12 }}>
              <div style={{ fontWeight: 600 }}>{p.name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{p.description}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--text)' }}>Poids: {p.weight_kg ?? '-'} kg</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Catégorie: {p.category}</span>
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
