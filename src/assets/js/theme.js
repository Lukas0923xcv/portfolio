// Runs in <head> before the page paints, so a saved light or dark choice never flashes.
try {
  var saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
