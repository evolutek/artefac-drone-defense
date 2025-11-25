import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import 'leaflet/dist/leaflet.css';
import './index.css';

const root = createRoot(document.getElementById('root')!);
root.render(<App />);