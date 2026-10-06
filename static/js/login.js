document.querySelectorAll('.tab').forEach(tab => {
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  };
});

async function doLogin() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value.trim();
  if (!username || !password) return alert('Preencha tudo!');
  
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = 'Entrando...';
  
  try {
    const r = await fetch('/api/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    const d = await r.json();
    if (d.ok) {
      btn.textContent = '✅ Bem-vindo!';
      setTimeout(() => location.href = '/chat', 500);
    } else {
      alert(d.error);
      btn.disabled = false;
      btn.textContent = 'Entrar 🚀';
    }
  } catch(e) {
    alert('Erro de conexão');
    btn.disabled = false;
    btn.textContent = 'Entrar 🚀';
  }
}

async function doRegister() {
  const username = document.getElementById('reg-user').value.trim();
  const password = document.getElementById('reg-pass').value.trim();
  if (!username || !password) return alert('Preencha tudo!');
  if (password.length < 4) return alert('Senha muito curta');
  
  const r = await fetch('/api/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password})
  });
  const d = await r.json();
  if (d.ok) {
    alert('Conta criada! Faça login ✨');
    document.querySelector('.tab[data-tab="login"]').click();
  } else {
    alert(d.error);
  }
}

document.getElementById('login-pass').addEventListener('keypress', e => {
  if (e.key === 'Enter') doLogin();
});
