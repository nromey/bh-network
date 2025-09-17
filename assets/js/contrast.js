<script>
(function () {
  var KEY = "bh-high-contrast";
  var btn = null;

  function apply(state) {
    var root = document.documentElement; // <html>
    if (state) {
      root.classList.add("high-contrast");
    } else {
      root.classList.remove("high-contrast");
    }
    if (btn) {
      btn.setAttribute("aria-pressed", state ? "true" : "false");
      btn.textContent = "High Contrast: " + (state ? "On" : "Off");
    }
  }

  function init() {
    btn = document.getElementById("hc-toggle");
    if (!btn) return;

    // initial state from storage
    var saved = localStorage.getItem(KEY);
    var state = saved === "true";

    apply(state);

    btn.addEventListener("click", function () {
      state = !state;
      localStorage.setItem(KEY, state ? "true" : "false");
      apply(state);
    });

    // Space/Enter work automatically on <button>; no extra handlers needed.
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>

