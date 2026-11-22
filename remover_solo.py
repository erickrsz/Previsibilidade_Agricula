# -*- coding: utf-8 -*-
"""Retira o solo do banco do TCC: a coluna CONFIGURACAO_SAFRA.id_solo e a tabela TIPO_SOLO.

O modelo nunca usou o solo e a calculadora não pede mais o tipo de solo
(decisão de 08/11). O banco era o último lugar onde ele continuava.

O QUE FAZ, nesta ordem:
    1. confere que nenhuma outra tabela aponta para TIPO_SOLO;
    2. guarda cópia de TIPO_SOLO e CONFIGURACAO_SAFRA em CSV e o CREATE TABLE
       das duas em .sql, na pasta onde o script roda (para desfazer, se preciso);
    3. tira a chave estrangeira e a coluna id_solo de CONFIGURACAO_SAFRA;
    4. apaga a tabela TIPO_SOLO.

O QUE NÃO TOCA, e confere no fim:
    LEITURA_IOT, SENSOR_IOT   contagem + CHECKSUM TABLE idênticos antes e depois
    CONFIGURACAO_SAFRA        as mesmas linhas, com os mesmos id_config, id_regiao,
                              id_cultura e data_plantio (LEITURA_IOT aponta para id_config)

USO (na pasta onde estão banco.py e banco_config.ini):
    python remover_solo.py              simula e mostra o que faria, sem escrever
    python remover_solo.py --aplicar    executa de verdade

Depois de aplicar, rode  python banco.py  para regravar banco_inventario.txt.
ALTER TABLE e DROP TABLE não têm rollback no MySQL: o desfazer é pelos arquivos
de cópia que este script grava antes de alterar qualquer coisa.
"""
import csv
import sys
from datetime import datetime

from banco import conectar

APLICAR = "--aplicar" in sys.argv
INTOCADAS = ["LEITURA_IOT", "SENSOR_IOT"]
CARIMBO = f"{datetime.now():%Y%m%d_%H%M%S}"


def log(s=""):
    print(s, flush=True)


def impressao(cur, tabela):
    cur.execute(f"SELECT COUNT(*) FROM `{tabela}`")
    n = cur.fetchone()[0]
    cur.execute(f"CHECKSUM TABLE `{tabela}`")
    return n, cur.fetchone()[1]


def existe_tabela(cur, tabela):
    cur.execute("""SELECT COUNT(*) FROM information_schema.TABLES
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""", (tabela,))
    return cur.fetchone()[0] > 0


def existe_coluna(cur, tabela, coluna):
    cur.execute("""SELECT COUNT(*) FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                     AND COLUMN_NAME = %s""", (tabela, coluna))
    return cur.fetchone()[0] > 0


def safras(cur):
    cur.execute("""SELECT id_config, id_regiao, id_cultura, data_plantio
                   FROM CONFIGURACAO_SAFRA ORDER BY id_config""")
    return [tuple(r) for r in cur.fetchall()]


def exportar(cur, tabela):
    cur.execute(f"SELECT * FROM `{tabela}`")
    nomes = [d[0] for d in cur.description]
    linhas = cur.fetchall()
    arq = f"backup_{tabela}_{CARIMBO}.csv"
    with open(arq, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(nomes)
        w.writerows(linhas)
    log(f"   {tabela}: {len(linhas)} linhas -> {arq}")


def executar(cur, sql, descricao):
    log(f"   {descricao}")
    log(f"      {sql}")
    if APLICAR:
        cur.execute(sql)


con = conectar()
cur = con.cursor()
log("SIMULAÇÃO — nada será gravado. Rode com --aplicar para valer.\n" if not APLICAR
    else "APLICANDO.\n")

# ---------------------------------------------------------------- estado ----
tem_tabela = existe_tabela(cur, "TIPO_SOLO")
tem_coluna = existe_coluna(cur, "CONFIGURACAO_SAFRA", "id_solo")
log(f"TIPO_SOLO existe: {tem_tabela} | CONFIGURACAO_SAFRA.id_solo existe: {tem_coluna}")
if not tem_tabela and not tem_coluna:
    cur.close(); con.close()
    sys.exit("Nada a fazer: o solo já saiu do banco.")

cur.execute("""SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME
               FROM information_schema.KEY_COLUMN_USAGE
               WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME = 'TIPO_SOLO'""")
refs = cur.fetchall()
log("Chaves estrangeiras que apontam para TIPO_SOLO:")
for t, c, n in refs:
    log(f"   {t}.{c}  ({n})")
estranhas = [r for r in refs if (r[0], r[1]) != ("CONFIGURACAO_SAFRA", "id_solo")]
if estranhas:
    cur.close(); con.close()
    sys.exit(f"ABORTADO: há outras tabelas apontando para TIPO_SOLO: {estranhas}. "
             "Mande esta saída antes de seguir.")
fk_solo = [n for t, c, n in refs]

antes = {t: impressao(cur, t) for t in INTOCADAS}
safras_antes = safras(cur)
log("\nAntes:")
for t, (n, ck) in antes.items():
    log(f"   {t:20s} {n:>7,} linhas  checksum {ck}")
log(f"   CONFIGURACAO_SAFRA   {len(safras_antes):>7,} linhas")

# ---------------------------------------------------------------- cópias ----
log("\n1. Cópias de segurança")
with open(f"backup_estrutura_solo_{CARIMBO}.sql", "w", encoding="utf-8") as f:
    for t in ["TIPO_SOLO", "CONFIGURACAO_SAFRA"]:
        if existe_tabela(cur, t):
            cur.execute(f"SHOW CREATE TABLE `{t}`")
            f.write(cur.fetchone()[1] + ";\n\n")
log(f"   estrutura -> backup_estrutura_solo_{CARIMBO}.sql")
if tem_tabela:
    exportar(cur, "TIPO_SOLO")
exportar(cur, "CONFIGURACAO_SAFRA")

# ------------------------------------------------------------- alteração ----
log("\n2. CONFIGURACAO_SAFRA")
if tem_coluna:
    for nome in fk_solo:
        executar(cur, f"ALTER TABLE CONFIGURACAO_SAFRA DROP FOREIGN KEY `{nome}`",
                 "tira a chave estrangeira para TIPO_SOLO")
    executar(cur, "ALTER TABLE CONFIGURACAO_SAFRA DROP COLUMN id_solo",
             "tira a coluna id_solo (o índice idx_config_solo sai junto)")
else:
    log("   coluna id_solo já não existe")

log("\n3. TIPO_SOLO")
if tem_tabela:
    executar(cur, "DROP TABLE TIPO_SOLO", "apaga a tabela")
else:
    log("   tabela já não existe")
if APLICAR:
    con.commit()

# ----------------------------------------------------------- conferência ----
log("\nDepois:")
ok = True
for t in INTOCADAS:
    agora = impressao(cur, t)
    igual = agora == antes[t]
    ok &= igual
    log(f"   {t:20s} {agora[0]:>7,} linhas  checksum {agora[1]}  "
        f"{'OK — idêntica' if igual else '<<< MUDOU!'}")
safras_depois = safras(cur)
igual = safras_depois == safras_antes
ok &= igual
log(f"   CONFIGURACAO_SAFRA   {len(safras_depois):>7,} linhas  "
    f"{'OK — mesmas safras e mesmos id_config' if igual else '<<< MUDOU!'}")

cur.execute("SHOW COLUMNS FROM CONFIGURACAO_SAFRA")
log("\nColunas de CONFIGURACAO_SAFRA agora: " + ", ".join(r[0] for r in cur.fetchall()))
log(f"TIPO_SOLO existe agora: {existe_tabela(cur, 'TIPO_SOLO')}")
cur.close()
con.close()

if not ok:
    sys.exit("\nATENÇÃO: algo que não devia mudar mudou. Mande esta saída antes de seguir.")
log("\n" + ("Concluído. Rode agora:  python banco.py   (regrava banco_inventario.txt)"
            if APLICAR else "Simulação concluída. Rode com --aplicar para gravar."))
