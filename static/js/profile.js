document.getElementById('avatar-input').onchange = (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => document.getElementById('avatar-preview').src = ev.target.result;
  reader.readAsDataURL(file);
};

async function saveProfile() {
  const bio = document.getElementById('prof-bio').value;
  const webhook = document.getElementById('prof-webhook').value;
  const code = document.getElementById('prof-code').value;
  const avatar = document.getElementById('avatar-input').files[0];
  
  const fd = new FormData();
  fd.append('bio', bio);
  fd.append('webhook', webhook);
  if (avatar) fd.append('avatar', avatar);
  
  const r = await fetch('/api/profile', {method:'POST', body: fd});
  const d = await r.json();
  
  if (d.ok) {
    myUser = d.user;
    alert('✅ Perfil salvo!');
    toggleProfile();
  } else {
    alert(d.error);
  }
  
  // Código admin (promoção própria)
  if (code) {
    const r2 = await fetch('/api/verify_webhook', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({code})
    });
    if (r2.ok) {
      alert('⭐ Você é admin agora!');
      document.getElementById('adminBtn').style.display = '';
    }
  }
}
