/* hurtig.ai — Mobile Navigation Toggle
   Adds hamburger menu functionality for mobile viewports.
   Include this script at the bottom of every page, after the nav element.
*/
(function () {
  var nav = document.querySelector('nav');
  if (!nav) return;

  var container = nav.querySelector('.max-w-7xl');
  if (!container) return;

  // Find the CTA button
  var cta = container.querySelector('.kiln-gradient');
  if (!cta) return;

  // Create hamburger button
  var hamburger = document.createElement('button');
  hamburger.className = 'md:hidden flex items-center justify-center w-10 h-10 rounded-lg hover:bg-cream-200 transition-colors order-last ml-2';
  hamburger.setAttribute('aria-label', 'Toggle menu');
  hamburger.setAttribute('aria-expanded', 'false');
  hamburger.innerHTML = '<span class="material-symbols-outlined text-ink text-2xl">menu</span>';

  // Insert hamburger after CTA (both visible on mobile)
  cta.parentNode.insertBefore(hamburger, cta.nextSibling);

  // Create mobile menu dropdown
  var mobileMenu = document.createElement('div');
  mobileMenu.className = 'md:hidden hidden border-t border-clay/10 bg-cream/95 backdrop-blur-md';
  mobileMenu.setAttribute('id', 'mobile-menu');

  // Clone the desktop nav links
  var desktopLinks = container.querySelector('.hidden.md\\:flex');
  if (!desktopLinks) return;

  var menuInner = document.createElement('div');
  menuInner.className = 'flex flex-col px-6 py-4 gap-1';

  var links = desktopLinks.querySelectorAll('a, button');
  for (var i = 0; i < links.length; i++) {
    var clone = links[i].cloneNode(true);
    // Reset classes for mobile layout
    clone.className = 'flex items-center gap-2 px-4 py-3 rounded-lg text-ink-light font-medium text-sm tracking-wide hover:bg-cream-200 hover:text-kiln transition-colors';
    menuInner.appendChild(clone);
  }

  // Add CTA link to mobile menu too
  var mobileCta = cta.cloneNode(true);
  mobileCta.className = 'kiln-gradient text-white px-4 py-3 rounded-lg font-semibold text-sm text-center mt-2';
  menuInner.appendChild(mobileCta);

  mobileMenu.appendChild(menuInner);
  nav.appendChild(mobileMenu);

  // Toggle handler
  hamburger.addEventListener('click', function () {
    var isOpen = mobileMenu.classList.contains('hidden');
    mobileMenu.classList.toggle('hidden');
    hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    hamburger.innerHTML = isOpen
      ? '<span class="material-symbols-outlined text-ink text-2xl">close</span>'
      : '<span class="material-symbols-outlined text-ink text-2xl">menu</span>';
  });

  // Close menu when clicking a link
  mobileMenu.addEventListener('click', function (e) {
    if (e.target.tagName === 'A' || e.target.closest('a')) {
      mobileMenu.classList.add('hidden');
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.innerHTML = '<span class="material-symbols-outlined text-ink text-2xl">menu</span>';
    }
  });
})();
