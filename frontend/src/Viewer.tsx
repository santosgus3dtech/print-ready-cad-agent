import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Box, Grid2X2, Maximize, RotateCw, ScanLine } from 'lucide-react';

interface ViewerProps { url?: string; busy: boolean; dimensions?: number[] }

export default function Viewer({ url, busy, dimensions }: ViewerProps) {
  const host = useRef<HTMLDivElement>(null);
  const runtime = useRef<{
    renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera;
    controls: OrbitControls; grid: THREE.GridHelper; model?: THREE.Group; fit: () => void;
  } | null>(null);
  const [wireframe, setWireframe] = useState(false);
  const [grid, setGrid] = useState(true);
  const [rotate, setRotate] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const element = host.current!;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); }
    catch { setError('WebGL is unavailable in this browser.'); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.setClearColor(0xe7eaee);
    renderer.domElement.setAttribute('aria-label', 'Interactive CAD model');
    element.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
    camera.position.set(120, 150, 180);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.autoRotateSpeed = 1.1;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8c9ba7, 1.8));
    const light = new THREE.DirectionalLight(0xffffff, 3.2);
    light.position.set(-100, 250, 120);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
    light.shadow.camera.left = -250; light.shadow.camera.right = 250;
    light.shadow.camera.top = 250; light.shadow.camera.bottom = -250;
    light.shadow.bias = -0.0001;
    scene.add(light);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000),
      new THREE.MeshStandardMaterial({ color: 0xe7eaee, roughness: 1 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.1;
    ground.receiveShadow = true;
    scene.add(ground);
    const helper = new THREE.GridHelper(1000, 100, 0xb6c1ca, 0xcbd2d9);
    helper.position.y = -0.05;
    const gridMaterial = helper.material as THREE.Material;
    gridMaterial.transparent = true; gridMaterial.opacity = 0.6;
    scene.add(helper);
    const fit = () => {
      const model = runtime.current?.model;
      if (!model) return;
      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());
      const direction = new THREE.Vector3(.6, .68, 1).normalize();
      const right = new THREE.Vector3().crossVectors(camera.up, direction).normalize();
      const up = new THREE.Vector3().crossVectors(direction, right).normalize();
      const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      const tanH = tanV * Math.max(camera.aspect, .01);
      let distance = 1;
      // Fit every box corner in camera space, including its perspective depth.
      for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
        const corner = new THREE.Vector3(x, y, z).sub(center);
        distance = Math.max(distance, corner.dot(direction) + Math.max(
          Math.abs(corner.dot(right)) / tanH, Math.abs(corner.dot(up)) / tanV) * 1.18);
      }
      controls.target.copy(center);
      camera.position.copy(center).add(direction.multiplyScalar(distance));
      camera.near = 0.1; camera.far = Math.max(2000, distance * 20); camera.updateProjectionMatrix();
      controls.update();
    };
    runtime.current = { renderer, scene, camera, controls, grid: helper, fit };
    const observer = new ResizeObserver(() => {
      const { width, height } = element.getBoundingClientRect();
      renderer.setSize(width, height);
      camera.aspect = width / Math.max(height, 1); camera.updateProjectionMatrix();
      fit();
    });
    observer.observe(element);
    renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
    return () => {
      observer.disconnect(); renderer.setAnimationLoop(null); controls.dispose();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(material => material.dispose());
        }
      });
      renderer.dispose(); element.removeChild(renderer.domElement); runtime.current = null;
    };
  }, []);

  useEffect(() => {
    const state = runtime.current;
    if (!state || !url) return;
    let active = true;
    setError(''); setLoading(true);
    state.renderer.domElement.dataset.loaded = 'false';
    new GLTFLoader().load(url, gltf => {
      if (!active) { disposeModel(gltf.scene); return; }
      if (state.model) { state.scene.remove(state.model); disposeModel(state.model); }
      const model = gltf.scene;
      model.scale.setScalar(1000);
      model.rotation.x = -Math.PI / 2;
      model.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());
      model.position.x -= center.x; model.position.z -= center.z; model.position.y -= box.min.y;
      model.traverse(object => {
        if (object instanceof THREE.Mesh) {
          object.castShadow = true; object.receiveShadow = true;
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(material => {
            if (material instanceof THREE.MeshStandardMaterial) { material.roughness = .56; material.metalness = .05; }
          });
        }
      });
      state.model = model; state.scene.add(model); state.fit(); setWireframe(false);
      state.renderer.domElement.dataset.loaded = 'true';
      state.renderer.domElement.dataset.modelSource = url;
      setLoading(false);
    }, undefined, () => { if (active) { setError('The model preview could not be loaded.'); setLoading(false); } });
    return () => { active = false; };
  }, [url]);

  useEffect(() => {
    runtime.current?.model?.traverse(object => {
      if (object instanceof THREE.Mesh) {
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(material => { if (material instanceof THREE.MeshStandardMaterial) material.wireframe = wireframe; });
      }
    });
  }, [wireframe]);
  useEffect(() => { if (runtime.current) runtime.current.grid.visible = grid; }, [grid]);
  useEffect(() => { if (runtime.current) runtime.current.controls.autoRotate = rotate; }, [rotate]);

  return <section className="viewport" aria-label="Model viewport">
    <div className="canvas-host" ref={host} />
    <div className="viewer-toolbar">
      <div className="tool-group">
        <button title="Auto rotate" aria-label="Auto rotate" aria-pressed={rotate} onClick={() => setRotate(!rotate)}><RotateCw size={18} /></button>
        <button title="Wireframe" aria-label="Wireframe" aria-pressed={wireframe} onClick={() => setWireframe(!wireframe)}><Box size={18} /></button>
        <button title="Fit view" aria-label="Fit view" onClick={() => runtime.current?.fit()}><Maximize size={18} /></button>
        <button title="Show grid" aria-label="Show grid" aria-pressed={grid} onClick={() => setGrid(!grid)}><Grid2X2 size={18} /></button>
      </div>
      <span className="units">mm</span>
    </div>
    {(busy || loading) && <div className="canvas-state"><span className="spinner" />{busy ? 'Generating geometry' : 'Loading preview'}</div>}
    {error && <div className="canvas-state error" role="alert">{error}</div>}
    {!url && !busy && !error && <div className="canvas-state"><ScanLine size={24} /> No model generated</div>}
    <div className="axes" aria-hidden="true"><span className="axis-y">Y</span><span className="axis-z">Z</span><span className="axis-x">X</span></div>
    {dimensions && <div className="dimension-label">Layout: {dimensions.map(x => Math.round(x * 10) / 10).join(' × ')} mm</div>}
  </section>;
}

function disposeModel(model: THREE.Group) {
  model.traverse(object => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(material => material.dispose());
    }
  });
}
