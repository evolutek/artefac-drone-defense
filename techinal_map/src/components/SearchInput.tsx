import React from 'react';

export default function SearchInput({
  value,
  onChange,
  placeholder = 'Rechercher',
  ariaLabel = 'Champ de recherche',
  small = true,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  ariaLabel?: string;
  small?: boolean;
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel}
      className={small ? 'input input-sm' : 'input'}
      style={{
        width: '100%',
        background: 'var(--glass)',
        color: '#fff',
        border: '1px solid var(--border)',
      }}
    />
  );
}