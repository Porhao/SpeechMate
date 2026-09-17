"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ParticleBackground() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || typeof window === "undefined") return;

    // ── Renderer ───────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 0, 55);

    // ── Particles ──────────────────────────────────────────────────────────
    const COUNT = 650;
    const pos   = new Float32Array(COUNT * 3);
    const col   = new Float32Array(COUNT * 3);
    const vel   = new Float32Array(COUNT * 3); // drift velocity

    const c1 = new THREE.Color("#5A5470"); // violet (primary)
    const c2 = new THREE.Color("#A78BFA"); // light purple
    const c3 = new THREE.Color("#4C1D95"); // deep purple

    for (let i = 0; i < COUNT; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 180;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 140;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 80;

      vel[i * 3]     = (Math.random() - 0.5) * 0.012;
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.008;
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.004;

      const r = Math.random();
      const c = r < 0.45 ? c1.clone().lerp(c2, Math.random())
               : r < 0.75 ? c2.clone().lerp(c3, Math.random())
               : c3.clone().lerp(c1, Math.random());
      col[i * 3]     = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color",    new THREE.BufferAttribute(col, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.9,
      vertexColors: true,
      transparent: true,
      opacity: 0.28,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const points = new THREE.Points(geo, mat);
    scene.add(points);

    // ── Connection lines (nearest-neighbour, computed on a subset) ─────────
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x7C3AED,
      transparent: true,
      opacity: 0.04,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const lineGeo  = new THREE.BufferGeometry();
    const linePos  = new Float32Array(COUNT * COUNT * 6); // over-allocated
    lineGeo.setAttribute("position", new THREE.BufferAttribute(linePos, 3));
    const lineObj  = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lineObj);

    // ── Floating orbs (3 large blurred spheres) ───────────────────────────
    const orbData = [
      { pos: [-25,  15, -20], color: "#5A5470", r: 7 },
      { pos: [ 30, -10, -25], color: "#403C54", r: 9 },
      { pos: [  0,  25, -30], color: "#A78BFA", r: 5 },
    ];

    const orbs: THREE.Mesh[] = orbData.map(({ pos: p, color, r }) => {
      const g = new THREE.SphereGeometry(r, 32, 32);
      const m = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.08,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(g, m);
      mesh.position.set(p[0], p[1], p[2]);
      scene.add(mesh);
      return mesh;
    });

    // ── Mouse parallax ────────────────────────────────────────────────────
    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    const onMouseMove = (e: MouseEvent) => {
      mouse.tx = (e.clientX / window.innerWidth  - 0.5) * 2;
      mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove, { passive: true });

    // ── Resize ────────────────────────────────────────────────────────────
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", onResize);

    // ── Animate ───────────────────────────────────────────────────────────
    let raf = 0;
    const clock = new THREE.Clock();
    let lineUpdateFrame = 0;

    const animate = () => {
      raf = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      // Smooth mouse follow
      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;
      camera.position.x = mouse.x * 6;
      camera.position.y = -mouse.y * 4;
      camera.lookAt(scene.position);

      // Drift particles
      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < COUNT; i++) {
        posAttr.array[i * 3]     += vel[i * 3];
        posAttr.array[i * 3 + 1] += vel[i * 3 + 1];
        posAttr.array[i * 3 + 2] += vel[i * 3 + 2];

        // Wrap around bounds
        if (Math.abs(posAttr.array[i * 3])     > 90)  posAttr.array[i * 3]     *= -0.98;
        if (Math.abs(posAttr.array[i * 3 + 1]) > 70)  posAttr.array[i * 3 + 1] *= -0.98;
        if (Math.abs(posAttr.array[i * 3 + 2]) > 40)  posAttr.array[i * 3 + 2] *= -0.98;
      }
      posAttr.needsUpdate = true;

      // Slow global rotation
      points.rotation.y = t * 0.018;
      points.rotation.x = Math.sin(t * 0.012) * 0.08;

      // Orb pulsing float
      orbs.forEach((orb, i) => {
        orb.position.y = orbData[i].pos[1] + Math.sin(t * 0.4 + i * 1.8) * 3;
        orb.position.x = orbData[i].pos[0] + Math.cos(t * 0.25 + i * 1.2) * 2;
        const s = 1 + Math.sin(t * 0.5 + i) * 0.12;
        orb.scale.setScalar(s);
        (orb.material as THREE.MeshBasicMaterial).opacity = 0.06 + Math.sin(t * 0.6 + i) * 0.025;
      });

      // Connection lines — recompute every 6 frames to save CPU
      lineUpdateFrame++;
      if (lineUpdateFrame % 6 === 0) {
        const SAMPLE  = 120; // only check first N particles for perf
        const THRESH  = 28;
        let lineCount = 0;
        const lp = lineGeo.attributes.position as THREE.BufferAttribute;
        for (let a = 0; a < SAMPLE && lineCount < 3000; a++) {
          const ax = posAttr.array[a * 3], ay = posAttr.array[a * 3 + 1], az = posAttr.array[a * 3 + 2];
          for (let b = a + 1; b < SAMPLE && lineCount < 3000; b++) {
            const bx = posAttr.array[b * 3], by = posAttr.array[b * 3 + 1], bz = posAttr.array[b * 3 + 2];
            const dist = Math.sqrt((ax-bx)**2+(ay-by)**2+(az-bz)**2);
            if (dist < THRESH) {
              lp.array[lineCount * 6]     = ax; lp.array[lineCount * 6 + 1] = ay; lp.array[lineCount * 6 + 2] = az;
              lp.array[lineCount * 6 + 3] = bx; lp.array[lineCount * 6 + 4] = by; lp.array[lineCount * 6 + 5] = bz;
              lineCount++;
            }
          }
        }
        lineGeo.setDrawRange(0, lineCount * 2);
        lp.needsUpdate = true;
      }

      renderer.render(scene, camera);
    };
    animate();

    // ── Cleanup ───────────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      geo.dispose(); mat.dispose(); lineGeo.dispose(); lineMat.dispose();
      orbs.forEach((o) => { o.geometry.dispose(); (o.material as THREE.Material).dispose(); });
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden
    />
  );
}
