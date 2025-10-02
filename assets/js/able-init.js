(function () {
  function loadScript(src, cb) {
    var s = document.createElement('script');
    s.src = src; s.async = true; s.onload = function(){ cb && cb(true); };
    s.onerror = function(){ cb && cb(false); };
    document.head.appendChild(s);
  }

  function ensureJQuery(cb) {
    if (window.jQuery) return cb(true);
    loadScript('https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js', function(ok){ cb(ok); });
  }

  function ensureAblePlayer(cb) {
    if (typeof AblePlayer !== 'undefined') return cb(true);
    loadScript('https://cdn.jsdelivr.net/gh/ableplayer/ableplayer@v4.7.0/build/ableplayer.min.js', function(ok){ cb(ok); });
  }

  function upgrade() {
    try {
      if (typeof AblePlayer === 'undefined' || !window.jQuery) return;
      var $ = window.jQuery;
      $('audio[data-able-player],video[data-able-player]').each(function(){
        var $media = $(this);
        if ($media.closest('.able-wrapper').length) return; // already initialized
        try { new AblePlayer($media); } catch (e) { /* no-op */ }
      });
    } catch(e) { /* no-op */ }
  }

  function init() {
    ensureJQuery(function(){
      ensureAblePlayer(function(){
        // Defer upgrade to ensure DOM is ready
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', upgrade);
        } else {
          upgrade();
        }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
