"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

type WinterSceneProps = {
  dx: number;
  dy: number;
};

export function WinterScene({ dx, dy }: WinterSceneProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const targetRef = useRef({ dx, dy });

  useEffect(() => {
    targetRef.current = { dx, dy };
  }, [dx, dy]);

  useEffect(() => {
    const mount = hostRef.current;
    if (!mount) {
      return;
    }
    const mountElement: HTMLDivElement = mount;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    mountElement.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 1.2, 9);

    const root = new THREE.Group();
    root.position.y = -0.35;
    scene.add(root);

    const ambient = new THREE.HemisphereLight(0xffffff, 0x7db7cb, 2.4);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 3.2);
    key.position.set(4, 8, 5);
    scene.add(key);

    const fill = new THREE.PointLight(0x9cfce0, 25, 12);
    fill.position.set(-3, 1.5, 4);
    scene.add(fill);

    const iceMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xf4fffb,
      roughness: 0.25,
      metalness: 0,
      transmission: 0.28,
      thickness: 0.45,
      clearcoat: 0.8,
      clearcoatRoughness: 0.18,
      transparent: true,
      opacity: 0.9,
    });
    const rimMaterial = new THREE.MeshStandardMaterial({
      color: 0xbff7ee,
      emissive: 0x1d6d63,
      emissiveIntensity: 0.3,
      roughness: 0.42,
      transparent: true,
      opacity: 0.72,
    });
    const modelMaterial = new THREE.MeshStandardMaterial({
      color: 0xe9fbf8,
      emissive: 0x4eeedc,
      emissiveIntensity: 0.08,
      roughness: 0.56,
      side: THREE.DoubleSide,
    });
    const edgeMaterial = new THREE.LineBasicMaterial({
      color: 0x64e9de,
      transparent: true,
      opacity: 0.28,
    });
    const edgeGeometries: THREE.EdgesGeometry[] = [];

    const loader = new GLTFLoader();
    const fallbackIgloo = new THREE.Group();
    root.add(fallbackIgloo);

    const blockGeometry = new THREE.BoxGeometry(0.82, 0.36, 0.32);
    const miniBlockGeometry = new THREE.BoxGeometry(0.38, 0.18, 0.18);

    for (let row = 0; row < 7; row += 1) {
      const y = row * 0.34;
      const radius = 2.65 - row * 0.3;
      const count = Math.max(5, 12 - row);
      for (let index = 0; index < count; index += 1) {
        const angle = (index / count) * Math.PI * 1.55 + Math.PI * 0.72;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius * 0.42;
        if (z < -0.6) {
          continue;
        }

        const block = new THREE.Mesh(blockGeometry, iceMaterial);
        block.position.set(x, y, z);
        block.rotation.y = -angle + Math.PI / 2;
        block.rotation.z = (index % 2 === 0 ? 1 : -1) * 0.035;
        fallbackIgloo.add(block);
      }
    }

    for (let index = 0; index < 20; index += 1) {
      const block = new THREE.Mesh(miniBlockGeometry, rimMaterial);
      block.position.set(
        -3.2 + (index % 10) * 0.72,
        -0.12 + Math.sin(index) * 0.04,
        1.6 + Math.floor(index / 10) * 0.32,
      );
      block.rotation.y = 0.18 * Math.sin(index);
      root.add(block);
    }

    const door = new THREE.Mesh(
      new THREE.BoxGeometry(1.15, 1.12, 0.85),
      new THREE.MeshPhysicalMaterial({
        color: 0xdffff4,
        roughness: 0.2,
        transmission: 0.18,
        thickness: 0.5,
        transparent: true,
        opacity: 0.82,
      }),
    );
    door.position.set(0, 0.28, 2.02);
    fallbackIgloo.add(door);

    loader.load(
      "/assets/igloo-poly-google.glb",
      (gltf) => {
        const model = gltf.scene;
        model.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.material = modelMaterial;
            const edgeGeometry = new THREE.EdgesGeometry(mesh.geometry, 36);
            edgeGeometries.push(edgeGeometry);
            const edges = new THREE.LineSegments(
              edgeGeometry,
              edgeMaterial,
            );
            mesh.add(edges);
          }
        });

        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const scale = 3.75 / Math.max(size.x, size.y, size.z, 1);

        model.scale.setScalar(scale);
        model.position.set(
          -center.x * scale,
          -center.y * scale + 0.12,
          -center.z * scale + 0.25,
        );
        model.rotation.y = Math.PI;
        fallbackIgloo.visible = false;
        root.add(model);
      },
      undefined,
      () => {
        fallbackIgloo.visible = true;
      },
    );

    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(4.4, 96),
      new THREE.MeshStandardMaterial({
        color: 0xf8fffb,
        roughness: 0.75,
        transparent: true,
        opacity: 0.42,
      }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.33;
    root.add(floor);

    const snowCount = 650;
    const snowPositions = new Float32Array(snowCount * 3);
    for (let index = 0; index < snowCount; index += 1) {
      snowPositions[index * 3] = (Math.random() - 0.5) * 11;
      snowPositions[index * 3 + 1] = Math.random() * 6;
      snowPositions[index * 3 + 2] = (Math.random() - 0.5) * 8;
    }

    const snowGeometry = new THREE.BufferGeometry();
    snowGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(snowPositions, 3),
    );
    const snow = new THREE.Points(
      snowGeometry,
      new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.035,
        transparent: true,
        opacity: 0.78,
        depthWrite: false,
      }),
    );
    scene.add(snow);

    let frame = 0;
    let animation = 0;

    function resize() {
      const width = mountElement.clientWidth;
      const height = mountElement.clientHeight;
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    }

    function animate() {
      animation = requestAnimationFrame(animate);
      frame += 0.01;

      const target = targetRef.current;
      root.rotation.y += (target.dx * 0.34 - root.rotation.y) * 0.045;
      root.rotation.x += (target.dy * -0.1 - root.rotation.x) * 0.035;
      root.position.x += (target.dx * 0.35 - root.position.x) * 0.03;

      const position = snowGeometry.attributes.position;
      for (let index = 0; index < snowCount; index += 1) {
        const yIndex = index * 3 + 1;
        const xIndex = index * 3;
        snowPositions[yIndex] -= 0.012 + (index % 5) * 0.001;
        snowPositions[xIndex] +=
          Math.sin(frame + index) * 0.0015 + target.dx * 0.001;
        if (snowPositions[yIndex] < -0.7) {
          snowPositions[yIndex] = 5.6;
          snowPositions[xIndex] = (Math.random() - 0.5) * 11;
        }
      }
      position.needsUpdate = true;
      snow.rotation.y = frame * 0.08;

      renderer.render(scene, camera);
    }

    resize();
    animate();
    const observer = new ResizeObserver(resize);
    observer.observe(mountElement);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(animation);
      renderer.dispose();
      blockGeometry.dispose();
      miniBlockGeometry.dispose();
      snowGeometry.dispose();
      iceMaterial.dispose();
      rimMaterial.dispose();
      modelMaterial.dispose();
      edgeMaterial.dispose();
      edgeGeometries.forEach((geometry) => geometry.dispose());
      mountElement.removeChild(renderer.domElement);
    };
  }, []);

  return <div className="h-full min-h-[360px] w-full" ref={hostRef} />;
}
