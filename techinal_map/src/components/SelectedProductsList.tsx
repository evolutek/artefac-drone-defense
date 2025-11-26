import React from 'react';
import type { Product } from '../data/products';

type SelectedProductsListProps = {
  selectedProducts: Array<{ product: Product; quantity: number }>;
  onQuantityChange: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
};

export default function SelectedProductsList({
  selectedProducts,
  onQuantityChange,
  onRemove,
}: SelectedProductsListProps) {
  if (selectedProducts.length === 0) return null;

  return (
    <div style={{ marginTop: 12, border: '1px solid var(--border)', borderRadius: 8, padding: 8 }}>
      {selectedProducts.map((entry) => (
        <div
          key={entry.product.id}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}
        >
          <span style={{ fontWeight: 600, fontSize: 13 }}>{entry.product.name}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {entry.product.weight_kg ?? '-'} kg
          </span>
          <label style={{ marginLeft: 'auto' }}>
            Quantité
            <select
              className="input input-sm"
              value={entry.quantity}
              onChange={(e) => {
                const q = Math.max(1, parseInt(e.target.value) || 1);
                onQuantityChange(entry.product.id, q);
              }}
              style={{ marginLeft: 8, width: 80 }}
              aria-label="Quantité (menu)"
            >
              {Array.from({ length: 20 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => onRemove(entry.product.id)}
          >
            Retirer
          </button>
        </div>
      ))}
    </div>
  );
}
