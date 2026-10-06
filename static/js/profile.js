// Preview ao escolher foto
document.getElementById('avatar-input').onchange = (e) => {
  const file = e.target.files[0];
  if (!file) return;

  // Valida tamanho (8MB)
  if (file.size > 8 * 1024 * 1024) {
    alert('Imagem muito grande (máx 8MB)');
    e.target.value = '';
    return;
  }

  // Valida tipo
  const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
  if (!validTypes.includes(file.type)) {
    alert('Formato inválido. Use PNG, JPG, GIF ou WEBP');
    e.target.value = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('avatar-preview').src = ev.target.result;
  };
  reader.readAsDataURL(file);
};

async function saveProfile() {
  const bio = document.getElementById('prof-bio').value;
  const webhook = document.getElementById('prof-webhook').value;
  const code = document.getElementById('prof-code').value;
  const avatarInput = document.getElementById('avatar-input');
  const avatar = avatarInput.files[0];

  const fd = new FormData();
  fd.append('bio', bio);
  fd.append('webhook', webhook);
  if (avatar) fd.append('avatar', avatar);

  // Feedback visual no botão
  const btns = document.querySelectorAll('#profileModal .btn-primary');
  const btn = btns[0];
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Enviando...';

  try {
    const r = await fetch('/api/profile', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin'
    });

    const d = await r.json();

    if (d.ok) {
      // Atualiza o myUser global
      if (typeof myUser !== 'undefined') {
        myUser = d.user;
      }

      // Atualiza preview do avatar com cache-bust
      if (d.user.avatar) {
        document.getElementById('avatar-preview').src = d.user.avatar + '?t=' + Date.now();
      }

      // Limpa input de arquivo
      avatarInput.value = '';

      alert('✅ Perfil atualizado!');
      toggleProfile();

      // Força recarregar mensagens para atualizar avatares antigos
      if (typeof loadMessages === 'function') {
        lastId = 0;
        document.getElementById('messages').innerHTML = '';
        loadMessages();
      }
    } else {
      alert('❌ ' + (d.error || 'Erro ao salvar'));
    }
  } catch (err) {
    alert('❌ Erro de conexão: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }

  // Código admin (promoção própria) - independente do avatar
  if (code) {
    try {
      const r2 = await fetch('/api/verify_webhook', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code}),
        credentials: 'same-origin'
      });
      if (r2.ok) {
        alert('⭐ Você é admin agora!');
        document.getElementById('adminBtn').style.display = '';
        document.getElementById('prof-code').value = '';
      } else {
        alert('❌ Código inválido');
      }
    } catch (err) {
      console.error(err);
    }
  }
}
