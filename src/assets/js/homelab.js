(() => {
  // ---------- Tabs. Without JavaScript all four panels are simply shown one after another. ----------
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  if (tabs.length) {
    document.documentElement.classList.add("js-tabs");
    const select = (tab, focus) => {
      tabs.forEach(t => {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", e => {
        const last = tabs.length - 1;
        const to = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[e.key];
        if (to === undefined) return;
        e.preventDefault();
        select(tabs[to], true);
      });
    });
    select(tabs.find(t => t.getAttribute("aria-selected") === "true") || tabs[0]);
  }

  // ---------- Network diagram: a radio group, the text comes from the "as text" list ----------
  const panel = document.getElementById("net-info");
  const boxes = [...document.querySelectorAll('.net [role="radio"]')];
  if (panel && boxes.length) {
    const text = {};
    document.querySelectorAll(".net-desc [data-node]").forEach(d => {
      text[d.dataset.node] = [d.querySelector("dt").textContent, d.querySelector("dd").textContent];
    });
    const show = (box, focus) => {
      boxes.forEach(b => { const on = b === box; b.setAttribute("aria-checked", String(on)); b.tabIndex = on ? 0 : -1; });
      const [h, p] = text[box.dataset.node];
      panel.querySelector("h4").textContent = h;
      panel.querySelector("p").textContent = p;
      if (focus) box.focus();
    };
    boxes.forEach((b, i) => {
      b.addEventListener("click", () => show(b));
      b.addEventListener("keydown", e => {
        const last = boxes.length - 1;
        const to = { ArrowDown: i === last ? 0 : i + 1, ArrowRight: i === last ? 0 : i + 1, ArrowUp: i === 0 ? last : i - 1,
                     ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[e.key];
        if (to === undefined) return;
        e.preventDefault();
        show(boxes[to], true);
      });
    });
    show(boxes.find(b => b.getAttribute("aria-checked") === "true") || boxes[0]);
  }
})();
