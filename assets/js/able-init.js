(function () {
  function initAblePlayers() {
    try {
      if (typeof AblePlayer === 'undefined' || !window.jQuery) return;
      var $ = window.jQuery;
      $(function(){
        $('audio[data-able-player],video[data-able-player]').each(function(){
          var $media = $(this);
          if ($media.closest('.able-wrapper').length) return; // already initialized
          try { new AblePlayer($media); } catch (e) { /* no-op */ }
        });
      });
    } catch(e) { /* no-op */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAblePlayers);
  } else {
    initAblePlayers();
  }
})();

