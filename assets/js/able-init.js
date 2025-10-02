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

  function ensureCookies(cb) {
    if (window.Cookies && typeof window.Cookies.get === 'function' && typeof window.Cookies.set === 'function') {
      return cb(true);
    }
    // Lightweight fallback shim for js-cookie API used by AblePlayer
    try {
      window.Cookies = window.Cookies || {};
      if (typeof window.Cookies.get !== 'function') {
        window.Cookies.get = function(name){
          var cname = name + '=';
          var decoded = decodeURIComponent(document.cookie || '');
          var ca = decoded.split(';');
          for (var i=0;i<ca.length;i++){
            var c = ca[i].trim();
            if (c.indexOf(cname) === 0) return c.substring(cname.length);
          }
          return undefined;
        };
      }
      if (typeof window.Cookies.set !== 'function') {
        window.Cookies.set = function(name, value, options){
          var days = (options && options.expires) ? options.expires : 365;
          var d = new Date();
          d.setTime(d.getTime() + (days*24*60*60*1000));
          var expires = '; expires=' + d.toUTCString();
          var path = '; path=' + ((options && options.path) ? options.path : '/');
          document.cookie = name + '=' + encodeURIComponent(value) + expires + path;
        };
      }
      return cb(true);
    } catch(e) {
      // As a last resort, try loading js-cookie from CDN
      loadScript('https://cdn.jsdelivr.net/npm/js-cookie@3.0.5/dist/js.cookie.min.js', function(ok){ cb(ok); });
    }
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
      // Simple diagnostics: log once if media exists but no player wrapper after a short delay
      setTimeout(function(){
        try {
          var anyMedia = document.querySelector('audio[data-able-player],video[data-able-player]');
          var anyAble = document.querySelector('.able-wrapper');
          if (anyMedia && !anyAble) console.warn('[AblePlayer] Upgrade did not attach to media.');
        } catch(e){}
      }, 300);
    } catch(e) { /* no-op */ }
  }

  function init() {
    ensureJQuery(function(){
      ensureCookies(function(){
        ensureAblePlayer(function(){
          // Defer upgrade to ensure DOM is ready
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', upgrade);
          } else {
            upgrade();
          }
        });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
