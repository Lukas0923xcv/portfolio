try {
var saved = localStorage.getItem("theme");
if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}