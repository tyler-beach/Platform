(function (root) {
  "use strict";

  function install(doc, host) {
    if (!doc || typeof doc.querySelectorAll !== "function" || typeof doc.createElement !== "function" || !doc.body) {
      return { count: 0 };
    }
    const figures = Array.from(doc.querySelectorAll("figure.diagram-figure"));
    const entries = figures.map((figure) => {
      const viewport = figure.querySelector(".diagram-viewport");
      const image = viewport && viewport.querySelector("img");
      if (!viewport || !image || !(image.currentSrc || image.src) || viewport.querySelector(".diagram-expand")) return null;
      const caption = figure.querySelector("figcaption");
      return { figure, viewport, image, caption: caption ? caption.textContent.trim() : "" };
    }).filter(Boolean);
    if (!entries.length) return { count: 0 };

    let viewer = null;
    const existingDialog = typeof doc.querySelector === "function" ? doc.querySelector("dialog.diagram-dialog") : null;
    if (existingDialog && existingDialog._diagramViewer) viewer = existingDialog._diagramViewer;
    if (!viewer) viewer = createViewer(doc);

    entries.forEach((entry) => {
      const button = doc.createElement("button");
      button.className = "diagram-expand";
      button.type = "button";
      button.textContent = "Expand";
      button.setAttribute("aria-haspopup", "dialog");
      button.setAttribute("aria-label", `Expand diagram: ${entry.caption || entry.image.alt || "Architecture diagram"}`);
      entry.viewport.appendChild(button);
      button.addEventListener("click", () => {
        const src = entry.image.currentSrc || entry.image.src;
        if (typeof viewer.dialog.showModal !== "function") {
          if (host && typeof host.open === "function") host.open(src, "_blank", "noopener");
          return;
        }
        viewer.opener = button;
        viewer.title.textContent = entry.caption || "Expanded diagram";
        viewer.image.src = src;
        viewer.image.alt = entry.image.alt || entry.caption || "Architecture diagram";
        viewer.caption.textContent = entry.caption;
        viewer.dialog.showModal();
        viewer.close.focus();
      });
    });

    return { count: entries.length, dialog: viewer.dialog };
  }

  function createViewer(doc) {
    const dialog = doc.createElement("dialog");
    dialog.className = "diagram-dialog";
    dialog.setAttribute("aria-labelledby", "diagram-viewer-title");

    const header = doc.createElement("div");
    header.className = "diagram-dialog__header";
    const title = doc.createElement("h2");
    title.id = "diagram-viewer-title";
    title.textContent = "Expanded diagram";
    const close = doc.createElement("button");
    close.className = "diagram-dialog__close";
    close.type = "button";
    close.setAttribute("aria-label", "Close expanded diagram");
    close.textContent = "Close";
    header.appendChild(title);
    header.appendChild(close);

    const imageFrame = doc.createElement("div");
    imageFrame.className = "diagram-dialog__image-frame";
    const image = doc.createElement("img");
    image.className = "diagram-dialog__image";
    imageFrame.appendChild(image);

    const caption = doc.createElement("p");
    caption.className = "diagram-dialog__caption";
    const hint = doc.createElement("p");
    hint.className = "diagram-dialog__hint";
    hint.textContent = "Press Escape to close.";
    dialog.appendChild(header);
    dialog.appendChild(imageFrame);
    dialog.appendChild(caption);
    dialog.appendChild(hint);
    doc.body.appendChild(dialog);

    const viewer = { dialog, title, close, image, caption, opener: null };
    dialog._diagramViewer = viewer;
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
      if (viewer.opener && typeof viewer.opener.focus === "function") viewer.opener.focus();
      viewer.opener = null;
    });
    dialog.addEventListener("cancel", () => dialog.close());
    return viewer;
  }

  root.DiagramViewerCore = { install };
  if (root.document$ && typeof root.document$.subscribe === "function") {
    root.document$.subscribe(() => install(root.document, root));
  } else if (root.document) {
    const start = () => install(root.document, root);
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", start, { once: true });
    else start();
  }
})(globalThis);
