"use client";

// A softly morphing 3D "voice orb" for the sign-in screens (three.js).
//
// - The sphere's surface is displaced on the GPU by animated 3D simplex noise,
//   shaded ink-navy → violet with a warm rim light to match the app's palette.
// - Two thin waveform rings orbit it, their radius modulated like a speech envelope.
// - `energyRef` (0–1) makes it react: the form bumps it on every keystroke so the orb
//   "listens" as you type; `busy` keeps it pulsing while you're being signed in.
// - Leans gently towards the pointer; pauses while the tab is hidden; renders a single
//   still frame for prefers-reduced-motion; cleans up all GPU resources on unmount.

import { useEffect, useRef, useState, type MutableRefObject } from "react";
import * as THREE from "three";

// Ashima Arts / Stefan Gustavson 3D simplex noise (MIT)
const NOISE_GLSL = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z); vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x; p1*=norm.y; p2*=norm.z; p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}`;

const VERTEX = /* glsl */ `
uniform float uTime;
uniform float uAmp;
varying vec3 vNormal;
varying vec3 vView;
varying float vDisp;
${NOISE_GLSL}
void main() {
  float n = snoise(normal * 1.4 + vec3(0.0, uTime * 0.32, 0.0));
  float detail = snoise(normal * 3.2 - vec3(uTime * 0.55)) * 0.35;
  float d = (n + detail) * uAmp;
  vec3 p = position + normal * d;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  vNormal = normalize(normalMatrix * normal);
  vView = -mv.xyz;
  vDisp = d;
  gl_Position = projectionMatrix * mv;
}`;

const FRAGMENT = /* glsl */ `
uniform vec3 uDeep;
uniform vec3 uMid;
uniform vec3 uRim;
varying vec3 vNormal;
varying vec3 vView;
varying float vDisp;
void main() {
  vec3 n = normalize(vNormal);
  float fresnel = pow(1.0 - max(dot(n, normalize(vView)), 0.0), 2.4);
  float key = max(dot(n, normalize(vec3(-0.45, 0.75, 0.55))), 0.0);
  vec3 base = mix(uDeep, uMid, smoothstep(-0.18, 0.22, vDisp) * 0.85 + 0.1);
  vec3 color = base * (0.9 + key * 0.45) + uRim * fresnel * 0.7;
  gl_FragColor = vec4(color, 1.0);
}`;

const RING_POINTS = 256;

function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export interface VoiceOrbProps {
  /** 0–1, read every frame; bump it to make the orb react. Decays on its own. */
  energyRef?: MutableRefObject<number>;
  /** Keeps the orb pulsing (e.g. while signing in). */
  busy?: boolean;
  className?: string;
}

export default function VoiceOrb({ energyRef, busy = false, className }: VoiceOrbProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const busyRef = useRef(busy);
  // Rendered client-side only (dynamic import with ssr: false), so `document` exists here
  const [webglFailed] = useState(() => !supportsWebGL());

  useEffect(() => { busyRef.current = busy; }, [busy]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || webglFailed) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      return;  // context creation can still fail (e.g. GPU blocklisted): the panel just stays plain
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);
    renderer.domElement.style.display = "block";

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0, 9);
    const group = new THREE.Group();
    scene.add(group);

    // Orb
    const orbGeometry = new THREE.IcosahedronGeometry(1.2, 64);
    const uniforms = {
      uTime: { value: 0 },
      uAmp: { value: 0.16 },
      uDeep: { value: new THREE.Color("#34497A") },
      uMid: { value: new THREE.Color("#8F89A8") },
      uRim: { value: new THREE.Color("#F0D3AE") },
    };
    const orbMaterial = new THREE.ShaderMaterial({ vertexShader: VERTEX, fragmentShader: FRAGMENT, uniforms });
    group.add(new THREE.Mesh(orbGeometry, orbMaterial));

    // Waveform rings
    const makeRing = (color: string, opacity: number) => {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(RING_POINTS * 3), 3));
      const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity });
      const line = new THREE.LineLoop(geometry, material);
      group.add(line);
      return { line, geometry, material };
    };
    const ringA = makeRing("#23345C", 0.38);
    const ringB = makeRing("#8A5A22", 0.28);
    ringA.line.rotation.x = Math.PI / 2.3;
    ringB.line.rotation.x = Math.PI / 1.85;
    ringB.line.rotation.y = 0.5;

    const updateRing = (ring: typeof ringA, radius: number, t: number, level: number, phase: number) => {
      const pos = ring.geometry.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < RING_POINTS; i++) {
        const a = (i / RING_POINTS) * Math.PI * 2;
        // A few travelling sine "formants", scaled by the current energy level
        const wave =
          Math.sin(a * 6 + t * 2.1 + phase) * 0.05 +
          Math.sin(a * 11 - t * 3.3 + phase) * 0.03 +
          Math.sin(a * 19 + t * 4.7) * 0.015;
        const r = radius + wave * (0.35 + level * 2.2);
        pos.setXYZ(i, Math.cos(a) * r, Math.sin(a) * r, 0);
      }
      pos.needsUpdate = true;
    };

    // Sizing
    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = `${w}px`;
      renderer.domElement.style.height = `${h}px`;
      camera.aspect = w / h;
      // Keep the orb fully visible on narrow/tall containers
      camera.position.z = w / h < 1 ? 9 / Math.max(w / h, 0.55) : 9;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    // Pointer parallax
    const target = { x: 0, y: 0 };
    const onPointer = (e: PointerEvent) => {
      target.x = (e.clientY / window.innerHeight - 0.5) * 0.35;
      target.y = (e.clientX / window.innerWidth - 0.5) * 0.5;
    };
    window.addEventListener("pointermove", onPointer);

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = new THREE.Timer();
    let level = 0;
    let raf = 0;

    const frame = (now?: number) => {
      timer.update(now);
      const dt = Math.min(timer.getDelta(), 0.05);
      const t = timer.getElapsed();
      const energy = energyRef?.current ?? 0;
      const busyPulse = busyRef.current ? 0.45 + Math.sin(t * 6) * 0.25 : 0;
      level += (Math.max(energy, busyPulse) - level) * Math.min(dt * 6, 1);
      if (energyRef) energyRef.current = Math.max(0, energy - dt * 0.9); // decays back to idle

      uniforms.uTime.value = t * (1 + level * 1.6);
      uniforms.uAmp.value = 0.14 + level * 0.22;
      updateRing(ringA, 1.9, t, level, 0);
      updateRing(ringB, 2.15, t * 0.8, level * 0.7, 1.7);

      group.rotation.y += (target.y + t * 0.08 - group.rotation.y) * 0.04;
      group.rotation.x += (target.x - group.rotation.x) * 0.04;
      group.scale.setScalar(1 + level * 0.05);
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
      document.removeEventListener("visibilitychange", onVisibility);
      orbGeometry.dispose(); orbMaterial.dispose();
      for (const ring of [ringA, ringB]) { ring.geometry.dispose(); ring.material.dispose(); }
      timer.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [energyRef, webglFailed]);

  return (
    <div ref={mountRef} className={className} aria-hidden>
      {webglFailed && (
        <div className="w-full h-full flex items-center justify-center">
          <div
            className="w-1/2 aspect-square rounded-full"
            style={{ background: "radial-gradient(circle at 35% 30%, #7A7490, #23345C 70%)", boxShadow: "0 0 80px rgba(227,185,138,0.35)" }}
          />
        </div>
      )}
    </div>
  );
}
