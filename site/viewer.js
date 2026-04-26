const THREE_MODULE_URL = "https://esm.sh/three@0.164.1";
const ORBIT_CONTROLS_MODULE_URL =
  "https://esm.sh/three@0.164.1/examples/jsm/controls/OrbitControls.js";
const STL_LOADER_MODULE_URL =
  "https://esm.sh/three@0.164.1/examples/jsm/loaders/STLLoader.js";

let viewerModulesPromise;

export async function ensureViewerModules() {
  if (!viewerModulesPromise) {
    viewerModulesPromise = Promise.all([
      import(THREE_MODULE_URL),
      import(ORBIT_CONTROLS_MODULE_URL),
      import(STL_LOADER_MODULE_URL),
    ]).then(([THREE, controls, loaders]) => ({
      THREE,
      OrbitControls: controls.OrbitControls,
      STLLoader: loaders.STLLoader,
    }));
  }
  return viewerModulesPromise;
}

function loadStl(loader, url) {
  return new Promise((resolve, reject) => {
    loader.load(url, resolve, undefined, reject);
  });
}

export async function mountViewer(container, statusEl, url, state) {
  const clearChildren = (node) => {
    while (node.firstChild) node.removeChild(node.firstChild);
  };

  const setViewerStatus = (message) => {
    statusEl.textContent = message;
    statusEl.hidden = false;
  };

  const clearViewer = () => {
    if (typeof state.cleanup === "function") {
      state.cleanup();
    }
    state.cleanup = null;
    clearChildren(container);
  };

  clearViewer();
  setViewerStatus("Loading 3D preview...");

  try {
    const { THREE, OrbitControls, STLLoader } = await ensureViewerModules();
    if (state.token !== state.currentToken) return;

    const width = Math.max(container.clientWidth, 1);
    const height = Math.max(container.clientHeight, 1);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07090f);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 5000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    container.appendChild(renderer.domElement);

    const ambient = new THREE.HemisphereLight(0xcad5ff, 0x141821, 1.5);
    const key = new THREE.DirectionalLight(0xffffff, 1.35);
    const rim = new THREE.DirectionalLight(0x7aa2ff, 0.85);
    key.position.set(2, 4, 3);
    rim.position.set(-3, 1, -2);
    scene.add(ambient, key, rim);

    const gridHelper = new THREE.GridHelper(200, 18, 0x365590, 0x182339);
    gridHelper.position.y = -18;
    scene.add(gridHelper);

    const loader = new STLLoader();
    const cacheBustedUrl = url + (url.includes('?') ? '&' : '?') + 't=' + Date.now();
    const geometry = await loadStl(loader, cacheBustedUrl);
    if (state.token !== state.currentToken) {
      geometry.dispose();
      renderer.dispose();
      clearChildren(container);
      return;
    }

    geometry.computeVertexNormals();
    geometry.center();

    const material = new THREE.MeshStandardMaterial({
      color: 0x9db8ff,
      metalness: 0.14,
      roughness: 0.42,
    });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const box = new THREE.Box3().setFromObject(mesh);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 1);

    gridHelper.scale.setScalar(Math.max(radius / 12, 1));
    gridHelper.position.y = box.min.y - radius * 0.08;

    camera.position.set(radius * 1.8, radius * 1.15, radius * 1.8);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;
    controls.minDistance = radius * 0.8;
    controls.maxDistance = radius * 6;
    controls.target.copy(sphere.center);
    controls.update();

    let frame = 0;
    const resize = () => {
      const nextWidth = Math.max(container.clientWidth, 1);
      const nextHeight = Math.max(container.clientHeight, 1);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight, false);
    };

    const onWindowResize = () => resize();
    window.addEventListener("resize", onWindowResize);

    let resizeObserver = null;
    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(() => resize());
      resizeObserver.observe(container);
    }

    state.cleanup = () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onWindowResize);
      if (resizeObserver) resizeObserver.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      clearChildren(container);
    };

    const render = () => {
      frame = requestAnimationFrame(render);
      controls.update();
      renderer.render(scene, camera);
    };

    statusEl.hidden = true;
    render();
  } catch (e) {
    clearViewer();
    setViewerStatus(
      e instanceof Error ? `Preview failed: ${e.message}` : `Preview failed: ${String(e)}`,
    );
  }
}
