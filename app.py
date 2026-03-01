from flask import Flask, render_template, request, redirect, session, url_for
import os
import cloudinary
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

# 🔥 CORREÇÃO IMPORTANTE PARA RENDER
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL não configurada.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

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

                # ======== CONFIG PADRÃO ========
                cur.execute("SELECT * FROM configuracoes LIMIT 1")
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO configuracoes (nome, profissao)
                        VALUES (%s, %s)
                    """, ("Patricia Lima", "Profissional da Beleza"))

                # ======== ADMIN PADRÃO ========
                cur.execute("SELECT * FROM admin LIMIT 1")
                if not cur.fetchone():
                    senha_hash = generate_password_hash("1234")
                    cur.execute("""
                        INSERT INTO admin (usuario, senha, chave_recuperacao)
                        VALUES (%s, %s, %s)
                    """, ("admin", senha_hash, "patricia123"))

        print("✅ Banco inicializado com sucesso.")

    except Exception as e:
        print("❌ Erro ao inicializar banco:", e)

# ================== CONFIGURAÇÃO ==================
def carregar_config():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM configuracoes LIMIT 1")
                return cur.fetchone()
    except Exception as e:
        print("Erro ao carregar config:", e)
        return {}

# ================== ROTAS ==================
@app.route("/")
def index():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM carrossel")
                imagens = cur.fetchall()
    except Exception as e:
        print("Erro index:", e)
        imagens = []
    return render_template("index.html", imagens=imagens, config=carregar_config())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = request.form.get("usuario")
            senha_digitada = request.form.get("senha")

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM admin WHERE usuario=%s", (user,))
                    admin = cur.fetchone()

            if admin and check_password_hash(admin["senha"], senha_digitada):
                session["admin"] = True
                return redirect(url_for("painel"))

        except Exception as e:
            print("Erro no login:", e)

    return render_template("admin.html", config=carregar_config())

    @app.route("/quemsou")
def quemsou():
    return render_template("quemsou.html", config=carregar_config())

@app.route("/atendimento")
def atendimento():
    return render_template("atendimento.html", config=carregar_config())

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
if DATABASE_URL:
    init_db()
else:
    print("⚠️ DATABASE_URL não configurada.")

if __name__ == "__main__":
    app.run(debug=True)