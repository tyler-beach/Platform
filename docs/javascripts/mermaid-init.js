document.addEventListener("DOMContentLoaded", function () {
  if (typeof mermaid !== "undefined") {
    mermaid.initialize({
      startOnLoad: true,
      securityLevel: "strict",
      theme: document.documentElement.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "default"
    });
  }
});
