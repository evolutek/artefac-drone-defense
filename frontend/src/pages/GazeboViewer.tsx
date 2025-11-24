import SimulationCanvas from '../components/SimulationCanvas'
import Terrain from '../components/Terrain'
import CoordinateGrid from '../components/CoordinateGrid'
import ExclusionZones from '../components/ExclusionZones'
import DroneMarkers from '../components/DroneMarkers'

export default function GazeboViewer() {
  return (
    <div className="h-screen w-screen">
      <SimulationCanvas>
        <Terrain />
        <CoordinateGrid />
        <ExclusionZones />
        <DroneMarkers />
      </SimulationCanvas>
    </div>
  )
}