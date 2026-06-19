(function () {
  const loginForm = document.getElementById('adminLoginForm');
  const message = document.getElementById('adminLoginMessage');
  function nextUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('next') || '/admin';
  }
  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const btn = loginForm.querySelector('button');
      const pin = document.getElementById('adminPinInput').value.trim();
      btn.disabled = true;
      btn.textContent = 'Provera...';
      message.textContent = 'Proveravam admin PIN...';
      try {
        const res = await fetch('/auth/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pin }),
        });
        if (!res.ok) throw new Error((await res.text()) || 'Prijava nije uspela');
        message.textContent = 'Uspešna prijava. Preusmeravam...';
        window.location.href = nextUrl();
      } catch (err) {
        message.textContent = 'Greška: ' + err.message;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Prijavi se';
      }
    });
  }

  document.addEventListener('click', async (event) => {
    const btn = event.target.closest('[data-admin-logout]');
    if (!btn) return;
    event.preventDefault();
    btn.disabled = true;
    try { await fetch('/auth/admin/logout', { method: 'POST' }); } catch (e) {}
    window.location.href = '/admin-login';
  });
})();
