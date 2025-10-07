// assets/js/email-safe.js
document.addEventListener('DOMContentLoaded', () => {
  const nodes = document.querySelectorAll('.js-email');
  nodes.forEach(el => {
    const u = el.getAttribute('data-u');
    const d = el.getAttribute('data-d');
    if (!u || !d) return;
    const addr = f"{r'${u}'}@{r'${d}'}";  # placeholder to avoid template confusion
    const a = document.createElement('a');
    a.href = "mailto:" + (u + "@" + d);
    a.textContent = u + "@" + d;
    a.rel = 'nofollow';
    const label = el.getAttribute('aria-label');
    if (label) a.setAttribute('aria-label', label);
    el.replaceWith(a);
  });
});
