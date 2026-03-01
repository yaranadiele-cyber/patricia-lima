from flask import Flask, render_template, request, redirect, session, url_for
import os
import cloudinary
import cloudinary.uploader
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")

# ================== CLOUDINARY ==================
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# ================== BANCO ==================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada nas variáveis de ambiente.")

def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, sslmode="require")

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        # ======== TABELAS ========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS servicos (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                preco TEXT,
                descricao TEXT,
                imagem TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS carrossel (
                id SERIAL PRIMARY KEY,
                imagem TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id SERIAL PRIMARY KEY,
                usuario TEXT UNIQUE,
                senha TEXT,
                chave_recuperacao TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS horarios (
                id SERIAL PRIMARY KEY,
                hora TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                id SERIAL PRIMARY KEY,
                texto_quem_sou TEXT,
                nome TEXT,
                profissao TEXT,
                logo TEXT,
                whatsapp TEXT,
                instagram TEXT,
                localizacao TEXT,
                cor_texto_principal TEXT DEFAULT '#ffffff',
                cor_botoes TEXT DEFAULT '#f2ae94',
                fonte_site TEXT DEFAULT 'Poppins'
            )
        """)

        # ======== CONFIGURAÇÃO PADRÃO ========
        cur.execute("SELECT * FROM configuracoes LIMIT 1")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO configuracoes (nome, profissao)
                VALUES ('Patricia Lima', 'Profissional da Beleza')
            """)

        # ======== RESETAR ADMIN (FORÇA SENHA 1234) ========
        cur.execute("DELETE FROM admin")

        senha_hash = generate_password_hash("1234")

        cur.execute("""
            INSERT INTO admin (usuario, senha, chave_recuperacao)
            VALUES (%s, %s, %s)
        """, ("admin", senha_hash, "patricia123"))

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Banco inicializado com sucesso.")

    except Exception as e:
        print("⚠️ Erro ao inicializar banco:", e)

# ================== CONFIGURAÇÃO ==================
def carregar_config():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM configuracoes LIMIT 1")
        cfg = cur.fetchone()
        cur.close()
        conn.close()
        return cfg
    except:
        return {}

# ================== ROTAS ==================
@app.route("/")
def index():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM carrossel")
        imagens = cur.fetchall()
        cur.close()
        conn.close()
    except:
        imagens = []
    return render_template("index.html", imagens=imagens, config=carregar_config())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("usuario")
        senha_digitada = request.form.get("senha")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE usuario=%s", (user,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and check_password_hash(admin["senha"], senha_digitada):
            session["admin"] = True
            return redirect(url_for("painel"))

    return render_template("admin.html", config=carregar_config())

@app.route("/painel")
def painel():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return render_template("painel.html", config=carregar_config())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ================== INICIALIZAÇÃO ==================
init_db()

if __name__ == "__main__":
    app.run()