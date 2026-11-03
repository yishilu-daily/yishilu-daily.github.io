(function () {
  document.querySelectorAll("[data-briefing]").forEach(function (root) {
    var pages = Array.prototype.slice.call(root.querySelectorAll("[data-brief-page]"));
    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-brief-tab]"));
    if (!pages.length) return;
    var index = 0;
    var startX = 0;

    function show(next) {
      index = Math.max(0, Math.min(pages.length - 1, next));
      pages.forEach(function (page, position) {
        page.hidden = position !== index;
      });
      tabs.forEach(function (tab, position) {
        var selected = position === index;
        tab.setAttribute("aria-selected", selected ? "true" : "false");
        tab.tabIndex = selected ? 0 : -1;
      });
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        show(Number(tab.getAttribute("data-brief-tab")) || 0);
      });
    });

    root.addEventListener("touchstart", function (event) {
      if (!event.changedTouches) return;
      startX = event.changedTouches[0].clientX;
    }, { passive: true });

    root.addEventListener("touchend", function (event) {
      if (!event.changedTouches) return;
      var delta = event.changedTouches[0].clientX - startX;
      if (Math.abs(delta) < 48) return;
      show(index + (delta < 0 ? 1 : -1));
    }, { passive: true });

    show(0);
  });
})();
