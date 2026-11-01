const $ = id => document.getElementById(id);
const choices = {
  format: ["unknown", "parker-g2", "pilot-g2", "d1", "euro", "proprietary", "other"],
  ink_type: ["unknown", "gel", "ballpoint", "rollerball", "hybrid", "fountain", "felt-tip", "other"],
  tip_shape: ["unknown", "needle", "conical", "synergy", "ballpoint", "fineliner", "felt", "other"]
};
const colors = ["#ffbd66", "#72d9c7", "#d6a6f3", "#f092a4", "#a9c7ff"];
const fields = ["id", "brand", "model", "source_pens", "format", "ink_type", "tip_shape", "tip_size_mm", "measurement_status", "rating", "colors", "source_pen_colors", "notes", "ink_notes", "measurement_notes", "pen_photos", "ink_photos"];
const data = await fetch(`designer-data.json?v=${Date.now()}`).then(response => {
  if (!response.ok) throw Error("Cartridge catalog failed to load");
  return response.json();
});
const catalog = data.refills;
const persistedIds = new Set(catalog.map(record => record.id));
const filterFields = ["brand", "ink_type", "tip_shape", "tip_size_mm", "format", "measurement_status"];
let draft = null;
let selectedId = null;
let draftIsNew = false;
let baseSegments = [];
const photoIndex = { pen_photos: 0, ink_photos: 0 };

for (const [key, values] of Object.entries(choices)) {
  const select = $(`field-${key}`);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value.replaceAll("-", " ").replace(/^./, letter => letter.toUpperCase());
    select.append(option);
  }
}

function listLines(value) { return Array.isArray(value) ? value : []; }
function splitLines(text) { return text.split(/\r?\n/).map(item => item.trim()).filter(Boolean); }
function photoUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("assets/")) return `../${path}`;
  return path;
}
function renderPhotos(key, target) {
  const container = $(target);
  container.replaceChildren();
  const paths = splitLines($(`field-${key}`).value);
  if (key === "pen_photos" && !paths.length) paths.push(...listLines(draft.photos));
  const prefix = key === "pen_photos" ? "pen" : "ink";
  photoIndex[key] = paths.length ? (photoIndex[key] + paths.length) % paths.length : 0;
  const count = $(`${prefix}-photo-count`);
  const caption = $(`${prefix}-photo-caption`);
  const previous = document.querySelector(`[data-photo-prev="${key}"]`);
  const next = document.querySelector(`[data-photo-next="${key}"]`);
  previous.disabled = next.disabled = paths.length < 2;
  if (!paths.length) {
    count.textContent = "No photos yet";
    caption.textContent = "";
    const empty = document.createElement("div");
    empty.className = "photo-empty";
    empty.innerHTML = '<span aria-hidden="true">▧</span><p>No photos yet</p>';
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "Add photos";
    add.addEventListener("click", () => { setMode("edit"); $("photo-path-editor").open = true; $(`field-${key}`).focus(); });
    empty.append(add);
    container.append(empty);
    return;
  }
  const path = paths[photoIndex[key]];
  const image = document.createElement("img");
  image.src = photoUrl(path);
  image.alt = `${key === "pen_photos" ? "Source pen" : "Ink or writing sample"} photo ${photoIndex[key] + 1} of ${paths.length}`;
  image.loading = "lazy";
  image.addEventListener("error", () => {
    if (!container.contains(image)) return;
    const message = document.createElement("div");
    message.className = "photo-error";
    message.textContent = "Image could not be loaded";
    container.replaceChildren(message);
  }, { once: true });
  container.append(image);
  count.textContent = `${photoIndex[key] + 1} / ${paths.length}`;
  const filename = path.split(/[?#]/)[0].split("/").at(-1) || "Photo";
  try { caption.textContent = decodeURIComponent(filename); }
  catch { caption.textContent = filename; }
}
function catalogLabel(record) { return `${record.brand || "Unknown brand"} ${record.model || "Unknown model"}`.trim(); }
function normalizeSearch(value) { return String(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " "); }
function filterValue(record, key) {
  const value = record[key];
  return value === undefined || value === null || value === "" ? "unknown" : String(value);
}
function filterLabel(key, value) {
  if (value === "unknown") return "Unknown";
  if (key === "tip_size_mm") return `${value} mm`;
  return value.replaceAll("-", " ").replace(/^./, letter => letter.toUpperCase());
}
function refreshFilterOptions() {
  for (const key of filterFields) {
    const select = $(`filter-${key}`);
    const selected = select.value;
    const values = [...new Set(catalog.map(record => filterValue(record, key)))];
    values.sort(key === "tip_size_mm" ? (a, b) => a === "unknown" ? 1 : b === "unknown" ? -1 : Number(a) - Number(b) : (a, b) => a.localeCompare(b));
    select.replaceChildren(new Option("All", ""));
    for (const value of values) select.add(new Option(filterLabel(key, value), value));
    select.value = values.includes(selected) ? selected : "";
  }
}
function filteredRecords() {
  const query = normalizeSearch($("catalog-search").value);
  return catalog.filter(record => {
    if (filterFields.some(key => $(`filter-${key}`).value && filterValue(record, key) !== $(`filter-${key}`).value)) return false;
    return !query || normalizeSearch([record.id, record.brand, record.model, ...(record.source_pens || []), record.format, record.ink_type, record.tip_shape, record.tip_size_mm, record.measurement_status, ...(record.colors || []), ...(record.source_pen_colors || []), record.notes, record.ink_notes].join(" ")).includes(query);
  });
}
function renderCatalog() {
  const matches = filteredRecords();
  $("catalog-count").textContent = `${matches.length} of ${catalog.length} cartridges`;
  $("catalog-list").replaceChildren();
  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No cartridges match these filters.";
    $("catalog-list").append(empty);
  }
  for (const record of matches) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `catalog-item${record.id === selectedId ? " is-active" : ""}`;
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", String(record.id === selectedId));
    const title = document.createElement("strong");
    title.textContent = catalogLabel(record);
    const subtitle = document.createElement("span");
    subtitle.textContent = `${record.ink_type || "Ink unknown"} · ${record.measurement_status}${record.source_pens?.length ? ` · ${record.source_pens.join(", ")}` : ""}`;
    button.append(title, subtitle);
    button.addEventListener("click", () => selectRecord(record));
    $("catalog-list").append(button);
  }
}
function applyCatalogFilters() {
  const matches = filteredRecords();
  if ($("editor-content").hidden && !matches.some(record => record.id === selectedId)) {
    if (matches.length) { selectRecord(matches[0]); return; }
    selectedId = null;
    $("detail-view").hidden = true;
    $("editor-empty").hidden = false;
    $("editor-empty").textContent = "No cartridges match these filters.";
  }
  renderCatalog();
}

function addSegmentRow(segment = {}, index = null) {
  const row = document.createElement("div");
  row.className = "segment-row";
  if (index !== null) row.dataset.originalIndex = String(index);
  const values = segment.kind === "taper"
    ? [segment.diameter_start_mm, segment.diameter_end_mm, segment.end_distance_mm]
    : [segment.diameter_mm, "", segment.end_distance_mm];
  for (const [column, value] of values.entries()) {
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "any";
    input.inputMode = "decimal";
    input.setAttribute("aria-label", `${["Start diameter", "End diameter", "End distance from writing tip"][column]} for segment ${$("segment-rows").children.length + 1}`);
    input.value = value ?? "";
    row.append(input);
  }
  $("segment-rows").append(row);
  return row;
}
function readSegments() {
  const result = [];
  const issues = [];
  let lastEnd = 0;
  for (const [index, row] of [...$("segment-rows").children].entries()) {
    const [start, end, distance] = [...row.querySelectorAll("input")].map(input => input.value.trim());
    if (!start && !end && !distance) continue;
    if (!distance || (!start && !end && draft.measurement_status !== "incomplete")) {
      issues.push(`Finish segment ${index + 1}`);
      continue;
    }
    const original = row.dataset.originalIndex === undefined ? {} : baseSegments[Number(row.dataset.originalIndex)];
    const segment = { ...original };
    delete segment.diameter_mm;
    delete segment.diameter_start_mm;
    delete segment.diameter_end_mm;
    if (start && end) {
      segment.kind = "taper";
      segment.diameter_start_mm = Number(start);
      segment.diameter_end_mm = Number(end);
    } else {
      segment.kind = "cylinder";
      if (start || end) segment.diameter_mm = Number(start || end);
    }
    segment.end_distance_mm = Number(distance);
    if (!(segment.end_distance_mm > lastEnd)) issues.push(`Segment ${index + 1} must end after the previous segment`);
    lastEnd = segment.end_distance_mm;
    for (const key of ["diameter_mm", "diameter_start_mm", "diameter_end_mm"]) {
      if (key in segment && !(segment[key] > 0)) issues.push(`Segment ${index + 1} needs a positive diameter`);
    }
    result.push(segment);
  }
  return { result, issues };
}
function yaml(value, depth = 0) {
  const pad = "  ".repeat(depth);
  if (Array.isArray(value)) return value.map(item => `${pad}- ${item && typeof item === "object" ? `\n${yaml(item, depth + 1)}` : JSON.stringify(item)}`).join("\n");
  if (value && typeof value === "object") return Object.entries(value).map(([key, item]) => `${pad}${key}:${item && typeof item === "object" && (Array.isArray(item) && item.length || !Array.isArray(item)) ? `\n${yaml(item, depth + 1)}` : ` ${Array.isArray(item) ? "[]" : JSON.stringify(item)}`}`).join("\n");
  return `${pad}${JSON.stringify(value)}`;
}
function exportRecord() {
  const record = structuredClone(draft);
  delete record.geometry_ready;
  delete record.overall_length_mm;
  for (const key of ["notes", "ink_notes", "measurement_notes"]) if (!record[key]) delete record[key];
  for (const key of ["pen_photos", "ink_photos", "colors", "source_pen_colors", "source_pens"]) if (!record[key]?.length) delete record[key];
  if (!record.tip_size_mm) delete record.tip_size_mm;
  if (!record.rating) delete record.rating;
  return record;
}
function download(record) {
  const url = URL.createObjectURL(new Blob([yaml(record) + "\n"], { type: "text/yaml" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${record.id}.yml`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function updateExport(issues) {
  const record = exportRecord();
  if (!/^[a-z0-9_-]+$/.test(record.id || "")) issues.push("Use a lowercase slug for the ID");
  for (const key of ["brand", "model", "format"]) if (!record[key]?.trim()) issues.push(`Enter ${key}`);
  if (record.measurement_status !== "incomplete" && !record.segments.length) issues.push("Enter at least one measured segment");
  $("segment-error").textContent = [...new Set(issues)].join(" · ");
  $("download-yaml").disabled = issues.length > 0;
  $("copy-yaml").disabled = issues.length > 0;
  const link = $("github-yaml");
  const exists = persistedIds.has(record.id);
  const url = exists
    ? `https://github.com/jquintus/pens/edit/main/refills/${encodeURIComponent(record.id)}.yml`
    : `https://github.com/jquintus/pens/new/main?filename=${encodeURIComponent(`refills/${record.id}.yml`)}&value=${encodeURIComponent(yaml(record) + "\n")}`;
  link.textContent = exists ? "Edit on GitHub" : "Create file on GitHub";
  if (!issues.length && url.length < 7000) {
    link.href = url;
    link.removeAttribute("aria-disabled");
    link.title = exists ? "Copy YAML first, then paste it into the GitHub editor" : "";
  } else {
    link.removeAttribute("href");
    link.setAttribute("aria-disabled", "true");
    link.title = issues.join(" · ") || "Record is too large for a prefilled URL; use Download";
  }
}
function drawProfile(segments, target = "profile") {
  const svg = $(target);
  svg.replaceChildren();
  const complete = segments.filter(segment => segment.end_distance_mm > 0 && (segment.diameter_mm || segment.diameter_start_mm && segment.diameter_end_mm));
  if (!complete.length) {
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", "400"); label.setAttribute("y", "105"); label.setAttribute("text-anchor", "middle"); label.setAttribute("fill", "#8b93a8");
    label.textContent = "Add dimensions to preview the cartridge";
    svg.append(label); return;
  }
  const total = complete.at(-1).end_distance_mm;
  const maxDiameter = Math.max(...complete.flatMap(segment => [segment.diameter_mm, segment.diameter_start_mm, segment.diameter_end_mm].filter(Boolean)));
  // Use one scale on both axes so the profile keeps its actual proportions.
  const scale = Math.min(730 / total, 130 / maxDiameter);
  const originX = (800 - total * scale) / 2;
  let previous = 0;
  for (const [index, segment] of complete.entries()) {
    const startDiameter = segment.diameter_start_mm || segment.diameter_mm;
    const endDiameter = segment.diameter_end_mm || segment.diameter_mm;
    const x1 = originX + previous * scale;
    const x2 = originX + segment.end_distance_mm * scale;
    const y1 = startDiameter * scale / 2;
    const y2 = endDiameter * scale / 2;
    const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    polygon.setAttribute("points", `${x1},${100-y1} ${x2},${100-y2} ${x2},${100+y2} ${x1},${100+y1}`);
    polygon.setAttribute("fill", colors[index % colors.length]);
    polygon.setAttribute("stroke", "#111827");
    polygon.setAttribute("stroke-width", "2");
    svg.append(polygon);
    previous = segment.end_distance_mm;
  }
}
function renderDetail() {
  $("detail-title").textContent = catalogLabel(draft);
  $("detail-status").textContent = `${draft.measurement_status} · ${draft.format}`;
  const metadata = $("detail-metadata");
  metadata.replaceChildren();
  const facts = [
    ["Brand", draft.brand], ["Model", draft.model], ["Pens using this refill", draft.source_pens?.join(", ")], ["Physical format", draft.format],
    ["Ink type", draft.ink_type], ["Tip type", draft.tip_shape],
    ["Tip size", draft.tip_size_mm ? `${draft.tip_size_mm} mm` : null],
    ["Refill ink colors", draft.colors?.join(", ")], ["Source pen ink colors", draft.source_pen_colors?.join(", ")], ["Rating", draft.rating ? `${"★".repeat(draft.rating)}${"☆".repeat(5 - draft.rating)}` : "Not rated"],
    ["Measurements", draft.measurement_status]
  ];
  for (const [name, value] of facts) {
    if (!value) continue;
    const label = document.createElement("dt");
    label.textContent = name;
    const content = document.createElement("dd");
    content.textContent = value;
    metadata.append(label, content);
  }
  const links = [...(draft.links || []), ...(draft.variants || []).filter(item => item?.url).map(item => ({ label: item.color || "Product variant", url: item.url }))];
  const linkList = $("detail-links");
  linkList.replaceChildren();
  for (const item of links) {
    if (!/^https?:\/\//i.test(item?.url || "")) continue;
    const anchor = document.createElement("a");
    anchor.href = item.url;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = item.label || "Product link";
    linkList.append(anchor);
  }
  $("detail-links-section").hidden = !linkList.childElementCount;
  const priceList = $("detail-prices");
  priceList.replaceChildren();
  for (const price of draft.prices || []) {
    if (!/^https:\/\//i.test(price?.url || "") || !(price.amount_usd > 0)) continue;
    const row = document.createElement("div");
    row.className = "detail-price";
    const amount = document.createElement("strong");
    amount.textContent = `$${Number(price.amount_usd).toFixed(2)}`;
    const link = document.createElement("a");
    link.href = price.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `${price.source} · ${price.item}`;
    const checked = document.createElement("small");
    checked.textContent = `Checked ${price.checked_on}`;
    row.append(amount, link, checked);
    priceList.append(row);
  }
  $("detail-prices-section").hidden = !priceList.childElementCount;
  for (const [key, id] of [["notes", "detail-notes"], ["ink_notes", "detail-ink-notes"], ["measurement_notes", "detail-measurement-notes"]]) {
    $(id).textContent = draft[key]?.trim() || "No notes yet.";
    $(id).classList.toggle("is-empty", !draft[key]?.trim());
  }
  const segments = draft.segments || [];
  $("detail-overall-length").textContent = segments.length ? `${segments.at(-1).end_distance_mm} mm overall` : "No dimensions";
  const list = $("detail-segments");
  list.replaceChildren();
  let previous = 0;
  for (const [index, segment] of segments.entries()) {
    const row = document.createElement("div");
    row.className = "detail-segment";
    const label = document.createElement("strong");
    label.textContent = `${index + 1}. ${segment.kind === "taper" ? "Taper" : "Cylinder"}`;
    const dimension = document.createElement("span");
    const diameter = segment.kind === "taper" ? `Ø ${segment.diameter_start_mm ?? "?"} → ${segment.diameter_end_mm ?? "?"} mm` : `Ø ${segment.diameter_mm ?? "?"} mm`;
    dimension.textContent = `${diameter} · ${previous}–${segment.end_distance_mm ?? "?"} mm from tip`;
    row.append(label, dimension);
    list.append(row);
    if (Number.isFinite(segment.end_distance_mm)) previous = segment.end_distance_mm;
  }
  if (!segments.length) list.textContent = "No dimensions recorded yet.";
  drawProfile(segments, "detail-profile");
}
function setMode(mode) {
  $("detail-view").hidden = mode !== "view";
  $("editor-content").hidden = mode !== "edit";
  if (mode === "view") renderDetail();
}
function generatedId(record) {
  const parts = [record.brand, record.model, record.tip_size_mm ? `${record.tip_size_mm}mm` : ""].filter(Boolean);
  const base = (parts.join("-").normalize("NFKD").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")) || "cartridge";
  let candidate = base;
  for (let suffix = 2; catalog.some(item => item.id === candidate); suffix++) candidate = `${base}-${suffix}`;
  return candidate;
}
function syncDraft() {
  if (!draft) return;
  for (const key of fields) {
    const value = $(`field-${key}`).value.trim();
    if (["pen_photos", "ink_photos", "source_pens"].includes(key)) draft[key] = splitLines(value);
    else if (["colors", "source_pen_colors"].includes(key)) draft[key] = value.split(",").map(item => item.trim()).filter(Boolean);
    else if (["rating", "tip_size_mm"].includes(key)) draft[key] = value ? Number(value) : undefined;
    else draft[key] = value;
  }
  if (draftIsNew) {
    draft.id = generatedId(draft);
    $("field-id").value = draft.id;
  }
  const { result, issues } = readSegments();
  draft.segments = result;
  draft.geometry_ready = draft.measurement_status !== "incomplete" && !issues.length && !!result.length;
  draft.overall_length_mm = draft.geometry_ready ? result.at(-1).end_distance_mm : null;
  $("record-title").textContent = catalogLabel(draft);
  $("record-status").textContent = draftIsNew ? "New record" : `${draft.measurement_status} · ${draft.format}`;
  $("overall-length").textContent = result.length ? `${result.at(-1).end_distance_mm} mm overall` : "No dimensions";
  $("design-with-cartridge").href = `designer.html?refill=${encodeURIComponent(draft.id)}`;
  $("design-with-cartridge").hidden = draftIsNew || !draft.geometry_ready;
  renderPhotos("pen_photos", "pen-photo-preview");
  renderPhotos("ink_photos", "ink-photo-preview");
  drawProfile(result);
  renderDetail();
  updateExport(issues);
}
function selectRecord(record, isNew = false) {
  draft = structuredClone(record);
  baseSegments = structuredClone(record.segments || []);
  selectedId = isNew ? null : record.id;
  draftIsNew = isNew;
  photoIndex.pen_photos = photoIndex.ink_photos = 0;
  $("editor-empty").hidden = true;
  $("photo-path-editor").open = false;
  for (const key of fields) {
    let value = draft[key];
    if (["colors", "source_pen_colors"].includes(key)) value = listLines(value).join(", ");
    if (["pen_photos", "ink_photos", "source_pens"].includes(key)) value = listLines(value).join("\n");
    $(`field-${key}`).value = value ?? (key in choices ? "unknown" : "");
  }
  $("segment-rows").replaceChildren();
  (draft.segments || []).forEach((segment, index) => addSegmentRow(segment, index));
  addSegmentRow();
  renderCatalog();
  syncDraft();
  setMode(isNew ? "edit" : "view");
  if (!isNew) history.replaceState(null, "", `?id=${encodeURIComponent(record.id)}`);
}

refreshFilterOptions();
$("catalog-search").addEventListener("input", applyCatalogFilters);
for (const key of filterFields) $(`filter-${key}`).addEventListener("change", applyCatalogFilters);
$("clear-filters").addEventListener("click", () => {
  $("catalog-search").value = "";
  for (const key of filterFields) $(`filter-${key}`).value = "";
  applyCatalogFilters();
});
$("new-cartridge").addEventListener("click", () => { selectRecord({ id: "", brand: "", model: "", format: "unknown", ink_type: "unknown", tip_shape: "unknown", measurement_status: "incomplete", segments: [] }, true); history.replaceState(null, "", location.pathname); $("field-brand").focus(); });
for (const key of fields) $(`field-${key}`).addEventListener("input", syncDraft);
$("segment-rows").addEventListener("input", event => {
  const row = event.target.closest(".segment-row");
  if (row === $("segment-rows").lastElementChild && [...row.querySelectorAll("input")].some(input => input.value.trim())) addSegmentRow();
  syncDraft();
});
$("segment-rows").addEventListener("focusout", event => {
  const row = event.target.closest(".segment-row");
  if (row && row !== $("segment-rows").lastElementChild && ![...row.querySelectorAll("input")].some(input => input.value.trim())) row.remove();
});
$("download-yaml").addEventListener("click", () => download(exportRecord()));
$("copy-yaml").addEventListener("click", async () => {
  const button = $("copy-yaml");
  try {
    await navigator.clipboard.writeText(yaml(exportRecord()) + "\n");
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }
  setTimeout(() => { button.textContent = "Copy YAML"; }, 2000);
});
$("edit-record").addEventListener("click", () => setMode("edit"));
$("done-editing").addEventListener("click", () => {
  syncDraft();
  if ($("download-yaml").disabled) { $("segment-error").scrollIntoView({ behavior: "smooth", block: "center" }); return; }
  const existing = catalog.findIndex(record => record.id === selectedId);
  if (existing >= 0) catalog[existing] = structuredClone(draft);
  else catalog.push(structuredClone(draft));
  selectedId = draft.id;
  draftIsNew = false;
  refreshFilterOptions();
  renderCatalog();
  setMode("view");
  history.replaceState(null, "", `?id=${encodeURIComponent(draft.id)}`);
});
for (const key of ["pen_photos", "ink_photos"]) {
  document.querySelector(`[data-photo-prev="${key}"]`).addEventListener("click", () => { photoIndex[key]--; renderPhotos(key, key === "pen_photos" ? "pen-photo-preview" : "ink-photo-preview"); });
  document.querySelector(`[data-photo-next="${key}"]`).addEventListener("click", () => { photoIndex[key]++; renderPhotos(key, key === "pen_photos" ? "pen-photo-preview" : "ink-photo-preview"); });
}
const initial = new URLSearchParams(location.search).get("id");
selectRecord(catalog.find(record => record.id === initial) || catalog.find(record => record.geometry_ready) || catalog[0]);
