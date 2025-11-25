import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
// @ts-ignore - types non fournis par le paquet
import ThreeGlobe from 'three-globe';

const container = document.getElementById('globe')!;

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight - 54);
renderer.setPixelRatio(window.devicePixelRatio);
// Améliore le rendu des couleurs et du ton
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.3;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1221);

const camera = new THREE.PerspectiveCamera(35, window.innerWidth / (window.innerHeight - 54), 0.1, 1000);
camera.position.set(0, 0, 250);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 105; // rayon du globe ≈ 100, autorise zoom très proche
controls.maxDistance = 500;
controls.zoomSpeed = 1.2;

// Lumières
scene.add(new THREE.AmbientLight(0xffffff, 0.9));
const hemiLight = new THREE.HemisphereLight(0x88aaff, 0x0b1221, 0.35);
scene.add(hemiLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
dirLight.position.set(200, 200, 200);
scene.add(dirLight);

// Globe topographique
const globe = new (ThreeGlobe as any)()
  .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-day.jpg')
  .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
  .arcsData([])
  .arcColor(() => ['#22d3ee', '#f59e0b'])
  .arcAltitude((d: any) => Math.min(0.35, Math.max(0.15, (d?.alt || 0.2))))
  .arcStroke(1.5)
  .arcDashLength(0.5)
  .arcDashGap(0.2)
  .arcDashAnimateTime(1500);

scene.add(globe);

// Ajuste le matériau du globe pour un relief plus doux
try {
  const globeMaterial = (globe as any).globeMaterial?.();
  if (globeMaterial) {
    globeMaterial.bumpScale = 0.35;
    globeMaterial.shininess = 8;
  }
} catch {}

// Atmosphère légère
const atmosphere = new THREE.Mesh(
  new THREE.SphereGeometry(102, 96, 96),
  new THREE.MeshPhongMaterial({
    color: 0x93c5fd,
    transparent: true,
    opacity: 0.06,
  })
);
scene.add(atmosphere);

// Resize
window.addEventListener('resize', () => {
  const h = window.innerHeight - 54;
  camera.aspect = window.innerWidth / h;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, h);
});

// UI plotting
const startLatEl = document.getElementById('start-lat') as HTMLInputElement;
const startLonEl = document.getElementById('start-lon') as HTMLInputElement;
const endLatEl = document.getElementById('end-lat') as HTMLInputElement;
const endLonEl = document.getElementById('end-lon') as HTMLInputElement;
const plotBtn = document.getElementById('plot') as HTMLButtonElement;

plotBtn.addEventListener('click', () => {
  const startLat = parseFloat(startLatEl.value);
  const startLng = parseFloat(startLonEl.value);
  const endLat = parseFloat(endLatEl.value);
  const endLng = parseFloat(endLonEl.value);

  if (
    [startLat, startLng, endLat, endLng].some(v => Number.isNaN(v)) ||
    Math.abs(startLat) > 90 || Math.abs(endLat) > 90 ||
    Math.abs(startLng) > 180 || Math.abs(endLng) > 180
  ) {
    alert('Coordonnées invalides. Utilisez lat ∈ [-90,90], lon ∈ [-180,180].');
    return;
  }

  const arc = { startLat, startLng, endLat, endLng, alt: 0.25 };
  (globe as any).arcsData([arc]);
});

// Animation
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();