"use client";

import React, { useEffect, useRef, useSyncExternalStore } from "react";
import * as THREE from "three";

interface CredLabHero3DProps {
  className?: string;
}

function subscribeReducedMotion(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}

function getReducedMotionSnapshot() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function getReducedMotionServerSnapshot() {
  return false;
}

function subscribeWebGL() {
  return () => {};
}

function getWebGLSnapshot() {
  if (typeof window === "undefined") return true;
  try {
    const testCanvas = document.createElement("canvas");
    return !!(testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function getWebGLServerSnapshot() {
  return true;
}

export function CredLabHero3D({ className = "" }: CredLabHero3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const webGLSupported = useSyncExternalStore(
    subscribeWebGL,
    getWebGLSnapshot,
    getWebGLServerSnapshot
  );
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    getReducedMotionServerSnapshot
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || reducedMotion || !webGLSupported) return;

    let animationFrameId: number;
    let isVisible = true;

    // Dimensions
    const width = container.clientWidth || 500;
    const height = container.clientHeight || 500;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 0, 11);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // Root Assembly Group
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // Materials
    const titaniumMaterial = new THREE.MeshStandardMaterial({
      color: 0x242424,
      roughness: 0.28,
      metalness: 0.88,
    });

    const titaniumDarkMaterial = new THREE.MeshStandardMaterial({
      color: 0x181818,
      roughness: 0.35,
      metalness: 0.92,
    });

    const orangeCoreMaterial = new THREE.MeshStandardMaterial({
      color: 0xff6b2c,
      emissive: 0xff6b2c,
      emissiveIntensity: 0.6,
      roughness: 0.2,
      metalness: 0.5,
    });

    const amberAccentMaterial = new THREE.MeshStandardMaterial({
      color: 0xffb547,
      emissive: 0xffb547,
      emissiveIntensity: 0.4,
      roughness: 0.15,
      metalness: 0.6,
    });

    // Outer Tech Chassis Ring (Faceted Octagon)
    const ringGroup = new THREE.Group();
    const ringSegments = 8;
    const ringRadius = 4.2;
    for (let i = 0; i < ringSegments; i++) {
      const angle = (i / ringSegments) * Math.PI * 2;
      const nextAngle = ((i + 1) / ringSegments) * Math.PI * 2;

      const p1 = new THREE.Vector3(Math.cos(angle) * ringRadius, Math.sin(angle) * ringRadius, 0);
      const p2 = new THREE.Vector3(Math.cos(nextAngle) * ringRadius, Math.sin(nextAngle) * ringRadius, 0);

      const segmentLength = p1.distanceTo(p2);
      const barGeo = new THREE.BoxGeometry(0.12, segmentLength, 0.25);
      const barMesh = new THREE.Mesh(barGeo, titaniumDarkMaterial);

      const midPoint = p1.clone().add(p2).multiplyScalar(0.5);
      barMesh.position.copy(midPoint);
      barMesh.rotation.z = Math.atan2(p2.y - p1.y, p2.x - p1.x) - Math.PI / 2;
      ringGroup.add(barMesh);

      // Node joints on corners
      if (i % 2 === 0) {
        const jointGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.35, 6);
        const jointMesh = new THREE.Mesh(jointGeo, amberAccentMaterial);
        jointMesh.position.copy(p1);
        jointMesh.rotation.x = Math.PI / 2;
        ringGroup.add(jointMesh);
      }
    }
    rootGroup.add(ringGroup);

    // Left Code Bracket < Assembly
    const leftBracketGroup = new THREE.Group();
    leftBracketGroup.position.set(-1.6, 0, 0);

    const bracketArmTopGeo = new THREE.BoxGeometry(0.42, 2.2, 0.5);
    const bracketArmTop = new THREE.Mesh(bracketArmTopGeo, titaniumMaterial);
    bracketArmTop.position.set(0.7, 0.85, 0);
    bracketArmTop.rotation.z = Math.PI / 4.8;
    leftBracketGroup.add(bracketArmTop);

    const bracketArmBottomGeo = new THREE.BoxGeometry(0.42, 2.2, 0.5);
    const bracketArmBottom = new THREE.Mesh(bracketArmBottomGeo, titaniumMaterial);
    bracketArmBottom.position.set(0.7, -0.85, 0);
    bracketArmBottom.rotation.z = -Math.PI / 4.8;
    leftBracketGroup.add(bracketArmBottom);

    rootGroup.add(leftBracketGroup);

    // Right Code Bracket > Assembly
    const rightBracketGroup = new THREE.Group();
    rightBracketGroup.position.set(1.6, 0, 0);

    const rightArmTop = new THREE.Mesh(bracketArmTopGeo, titaniumMaterial);
    rightArmTop.position.set(-0.7, 0.85, 0);
    rightArmTop.rotation.z = -Math.PI / 4.8;
    rightBracketGroup.add(rightArmTop);

    const rightArmBottom = new THREE.Mesh(bracketArmBottomGeo, titaniumMaterial);
    rightArmBottom.position.set(-0.7, -0.85, 0);
    rightArmBottom.rotation.z = Math.PI / 4.8;
    rightBracketGroup.add(rightArmBottom);

    rootGroup.add(rightBracketGroup);

    // Integrated Verification Checkmark Motif ✓
    const checkmarkGroup = new THREE.Group();
    checkmarkGroup.position.set(-0.15, -0.15, 0.45);

    // Short stroke of checkmark
    const checkShortGeo = new THREE.BoxGeometry(0.46, 1.4, 0.55);
    const checkShortMesh = new THREE.Mesh(checkShortGeo, orangeCoreMaterial);
    checkShortMesh.position.set(-0.55, -0.1, 0);
    checkShortMesh.rotation.z = -Math.PI / 4;
    checkmarkGroup.add(checkShortMesh);

    // Long stroke of checkmark
    const checkLongGeo = new THREE.BoxGeometry(0.46, 2.8, 0.55);
    const checkLongMesh = new THREE.Mesh(checkLongGeo, orangeCoreMaterial);
    checkLongMesh.position.set(0.8, 0.45, 0);
    checkLongMesh.rotation.z = Math.PI / 5.2;
    checkmarkGroup.add(checkLongMesh);

    rootGroup.add(checkmarkGroup);

    // Floating Data Particles & Geometric Polyhedrons
    const particleCount = 28;
    const particleMeshes: {
      mesh: THREE.Mesh;
      basePos: THREE.Vector3;
      speed: number;
      orbitRadius: number;
      orbitSpeed: number;
      phase: number;
    }[] = [];

    const geomOcta = new THREE.OctahedronGeometry(0.2, 0);
    const geomTetra = new THREE.TetrahedronGeometry(0.24, 0);
    const geomBox = new THREE.BoxGeometry(0.18, 0.18, 0.18);

    for (let i = 0; i < particleCount; i++) {
      const geo = i % 3 === 0 ? geomOcta : i % 3 === 1 ? geomTetra : geomBox;
      const mat = i % 2 === 0 ? orangeCoreMaterial : amberAccentMaterial;
      const mesh = new THREE.Mesh(geo, mat);

      const radius = 3.2 + Math.random() * 2.8;
      const theta = Math.random() * Math.PI * 2;
      const phi = (Math.random() - 0.5) * Math.PI * 0.8;

      const basePos = new THREE.Vector3(
        radius * Math.cos(theta) * Math.cos(phi),
        radius * Math.sin(phi),
        radius * Math.sin(theta) * Math.cos(phi)
      );

      mesh.position.copy(basePos);
      rootGroup.add(mesh);

      particleMeshes.push({
        mesh,
        basePos,
        speed: 0.5 + Math.random() * 1.5,
        orbitRadius: radius,
        orbitSpeed: (Math.random() - 0.5) * 0.8,
        phase: Math.random() * Math.PI * 2,
      });
    }

    // Lights
    const ambientLight = new THREE.AmbientLight(0xfff7ef, 1.2);
    scene.add(ambientLight);

    const dirKeyLight = new THREE.DirectionalLight(0xffffff, 2.2);
    dirKeyLight.position.set(6, 8, 10);
    scene.add(dirKeyLight);

    const orangeCoreLight = new THREE.PointLight(0xff6b2c, 4.0, 12);
    orangeCoreLight.position.set(0, 0, 2);
    scene.add(orangeCoreLight);

    const amberRimLight = new THREE.DirectionalLight(0xffb547, 2.0);
    amberRimLight.position.set(-8, -4, -4);
    scene.add(amberRimLight);

    // Mouse Interaction
    let targetRotationX = 0;
    let targetRotationY = 0;
    let currentRotationX = 0;
    let currentRotationY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
      targetRotationY = x * 0.45;
      targetRotationX = y * 0.35;
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth || 500;
      const newHeight = container.clientHeight || 500;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Visibility Observer to throttle/pause when offscreen
    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible = entry.isIntersecting;
        });
      },
      { threshold: 0.05 }
    );
    visibilityObserver.observe(container);

    // Animation Loop
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isVisible) return;

      const elapsed = clock.getElapsedTime();

      // Smooth Lerp for Mouse Parallax
      currentRotationX += (targetRotationX - currentRotationX) * 0.05;
      currentRotationY += (targetRotationY - currentRotationY) * 0.05;

      // Continuous Slow Rotation + Parallax Tilt
      rootGroup.rotation.y = elapsed * 0.35 + currentRotationY;
      rootGroup.rotation.x = Math.sin(elapsed * 0.25) * 0.1 + currentRotationX;
      rootGroup.rotation.z = Math.cos(elapsed * 0.2) * 0.05;

      // Subtle breathing motion for checkmark
      checkmarkGroup.position.z = 0.45 + Math.sin(elapsed * 1.5) * 0.08;

      // Counter-rotate outer chassis ring slowly
      ringGroup.rotation.z = -elapsed * 0.15;

      // Animate floating particles
      for (let i = 0; i < particleMeshes.length; i++) {
        const p = particleMeshes[i];
        p.mesh.rotation.x += 0.02 * p.speed;
        p.mesh.rotation.y += 0.03 * p.speed;

        const currentAngle = p.phase + elapsed * p.orbitSpeed;
        p.mesh.position.x = Math.cos(currentAngle) * p.orbitRadius;
        p.mesh.position.y = p.basePos.y + Math.sin(elapsed * p.speed + p.phase) * 0.35;
        p.mesh.position.z = Math.sin(currentAngle) * p.orbitRadius;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("mousemove", handleMouseMove);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();

      // Dispose Geometries and Materials
      bracketArmTopGeo.dispose();
      bracketArmBottomGeo.dispose();
      checkShortGeo.dispose();
      checkLongGeo.dispose();
      geomOcta.dispose();
      geomTetra.dispose();
      geomBox.dispose();
      titaniumMaterial.dispose();
      titaniumDarkMaterial.dispose();
      orangeCoreMaterial.dispose();
      amberAccentMaterial.dispose();
      renderer.dispose();

      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [reducedMotion, webGLSupported]);

  // CSS/SVG Fallback for when WebGL is unsupported or reduced motion is active
  if (!webGLSupported || reducedMotion) {
    return (
      <div
        className={`relative flex items-center justify-center select-none ${className}`}
        style={{ minHeight: "380px" }}
      >
        <div className="relative w-72 h-72 sm:w-88 sm:h-88 flex items-center justify-center">
          {/* Radial Orange Ambient Halo */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#FF6B2C]/20 via-[#FFB547]/10 to-transparent blur-3xl animate-pulse" />

          {/* Precision Octagonal Frame */}
          <div className="relative w-64 h-64 sm:w-76 sm:h-76 rounded-3xl border-2 border-[#FF6B2C]/30 bg-[#161616]/90 p-8 flex items-center justify-center shadow-2xl backdrop-blur-md">
            <svg
              viewBox="0 0 100 100"
              className="w-44 h-44 drop-shadow-[0_0_24px_rgba(255,107,44,0.4)]"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="fallback-bracket" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#4A4A4A" />
                  <stop offset="100%" stopColor="#252525" />
                </linearGradient>
                <linearGradient id="fallback-orange" x1="20" y1="20" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#FFB547" />
                  <stop offset="100%" stopColor="#FF6B2C" />
                </linearGradient>
              </defs>

              {/* Left Bracket < */}
              <path
                d="M32 25L14 50L32 75"
                stroke="url(#fallback-bracket)"
                strokeWidth="7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Right Bracket > */}
              <path
                d="M68 25L86 50L68 75"
                stroke="url(#fallback-bracket)"
                strokeWidth="7"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.4"
              />

              {/* Integrated Verification Checkmark ✓ */}
              <path
                d="M32 52L46 66L82 28"
                stroke="url(#fallback-orange)"
                strokeWidth="8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`relative flex items-center justify-center w-full h-[380px] sm:h-[480px] lg:h-[540px] select-none ${className}`}
      aria-label="Interactive 3D CredLab code verification centerpiece"
    />
  );
}

export default CredLabHero3D;
