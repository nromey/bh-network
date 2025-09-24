// /assets/js/net-view.js
(function () {
  // Use one global key for all nets sections across the site
  const KEY = "netView:global:nets";

  const setView = (view) => {
    // Persist the chosen view
    try { localStorage.setItem(KEY, view); } catch (_) {}

    // Apply to all .nets-section blocks on the page
    document.querySelectorAll(".nets-section").forEach((section) => {
      const table = section.querySelector(".view-table");
      const headings = section.querySelector(".view-headings");
      if (!table || !headings) return;

      if (view === "headings") {
        table.setAttribute("hidden", "hidden");
        headings.removeAttribute("hidden");
        section.dataset.view = "headings";
      } else {
        headings.setAttribute("hidden", "hidden");
        table.removeAttribute("hidden");
        section.dataset.view = "table";
      }

      // Sync radio buttons
      const radios = section.querySelectorAll('input[name^="net-view"]');
      radios.forEach((r) => {
        r.checked = (r.value === view);
      });
    });
  };

  // Initialize from saved preference or fall back to HTML default
  let initial = "table";
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "headings" || saved === "table") {
      initial = saved;
    } else {
      // check the first section's data-view as a hint
      const first = document.querySelector(".nets-section");
      if (first && first.dataset.view === "headings") initial = "headings";
    }
  } catch (_) {
    const first = document.querySelector(".nets-section");
    if (first && first.dataset.view === "headings") initial = "headings";
  }
  setView(initial);

  // Listen for changes in any section (radio buttons)
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t && t.name && t.name.startsWith("net-view")) {
      if (t.value === "table" || t.value === "headings") {
        setView(t.value); // updates all sections + saves globally
      }
    }
  });
})();
