import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

const params = new URL(window.location.href).searchParams
const world = params.get('world')
if (world) {
  document.title = `PX4_GZ_WORLD=${world}`
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
