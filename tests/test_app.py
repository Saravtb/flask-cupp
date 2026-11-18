import importlib
import os
import re

import pytest


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    def criar(hardened=False):
        monkeypatch.setenv("ESCOLA_DB", str(tmp_path / "t.db"))
        monkeypatch.setenv("HARDENED", "1" if hardened else "0")
        monkeypatch.setenv("MAX_FALHAS", "3")
        import init_db
        importlib.reload(init_db)
        init_db.criar()
        import app as portal
        importlib.reload(portal)
        portal.app.config["TESTING"] = True
        return portal.app.test_client()
    return criar


def logar(c, u, s, token=None):
    dados = {"usuario": u, "senha": s}
    if token:
        dados["csrf_token"] = token
    return c.post("/login", data=dados)


def test_admin_edita_notas(cliente):
    c = cliente()
    assert logar(c, "admin", "carlos1980").status_code == 302
    assert c.post("/admin/aluno/1", data={"1": "9.5"}).status_code == 302
    import sqlite3
    nota = sqlite3.connect(os.environ["ESCOLA_DB"]).execute(
        "select nota from notas where id=1").fetchone()[0]
    assert nota == 9.5


def test_aluno_nao_edita(cliente):
    c = cliente()
    logar(c, "ana.souza", "ana2005")
    assert c.get("/painel").status_code == 200
    assert c.get("/admin/aluno/1").status_code == 403
    assert c.post("/admin/aluno/1", data={"1": "10"}).status_code == 403


def test_sem_login_redireciona(cliente):
    c = cliente()
    assert c.get("/painel").status_code == 302


def test_senha_errada(cliente):
    c = cliente()
    assert logar(c, "admin", "errada").status_code == 200


def test_modo_vulneravel_nao_bloqueia(cliente):
    c = cliente()
    for i in range(10):
        assert logar(c, "admin", f"x{i}").status_code == 200
    assert logar(c, "admin", "carlos1980").status_code == 302


def test_modo_endurecido_bloqueia_e_exige_csrf(cliente):
    c = cliente(hardened=True)
    assert c.post("/login", data={"usuario": "admin", "senha": "carlos1980"}).status_code == 400
    for i in range(3):
        html = c.get("/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html).group(1)
        assert logar(c, "admin", f"x{i}", token).status_code == 200
    html = c.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html).group(1)
    assert logar(c, "admin", "carlos1980", token).status_code == 429
