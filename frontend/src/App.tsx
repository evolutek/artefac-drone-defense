import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MapView } from './pages/MapView';
import { DebugDashboard } from './pages/DebugDashboard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main route - Topographic Map */}
        <Route path="/" element={<MapView />} />

        {/* Debug Dashboard - Original control interface */}
        <Route path="/debug" element={<DebugDashboard />} />

        {/* Catch-all redirect to map */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
