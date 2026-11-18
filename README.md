# flask-cupp

Portal acadêmico em Flask com dois níveis de acesso (administrador e aluno), usado para estudar ataque de dicionário com wordlists geradas pelo CUPP. Projeto da disciplina de Pós-exploração em sistemas, Superior de Tecnologia em Segurança Cibernética (SENAI-SP).

> **Uso exclusivo em laboratório.** A aplicação tem senhas fracas de propósito e o script de ataque só aceita alvos em `localhost`. Todos os dados são fictícios. Não use essas técnicas contra sistemas sem autorização por escrito.

## O que o projeto faz

1. `app.py`: portal Flask + SQLite. O administrador edita notas; o aluno só visualiza os próprios dados e notas (qualquer tentativa de edição retorna 403).
2. `scripts/gen_wordlist.sh`: gera `wordlist.txt` com o [CUPP](https://github.com/Mebus/cupp) a partir de dois perfis fictícios.
3. `attack.py`: tenta cada senha da lista contra `/login`, com suporte a várias threads.
4. Modo endurecido (`HARDENED=1`): mostra como bloqueio por tentativas e token CSRF barram o mesmo ataque.

## Estrutura

```
app.py              portal Flask (modos vulnerável e endurecido)
init_db.py          cria escola.db com alunos, notas e usuários
attack.py           ataque de dicionário (argparse, threads)
wordlist.txt        wordlist gerada pelo CUPP (6751 senhas)
scripts/            gen_wordlist.sh
templates/          páginas HTML
tests/              testes com pytest
```

## Como rodar

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python3 init_db.py        # cria o banco
python3 app.py            # terminal 1: portal em http://127.0.0.1:5000

python3 attack.py admin wordlist.txt --workers 8       # terminal 2
python3 attack.py ana.souza wordlist.txt
```

Para gerar a wordlist de novo (opcional): `./scripts/gen_wordlist.sh`.

## Modos do portal

| | Vulnerável (padrão) | Endurecido (`HARDENED=1`) |
|---|---|---|
| Limite de tentativas | não | 5 falhas por usuário em 5 min, depois HTTP 429 |
| Token CSRF | não | sim, em todos os POST |
| Cookie de sessão | padrão | HttpOnly e SameSite=Lax |
| Segredo da sessão | fixo | aleatório a cada início |
| Log de falhas de login | sim | sim |

```bash
HARDENED=1 python3 app.py
python3 attack.py admin wordlist.txt --workers 8
```

Variáveis opcionais: `MAX_FALHAS`, `JANELA_BLOQUEIO` (segundos) e `ESCOLA_DB`.

## Resultados medidos

Credenciais de teste: `admin:carlos1980` e `ana.souza:ana2005`, ambas presentes na wordlist.

| Cenário | Resultado |
|---|---|
| Modo vulnerável, admin, 1 thread | senha na tentativa 4806, cerca de 6 min |
| Modo vulnerável, aluna, 1 thread | senha na tentativa 3902, cerca de 5 min |
| Modo vulnerável, admin, 8 threads | senha na tentativa 4806, 212 s |
| Modo endurecido, admin, 8 threads | bloqueado com HTTP 429 após 13 tentativas, em 0,6 s |

O tempo por tentativa é dominado pelo hash scrypt das senhas, que já encarece o ataque. O ganho com threads é limitado por isso.

## Testes

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q
```

Cobrem os dois papéis, o 403 para aluno, a edição de notas pelo admin, o comportamento sem bloqueio no modo vulnerável e o bloqueio mais CSRF no modo endurecido.

## Mitigações demonstradas e recomendadas

Implementadas no modo endurecido: bloqueio por tentativas, CSRF, cookie restrito e log de falhas. Recomendadas além disso: política de senha que recuse nome, data e empresa, autenticação em dois fatores para o administrador, checagem de senhas em listas vazadas e bloqueio também por IP.

## Licença

MIT. Veja `LICENSE`.
