import React from 'react';

export default function Modal({
  open,
  title,
  header,
  onClose,
  children
}: {
  open: boolean;
  title?: string;
  header?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 2000,
      background: 'rgba(0,0,0,0.35)'
    }} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)',
          width: 'min(960px, 96vw)',
          background: 'var(--glass)',
          backdropFilter: 'saturate(180%) blur(8px)',
          borderRadius: 12,
          border: '1px solid var(--border)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
          padding: 20,
          maxHeight: '85vh',
          overflowY: 'auto'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          {header ?? (
            <h3 style={{ margin: 0, flex: '1 1 0%' }}>{title ?? 'Créer une mission'}</h3>
          )}
          <button
            onClick={onClose}
            className="btn btn-sm"
            style={{ padding: '0 8px', fontSize: 16 }}
            aria-label="Fermer"
          >✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}