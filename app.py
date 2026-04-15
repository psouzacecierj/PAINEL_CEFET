import pandas as pd
import streamlit as st
from datetime import datetime
import re

# ------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA COISA APÓS IMPORTS)
# ------------------------------------------------------
st.set_page_config(
    page_title="CCR – CEFET",
    layout="wide"
)

# ------------------------------------------------------
# LOGO + TÍTULO
# ------------------------------------------------------
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    st.image("logo-cecierj.png", width=150)

with col_titulo:
    st.title("Controle de Cadastro de Reserva – CEFET")

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

# ======================================================
# DIAGNÓSTICO - VER O QUE ESTÁ SENDO LIDO
# ======================================================
st.subheader("🔍 Diagnóstico - Valores únicos encontrados:")

with st.expander("Ver valores únicos na planilha"):
    st.write("**Disciplinas únicas:**")
    st.write(df["Disciplina"].dropna().unique().tolist())
    
    st.write("**Status únicos:**")
    st.write(df["Status"].dropna().unique().tolist())
    
    st.write("**Funções únicas:**")
    st.write(df["Função"].dropna().unique().tolist())
    
    st.write("**Editais únicos:**")
    st.write(df["Edital"].dropna().unique().tolist())
# ======================================================

# ------------------------------------------------------
# FUNÇÃO PARA CONVERTER DATAS EM DIFERENTES FORMATOS
# ------------------------------------------------------
def converter_data(data_str):
    """Converte diferentes formatos de data para objeto datetime"""
    if pd.isna(data_str) or data_str == "":
        return pd.NaT
    
    data_str = str(data_str).strip()
    
    # Formato: "Março de 2025"
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
    
    # Formato: "01/03/2025" ou "01-03-2025"
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(data_str, fmt)
        except:
            continue
    
    return pd.NaT

# ------------------------------------------------------
# LIMPEZA DE LINHAS SUJEIRA
# ------------------------------------------------------
df = df[df["Edital"] != "Edital"]
df = df[df["Função"].notna() & df["Disciplina"].notna()]

# ------------------------------------------------------
# FORMATAÇÃO DE DATAS PARA EXIBIÇÃO
# ------------------------------------------------------
def formatar_datas(df_mostrar: pd.DataFrame) -> pd.DataFrame:
    col_datas = [
        "Prazo para convocação",
        "Validade pagamento bolsa",
        "Data convocação",
    ]

    for col in col_datas:
        if col in df_mostrar.columns:
            df_mostrar[col] = df_mostrar[col].apply(converter_data)
            df_mostrar[col] = df_mostrar[col].dt.strftime("%d/%m/%Y")
            df_mostrar[col] = df_mostrar[col].fillna("")

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
# CÁLCULO DE KPIs
# ------------------------------------------------------
def calcular_kpis(df_base: pd.DataFrame) -> dict:
    df_tmp = df_base.copy()

    df_tmp["Prazo para convocação"] = df_tmp["Prazo para convocação"].apply(converter_data)

    hoje = pd.Timestamp.today().normalize()

    expirado_por_prazo = (
        (df_tmp["Status"] != "Convocado")
        & df_tmp["Prazo para convocação"].notna()
        & (df_tmp["Prazo para convocação"] < hoje)
    )

    expirado_por_obs = (
        df_tmp["Obs"]
        .fillna("")
        .astype(str)
        .str.contains("expirado para convocação", case=False, na=False)
    )

    expirados_mask = expirado_por_prazo | expirado_por_obs

    total = len(df_tmp)
    convocados = (df_tmp["Status"] == "Convocado").sum()
    aguardando = (
        (df_tmp["Status"] == "Aguardando convocação")
        & (~expirados_mask)
    ).sum()
    expirados = expirados_mask.sum()
    outros = total - (convocados + aguardando + expirados)

    return {
        "Total de candidatos": total,
        "Convocados": convocados,
        "Aguardando convocação": aguardando,
        "Expirados": expirados,
        "Outros status": outros,
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

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("📝 Total de candidatos", kpis["Total de candidatos"])
col2.metric("✅ Convocados", kpis["Convocados"])
col3.metric("⏳ Aguardando convocação", kpis["Aguardando convocação"])
col4.metric("⚠️ Expirados", kpis["Expirados"])
col5.metric("🔄 Outros status", kpis["Outros status"])

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

# ---- REMOVER LINHAS INDESEJADAS ANTES DOS FILTROS ----
# Remover linhas onde Disciplina contém "posição por cotas" ou "posição por ampla concorrência"
df_filtrado = df_filtrado[
    ~df_filtrado["Disciplina"].astype(str).str.contains("posição por cotas|posição por ampla concorrência", case=False, na=False)
]

# Remover linhas onde Status contém "data da convocação"
df_filtrado = df_filtrado[
    ~df_filtrado["Status"].astype(str).str.contains("data da convocação", case=False, na=False)
]

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

# Remover "ampla concorrência" da lista
funcoes_str = [f for f in funcoes_str if "ampla concorrência" not in f.lower()]

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

df_mostrar = formatar_datas(df_mostrar)

st.caption(f"📊 Mostrando {len(df_mostrar)} registro(s)")
st.dataframe(df_mostrar, use_container_width=True)