const grid = document.getElementById("grid");
const loading = document.getElementById("loading");
const errorEl = document.getElementById("error");
const preview = document.getElementById("preview");
const previewClose = document.getElementById("preview-close");
const previewDismiss = document.getElementById("preview-dismiss");
const previewTitle = document.getElementById("preview-title");
const previewMeta = document.getElementById("preview-meta");
const previewDescription = document.getElementById("preview-description");
const previewMetrics = document.getElementById("preview-metrics");
const previewDownloads = document.getElementById("preview-downloads");
const viewer = document.getElementById("viewer");
const viewerStatus = document.getElementById("viewer-status");

let viewerModulesPromise;

const viewerState = {
  cleanup: null,
  token: 0,
};

function formatMetric(key, value) {
  if (value === null || value === undefined) return null;
  const k = key.replace(/_/g, " ");
  return `${k}: ${value}`;
}

function metricsChips(metrics, limit = 6) {
  if (!metrics || typeof metrics !== "object") return [];
  const lines = Object.entries(metrics)
    .map(([k, v]) => formatMetric(k, v))
    .filter(Boolean);
  return Number.isFinite(limit) ? lines.slice(0, limit) : lines;
}

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function downloadButton(label, href, disabled) {
  const a = document.createElement("a");
  a.className = disabled ? "btn btn--ghost" : "btn";
  a.textContent = label;
  if (disabled) {
    a.setAttribute("aria-disabled", "true");
  } else {
    a.href = href;
    a.download = "";
  }
  return a;
}

function previewButton(disabled) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "card__preview-trigger";
  button.textContent = disabled ? "3D preview pending build" : "Open 3D preview";
  button.disabled = disabled;
  return button;
}

function renderDownloads(container, downloads) {
  clearChildren(container);
  const d = downloads || {};
  container.appendChild(downloadButton("STEP", d.step ? `./${d.step}` : "#", !d.step));
  container.appendChild(downloadButton("STL", d.stl ? `./${d.stl}` : "#", !d.stl));
  container.appendChild(downloadButton("G-code", d.gcode ? `./${d.gcode}` : "#", !d.gcode));
}

function setViewerStatus(message) {
  viewerStatus.textContent = message;
  viewerStatus.hidden = false;
}

function clearViewer() {
  if (typeof viewerState.cleanup === "function") {
    viewerState.cleanup();
  }
  viewerState.cleanup = null;
  clearChildren(viewer);
}

function closePreview() {
  viewerState.token += 1;
  clearViewer();
  preview.hidden = true;
  document.body.classList.remove("is-modal-open");
}

function openPreview(pen) {
  previewTitle.textContent = pen.title;
  previewMeta.textContent = `${pen.id} | ${pen.slug}`;
  previewDescription.textContent = pen.description || "No description yet.";

  clearChildren(previewMetrics);
  for (const line of metricsChips(pen.metrics, Number.POSITIVE_INFINITY)) {
    const li = document.createElement("li");
    li.textContent = line;
    previewMetrics.appendChild(li);
  }

  renderDownloads(previewDownloads, pen.downloads);

  preview.hidden = false;
  document.body.classList.add("is-modal-open");

  if (!pen.downloads?.stl) {
    clearViewer();
    setViewerStatus("Preview requires an STL sidecar. Run the build/deploy flow once to publish it.");
    return;
  }

  const token = viewerState.token + 1;
  viewerState.token = token;
  mountViewer(`./${pen.downloads.stl}`, token);
}

async function ensureViewerModules() {
  if (!viewerModulesPromise) {
    viewerModulesPromise = Promise.all([
      import("three"),
      import("three/addons/controls/OrbitControls.js"),
      import("three/addons/loaders/STLLoader.js"),
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

async function mountViewer(url, token) {
  clearViewer();
  setViewerStatus("Loading 3D preview...");

  try {
    const { THREE, OrbitControls, STLLoader } = await ensureViewerModules();
    if (token !== viewerState.token) return;

    const width = Math.max(viewer.clientWidth, 1);
    const height = Math.max(viewer.clientHeight, 1);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07090f);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 5000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    viewer.appendChild(renderer.domElement);

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
    const geometry = await loadStl(loader, url);
    if (token !== viewerState.token) {
      geometry.dispose();
      renderer.dispose();
      clearChildren(viewer);
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
      const nextWidth = Math.max(viewer.clientWidth, 1);
      const nextHeight = Math.max(viewer.clientHeight, 1);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight, false);
    };

    const onWindowResize = () => resize();
    window.addEventListener("resize", onWindowResize);

    let resizeObserver = null;
    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(() => resize());
      resizeObserver.observe(viewer);
    }

    viewerState.cleanup = () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onWindowResize);
      if (resizeObserver) resizeObserver.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      clearChildren(viewer);
    };

    const render = () => {
      frame = requestAnimationFrame(render);
      controls.update();
      renderer.render(scene, camera);
    };

    viewerStatus.hidden = true;
    render();
  } catch (e) {
    clearViewer();
    setViewerStatus(
      e instanceof Error ? `Preview failed: ${e.message}` : `Preview failed: ${String(e)}`,
    );
  }
}

function renderCard(pen) {
  const article = document.createElement("article");
  article.className = "card";

  const visual = document.createElement("div");
  visual.className = "card__visual";

  if (pen.images && pen.images.length) {
    const img = document.createElement("img");
    img.src = `./${pen.images[0]}`;
    img.alt = `${pen.title} preview`;
    img.loading = "lazy";
    visual.appendChild(img);
  } else {
    visual.classList.add("card__visual--empty");
    visual.textContent = "Add images in assets/ + gallery in config";
  }

  const previewTrigger = previewButton(!pen.downloads?.stl);
  previewTrigger.addEventListener("click", () => openPreview(pen));
  visual.appendChild(previewTrigger);

  const body = document.createElement("div");
  body.className = "card__body";

  const title = document.createElement("h2");
  title.className = "card__title";
  title.textContent = pen.title;

  const idLine = document.createElement("p");
  idLine.className = "card__id";
  idLine.textContent = pen.id;

  const desc = document.createElement("p");
  desc.className = "card__desc";
  desc.textContent = pen.description || "No description yet.";

  const ul = document.createElement("ul");
  ul.className = "metrics";
  for (const line of metricsChips(pen.metrics)) {
    const li = document.createElement("li");
    li.textContent = line;
    ul.appendChild(li);
  }

  const dl = document.createElement("div");
  dl.className = "downloads";
  renderDownloads(dl, pen.downloads);

  body.appendChild(title);
  body.appendChild(idLine);
  body.appendChild(desc);
  if (ul.children.length) body.appendChild(ul);
  body.appendChild(dl);

  article.appendChild(visual);
  article.appendChild(body);
  return article;
}

previewClose.addEventListener("click", closePreview);
previewDismiss.addEventListener("click", closePreview);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !preview.hidden) closePreview();
});

async function run() {
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`data.json HTTP ${res.status}`);
    const data = await res.json();
    const pens = data.pens || [];
    loading.hidden = true;
    if (!pens.length) {
      errorEl.hidden = false;
      errorEl.textContent = "No configurations found in data.json.";
      return;
    }
    grid.hidden = false;
    for (const pen of pens) {
      grid.appendChild(renderCard(pen));
    }
  } catch (e) {
    loading.hidden = true;
    errorEl.hidden = false;
    errorEl.textContent = e instanceof Error ? e.message : String(e);
  }
}

run();
