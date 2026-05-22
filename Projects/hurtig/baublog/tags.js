/* baublog.hurtig.ai — Tag filtering for the index page.
   Click a tag pill to filter posts. Click again to clear. */

(function () {
  let activeTag = null;

  document.addEventListener("DOMContentLoaded", function () {
    const pills = document.querySelectorAll(".tag-pill");
    const cards = document.querySelectorAll(".post-card");

    pills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        const tag = pill.dataset.tag;

        if (activeTag === tag) {
          // Deselect
          activeTag = null;
          pills.forEach(function (p) { p.classList.remove("active"); });
          cards.forEach(function (c) { c.style.display = ""; });
        } else {
          // Select
          activeTag = tag;
          pills.forEach(function (p) {
            p.classList.toggle("active", p.dataset.tag === tag);
          });
          cards.forEach(function (c) {
            const cardTags = (c.dataset.tags || "").split(",");
            c.style.display = cardTags.includes(tag) ? "" : "none";
          });
        }
      });
    });
  });
})();
