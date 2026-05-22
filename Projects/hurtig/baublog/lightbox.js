/* baublog.hurtig.ai — Lightbox for photo galleries
   Pure JS, no dependencies. Click any .photo-grid img to open.
   Arrow keys / swipe / click to navigate. Esc to close. */

(function () {
  let overlay, imgEl, counter, images, idx;

  function create() {
    overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.innerHTML = `
      <button class="lightbox-close" aria-label="Close">&times;</button>
      <button class="lightbox-nav" style="left:1rem" aria-label="Previous">&lsaquo;</button>
      <img src="" alt="">
      <button class="lightbox-nav" style="right:1rem" aria-label="Next">&rsaquo;</button>
      <div class="lightbox-counter"></div>
    `;
    document.body.appendChild(overlay);

    imgEl = overlay.querySelector("img");
    counter = overlay.querySelector(".lightbox-counter");

    overlay.querySelector(".lightbox-close").addEventListener("click", close);
    overlay.querySelectorAll(".lightbox-nav")[0].addEventListener("click", prev);
    overlay.querySelectorAll(".lightbox-nav")[1].addEventListener("click", next);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });

    document.addEventListener("keydown", function (e) {
      if (!overlay.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    });

    // Touch swipe
    let startX = 0;
    overlay.addEventListener("touchstart", function (e) {
      startX = e.changedTouches[0].screenX;
    });
    overlay.addEventListener("touchend", function (e) {
      const dx = e.changedTouches[0].screenX - startX;
      if (Math.abs(dx) > 50) {
        dx > 0 ? prev() : next();
      }
    });
  }

  function open(gallery, startIdx) {
    if (!overlay) create();
    images = gallery;
    idx = startIdx;
    show();
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function close() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  function show() {
    imgEl.src = images[idx].dataset.full || images[idx].src;
    counter.textContent = (idx + 1) + " / " + images.length;
  }

  function prev() {
    idx = (idx - 1 + images.length) % images.length;
    show();
  }

  function next() {
    idx = (idx + 1) % images.length;
    show();
  }

  // Attach to all .photo-grid containers
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".photo-grid").forEach(function (grid) {
      var imgs = Array.from(grid.querySelectorAll("img"));
      imgs.forEach(function (img, i) {
        img.addEventListener("click", function () {
          open(imgs, i);
        });
      });
    });
  });
})();
