let lastId = 0;
let myUser = null;
let selectedImage = null;

async function loadMe() {
  const r = await fetch('/api/me');
  if (!r.ok) { location.href = '/'; return; }
  myUser = await r.json();
  if (myUser.is_admin) document.getElementById('adminBtn').style.display = '';
  document.getElementById('prof-bio').value = myUser.bio || '';
  document.getElementById('prof-webhook').value = myUser.webhook || '';
  if (myUser.avatar) document.getElementById('avatar-preview').src = myUser.avatar;
}

async function loadMessages() {
  const r = await fetch('/api/messages');
  const msgs = await r.json();
  const container = document.getElementById('messages');
  
  msgs.forEach(m => {
    if (m.id <= lastId) return;
    lastId = m.id;
    addMessage(m);
  });
}

function addMessage(m) {
  const container = document.getElementById('messages');
  const div = document.createElement('div');
  const mine = myUser && m.username === myUser.username;
  div.className = 'msg' + (mine ? ' mine' : '');
  
  const avatarHTML = m.avatar 
    ? `<img class="msg-avatar" src="${m.avatar}">`
    : `<div class="msg-avatar">${m.username[0].toUpperCase()}</div>`;
  
  const time = new Date(m.timestamp + 'Z').toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
  
  div.innerHTML = `
    ${avatarHTML}
    <div>
      <div class="msg-bubble">
        <div class="msg-name">${escapeHtml(m.username)}</div>
        ${m.content ? `<div class="msg-text">${escapeHtml(m.content)}</div>` : ''}
        ${m.image ? `<img class="msg-img" src="${m.image}" onclick="window.open('${m.image}')">` : ''}
        <div class="msg-time">${time}</div>
      </div>
    </div>
  `;
  
  container.appendChild(div);
  const main = document.getElementById('chatMain');
  main.scrollTop = main.scrollHeight;
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

document.getElementById('img-input').onchange = (e) => {
  const file = e.target.files[0];
  if (!file) return;
  selectedImage = file;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('preview-img').src = ev.target.result;
    document.getElementById('preview-box').style.display = 'block';
  };
  reader.readAsDataURL(file);
};

function clearPreview() {
  selectedImage = null;
  document.getElementById('img-input').value = '';
  document.getElementById('preview-box').style.display = 'none';
}

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const content = input.value.trim();
  
  if (!content && !selectedImage) return;
  
  const fd = new FormData();
  fd.append('content', content);
  if (selectedImage) fd.append('image', selectedImage);
  
  input.value = '';
  clearPreview();
  
  const r = await fetch('/api/messages', {method: 'POST', body: fd});
  if (r.ok) loadMessages();
}

document.getElementById('msg-input').addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

async function updateOnline() {
  const r = await fetch('/api/online');
  const d = await r.json();
  document.getElementById('online-count').textContent = d.count;
  fetch('/api/ping', {method: 'POST'});
}

async function doLogout() {
  if (!confirm('Sair do chat?')) return;
  await fetch('/api/logout', {method: 'POST'});
  location.href = '/';
}

function toggleProfile() {
  document.getElementById('profileModal').classList.toggle('active');
}

function toggleAdmin() {
  document.getElementById('adminModal').classList.toggle('active');
  if (document.getElementById('adminModal').classList.contains('active')) {
    loadUserList();
  }
}

async function banUser() {
  const target = document.getElementById('admin-target').value.trim();
  if (!target) return alert('Digite o usuário');
  if (!confirm(`Banir ${target}? Esta ação é irreversível.`)) return;
  const r = await fetch('/api/admin/ban', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username: target})
  });
  const d = await r.json();
  if (d.ok) { alert('✅ Banido'); loadUserList(); }
  else alert(d.error);
}

async function promoteUser() {
  const target = document.getElementById('admin-target').value.trim();
  if (!target) return alert('Digite o usuário');
  const code = prompt('Código de verificação (webhook):');
  if (!code) return;
  const r = await fetch('/api/admin/promote', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username: target, code})
  });
  const d = await r.json();
  if (d.ok) { alert('⭐ Promovido!'); loadUserList(); }
  else alert(d.error);
}

async function loadUserList() {
  const r = await fetch('/api/admin/list');
  if (!r.ok) return;
  const users = await r.json();
  const list = document.getElementById('user-list');
  list.innerHTML = users.map(u => 
    `<div class="user-item ${u.is_admin ? 'admin' : ''}">
      <span>${u.is_admin ? '⭐ ' : ''}${escapeHtml(u.username)}</span>
      <span style="opacity:.5">#${u.id}</span>
    </div>`
  ).join('');
}

// Init
(async function() {
  await loadMe();
  await loadMessages();
  await updateOnline();
  
  setInterval(loadMessages, 2000);
  setInterval(updateOnline, 10000);
  setInterval(() => fetch('/api/ping', {method:'POST'}), 30000);
  
  window.addEventListener('beforeunload', () => {
    navigator.sendBeacon('/api/logout');
  });
})();
