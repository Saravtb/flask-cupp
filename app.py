"""Portal academico didatico (Flask + SQLite) com dois niveis de acesso.

Projeto de estudo de pos-exploracao. Roda em dois modos:

  vulneravel (padrao)  sem limite de tentativas e sem CSRF, para praticar
                       ataque de dicionario com wordlists do CUPP.
  endurecido           HARDENED=1: bloqueio por tentativas, token CSRF,
                       cookie de sessao restrito e segredo aleatorio.

Use apenas em localhost e em ambiente de laboratorio.
"""
import logging
import os
import secrets
import sqlite3
import time
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

HARDENED = os.environ.get("HARDENED", "0") == "1"
DB = os.environ.get("ESCOLA_DB", "escola.db")
MAX_FALHAS = int(os.environ.get("MAX_FALHAS", "5"))
JANELA_BLOQUEIO = int(os.environ.get("JANELA_BLOQUEIO", "300"))  # segundos

app = Flask(__name__)
app.secret_key = (secrets.token_hex(32) if HARDENED
                  else "chave-de-laboratorio")
if HARDENED:
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("portal")

# usuario -> lista de instantes de falha (somente modo endurecido)
_falhas = {}


def bloqueado(usuario):
    agora = time.time()
    recentes = [t for t in _falhas.get(usuario, []) if agora - t < JANELA_BLOQUEIO]
    _falhas[usuario] = recentes
    return len(recentes) >= MAX_FALHAS


def registrar_falha(usuario):
    _falhas.setdefault(usuario, []).append(time.time())


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["hardened"] = HARDENED


@app.before_request
def verificar_csrf():
    if HARDENED and request.method == "POST":
        enviado = request.form.get("csrf_token", "")
        if not enviado or not secrets.compare_digest(enviado, session.get("csrf", "")):
            abort(400)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if HARDENED and bloqueado(user):
            log.warning("login bloqueado usuario=%s ip=%s", user, request.remote_addr)
            return render_template("login.html", erro="Muitas tentativas. Tente mais tarde."), 429
        row = get_db().execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (user,)).fetchone()
        if row and check_password_hash(row["senha_hash"], senha):
            session.clear()
            session["user_id"] = row["id"]
            session["role"] = row["papel"]
            session["aluno_id"] = row["aluno_id"]
            log.info("login ok usuario=%s papel=%s", user, row["papel"])
            return redirect(url_for("painel"))
        if HARDENED:
            registrar_falha(user)
        log.warning("login falhou usuario=%s ip=%s", user, request.remote_addr)
        flash("Usuario ou senha invalidos.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/painel")
@login_required()
def painel():
    db = get_db()
    if session["role"] == "admin":
        alunos = db.execute("SELECT * FROM alunos ORDER BY nome").fetchall()
        return render_template("admin.html", alunos=alunos)
    aluno = db.execute("SELECT * FROM alunos WHERE id = ?",
                       (session["aluno_id"],)).fetchone()
    notas = db.execute("SELECT * FROM notas WHERE aluno_id = ? ORDER BY materia",
                       (aluno["id"],)).fetchall()
    return render_template("aluno.html", aluno=aluno, notas=notas)


@app.route("/admin/aluno/<int:aluno_id>", methods=["GET", "POST"])
@login_required("admin")
def editar_notas(aluno_id):
    db = get_db()
    aluno = db.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
    if aluno is None:
        abort(404)
    if request.method == "POST":
        for nota_id, valor in request.form.items():
            if not nota_id.isdigit():
                continue
            try:
                v = float(valor.replace(",", "."))
            except ValueError:
                continue
            if 0 <= v <= 10:
                db.execute("UPDATE notas SET nota = ? WHERE id = ? AND aluno_id = ?",
                           (v, int(nota_id), aluno_id))
        db.commit()
        flash("Notas atualizadas.")
        return redirect(url_for("editar_notas", aluno_id=aluno_id))
    notas = db.execute("SELECT * FROM notas WHERE aluno_id = ? ORDER BY materia",
                       (aluno_id,)).fetchall()
    return render_template("editar.html", aluno=aluno, notas=notas)


if __name__ == "__main__":
    modo = "ENDURECIDO" if HARDENED else "VULNERAVEL (laboratorio)"
    print(f"[*] Modo: {modo} | http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
