"use client";

// A small three.js "claymation" scene in the Clay palette (see DESIGN.md): one hero object
// for the page (a microphone, a briefcase or a slide board) with speech bubbles and soft
// shapes floating around it.
//
// - Matte "clay" materials, a warm key light and a soft contact shadow; no image assets.
// - Leans towards the pointer; a click squashes the hero object like clay.
// - Pauses while the tab is hidden; a single still frame for prefers-reduced-motion;
//   every GPU resource is disposed on unmount. Load it with next/dynamic (ssr: false).

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

export type ClayVariant = "mic" | "interview" | "present" | "logo";  // logo: the mic alone, turning (nav bar)

const C = {
  pink: "#FF4D8B", pinkDeep: "#D6245F", teal: "#1A3A3A", tealSoft: "#2F6B6B", lavender: "#B8A4ED",
  peach: "#FFB084", ochre: "#E8B94A", mint: "#A4D4C5", cream: "#FFFAF0", ink: "#0A0A0A",
};

function clay(color: string) {
  return new THREE.MeshPhysicalMaterial({
    color, roughness: 0.62, metalness: 0, clearcoat: 0.25, clearcoatRoughness: 0.7, sheen: 0.4, sheenColor: new THREE.Color("#ffffff"),
  });
}

function mesh(geo: THREE.BufferGeometry, color: string) {
  return new THREE.Mesh(geo, clay(color));
}

// ── Hero objects (built around the origin, ~2.4 units tall) ─────────────────────
function microphone(): THREE.Group {
  const g = new THREE.Group();
  const head = mesh(new THREE.SphereGeometry(0.62, 48, 32), C.pink);
  head.scale.set(1, 1.08, 1);
  head.position.y = 0.75;
  g.add(head);
  // Grille: rings around the head
  for (const y of [-0.3, -0.1, 0.1, 0.3]) {
    const r = Math.sqrt(0.62 ** 2 - y ** 2) * 1.005;
    const ring = mesh(new THREE.TorusGeometry(r, 0.022, 10, 64), C.pinkDeep);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.75 + y * 1.08;
    g.add(ring);
  }
  for (const a of [0, Math.PI / 3, (2 * Math.PI) / 3]) {
    const ring = mesh(new THREE.TorusGeometry(0.625, 0.02, 10, 64), C.pinkDeep);
    ring.scale.set(1, 1.08, 1);
    ring.rotation.y = a;
    ring.position.y = 0.75;
    g.add(ring);
  }
  const collar = mesh(new THREE.TorusGeometry(0.42, 0.11, 20, 48), C.cream);
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 0.12;
  g.add(collar);
  const body = mesh(new THREE.CylinderGeometry(0.36, 0.24, 1.35, 48), C.cream);
  body.position.y = -0.58;
  g.add(body);
  const band = mesh(new THREE.TorusGeometry(0.31, 0.05, 12, 48), C.teal);
  band.rotation.x = Math.PI / 2;
  band.position.y = -0.62;
  g.add(band);
  const button = mesh(new RoundedBoxGeometry(0.16, 0.3, 0.1, 3, 0.04), C.ochre);
  button.position.set(0, -0.25, 0.33);
  g.add(button);
  const cap = mesh(new THREE.SphereGeometry(0.24, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), C.teal);
  cap.position.y = -1.25;
  g.add(cap);
  g.rotation.z = -0.32;
  return g;
}

function briefcase(): THREE.Group {
  const g = new THREE.Group();
  const body = mesh(new RoundedBoxGeometry(2.1, 1.45, 0.62, 6, 0.2), C.teal);
  g.add(body);
  const flap = mesh(new RoundedBoxGeometry(2.14, 0.5, 0.66, 6, 0.18), C.tealSoft);
  flap.position.y = 0.42;
  g.add(flap);
  const handle = mesh(new THREE.TorusGeometry(0.34, 0.08, 16, 48, Math.PI), C.ochre);
  handle.position.y = 0.73;
  g.add(handle);
  for (const x of [-0.55, 0.55]) {
    const clasp = mesh(new RoundedBoxGeometry(0.24, 0.2, 0.12, 3, 0.05), C.ochre);
    clasp.position.set(x, 0.18, 0.33);
    g.add(clasp);
  }
  g.rotation.set(0.12, -0.35, 0.06);
  return g;
}

function slideBoard(): THREE.Group {
  const g = new THREE.Group();
  const frame = mesh(new RoundedBoxGeometry(2.3, 1.55, 0.14, 5, 0.06), C.teal);
  frame.position.y = 0.45;
  g.add(frame);
  const screen = mesh(new RoundedBoxGeometry(2.05, 1.3, 0.06, 4, 0.03), C.cream);
  screen.position.set(0, 0.45, 0.07);
  g.add(screen);
  // A little bar chart on the slide
  [[C.pink, 0.45], [C.lavender, 0.75], [C.ochre, 0.6], [C.mint, 0.95]].forEach(([color, h], i) => {
    const bar = mesh(new RoundedBoxGeometry(0.26, h as number, 0.1, 3, 0.05), color as string);
    bar.position.set(-0.6 + i * 0.4, -0.05 + (h as number) / 2, 0.14);
    g.add(bar);
  });
  for (const [x, rz] of [[-0.55, -0.25], [0.55, 0.25]] as const) {
    const leg = mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.3, 16), C.tealSoft);
    leg.position.set(x, -0.75, -0.05);
    leg.rotation.z = rz;
    g.add(leg);
  }
  g.rotation.set(0.05, -0.3, 0);
  return g;
}

function speechBubble(color: string, w: number, h: number, dots: string): THREE.Group {
  const g = new THREE.Group();
  g.add(mesh(new RoundedBoxGeometry(w, h, 0.32, 6, Math.min(w, h) * 0.32), color));
  const tail = mesh(new THREE.ConeGeometry(0.15, 0.36, 24), color);
  tail.position.set(-w * 0.28, -h / 2 - 0.12, 0);
  tail.rotation.z = Math.PI - 0.5;
  g.add(tail);
  for (let i = -1; i <= 1; i++) {
    const dot = mesh(new THREE.SphereGeometry(h * 0.1, 20, 12), dots);
    dot.position.set(i * w * 0.24, 0, 0.17);
    g.add(dot);
  }
  return g;
}

/** A soft round shadow under the scene, drawn once into a canvas texture. */
function contactShadow(): THREE.Mesh {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, "rgba(10,10,10,0.28)");
  grad.addColorStop(1, "rgba(10,10,10,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(3.6, 1.2),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false }),
  );
  m.rotation.x = -Math.PI / 2;
  m.position.y = -1.75;
  return m;
}

function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export default function ClayScene({ variant = "mic", className }: { variant?: ClayVariant; className?: string }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webglFailed] = useState(() => !supportsWebGL());

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || webglFailed) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.style.display = "block";
    mount.appendChild(renderer.domElement);

    const logo = variant === "logo";
    const baseZ = logo ? 6.2 : 9;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
    camera.position.set(0, logo ? -0.15 : 0.3, baseZ);
    scene.add(new THREE.HemisphereLight(0xfffaf0, 0x9a8a74, 1.6));
    const key = new THREE.DirectionalLight(0xfff1e0, 2.4);
    key.position.set(-3, 5, 4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xb8a4ed, 1.2);
    rim.position.set(4, 1, -3);
    scene.add(rim);

    const world = new THREE.Group();
    scene.add(world);
    if (!logo) world.add(contactShadow());

    const hero = variant === "interview" ? briefcase() : variant === "present" ? slideBoard() : microphone();
    world.add(hero);

    // Floating companions: [object, base position, bob speed, bob phase]
    const floaters: [THREE.Object3D, THREE.Vector3, number, number][] = [];
    const float = (o: THREE.Object3D, x: number, y: number, z: number, speed: number, phase: number) => {
      if (logo) {  // the logo is just the mic: free what was built for the scene
        o.traverse((m) => { if (m instanceof THREE.Mesh) { m.geometry.dispose(); (m.material as THREE.Material).dispose(); } });
        return;
      }
      o.position.set(x, y, z);
      world.add(o);
      floaters.push([o, new THREE.Vector3(x, y, z), speed, phase]);
    };
    const bubbleA = speechBubble(C.lavender, 1.25, 0.82, C.cream);
    bubbleA.scale.setScalar(0.85);
    bubbleA.rotation.set(0, -0.25, 0.08);
    float(bubbleA, 1.85, 1.15, 0.2, 1.1, 0);
    const bubbleB = speechBubble(C.mint, 0.9, 0.6, C.teal);
    bubbleB.scale.set(-0.8, 0.8, 0.8);  // mirrored: its tail points the other way
    float(bubbleB, -1.95, 0.55, -0.2, 1.3, 1.8);
    float(mesh(new THREE.TorusGeometry(0.26, 0.11, 20, 40), C.ochre), -1.6, -1.1, 0.6, 0.9, 0.9);
    float(mesh(new THREE.SphereGeometry(0.2, 32, 16), C.peach), 1.75, -0.95, 0.7, 1.5, 2.4);
    float(mesh(new THREE.SphereGeometry(0.13, 24, 12), C.pink), 2.3, 0.15, -0.6, 1.7, 3.1);
    float(mesh(new THREE.CapsuleGeometry(0.1, 0.28, 8, 16), C.tealSoft), -2.35, 1.55, -0.5, 1.2, 4.0);

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = `${w}px`;
      renderer.domElement.style.height = `${h}px`;
      camera.aspect = w / h;
      // Keep the whole scene in frame on narrow containers
      camera.position.z = logo ? baseZ : w / h < 1.25 ? baseZ * (1.25 / Math.max(w / h, 0.6)) : baseZ;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    const target = { x: 0, y: 0 };
    const onPointer = (e: PointerEvent) => {
      target.x = (e.clientY / window.innerHeight - 0.5) * 0.3;
      target.y = (e.clientX / window.innerWidth - 0.5) * 0.6;
    };
    window.addEventListener("pointermove", onPointer);
    let squash = 0;
    const onPress = () => { squash = 1; };
    renderer.domElement.addEventListener("pointerdown", onPress);

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = new THREE.Timer();
    const heroBase = hero.rotation.clone();
    let raf = 0;

    const frame = (now?: number) => {
      timer.update(now);
      const dt = Math.min(timer.getDelta(), 0.05);
      const t = timer.getElapsed();
      world.rotation.y += (target.y - world.rotation.y) * 0.05;
      world.rotation.x += (target.x - world.rotation.x) * 0.05;
      hero.position.y = Math.sin(t * 1.1) * (logo ? 0.03 : 0.08);
      hero.rotation.y = logo ? heroBase.y + t * 0.9 : heroBase.y + Math.sin(t * 0.5) * 0.18;
      // Click: a springy clay squash (wider and shorter, then back)
      squash = Math.max(0, squash - dt * 1.8);
      const s = Math.sin(squash * Math.PI * 3) * squash * 0.14;
      hero.scale.set(1 + s, 1 - s, 1 + s);
      for (const [o, base, speed, phase] of floaters) {
        o.position.y = base.y + Math.sin(t * speed + phase) * 0.14;
        o.rotation.z = Math.sin(t * speed * 0.6 + phase) * 0.12;
      }
      renderer.render(scene, camera);
    };
    const loop = (now: number) => { frame(now); raf = requestAnimationFrame(loop); };
    const onVisibility = () => {
      cancelAnimationFrame(raf);
      if (!document.hidden && !reduceMotion) { timer.reset(); raf = requestAnimationFrame(loop); }
    };
    if (reduceMotion) frame();
    else raf = requestAnimationFrame(loop);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("pointermove", onPointer);
      renderer.domElement.removeEventListener("pointerdown", onPress);
      document.removeEventListener("visibilitychange", onVisibility);
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          o.geometry.dispose();
          const mat = o.material as THREE.Material & { map?: THREE.Texture | null };
          mat.map?.dispose();
          mat.dispose();
        }
      });
      timer.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [variant, webglFailed]);

  return <div ref={mountRef} className={className} aria-hidden />;
}
