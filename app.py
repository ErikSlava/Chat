from flask import Flask, request, jsonify, render_template, send_from_directory, session
from werkzeug.utils import secure_filename
from database import init_db, get_db
import os, uuid, requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'kwai_chat_secret_2024_gabriel_erik'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Caminhos absolutos (evita problema de CWD)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

WEBHOOK_ENTRADA = "https://discord.com/api/webhooks/1556831405181243432/LWyJQOZDyhA3MBPYLDXPNzSS1gcFMqbwk2HmakIuWLy11K8gD3jxC41ff2vzSh5F-B0z"
WEBHOOK_ADMIN_VERIFY = "https://discord.com/api/webhooks/1556832094418632746/SQBBiwcMXSWXdiJyEX6eR_Dpwhv5Z0WcUXnKbVv92S1DdIs1LFGYKbty6pyk74j1OxuH"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def get_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def send_webhook(url, content=None, embed=None):
    try:
        data = {}
        if content: data['content'] = content
        if embed: data['embeds'] = [embed]
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        print(f"Webhook erro: {e}")


init_db()


# ---------- ROTAS ----------

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/chat')
def chat_page():
    return render_template('chat.html')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Preencha tudo'}), 400

    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, ip, bio) VALUES (?, ?, ?, ?)",
                   (username, password, get_ip(), 'Olá! Sou novo aqui 👋'))
        db.commit()
    except Exception:
        db.close()
        return jsonify({'error': 'Usuário já existe'}), 400
    db.close()
    return jsonify({'ok': True})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                      (username, password)).fetchone()

    if not user:
        db.close()
        return jsonify({'error': 'Credenciais inválidas'}), 401

    db.execute("INSERT OR REPLACE INTO online (ip, username, user_agent, last_seen) VALUES (?, ?, ?, ?)",
               (get_ip(), username, request.headers.get('User-Agent', ''), datetime.now()))
    db.commit()
    db.close()

    session['user_id'] = user['id']
    session['username'] = user['username']
    session.permanent = True

    send_webhook(WEBHOOK_ENTRADA, embed={
        'title': '🟢 Usuário entrou',
        'color': 0x00ff00,
        'fields': [
            {'name': 'Usuário', 'value': username, 'inline': True},
            {'name': 'IP', 'value': get_ip(), 'inline': True},
            {'name': 'Admin', 'value': 'Sim' if user['is_admin'] else 'Não', 'inline': True},
            {'name': 'User-Agent', 'value': request.headers.get('User-Agent', 'N/A')[:200]}
        ],
        'timestamp': datetime.utcnow().isoformat()
    })

    return jsonify({
        'ok': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'bio': user['bio'],
            'avatar': user['avatar'],
            'is_admin': bool(user['is_admin'])
        }
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    username = session.get('username', 'Anônimo')
    db = get_db()
    db.execute("DELETE FROM online WHERE ip=?", (get_ip(),))
    db.commit()
    db.close()

    send_webhook(WEBHOOK_ENTRADA, embed={
        'title': '🔴 Usuário saiu',
        'color': 0xff0000,
        'fields': [
            {'name': 'Usuário', 'value': username, 'inline': True},
            {'name': 'IP', 'value': get_ip(), 'inline': True}
        ]
    })
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/me')
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Não logado'}), 401
    db = get_db()
    user = db.execute(
        "SELECT id, username, bio, avatar, is_admin, webhook FROM users WHERE id=?", (uid,)
    ).fetchone()
    db.close()
    if not user:
        session.clear()
        return jsonify({'error': 'Não encontrado'}), 404
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'bio': user['bio'] or '',
        'avatar': user['avatar'] or '',
        'is_admin': bool(user['is_admin']),
        'webhook': user['webhook'] or ''
    })


@app.route('/api/profile', methods=['POST'])
def update_profile():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Não logado'}), 401

    bio = request.form.get('bio', '')
    webhook = request.form.get('webhook', '')

    db = get_db()
    old_user = db.execute("SELECT avatar FROM users WHERE id=?", (uid,)).fetchone()
    if not old_user:
        db.close()
        return jsonify({'error': 'Usuário não existe'}), 404

    avatar_path = old_user['avatar']  # mantém o antigo por padrão

    # ----------- PROCESSAMENTO DO AVATAR -----------
    if 'avatar' in request.files:
        f = request.files['avatar']
        if f and f.filename and f.filename.strip():
            if not allowed_file(f.filename):
                db.close()
                return jsonify({'error': 'Formato de imagem não permitido'}), 400

            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], fname)

            try:
                f.save(filepath)
                # Verifica se realmente salvou
                if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                    raise Exception("Falha ao salvar arquivo")

                # Remove avatar antigo (se existir e for um upload)
                if old_user['avatar'] and old_user['avatar'].startswith('/static/uploads/'):
                    old_filename = old_user['avatar'].replace('/static/uploads/', '')
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                    if os.path.exists(old_path):
                        try: os.remove(old_path)
                        except: pass

                avatar_path = f"/static/uploads/{fname}"
            except Exception as e:
                db.close()
                return jsonify({'error': f'Erro ao salvar imagem: {str(e)}'}), 500
    # ------------------------------------------------

    db.execute("UPDATE users SET bio=?, webhook=?, avatar=? WHERE id=?",
               (bio, webhook, avatar_path, uid))
    db.commit()

    user = db.execute(
        "SELECT id, username, bio, avatar, is_admin, webhook FROM users WHERE id=?", (uid,)
    ).fetchone()
    db.close()

    # Também atualiza o avatar nas mensagens antigas do usuário (opcional, mas legal)
    db2 = get_db()
    db2.execute("UPDATE messages SET avatar=? WHERE user_id=?", (avatar_path, uid))
    db2.commit()
    db2.close()

    return jsonify({
        'ok': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'bio': user['bio'] or '',
            'avatar': user['avatar'] or '',
            'is_admin': bool(user['is_admin']),
            'webhook': user['webhook'] or ''
        }
    })


@app.route('/api/messages', methods=['GET'])
def get_messages():
    db = get_db()
    rows = db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 100").fetchall()
    db.close()
    msgs = [dict(r) for r in rows][::-1]
    return jsonify(msgs)


@app.route('/api/messages', methods=['POST'])
def send_message():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Não logado'}), 401

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'Usuário não existe'}), 401

    content = request.form.get('content', '').strip()
    image_path = None

    if 'image' in request.files:
        f = request.files['image']
        if f and f.filename and f.filename.strip() and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = f"{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            image_path = f"/static/uploads/{fname}"

    if not content and not image_path:
        db.close()
        return jsonify({'error': 'Mensagem vazia'}), 400

    db.execute("INSERT INTO messages (user_id, username, avatar, content, image) VALUES (?, ?, ?, ?, ?)",
               (user['id'], user['username'], user['avatar'] or '', content, image_path))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/online')
def online_count():
    db = get_db()
    limit = datetime.now() - timedelta(minutes=2)
    rows = db.execute("SELECT username FROM online WHERE last_seen > ?", (limit,)).fetchall()
    db.close()
    return jsonify({'count': len(rows), 'users': [r['username'] for r in rows]})


@app.route('/api/ping', methods=['POST'])
def ping():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False})
    db = get_db()
    db.execute("INSERT OR REPLACE INTO online (ip, username, user_agent, last_seen) VALUES (?, ?, ?, ?)",
               (get_ip(), session.get('username', ''), request.headers.get('User-Agent', ''), datetime.now()))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/admin/ban', methods=['POST'])
def ban_user():
    uid = session.get('user_id')
    db = get_db()
    me = db.execute("SELECT is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not me or not me['is_admin']:
        db.close()
        return jsonify({'error': 'Sem permissão'}), 403

    target = request.json.get('username')
    target_user = db.execute("SELECT * FROM users WHERE username=?", (target,)).fetchone()
    if not target_user:
        db.close()
        return jsonify({'error': 'Usuário não encontrado'}), 404

    db.execute("DELETE FROM users WHERE username=?", (target,))
    db.execute("DELETE FROM online WHERE username=?", (target,))
    db.commit()
    db.close()

    send_webhook(WEBHOOK_ENTRADA, embed={
        'title': '🔨 Usuário banido',
        'color': 0xff8800,
        'fields': [
            {'name': 'Admin', 'value': session.get('username'), 'inline': True},
            {'name': 'Banido', 'value': target, 'inline': True}
        ]
    })
    return jsonify({'ok': True})


@app.route('/api/admin/promote', methods=['POST'])
def promote_user():
    uid = session.get('user_id')
    db = get_db()
    me = db.execute("SELECT is_admin, username FROM users WHERE id=?", (uid,)).fetchone()
    if not me or not me['is_admin']:
        db.close()
        return jsonify({'error': 'Sem permissão'}), 403

    target = request.json.get('username')
    code = request.json.get('code', '')

    send_webhook(WEBHOOK_ADMIN_VERIFY, embed={
        'title': '🔐 Tentativa de promoção admin',
        'color': 0xffcc00,
        'fields': [
            {'name': 'Solicitante', 'value': me['username'], 'inline': True},
            {'name': 'Alvo', 'value': target, 'inline': True},
            {'name': 'Código', 'value': code or 'N/A', 'inline': True}
        ]
    })

    if code != "KWAI-ADMIN-2024":
        db.close()
        return jsonify({'error': 'Código de verificação inválido'}), 403

    db.execute("UPDATE users SET is_admin=1 WHERE username=?", (target,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/verify_webhook', methods=['POST'])
def verify_webhook():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Não logado'}), 401
    code = request.json.get('code', '')
    if code == "KWAI-ADMIN-2024":
        db = get_db()
        db.execute("UPDATE users SET is_admin=1 WHERE id=?", (uid,))
        db.commit()
        db.close()
        return jsonify({'ok': True})
    return jsonify({'error': 'Código inválido'}), 403


@app.route('/api/admin/list')
def list_users():
    uid = session.get('user_id')
    db = get_db()
    me = db.execute("SELECT is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not me or not me['is_admin']:
        db.close()
        return jsonify({'error': 'Sem permissão'}), 403
    rows = db.execute("SELECT id, username, bio, avatar, is_admin FROM users").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
