let deferredInstallPrompt = null;

function createPwaInstallButton() {
  if (document.getElementById('pwaInstallBtn')) return;
  const button = document.createElement('button');
  button.id = 'pwaInstallBtn';
  button.className = 'pwa-install-btn hidden';
  button.type = 'button';
  button.textContent = 'Instaliraj kao aplikaciju';
  button.addEventListener('click', async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice.catch(() => null);
    deferredInstallPrompt = null;
    button.classList.add('hidden');
  });
  document.body.appendChild(button);
}

function createOfflineBadge() {
  if (document.getElementById('offlineBadge')) return;
  const badge = document.createElement('div');
  badge.id = 'offlineBadge';
  badge.className = 'offline-badge hidden';
  badge.textContent = 'Offline režim — prikaz može biti zastareo';
  document.body.appendChild(badge);

  const update = () => badge.classList.toggle('hidden', navigator.onLine);
  window.addEventListener('online', update);
  window.addEventListener('offline', update);
  update();
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => null);
  });
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  createPwaInstallButton();
  document.getElementById('pwaInstallBtn')?.classList.remove('hidden');
});

window.addEventListener('appinstalled', () => {
  deferredInstallPrompt = null;
  document.getElementById('pwaInstallBtn')?.classList.add('hidden');
});

createPwaInstallButton();
createOfflineBadge();
