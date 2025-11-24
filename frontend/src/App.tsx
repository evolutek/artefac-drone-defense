import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MapView } from './pages/MapView';
import { DebugDashboard } from './pages/DebugDashboard';
import GazeboViewer from './pages/GazeboViewer';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main route - Topographic Map */}
        <Route path="/" element={<MapView />} />

        {/* Debug Dashboard - Original control interface */}
        <Route path="/debug" element={<DebugDashboard />} />

        {/* Gazebo Web Viewer */}
        <Route path="/gazebo" element={<GazeboViewer />} />

        {/* Catch-all redirect to map */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
