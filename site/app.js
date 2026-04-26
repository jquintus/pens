const grid = document.getElementById("grid");
const loading = document.getElementById("loading");
const errorEl = document.getElementById("error");

const DEFAULT_PEN_IMAGE = "assets/default-pen.svg";

function formatDimension(key, value) {
  if (value === null || value === undefined) return null;
  const k = key.replace(/_/g, " ");
  return `${k}: ${value}`;
}

function noseConeChips(noseCone, limit = 6) {
  if (!noseCone || typeof noseCone !== "object") return [];
  const lines = Object.entries(noseCone)
    .map(([k, v]) => formatDimension(k, v))
    .filter(Boolean);
  return Number.isFinite(limit) ? lines.slice(0, limit) : lines;
}

function assetUrl(path) {
  return `./${path}`;
}

function resolveImages(pen) {
  if (Array.isArray(pen.images) && pen.images.length) return pen.images;
  return [DEFAULT_PEN_IMAGE];
}

function createImage(path, alt) {
  const img = document.createElement("img");
  img.src = assetUrl(path);
  img.alt = alt;
  img.loading = "lazy";
  img.addEventListener("error", () => {
    if (!img.dataset.fallbackApplied) {
      img.dataset.fallbackApplied = "true";
      img.src = assetUrl(DEFAULT_PEN_IMAGE);
    }
  });
  return img;
}

function renderCard(pen) {
  const article = document.createElement("article");
  article.className = "card";

  const visual = document.createElement("div");
  visual.className = "card__visual";
  const mainImage = resolveImages(pen)[0];
  visual.appendChild(createImage(mainImage, `${pen.title} preview`));

  const link = document.createElement("a");
  link.href = `./pens/${pen.slug}.html`;
  link.className = "card__preview-trigger";
  link.textContent = "View Details & 3D Preview";
  visual.appendChild(link);

  const body = document.createElement("div");
  body.className = "card__body";

  const title = document.createElement("h2");
  title.className = "card__title";
  const titleLink = document.createElement("a");
  titleLink.href = `./pens/${pen.slug}.html`;
  titleLink.textContent = pen.title;
  titleLink.style.textDecoration = "none";
  titleLink.style.color = "inherit";
  title.appendChild(titleLink);

  const idLine = document.createElement("p");
  idLine.className = "card__id";
  idLine.textContent = pen.id;

  const desc = document.createElement("p");
  desc.className = "card__desc";
  desc.textContent = pen.description || "No description yet.";

  const ul = document.createElement("ul");
  ul.className = "metrics";
  for (const line of noseConeChips(pen.nose_cone)) {
    const li = document.createElement("li");
    li.textContent = line;
    ul.appendChild(li);
  }

  body.appendChild(title);
  body.appendChild(idLine);
  body.appendChild(desc);
  if (ul.children.length) body.appendChild(ul);

  article.appendChild(visual);
  article.appendChild(body);
  return article;
}

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
