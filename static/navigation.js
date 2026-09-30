/* Les sous-menus restent utilisables sans JavaScript grâce à details/summary. */
(() => {
  'use strict';

  const nav = document.querySelector('.level-nav');
  if (!nav) return;
  const menus = [...nav.querySelectorAll('.level-menu')];

  function closeMenus(except = null) {
    menus.forEach((menu) => {
      if (menu !== except) menu.open = false;
    });
  }

  menus.forEach((menu) => {
    // Complète l’attribut name pour les navigateurs qui ne le gèrent pas encore.
    menu.addEventListener('toggle', () => {
      if (menu.open) closeMenus(menu);
    });
    menu.addEventListener('focusout', (event) => {
      if (event.relatedTarget && !menu.contains(event.relatedTarget)) menu.open = false;
    });
  });

  document.addEventListener('click', (event) => {
    if (!nav.contains(event.target)) closeMenus();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const openMenu = menus.find((menu) => menu.open);
    if (!openMenu) return;
    event.preventDefault();
    closeMenus();
    openMenu.querySelector('summary').focus({preventScroll: true});
  });
})();
