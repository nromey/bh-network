(function () {
  // Loop through all nets sections on the page
  document.querySelectorAll(".nets-section").forEach((section, idx) => {
    const KEY = "netView:" + (location.pathname || "/") + ":" + idx;

    const setView = (view) => {
      try {
        localStorage.setItem(KEY, view);
      } catch (e) {}

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
    };

    // Initialize from saved preference
    let initial = "table";
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "headings" || saved === "table") {
        initial = saved;
      }
    } catch (e) {}
    setView(initial);

    // Listen for changes inside this section only
    section.addEventListener("change", (e) => {
      const t = e.target;
      if (t && t.name && t.name.startsWith("net-view")) {
        setView(t.value);
      }
    });
  });
})();
