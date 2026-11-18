"""Cria o banco (escola.db por padrao) com alunos ficticios, notas e usuarios.

As senhas sao fracas DE PROPOSITO e derivam de dados pessoais previsiveis,
para serem encontradas pela wordlist do CUPP.
"""
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB = os.environ.get("ESCOLA_DB", "escola.db")
SENHA_ADMIN = "carlos1980"
SENHA_ALUNO = "ana2005"

ALUNOS = [
    (1, "Ana Souza",    "12/04/2005", "Rua das Flores, 100 - Sao Paulo",  "(11) 90000-0001"),
    (2, "Bruno Lima",   "03/09/2004", "Av. Central, 250 - Sao Paulo",     "(11) 90000-0002"),
    (3, "Carla Mendes", "21/01/2005", "Rua do Sol, 45 - Osasco",          "(11) 90000-0003"),
    (4, "Diego Ramos",  "30/07/2003", "Rua Nova, 780 - Guarulhos",        "(11) 90000-0004"),
    (5, "Elisa Prado",  "18/11/2004", "Alameda Azul, 12 - Santo Andre",   "(11) 90000-0005"),
]
MATERIAS = ["Pentest Web", "Redes", "Sistemas Operacionais", "Pos-exploracao"]
NOTAS = [7.5, 8.0, 6.5, 9.0, 5.5, 7.0, 8.5, 6.0, 9.5, 8.0,
         7.0, 7.5, 6.0, 5.0, 8.5, 9.0, 7.5, 8.0, 6.5, 7.0]


def criar():
    if os.path.exists(DB):
        os.remove(DB)
    db = sqlite3.connect(DB)
    db.executescript("""
    CREATE TABLE alunos (id INTEGER PRIMARY KEY, nome TEXT, nascimento TEXT,
                         endereco TEXT, celular TEXT);
    CREATE TABLE notas (id INTEGER PRIMARY KEY, aluno_id INTEGER, materia TEXT,
                        nota REAL);
    CREATE TABLE usuarios (id INTEGER PRIMARY KEY, usuario TEXT UNIQUE,
                           senha_hash TEXT, papel TEXT, aluno_id INTEGER);
    """)
    db.executemany("INSERT INTO alunos VALUES (?,?,?,?,?)", ALUNOS)
    i = 0
    for a in ALUNOS:
        for m in MATERIAS:
            db.execute("INSERT INTO notas (aluno_id, materia, nota) VALUES (?,?,?)",
                       (a[0], m, NOTAS[i]))
            i += 1
    db.execute("INSERT INTO usuarios (usuario, senha_hash, papel, aluno_id) VALUES (?,?,?,?)",
               ("admin", generate_password_hash(SENHA_ADMIN), "admin", None))
    db.execute("INSERT INTO usuarios (usuario, senha_hash, papel, aluno_id) VALUES (?,?,?,?)",
               ("ana.souza", generate_password_hash(SENHA_ALUNO), "aluno", 1))
    db.commit()
    db.close()
    print(f"Banco criado: {DB}")


if __name__ == "__main__":
    criar()
