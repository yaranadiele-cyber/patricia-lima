from flask import Flask, render_template, request, redirect, session, url_for
import os
import cloudinary
import cloudinary.uploader
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")

# ================== CLOUDINARY ==================
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# ================== BANCO SUPABASE ==================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada nas variáveis de ambiente.")

def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require"
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # ================= TABELAS =================

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

    # ================= INSERÇÕES PADRÃO =================

    cur.execute("SELECT * FROM configuracoes LIMIT 1")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO configuracoes (nome, profissao)
            VALUES ('Patricia Lima', 'Profissional da Beleza')
        """)

    # Criar admin apenas se não existir
    cur.execute("SELECT * FROM admin LIMIT 1")
    if not cur.fetchone():
        senha_hash = generate_password_hash("1234")
        cur.execute("""
            INSERT INTO admin (usuario, senha, chave_recuperacao)
            VALUES (%s, %s, %s)
        """, ("admin", senha_hash, "patricia123"))

    conn.commit()
    cur.close()
    conn.close()

with app.app_context():
    init_db()

# ================= FUNÇÃO CONFIG ==================

def carregar_config():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM configuracoes LIMIT 1")
    cfg = cur.fetchone()
    cur.close()
    conn.close()
    return cfg

# ================= ROTAS PÚBLICAS ==================

@app.route("/")
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM carrossel")
    imagens = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", imagens=imagens, config=carregar_config())

@app.route("/quemsou")
def quemsou():
    return render_template("quemsou.html", config=carregar_config())

@app.route("/atendimento")
def atendimento():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM servicos")
    servicos = cur.fetchall()
    cur.execute("SELECT * FROM horarios ORDER BY hora ASC")
    horarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("atendimento.html",
                           servicos=servicos,
                           horarios=horarios,
                           config=carregar_config())

# ================= LOGIN ==================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get('usuario')
        senha_digitada = request.form.get('senha')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE usuario=%s", (user,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and check_password_hash(admin["senha"], senha_digitada):
            session['admin'] = True
            return redirect(url_for('painel'))

    return render_template("admin.html", config=carregar_config())

@app.route("/painel")
def painel():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template("painel.html", config=carregar_config())

# ================= APARÊNCIA ==================

@app.route("/admin/aparencia", methods=["GET", "POST"])
def admin_aparencia():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        file = request.files.get('foto_perfil')

        if file and file.filename != '':
            resultado = cloudinary.uploader.upload(
                file,
                folder="site_patricia/perfil"
            )
            imagem_url = resultado["secure_url"]
            cur.execute("UPDATE configuracoes SET logo=%s WHERE id=1", (imagem_url,))

        cur.execute("""
            UPDATE configuracoes SET 
            nome=%s,
            profissao=%s,
            texto_quem_sou=%s,
            whatsapp=%s,
            instagram=%s,
            localizacao=%s,
            cor_texto_principal=%s,
            cor_botoes=%s,
            fonte_site=%s
            WHERE id=1
        """, (
            request.form.get('nome'),
            request.form.get('profissao'),
            request.form.get('texto'),
            request.form.get('whatsapp'),
            request.form.get('instagram'),
            request.form.get('localizacao'),
            request.form.get('cor_txt'),
            request.form.get('cor_btn'),
            request.form.get('fonte')
        ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('painel'))

    cur.close()
    conn.close()
    return render_template("admin_aparencia.html", config=carregar_config())

# ================= SERVIÇOS ==================

@app.route("/admin/servicos", methods=["GET", "POST"])
def admin_servicos():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        nome = request.form.get('nome')
        preco = request.form.get('preco')
        descricao = request.form.get('descricao')
        file = request.files.get('imagem')

        imagem_url = ""

        if file and file.filename != '':
            resultado = cloudinary.uploader.upload(
                file,
                folder="site_patricia/servicos"
            )
            imagem_url = resultado["secure_url"]

        cur.execute("""
            INSERT INTO servicos (nome, preco, descricao, imagem)
            VALUES (%s, %s, %s, %s)
        """, (nome, preco, descricao, imagem_url))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_servicos'))

    cur.execute("SELECT * FROM servicos")
    servicos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_servicos.html",
                           servicos=servicos,
                           config=carregar_config())

# ================= LOGOUT ==================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

# ================= START ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)