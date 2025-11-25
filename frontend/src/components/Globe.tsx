import { useEffect, useRef } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useTelemetry } from '../hooks/useTelemetry'

export function Globe() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<Cesium.Viewer | null>(null)
  const drones = useTelemetry()

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return
    const viewer = new Cesium.Viewer(containerRef.current, {
      animation: false,
      timeline: false,
      baseLayerPicker: true,
      geocoder: false,
      homeButton: true,
      sceneModePicker: true,
      navigationHelpButton: false,
    })
    viewerRef.current = viewer
    viewer.scene.globe.depthTestAgainstTerrain = true
    viewer.scene.requestRenderMode = true
    return () => {
      viewer.destroy()
      viewerRef.current = null
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return

    // Update or create entities for each drone
    Object.entries(drones).forEach(([id, state]) => {
      const latest = state.latest
      if (!latest || latest.latitude === undefined || latest.longitude === undefined) return
      const position = Cesium.Cartesian3.fromDegrees(latest.longitude!, latest.latitude!, latest.altitude ?? 0)

      let entity = viewer.entities.getById(id)
      if (!entity) {
        entity = viewer.entities.add({
          id,
          position: new Cesium.ConstantPositionProperty(position),
          point: { pixelSize: 10, color: Cesium.Color.CYAN },
          label: { text: id, font: '14px sans-serif', pixelOffset: new Cesium.Cartesian2(0, -20), fillColor: Cesium.Color.WHITE },
        })
      } else {
        entity.position = new Cesium.ConstantPositionProperty(position)
      }

      // Update path polyline
      if (state.path.length >= 2) {
        const positions = state.path.map(p => Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.alt ?? 0))
        let pathEntity = viewer.entities.getById(`${id}-path`)
        if (!pathEntity) {
          pathEntity = viewer.entities.add({
            id: `${id}-path`,
            polyline: { positions: new Cesium.CallbackProperty(() => positions, false), width: 2, material: Cesium.Color.YELLOW.withAlpha(0.8) },
          })
        } else if (pathEntity.polyline) {
          pathEntity.polyline.positions = new Cesium.CallbackProperty(() => positions, false)
        }
      }

      // Keep camera roughly following the drone on first updates
      if (viewer.camera) {
        viewer.scene.requestRender()
      }
    })
  }, [drones])

  return (
    <div className="bg-white rounded-lg shadow p-2">
      <h3 className="text-lg font-semibold mb-2">Globe - Trajectoire en temps réel</h3>
      <div ref={containerRef} style={{ width: '100%', height: '400px' }} />
    </div>
  )
}