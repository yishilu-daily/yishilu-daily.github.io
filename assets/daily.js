(function () {
  var root = document.querySelector("[data-issue-app]");
  if (!root) return;

  var dates = [];
  try {
    dates = JSON.parse(root.getAttribute("data-dates") || "[]");
  } catch (error) {
    dates = [];
  }

  var issues = Array.prototype.slice.call(root.querySelectorAll("[data-issue]"));
  var input = root.querySelector("[data-issue-date]");
  var empty = root.querySelector("[data-issue-empty]");
  var emptyLabel = root.querySelector("[data-empty-label]");
  var prev = root.querySelector("[data-issue-prev]");
  var next = root.querySelector("[data-issue-next]");

  function isDay(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(value || "");
  }

  function before(day) {
    var found = "";
    dates.forEach(function (date) {
      if (date < day) found = date;
    });
    return found;
  }

  function after(day) {
    var found = "";
    dates.some(function (date) {
      if (date > day) {
        found = date;
        return true;
      }
      return false;
    });
    return found;
  }

  function setStep(link, day) {
    if (!link) return;
    if (!day) {
      link.setAttribute("aria-disabled", "true");
      link.removeAttribute("href");
      return;
    }
    link.removeAttribute("aria-disabled");
    link.setAttribute("href", "/daily/?d=" + day);
  }

  function show(day) {
    var known = false;
    issues.forEach(function (issue) {
      var match = issue.getAttribute("data-issue") === day;
      issue.hidden = !match;
      if (match) known = true;
    });
    if (empty) empty.hidden = known || !day;
    if (emptyLabel) {
      emptyLabel.textContent = isDay(day) ? formatDay(day) + "，" : "";
    }
    if (input && isDay(day)) {
      input.value = day;
      input.setAttribute("value", day);
    }
    setStep(prev, before(day || "9999-99-99"));
    setStep(next, after(day || "0000-00-00"));
    return known;
  }

  function formatDay(day) {
    var parts = day.split("-");
    return Number(parts[0]) + "年" + Number(parts[1]) + "月" + Number(parts[2]) + "日";
  }

  function fromUrl() {
    var query = new URLSearchParams(window.location.search).get("d");
    if (isDay(query)) return query;
    return root.getAttribute("data-latest") || dates[dates.length - 1] || "";
  }

  function onDailyPath() {
    var path = window.location.pathname;
    return path === "/daily" || path === "/daily/";
  }

  function go(day, push) {
    show(day);
    if (!onDailyPath()) {
      window.location.href = "/daily/?d=" + day;
      return;
    }
    var url = "/daily/?d=" + day;
    if (push) window.history.pushState({ d: day }, "", url);
    else window.history.replaceState({ d: day }, "", url);
  }

  var initial = fromUrl();
  show(initial);
  if (onDailyPath() && initial && new URLSearchParams(window.location.search).get("d") !== initial) {
    window.history.replaceState({ d: initial }, "", "/daily/?d=" + initial);
  }

  if (input) {
    input.addEventListener("change", function () {
      if (!isDay(input.value)) return;
      if (onDailyPath()) go(input.value, true);
      else window.location.href = "/daily/?d=" + input.value;
    });
  }

  root.addEventListener("click", function (event) {
    var link = event.target.closest("[data-issue-prev], [data-issue-next]");
    if (!link || link.getAttribute("aria-disabled") === "true") {
      if (link) event.preventDefault();
      return;
    }
    if (!onDailyPath()) return;
    var href = link.getAttribute("href");
    if (!href) return;
    event.preventDefault();
    var day = new URL(href, window.location.origin).searchParams.get("d");
    if (isDay(day)) go(day, true);
  });

  window.addEventListener("popstate", function () {
    show(fromUrl());
  });
})();
