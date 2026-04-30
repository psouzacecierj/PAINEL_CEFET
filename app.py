import pandas as pd
import streamlit as st
from datetime import datetime
import re

# ------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------
st.set_page_config(
    page_title="CCR – CEFET/RJ",
    layout="wide"
)

# ------------------------------------------------------
# LOGO + TÍTULO
# ------------------------------------------------------
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    st.image("logo-cecierj.png", width=150)

with col_titulo:
    st.title("Controle de Cadastro Reserva – Engenharia de Produção CEFET/RJ – CEDERJ")

# ------------------------------------------------------
# LEITURA DA BASE (Google Sheets - CSV)
# ------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados() -> pd.DataFrame:
    sheet_id = "1by0MnnKcCZcAhUepxbPvNa1tVZevVZOrU15ST0fbAfw"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {str(e)}")
        return pd.DataFrame()

df = carregar_dados()

if df.empty:
    st.stop()

# ------------------------------------------------------
# LIMPEZA COMPLETA DE LINHAS SUJEIRA
# ------------------------------------------------------
# Remover cabeçalhos repetidos
df = df[df["Edital"] != "Edital"]

# Remover linhas onde Disciplina é cabeçalho ou valor inválido
df = df[~df["Disciplina"].astype(str).str.contains("Disciplina", case=False, na=False)]
df = df[~df["Disciplina"].astype(str).str.contains("Posição Cotas", case=False, na=False)]

# Remover linhas onde Status é inválido
df = df[~df["Status"].astype(str).str.contains("Data convocação", case=False, na=False)]
df = df[~df["Status"].astype(str).str.contains("julho", case=False, na=False)]

# Remover linhas onde Função é inválida
df = df[~df["Função"].astype(str).str.contains("Posição Ampla Concorrêcia", case=False, na=False)]
df = df[~df["Função"].astype(str).str.contains("^1$|^2$", case=False, na=False, regex=True)]

# Remover linhas com valores nulos essenciais
df = df[df["Função"].notna() & df["Disciplina"].notna()]

# ------------------------------------------------------
# FUNÇÃO PARA CONVERTER DATAS PARA CÁLCULO
# ------------------------------------------------------
def converter_para_calculo(data_str):
    """Converte diferentes formatos de data para objeto datetime"""
    if pd.isna(data_str) or data_str == "":
        return pd.NaT
    
    data_str = str(data_str).strip()
    
    # Formato: "Março de 2025" ou "01/03/2023"
    match = re.match(r"(\w+) de (\d{4})", data_str)
    if match:
        mes_nome, ano = match.groups()
        meses = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        mes_num = meses.get(mes_nome, 1)
        return datetime(int(ano), mes_num, 1)
    
    # Formato: "01/03/2025" ou "30/06/27"
    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(data_str, fmt)
        except:
            continue
    
    return pd.NaT

# ------------------------------------------------------
# FORMATAÇÃO DE DATAS PARA EXIBIÇÃO
# ------------------------------------------------------
def formatar_datas(df_mostrar: pd.DataFrame) -> pd.DataFrame:
    """Mantém as datas exatamente como estão na planilha"""
    return df_mostrar

# ------------------------------------------------------
# BUSCA POR CANDIDATO
# ------------------------------------------------------
def buscar_ocorrencias_candidato(
    nome_parcial: str,
    df_base: pd.DataFrame
) -> pd.DataFrame:

    mask_nome = df_base["Candidato"].str.contains(
        nome_parcial,
        case=False,
        na=False
    )

    df_encontrados = df_base[mask_nome].copy()

    if df_encontrados.empty:
        return pd.DataFrame()

    colunas_layout = [
        "Edital",
        "Função",
        "Disciplina",
        "Posição",
        "Candidato",
        "Titulação",
        "Status",
        "Prazo para convocação",
        "Validade pagamento bolsa",
        "Data convocação",
        "Obs",
    ]

    colunas_existentes = [col for col in colunas_layout if col in df_encontrados.columns]

    return (
        df_encontrados
        .sort_values(
            by=["Candidato", "Edital", "Função", "Disciplina", "Posição"]
        )[colunas_existentes]
    )

# ------------------------------------------------------
# CÁLCULO DE KPIS (CORRIGIDO PARA CONTAR "Expirado" DA PLANILHA)
# ------------------------------------------------------
def calcular_kpis(df_base: pd.DataFrame) -> dict:
    df_tmp = df_base.copy()

    total = len(df_tmp)
    convocados = (df_tmp["Status"] == "Convocado").sum() if "Status" in df_tmp.columns else 0
    aguardando = (df_tmp["Status"] == "Aguardando convocação").sum() if "Status" in df_tmp.columns else 0
    recusou = (df_tmp["Status"] == "Recusou").sum() if "Status" in df_tmp.columns else 0
    
    # CORREÇÃO: Conta "Expirado" (com E maiúsculo) que está na planilha
    expirados = (
        (df_tmp["Status"] == "Expirado") |  # Exato com E maiúsculo
        (df_tmp["Status"] == "expirado")    # Exato com minúsculo (fallback)
    ).sum() if "Status" in df_tmp.columns else 0

    return {
        "Total de candidatos": total,
        "Convocados": convocados,
        "Aguardando convocação": aguardando,
        "Expirados": expirados,
        "Recusou": recusou,
    }

# ------------------------------------------------------
# KPIs COM FILTRO POR EDITAL
# ------------------------------------------------------
st.markdown("---")
st.subheader("📊 Indicadores")

opcoes_edital_kpi = ["(todos)"] + sorted(
    df["Edital"].dropna().unique().tolist()
)

edital_kpi = st.selectbox(
    "Filtrar indicadores por edital:",
    opcoes_edital_kpi
)

df_kpi = df if edital_kpi == "(todos)" else df[df["Edital"] == edital_kpi]
kpis = calcular_kpis(df_kpi)

# 5 colunas para os KPIs
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("📝 Total", kpis["Total de candidatos"])
col2.metric("✅ Convocados", kpis["Convocados"])
col3.metric("⏳ Aguardando", kpis["Aguardando convocação"])
col4.metric("⚠️ Expirados", kpis["Expirados"])
col5.metric("❌ Recusou", kpis["Recusou"])

# ------------------------------------------------------
# BUSCA POR CANDIDATO
# ------------------------------------------------------
st.markdown("---")
st.subheader("🔍 Buscar candidato (todas as ocorrências)")

nome = st.text_input("Digite pelo menos 3 letras do nome:")

if nome and len(nome.strip()) >= 3:
    resultado = buscar_ocorrencias_candidato(nome.strip(), df)

    if resultado.empty:
        st.info("ℹ️ Nenhum candidato encontrado para essa busca.")
    else:
        st.success(f"✅ {len(resultado)} ocorrência(s) encontrada(s)")
        st.dataframe(
            formatar_datas(resultado.copy()),
            use_container_width=True
        )

elif nome:
    st.warning("⚠️ Digite pelo menos 3 letras do nome.")

# ------------------------------------------------------
# FILTROS TIPO EXCEL
# ------------------------------------------------------
st.markdown("---")
st.subheader("📋 Fila por Edital / Função / Disciplina")

df_filtrado = df.copy()

# ---- FILTRO EDITAL ----
opcoes_edital = ["(todos)"] + sorted(
    df_filtrado["Edital"].dropna().unique().tolist()
)
edital_sel = st.selectbox("📌 Edital", options=opcoes_edital)

if edital_sel != "(todos)":
    df_filtrado = df_filtrado[df_filtrado["Edital"] == edital_sel]

# ---- FILTRO FUNÇÃO ----
funcoes_validas = df_filtrado["Função"].dropna()
funcoes_str = funcoes_validas.astype(str).unique().tolist()

funcao_options = ["(todos)"] + sorted(funcoes_str)
funcao_sel = st.selectbox("💼 Função", options=funcao_options)

if funcao_sel != "(todos)":
    df_filtrado = df_filtrado[
        df_filtrado["Função"].astype(str) == funcao_sel
    ]

# ---- FILTRO DISCIPLINA ----
df_filtrado = df_filtrado[df_filtrado["Disciplina"].notna()]

disc_validas = df_filtrado["Disciplina"].dropna().unique().tolist()

disc_options = ["(todas)"] + sorted(disc_validas)
disc_sel = st.selectbox("📚 Disciplina", options=disc_options)

if disc_sel != "(todas)":
    df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_sel]

# ---- FILTRO STATUS ----
status_validos = df_filtrado["Status"].dropna().unique().tolist()

status_options = ["(todos)"] + sorted(status_validos)
status_sel = st.selectbox("🏷️ Status", options=status_options)

if status_sel != "(todos)":
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]

# ---- TRATAMENTO DA POSIÇÃO E EXIBIÇÃO ----
if "Posição" in df_filtrado.columns:
    df_filtrado["Posição"] = pd.to_numeric(
        df_filtrado["Posição"],
        errors="coerce"
    )

colunas_layout = [
    "Edital",
    "Função",
    "Disciplina",
    "Posição",
    "Candidato",
    "Titulação",
    "Status",
    "Prazo para convocação",
    "Validade pagamento bolsa",
    "Data convocação",
    "Obs",
]

colunas_existentes = [col for col in colunas_layout if col in df_filtrado.columns]

if "Posição" in colunas_existentes:
    df_mostrar = (
        df_filtrado
        .sort_values(by="Posição", na_position="last")[colunas_existentes]
        .copy()
    )
else:
    df_mostrar = df_filtrado[colunas_existentes].copy()

st.caption(f"📊 Mostrando {len(df_mostrar)} registro(s)")
st.dataframe(df_mostrar, use_container_width=True)