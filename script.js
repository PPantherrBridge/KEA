const menuToggle = document.querySelector('.menu-toggle');
const menuWrap = document.querySelector('.menu-wrap');
const moreDropdown = document.querySelector('.more-dropdown');
const moreBtn = document.querySelector('.more-btn');

menuToggle?.addEventListener('click', () => {
  const isOpen = menuWrap.classList.toggle('open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});

moreBtn?.addEventListener('click', () => {
  const isOpen = moreDropdown.classList.toggle('open');
  moreBtn.setAttribute('aria-expanded', String(isOpen));
});

document.addEventListener('click', (event) => {
  if (!moreDropdown?.contains(event.target)) {
    moreDropdown?.classList.remove('open');
    moreBtn?.setAttribute('aria-expanded', 'false');
  }
});
