#!/bin/sh
# Gera wordlist.txt com o CUPP a partir de dois perfis ficticios (admin e aluna).
# Requer git e python3. Baixa o CUPP em ./cupp se ainda nao existir.
set -e
[ -d cupp ] || git clone --depth 1 https://github.com/Mebus/cupp cupp
cd cupp
# ordem das perguntas: nome, sobrenome, apelido, nascimento, parceiro (3),
# filho (3), pet, empresa, palavras-chave, chars especiais, numeros, leet, hyperspeed
printf 'carlos\nsilva\ncarlao\n15031980\n\n\n\n\n\n\nrex\nsenai\nn\nn\nn\nn\nn\n' | python3 cupp.py -i -q >/dev/null
mv carlos.txt ../wl_admin.txt
printf 'ana\nsouza\naninha\n12042005\n\n\n\n\n\n\nmel\nsenai\nn\nn\nn\nn\nn\n' | python3 cupp.py -i -q >/dev/null
mv ana.txt ../wl_aluno.txt
cd ..
cat wl_admin.txt wl_aluno.txt | sort -u > wordlist.txt
rm -f wl_admin.txt wl_aluno.txt
echo "wordlist.txt: $(wc -l < wordlist.txt) senhas"
