import React, { useEffect, useRef } from 'react';
import {
  Scene,
  PerspectiveCamera,
  WebGLRenderer,
  Color,
  AmbientLight,
  DirectionalLight,
  SphereGeometry,
  Mesh,
  MeshPhongMaterial,
  BufferGeometry,
  Float32BufferAttribute,
  Points,
  PointsMaterial,
  TextureLoader,
  Clock
} from 'three';

export default function IntroSplash({ onComplete, loop = false, speed = 6.0 }: { onComplete?: () => void; loop?: boolean; speed?: number }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<WebGLRenderer | null>(null);

  useEffect(() => {
    const container = containerRef.current!;
    const scene = new Scene();
    scene.background = null; // transparent

    const camera = new PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 3.2);

    const renderer = new WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    // Lights
    const ambient = new AmbientLight(0xffffff, 0.5);
    scene.add(ambient);

    const dir = new DirectionalLight(0xffffff, 1.1);
    dir.position.set(2.5, 1.8, 3.2);
    scene.add(dir);

    // Earth textures
    const loader = new TextureLoader();
    let globe: Mesh | null = null;
    const globeGeo = new SphereGeometry(1, 64, 64);
    loader.loadAsync('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg')
      .then(async (diffuse) => {
        const [normal, specular] = await Promise.all([
          loader.loadAsync('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_normal_2048.jpg'),
          loader.loadAsync('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_specular_2048.jpg')
        ]);
        const globeMat = new MeshPhongMaterial({
          map: diffuse,
          normalMap: normal,
          specularMap: specular,
          specular: new Color(0x222222),
          shininess: 18
        });
        globe = new Mesh(globeGeo, globeMat);
        scene.add(globe);
        startAnimation(globe);
      })
      .catch(() => {
        // Fallback: solid color sphere if textures fail
        const globeMat = new MeshPhongMaterial({ color: new Color('#1e88e5') });
        globe = new Mesh(globeGeo, globeMat);
        scene.add(globe);
        startAnimation(globe);
      });

    // Simple starfield
    const starGeo = new BufferGeometry();
    const starCount = 600;
    const positions = new Float32BufferAttribute(new Float32Array(starCount * 3), 3);
    for (let i = 0; i < starCount; i++) {
      const r = 8 + Math.random() * 6;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions.setXYZ(i, r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta), r * Math.cos(phi));
    }
    starGeo.setAttribute('position', positions);
    const stars = new Points(starGeo, new PointsMaterial({ color: 0xffffff, size: 0.02 }));
    scene.add(stars);

    const clock = new Clock();
    let rafId = 0;
    let angleY = 0;
    const rotSpeed = speed;
    function startAnimation(mesh: Mesh) {
      const animate = () => {
        const dt = clock.getDelta();
        angleY += rotSpeed * dt;
        // Rotation horizontale pure (autour de l’axe Y)
        mesh.rotation.y = angleY;
        mesh.rotation.x = 0;
        renderer.render(scene, camera);
        if (!loop && angleY >= Math.PI * 2) {
          onComplete?.();
          return;
        }
        rafId = requestAnimationFrame(animate);
      };
      rafId = requestAnimationFrame(animate);
    }

    // Note: les grilles lat/long ont été retirées au profit de la texture réaliste

    const onResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div className="intro-splash" ref={containerRef}>
      <div className="intro-logo">
        <img src="/assets/logo-artifact-ago-white.png" alt="Logo" />
      </div>
    </div>
  );
}