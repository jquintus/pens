const grid = document.getElementById("grid");
const loading = document.getElementById("loading");
const errorEl = document.getElementById("error");

function formatMetric(key, value) {
  if (value === null || value === undefined) return null;
  const k = key.replace(/_/g, " ");
  return `${k}: ${value}`;
}

function metricsChips(metrics) {
  if (!metrics || typeof metrics !== "object") return [];
  return Object.entries(metrics)
    .map(([k, v]) => formatMetric(k, v))
    .filter(Boolean)
    .slice(0, 6);
}

function downloadButton(label, href, disabled) {
  const a = document.createElement("a");
  a.className = disabled ? "btn btn--ghost" : "btn";
  a.textContent = label;
  if (disabled) {
    a.setAttribute("aria-disabled", "true");
    a.removeAttribute("href");
  } else {
    a.href = href;
    a.download = "";
  }
  return a;
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
  const d = pen.downloads || {};
  dl.appendChild(
    downloadButton(
      "STEP",
      d.step ? `./${d.step}` : "#",
      !d.step,
    ),
  );
  dl.appendChild(
    downloadButton(
      "STL",
      d.stl ? `./${d.stl}` : "#",
      !d.stl,
    ),
  );
  dl.appendChild(
    downloadButton(
      "G-code",
      d.gcode ? `./${d.gcode}` : "#",
      !d.gcode,
    ),
  );

  body.appendChild(title);
  body.appendChild(idLine);
  body.appendChild(desc);
  if (ul.children.length) body.appendChild(ul);
  body.appendChild(dl);

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
