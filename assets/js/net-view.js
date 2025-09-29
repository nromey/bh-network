// /assets/js/net-view.js
(function () {
  // Use one global key for all nets sections across the site
  const KEY = "netView:global:nets";

  const announceView = (section, view) => {
    const status = section.querySelector('[data-net-view-status]');
    if (!status) return;

    const message = view === "headings"
      ? "Headings view selected"
      : "Table view selected";

    status.textContent = message;
  };

  const setView = (view, options = {}) => {
    const { announce = false } = options;

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

      // Sync toggle buttons
      const buttons = section.querySelectorAll('[data-view-button]');
      buttons.forEach((btn) => {
        const isActive = btn.dataset.viewButton === view;
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
      });

      if (announce) announceView(section, view);
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

  // Listen for clicks on the toggle buttons
  document.addEventListener("click", (e) => {
    const btn = e.target.closest('[data-view-button]');
    if (!btn) return;

    const value = btn.dataset.viewButton;
    if (!value || (value !== "table" && value !== "headings")) return;

    if (btn.getAttribute("aria-pressed") === "true") return;

    setView(value, { announce: true });
  });
})();
