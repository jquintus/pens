import { mountViewer } from "../viewer.js";

const { stl } = JSON.parse(document.getElementById("preview-data").textContent);
const viewer = document.getElementById("viewer");
const status = document.getElementById("viewer-status");
const image = document.getElementById("main-image");
const state = { token: 1, currentToken: 1, cleanup: null };

function showImage(src) {
  state.currentToken++;
  if (state.cleanup) state.cleanup();
  state.cleanup = null;
  image.querySelector("img").src = src;
  image.hidden = false;
  viewer.hidden = true;
  status.hidden = true;
}

function showViewer() {
  if (!stl) return;
  image.hidden = true;
  viewer.hidden = false;
  status.hidden = false;
  state.currentToken++;
  state.token = state.currentToken;
  mountViewer(viewer, status, stl, state);
}

document.getElementById("show-viewer").addEventListener("click", showViewer);
for (const button of document.querySelectorAll("[data-image]")) {
  button.addEventListener("click", () => showImage(button.dataset.image));
}
if (stl) showViewer();
else showImage(image.querySelector("img").src);
window.addEventListener("pagehide", () => {
  state.currentToken++;
  if (state.cleanup) state.cleanup();
});
