import sqlite3
import os

DB_PATH = 'chat.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        bio TEXT DEFAULT '',
        avatar TEXT DEFAULT '',
        ip TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        webhook TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        avatar TEXT,
        content TEXT,
        image TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS online (
        ip TEXT PRIMARY KEY,
        username TEXT,
        user_agent TEXT,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    # Cria admins padrão
    admins = [
        ('yuzzi', 'gabriel_gay', 1),
        ('erikslava', 'vadia_chan123', 1)
    ]
    for u, p, a in admins:
        try:
            c.execute("INSERT INTO users (username, password, is_admin, bio) VALUES (?, ?, ?, ?)",
                      (u, p, a, 'Administrador'))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
