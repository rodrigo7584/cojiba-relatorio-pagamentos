import os
import locale
import pandas as pd
import re
import unicodedata
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import tempfile
import shutil
import chardet  # nova

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Função para deletar arquivos
# -------------------------------
def limpar_arquivos(arquivos):
    for f in arquivos:
        if os.path.exists(f):
            os.remove(f)

# -------------------------------
# Função processar
# -------------------------------
def processar_arquivos(holerites, cartoes):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

    tamanho_bloco = 73
    registros = []
    linhas = []
    dfs = []

    # -------------------------------
    # Função para normalizar nomes
    # -------------------------------
    def normalizar(texto):
        texto = str(texto).strip().upper()
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )

    # -------------------------------
    # Leitura dos cartões
    # -------------------------------
    for arquivo in cartoes:
        df_temp = pd.read_excel(
            arquivo,
            skiprows=2,
            skipfooter=1,
            header=None,
            usecols=[0, 1, 2],
            names=["NOME", "SIGA", "COMISSAO"]
        )

        df_temp.columns = df_temp.columns.str.strip().str.upper()
        dfs.append(df_temp)

    df_cartoes = pd.concat(dfs, ignore_index=True)
    df_cartoes["NOME"] = df_cartoes["NOME"].apply(normalizar)

    # -------------------------------
    # Leitura dos holerites
    # -------------------------------
    for arquivo_nome in holerites:
        with open(arquivo_nome, 'rb') as f:
            raw = f.read()
            enc = chardet.detect(raw)['encoding']

        linhas = raw.decode(enc).splitlines()

    # -------------------------------
    # Processamento dos blocos
    # -------------------------------
    for i in range(0, len(linhas), tamanho_bloco):
        bloco = linhas[i:i + tamanho_bloco]
        
        if len(bloco) > 1:
            # Empresa
            linha1 = bloco[0].strip()
            partesLinha1 = linha1.split(",")
            empresa = ""
            for j, parte in enumerate(partesLinha1):
                if "Recibo de Pagamento" in parte:
                    if j > 0:
                        empresa = partesLinha1[j - 1].strip()
                    break

            # Nome e cargo
            linha3 = bloco[3].strip()
            partesLinha3 = linha3.split(",")
            nome = partesLinha3[2]
            cargo = partesLinha3[5]

            # Vale
            vale = 0
            for linha in bloco:
                if "Desc.Adto Salarial" in linha:
                    match = re.search(r'Desc\.Adto Salarial.*?"\s*([\d.,]+)\s*"', linha)
                    if match:
                        vale = locale.atof(match.group(1))
                    break

            # Pagamento
            linha30 = bloco[30].strip()
            partesLinha30 = linha30.split('"')
            #print (f"Pagamento: {partesLinha30}")
            pagamento = locale.atof(partesLinha30[1].strip())
            

            registro = {
                "Empresa": empresa,
                "Nome": nome,
                "Nome_norm": normalizar(nome),
                "Cargo": cargo,
                "Vale": vale,
                "Pagamento": pagamento,
                "Salário": round(pagamento + vale, 2)
            }
            registros.append(registro)
            #print(registro)

    # -------------------------------
    # Cruzamento com df_cartoes
    # -------------------------------
    print(f"Total de registros processados: {len(registros)}")
    for registro in registros:

        linha = df_cartoes[df_cartoes["NOME"] == registro["Nome_norm"]]

        if not linha.empty:
            siga = pd.to_numeric(linha.iloc[0]["SIGA"], errors="coerce")
            comissao = pd.to_numeric(linha.iloc[0]["COMISSAO"], errors="coerce")

            registro["Sigacred"] = 0 if pd.isna(siga) else float(siga)
            registro["Comissão"] = 0 if pd.isna(comissao) else float(comissao)
        else:
            registro["Sigacred"] = 0
            registro["Comissão"] = 0

        registro["Pagamento total"] = (
            registro["Comissão"] +
            registro["Sigacred"] +
            registro["Salário"]
        )
    
    df_saida = pd.DataFrame(registros)

    # -------------------------------
    # Encontrar quem está no cartão mas NÃO no registro
    # -------------------------------
    nomes_registros = set(df_saida["Nome_norm"])
    df_sem = df_cartoes[~df_cartoes["NOME"].isin(nomes_registros)].copy()

    df_sem = df_sem.rename(columns={
        "NOME": "Nome",
        "SIGA": "Sigacred",
        "COMISSAO": "Comissão"
    })

    return df_saida, df_sem

@app.post("/processar/")
async def processar(
    background_tasks: BackgroundTasks,
    holerites: list[UploadFile] = File(...),
    cartoes: list[UploadFile] = File(...)
):
    arquivos_holerite = []
    arquivos_cartao = []

    try:
        if not holerites or not cartoes:
            raise HTTPException(400, "Envie todos os arquivos necessários")

        # salvar arquivos
        for file in holerites:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            shutil.copyfileobj(file.file, tmp)
            tmp.close()
            arquivos_holerite.append(tmp.name)

        for file in cartoes:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
            shutil.copyfileobj(file.file, tmp)
            tmp.close()
            arquivos_cartao.append(tmp.name)

        # processa
        df_saida, df_sem = processar_arquivos(arquivos_holerite, arquivos_cartao)

        # gerar excel
        nome_arquivo = f"resultado_{uuid.uuid4().hex}.xlsx"

        with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
            df_saida.drop(columns=["Nome_norm"], errors="ignore").to_excel(
                writer, sheet_name="GERAL", index=False
            )

            for empresa, grupo in df_saida.groupby("Empresa"):
                nome_sheet = str(empresa)[:31]
                grupo.drop(columns=["Nome_norm"], errors="ignore").to_excel(
                    writer, sheet_name=nome_sheet, index=False
                )

            df_sem.to_excel(writer, sheet_name="SEM REGISTRO", index=False)

        # agenda limpeza
        background_tasks.add_task(
            limpar_arquivos,
            arquivos_holerite + arquivos_cartao + [nome_arquivo]
        )

        return FileResponse(
            path=nome_arquivo,
            filename="relatorio.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise

    except Exception as e:
        limpar_arquivos(arquivos_holerite + arquivos_cartao)
        raise HTTPException(500, f"Erro inesperado: {str(e)}")

@app.get("/versao")
def versao():
    return {"versao": "1.0.12", "mensagem": "API atualizadas"}
