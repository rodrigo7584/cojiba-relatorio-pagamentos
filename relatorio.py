from sqlalchemy import create_engine
import pandas as pd

# lista de IPs dos bancos
ips = ["192.168.6.201", "192.168.6.202", "192.168.6.203", "192.168.6.204", "192.168.6.205","192.168.6.206", "192.168.6.207", "192.168.6.208", "192.168.6.209", "192.168.6.210", "192.168.6.211", "192.168.6.212", "192.168.6.213", "192.168.6.214", "192.168.6.215", "192.168.6.216", "192.168.6.217","192.168.6.218"]

# credenciais comuns
user = "consinco"
password = "consinco"
database = "consinco"

# query = """
# SELECT pag.seqdocto, pag.valor, pag.vlrtotal, pag.nroformapagto, fpg.formapagto
# FROM tb_doctopagto pag
# JOIN tb_doctoitem doc ON pag.seqdocto = doc.seqdocto
# JOIN tb_formapagto fpg ON pag.nroformapagto = fpg.nroformapagto
# WHERE doc.dtahoremissao LIKE '%%2026-04-18%%'
# AND doc.seqproduto = 42587;
# """


query = """
SELECT pag.seqdocto, pag.valor, pag.vlrtotal, pag.nroformapagto, fpg.formapagto, pro.desccompleta
FROM tb_doctopagto pag
JOIN tb_doctoitem doc
ON pag.seqdocto = doc.seqdocto
JOIN tb_formapagto fpg
ON pag.nroformapagto = fpg.nroformapagto
JOIN tb_produto pro
ON doc.seqproduto = pro.seqproduto
WHERE doc.dtahoremissao LIKE "%%2026-05-05%%"
AND pro.desccompleta LIKE "%%codorna%%";
"""

resultados = []

for ip in ips:
    try:
        # cria engine SQLAlchemy
        engine = create_engine(f"mysql+pymysql://{user}:{password}@{ip}/{database}")
        print(f"Conectando ao banco {ip}...")
        df = pd.read_sql(query, engine)

        if df.empty:
            print(f"Nenhum resultado no banco {ip}")
        else:
            df["Banco"] = ip
            resultados.append(df)

    except Exception as e:
        print(f"Erro ao conectar ou executar no banco {ip}: {e}")

# junta tudo em um único DataFrame (se houver resultados)
if resultados:
    df_final = pd.concat(resultados, ignore_index=True)
    df_final.to_excel("relatorio_pagamentos.xlsx", index=False)
    print("Relatório gerado: relatorio_pagamentos.xlsx")
else:
    print("Nenhum resultado em nenhum banco.")
