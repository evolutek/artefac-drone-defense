import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useTelemetry } from '../hooks/useTelemetry'

export function DroneSimView() {
  const mountRef = useRef<HTMLDivElement | null>(null)
  const droneMeshRef = useRef<THREE.Mesh | null>(null)
  const pathGeometryRef = useRef<THREE.BufferGeometry | null>(null)
  const pathPointsRef = useRef<THREE.Vector3[]>([])
  const drones = useTelemetry()

  useEffect(() => {
    if (!mountRef.current) return
    const width = mountRef.current.clientWidth
    const height = 400
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x111827)
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
    camera.position.set(10, 10, 15)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    mountRef.current.appendChild(renderer.domElement)

    const grid = new THREE.GridHelper(100, 20)
    scene.add(grid)
    const light = new THREE.DirectionalLight(0xffffff, 1)
    light.position.set(10, 20, 10)
    scene.add(light)
    scene.add(new THREE.AmbientLight(0x404040))

    // Simple drone representation
    const droneMesh = new THREE.Mesh(
      new THREE.BoxGeometry(1, 0.3, 1),
      new THREE.MeshStandardMaterial({ color: 0x00c4ff })
    )
    scene.add(droneMesh)
    droneMeshRef.current = droneMesh

    // Path line
    const pathGeometry = new THREE.BufferGeometry()
    const pathMaterial = new THREE.LineBasicMaterial({ color: 0xffd400 })
    const pathLine = new THREE.Line(pathGeometry, pathMaterial)
    scene.add(pathLine)
    pathGeometryRef.current = pathGeometry
    pathPointsRef.current = []

    let animId: number
    const animate = () => {
      animId = requestAnimationFrame(animate)
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      cancelAnimationFrame(animId)
      renderer.dispose()
      mountRef.current?.removeChild(renderer.domElement)
      droneMeshRef.current = null
      pathGeometryRef.current = null
      pathPointsRef.current = []
    }
  }, [])

  useEffect(() => {
    // Update the 3D view with the first drone data
    const mesh = droneMeshRef.current
    const pathGeometry = pathGeometryRef.current
    if (!mesh || !pathGeometry) return
    // Find drone id and telemetry
    const [firstId, state] = Object.entries(drones)[0] || []
    if (!firstId || !state?.latest) return
    const latest = state.latest

    // Convert NED-ish or absolute positions to local frame
    const x = latest.position_x ?? 0
    const y = latest.altitude ?? latest.position_z ?? 0
    const z = latest.position_y ?? 0
    mesh.position.set(x, y, z)

    // Append to path and update geometry
    const pts = pathPointsRef.current
    const last = pts[pts.length - 1]
    if (!last || last.distanceTo(new THREE.Vector3(x, y, z)) > 0.05) {
      pts.push(new THREE.Vector3(x, y, z))
      if (pts.length > 2000) pts.shift()
      const positions = new Float32Array(pts.length * 3)
      for (let i = 0; i < pts.length; i++) {
        positions[i * 3] = pts[i].x
        positions[i * 3 + 1] = pts[i].y
        positions[i * 3 + 2] = pts[i].z
      }
      pathGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      pathGeometry.computeBoundingSphere()
    }
  }, [drones])

  return (
    <div className="bg-white rounded-lg shadow p-2">
      <h3 className="text-lg font-semibold mb-2">Vue 3D locale du drone</h3>
      <div ref={mountRef} style={{ width: '100%', height: '400px' }} />
    </div>
  )
}