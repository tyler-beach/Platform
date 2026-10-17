const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "diagram-viewer.js"), "utf8");
const context = { document: undefined, console };
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "diagram-viewer.js" });

class Element {
  constructor(tagName, doc) {
    this.tagName = tagName;
    this.ownerDocument = doc;
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this.className = "";
    this.textContent = "";
    this.open = false;
    this.currentSrc = "";
    this.src = "";
    this.alt = "";
    this.type = "";
  }

  appendChild(child) { this.children.push(child); return child; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, handler) { (this.listeners[name] ||= []).push(handler); }
  focus() { this.ownerDocument.activeElement = this; }
  dispatch(name, event = {}) {
    for (const handler of this.listeners[name] || []) handler({ target: this, currentTarget: this, ...event });
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
  querySelectorAll(selector) {
    const matches = [];
    const visit = (node) => {
      for (const child of node.children) {
        const matchesTag = !selector.startsWith(".") && child.tagName === selector;
        const matchesClass = selector.startsWith(".") && child.className.split(" ").includes(selector.slice(1));
        if (matchesTag || matchesClass) matches.push(child);
        visit(child);
      }
    };
    visit(this);
    return matches;
  }
  showModal() { this.open = true; }
  close() { this.open = false; this.dispatch("close"); }
}

function makeDocument(figures, { dialogSupported = true } = {}) {
  const doc = {
    activeElement: null,
    figures,
    body: null,
    querySelectorAll(selector) {
      if (selector === "figure.diagram-figure") return figures;
      if (selector === "dialog.diagram-dialog") return this.body.children.filter(node => node.tagName === "dialog" && node.className === "diagram-dialog");
      return [];
    },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    createElement(tag) {
      const element = new Element(tag, doc);
      if (tag === "dialog" && !dialogSupported) element.showModal = undefined;
      return element;
    },
  };
  doc.body = new Element("body", doc);
  return doc;
}

function makeFigure(doc, { src, alt, caption }) {
  const figure = new Element("figure", doc);
  figure.className = "diagram-figure";
  const viewport = new Element("div", doc);
  viewport.className = "diagram-viewport";
  const img = new Element("img", doc);
  img.src = src;
  img.currentSrc = src;
  img.alt = alt;
  viewport.appendChild(img);
  figure.appendChild(viewport);
  const figcaption = new Element("figcaption", doc);
  figcaption.textContent = caption;
  figure.appendChild(figcaption);
  return { figure, viewport, img };
}

function install(doc, host = {}) {
  return context.DiagramViewerCore.install(doc, host);
}

test("adds an expand control for each SVG figure and leaves pages without figures untouched", () => {
  const doc = makeDocument([]);
  assert.equal(install(doc).count, 0);
  assert.equal(doc.body.children.length, 0);

  const populated = makeDocument([]);
  const first = makeFigure(populated, { src: "one.svg", alt: "First diagram", caption: "First caption" });
  const second = makeFigure(populated, { src: "two.svg", alt: "Second diagram", caption: "Second caption" });
  populated.figures.push(first.figure, second.figure);
  assert.equal(install(populated).count, 2);
  assert.equal(first.viewport.children.filter(node => node.tagName === "button").length, 1);
  assert.equal(second.viewport.children.filter(node => node.tagName === "button").length, 1);
  assert.equal(first.img.src, "one.svg");
  assert.equal(install(populated).count, 0);
  assert.equal(populated.body.children.filter(node => node.tagName === "dialog").length, 1);
});

test("opens the selected vector, preserves text descriptions, closes, and restores focus", () => {
  const doc = makeDocument([]);
  const first = makeFigure(doc, { src: "one.svg", alt: "First diagram", caption: "First caption" });
  const second = makeFigure(doc, { src: "two.svg", alt: "Second diagram", caption: "Second caption" });
  doc.figures.push(first.figure, second.figure);
  install(doc);
  const opener = second.viewport.children.find(node => node.tagName === "button");
  assert.match(opener.attributes["aria-label"], /Second caption/);
  opener.dispatch("click");
  const dialog = doc.body.children.find(node => node.tagName === "dialog");
  assert.equal(dialog.open, true);
  const image = dialog.querySelector("img");
  assert.equal(image.src, "two.svg");
  assert.equal(image.alt, "Second diagram");
  assert.equal(dialog.querySelector(".diagram-dialog__caption").textContent, "Second caption");
  const close = dialog.querySelector("button");
  close.dispatch("click");
  assert.equal(dialog.open, false);
  assert.equal(doc.activeElement, opener);
});

test("opens the original SVG in a separate tab when native dialog support is unavailable", () => {
  const doc = makeDocument([], { dialogSupported: false });
  const item = makeFigure(doc, { src: "full.svg", alt: "Diagram", caption: "Caption" });
  doc.figures.push(item.figure);
  const calls = [];
  install(doc, { open: (...args) => calls.push(args) });
  item.viewport.children.find(node => node.tagName === "button").dispatch("click");
  assert.deepEqual(calls, [["full.svg", "_blank", "noopener"]]);
});

test("closes on the native Escape cancellation event and restores focus", () => {
  const doc = makeDocument([]);
  const item = makeFigure(doc, { src: "full.svg", alt: "Diagram", caption: "Caption" });
  doc.figures.push(item.figure);
  install(doc);
  const opener = item.viewport.children.find(node => node.tagName === "button");
  opener.dispatch("click");
  const dialog = doc.body.children.find(node => node.tagName === "dialog");
  dialog.dispatch("cancel");
  assert.equal(dialog.open, false);
  assert.equal(doc.activeElement, opener);
});

test("rebinds new figures after instant navigation and reuses the shared dialog", () => {
  const doc = makeDocument([]);
  const first = makeFigure(doc, { src: "first.svg", alt: "First", caption: "First caption" });
  const second = makeFigure(doc, { src: "second.svg", alt: "Second", caption: "Second caption" });
  doc.figures.push(first.figure);
  const subscribers = [];
  const navContext = {
    document: doc,
    document$: { subscribe(callback) { subscribers.push(callback); callback(); } },
    console,
  };
  navContext.globalThis = navContext;
  vm.runInNewContext(source, navContext, { filename: "diagram-viewer-instant-navigation.js" });
  assert.equal(first.viewport.children.filter(node => node.tagName === "button").length, 1);

  doc.figures.splice(0, doc.figures.length, second.figure);
  subscribers[0]();
  const opener = second.viewport.children.find(node => node.tagName === "button");
  assert.ok(opener);
  opener.dispatch("click");
  const dialogs = doc.body.children.filter(node => node.tagName === "dialog");
  assert.equal(dialogs.length, 1);
  assert.equal(dialogs[0].querySelector("img").src, "second.svg");
});
