// /assets/js/home-week-filter.js
(function () {
  const section = document.getElementById("home-week-nets");
  if (!section) return;

  const checkboxes = Array.from(section.querySelectorAll('[data-category-toggle]'));
  if (!checkboxes.length) return;

  const status = section.querySelector('[data-week-filter-status]');
  const emptyMessage = section.querySelector('[data-week-empty]');
  const primary = section.dataset.primaryCategory || "";

  const labelMap = new Map();
  checkboxes.forEach((cb) => {
    labelMap.set(cb.value, cb.dataset.label || cb.value);
  });

  const getItems = () => Array.from(section.querySelectorAll('[data-category-item]'));

  const describeSelection = (selected, visibleCount) => {
    if (!selected.size) return "No categories selected. Weekly nets hidden.";
    if (!visibleCount) return "No upcoming nets match the selected categories.";
    const labels = Array.from(selected).map((cat) => labelMap.get(cat) || cat);
    if (labels.length === 1) return `Showing nets for ${labels[0]}.`;
    const last = labels.pop();
    return `Showing nets for ${labels.join(", ")} and ${last}.`;
  };

  const applySelection = (selected) => {
    const items = getItems();
    let visibleCount = 0;
    items.forEach((item) => {
      const cat = item.dataset.category;
      item.toggleAttribute("hidden", !selected.has(cat));
      if (!item.hasAttribute("hidden")) visibleCount += 1;
    });
    if (emptyMessage) emptyMessage.toggleAttribute("hidden", visibleCount !== 0);
    if (status) status.textContent = describeSelection(selected, visibleCount);
  };

  const collectSelected = () => {
    const selected = new Set();
    checkboxes.forEach((cb) => {
      if (cb.checked) selected.add(cb.value);
    });
    return selected;
  };

  const ensurePrimary = () => {
    if (!primary) return;
    const hasPrimary = checkboxes.some((cb) => cb.value === primary);
    if (!hasPrimary) {
      checkboxes.forEach((cb) => (cb.checked = true));
      return;
    }
    checkboxes.forEach((cb) => {
      cb.checked = cb.value === primary;
    });
  };

  const update = () => {
    const selected = collectSelected();
    applySelection(selected);
  };

  checkboxes.forEach((cb) => {
    cb.addEventListener("change", update);
  });

  section.querySelectorAll('[data-category-select]').forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.categorySelect;
      if (mode === "all") {
        checkboxes.forEach((cb) => {
          cb.checked = true;
        });
      } else if (mode === "primary") {
        ensurePrimary();
      }
      update();
    });
  });

  document.addEventListener("bhn:week-hydrated", (event) => {
    const target = event.detail && event.detail.container;
    if (target && target.id !== section.id) return;
    update();
  });

  update();
})();
