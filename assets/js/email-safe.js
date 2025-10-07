// assets/js/email-safe.js
// Build <a href="mailto:..."> links from spans with data-u (user) and data-d (domain).
// Avoids plain emails in the static HTML to reduce spam scraping.
document.addEventListener('DOMContentLoaded', () => {
  const nodes = document.querySelectorAll('.js-email');
  nodes.forEach(el => {
    const u = el.getAttribute('data-u');
    const d = el.getAttribute('data-d');
    if (!u || !d) return;
    const addr = `${u}@${d}`;
    const a = document.createElement('a');
    a.href = `mailto:${addr}`;
    a.textContent = addr;
    a.rel = 'nofollow';
    // Use aria-label if provided; otherwise fall back to the address
    const label = el.getAttribute('aria-label');
    if (label) a.setAttribute('aria-label', label);
    el.replaceWith(a);
  });
});
