from flask import Flask, render_template, request, redirect, session, url_for
import os
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash
import time

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")

# ================== BANCO ==================
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL não configurada.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# ================== INICIALIZA BANCO ==================
def init_db():
    tentativas = 5
    while tentativas > 0:
        try:
            with get_db() as conn:
                with conn.cursor() as cur:

                    # Tabela admin
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS admin (
                            id SERIAL PRIMARY KEY,
                            usuario TEXT UNIQUE,
                            senha TEXT
                        )
                    """)

                    # Tabela serviços
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS servicos (
                            id SERIAL PRIMARY KEY,
                            nome TEXT,
                            preco TEXT,
                            descricao TEXT,
                            imagem TEXT
                        )
                    """)

                    # Tabela carrossel
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS carrossel (
                            id SERIAL PRIMARY KEY,
                            imagem TEXT
                        )
                    """)

                    # Tabela horários
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS horarios (
                            id SERIAL PRIMARY KEY,
                            hora TEXT
                        )
                    """)

                    # Admin padrão
                    cur.execute("SELECT * FROM admin LIMIT 1")
                    if not cur.fetchone():
                        senha_hash = generate_password_hash("1234")
                        cur.execute(
                            "INSERT INTO admin (usuario, senha) VALUES (%s, %s)",
                            ("admin", senha_hash)
                        )

                    conn.commit()
                    print("Banco inicializado com sucesso!")
                    return

        except Exception as e:
            print("Erro ao conectar no banco, tentando novamente...", e)
            tentativas -= 1
            time.sleep(3)

    print("Não foi possível conectar ao banco.")

# ================== SITE ==================
@app.route("/")
def index():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM carrossel ORDER BY id DESC")
            imagens = cur.fetchall()
            cur.execute("SELECT * FROM servicos ORDER BY id DESC")
            servicos = cur.fetchall()
    return render_template("index.html", imagens=imagens, servicos=servicos)

@app.route("/quemsou")
def quemsou():
    return render_template("quemsou.html")

@app.route("/atendimento")
def atendimento():
    return render_template("atendimento.html")

# ================== LOGIN ==================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("usuario")
        senha_digitada = request.form.get("senha")

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM admin WHERE usuario=%s", (user,))
                    admin = cur.fetchone()

            if admin and check_password_hash(admin["senha"], senha_digitada):
                session["admin"] = True
                return redirect(url_for("painel"))

        except Exception as e:
            print("Erro no login:", e)
            return "Erro interno no servidor."

    return render_template("admin.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ================== PAINEL ==================
@app.route("/painel")
def painel():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return render_template("painel.html")

# ================== CARROSSEL ==================
@app.route("/admin/carrossel", methods=["GET", "POST"])
def admin_carrossel():
    if not session.get("admin"):
        return redirect(url_for("login"))

    os.makedirs("static/uploads", exist_ok=True)

    with get_db() as conn:
        with conn.cursor() as cur:
            if request.method == "POST":
                imagem = request.files.get("imagem_carrossel")
                if imagem and imagem.filename != "":
                    caminho = f"static/uploads/{imagem.filename}"
                    imagem.save(caminho)
                    cur.execute(
                        "INSERT INTO carrossel (imagem) VALUES (%s)",
                        ("/" + caminho,)
                    )
                    conn.commit()
                return redirect(url_for("admin_carrossel"))

            cur.execute("SELECT * FROM carrossel ORDER BY id DESC")
            imagens = cur.fetchall()

    return render_template("admin_carrossel.html", imagens=imagens)

@app.route("/admin/carrossel/excluir/<int:id>")
def excluir_carrossel(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM carrossel WHERE id=%s", (id,))
            conn.commit()

    return redirect(url_for("admin_carrossel"))

# ================== SERVIÇOS ==================
@app.route("/admin/servicos", methods=["GET", "POST"])
def admin_servicos():
    if not session.get("admin"):
        return redirect(url_for("login"))

    os.makedirs("static/uploads", exist_ok=True)

    with get_db() as conn:
        with conn.cursor() as cur:
            if request.method == "POST":
                nome = request.form.get("nome")
                preco = request.form.get("preco")
                descricao = request.form.get("descricao")
                imagem = request.files.get("imagem")

                caminho_img = None
                if imagem and imagem.filename != "":
                    caminho = f"static/uploads/{imagem.filename}"
                    imagem.save(caminho)
                    caminho_img = "/" + caminho

                cur.execute("""
                    INSERT INTO servicos (nome, preco, descricao, imagem)
                    VALUES (%s, %s, %s, %s)
                """, (nome, preco, descricao, caminho_img))
                conn.commit()
                return redirect(url_for("admin_servicos"))

            cur.execute("SELECT * FROM servicos ORDER BY id DESC")
            servicos = cur.fetchall()

    return render_template("admin_servicos.html", servicos=servicos)

@app.route("/admin/servicos/excluir/<int:id>")
def excluir_servico(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM servicos WHERE id=%s", (id,))
            conn.commit()

    return redirect(url_for("admin_servicos"))

# ================== HORÁRIOS ==================
@app.route("/admin/horarios", methods=["GET", "POST"])
def admin_horarios():
    if not session.get("admin"):
        return redirect(url_for("login"))

    with get_db() as conn:
        with conn.cursor() as cur:
            if request.method == "POST":
                novo = request.form.get("novo_horario")
                cur.execute("INSERT INTO horarios (hora) VALUES (%s)", (novo,))
                conn.commit()
                return redirect(url_for("admin_horarios"))

            cur.execute("SELECT * FROM horarios ORDER BY hora")
            horarios = cur.fetchall()

    return render_template("admin_horarios.html", horarios=horarios)

@app.route("/admin/horarios/excluir/<int:id>")
def excluir_horario(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM horarios WHERE id=%s", (id,))
            conn.commit()

    return redirect(url_for("admin_horarios"))

# ================== SEGURANÇA ==================
@app.route("/admin/seguranca", methods=["GET", "POST"])
def admin_seguranca():
    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        senha_hash = generate_password_hash(senha)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE admin SET usuario=%s, senha=%s WHERE id=1",
                    (usuario, senha_hash)
                )
                conn.commit()

        session.clear()
        return redirect(url_for("login"))

    return render_template("admin_seguranca.html")

# ================== START ==================
init_db()

if __name__ == "__main__":
    app.run(debug=True)