let installPrompt;
const installButton = document.getElementById('install');
const status = document.getElementById('status');
function updateConnection() {
  status.textContent = navigator.onLine ? '' : 'Koneksi terputus. Penghitungan dan pengolahan PDF memerlukan internet.';
  status.hidden = navigator.onLine;
}
window.addEventListener('online', updateConnection);
window.addEventListener('offline', updateConnection);
updateConnection();
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  installPrompt = event;
  installButton.hidden = false;
});
installButton.addEventListener('click', async () => {
  if (!installPrompt) return;
  try {
    await installPrompt.prompt();
    await installPrompt.userChoice;
  } finally {
    installPrompt = undefined;
    installButton.hidden = true;
  }
});
window.addEventListener('appinstalled', () => {
  installPrompt = undefined;
  installButton.hidden = true;
});
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {
    status.textContent = 'Pemasangan aplikasi belum tersedia. Aplikasi tetap bisa dibuka melalui tombol Buka langsung.';
    status.hidden = false;
  });
}
