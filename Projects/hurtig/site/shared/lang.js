/* hurtig.ai — Language Toggle
   Auto-wires the DE/EN nav button to link to the equivalent page
   in the other language. No manual configuration needed per page.
*/
(function () {
  var inDE = location.pathname.indexOf("/de/") !== -1;
  var page = location.pathname.split("/").pop() || "index.html";
  var base = inDE ? "../" : "de/";
  var label = inDE ? "EN" : "DE";

  // Find the nav element containing both "DE" and "EN"
  var els = document.querySelectorAll("nav button, nav a");
  for (var i = 0; i < els.length; i++) {
    var txt = els[i].textContent.trim();
    if (txt.indexOf("DE") !== -1 && txt.indexOf("EN") !== -1) {
      var a = document.createElement("a");
      a.href = base + page;
      a.className = els[i].className;
      a.innerHTML =
        '<span class="material-symbols-outlined text-[16px]">language</span> ' +
        label;
      els[i].parentNode.replaceChild(a, els[i]);
      break;
    }
  }
})();
