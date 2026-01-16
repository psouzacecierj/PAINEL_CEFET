import pandas as pd
import streamlit as st

# ------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
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
    st.image("logo-cecierj.png", width="stretch")

with col_titulo:
    st.title("Controle de Cadastro de Reserva – CEFET")

# ------------------------------------------------------
# LEITURA DA BASE
# ------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados() -> pd.DataFrame:
    url = (
        "https://docs.google.com/spreadsheets/d/"
        "1wAIF2-cHGP8wQpoDBVBp--xi_7-wuhTQ"
        "/export?format=xlsx"
    )
    return pd.read_excel(url)

df = carregar_dados()

# ------------------------------------------------------
# LIMPEZA DE LINHAS SUJEIRA
# ------------------------------------------------------
df = df[df["Edital"] != "Edital"]
df = df[df["Grupo"].notna() & df["Disciplina"].notna()]

# ------------------------------------------------------
# FORMATAÇÃO DE DATAS
# ------------------------------------------------------
def formatar_datas(df_mostrar: pd.DataFrame) -> pd.DataFrame:
    col_datas = [
        "Prazo para convocação",
        "Validade pagamento bolsa",
        "Data convocação",
    ]

    for col in col_datas:
        if col in df_mostrar.columns:
            df_mostrar[col] = pd.to_datetime(
                df_mostrar[col],
                errors="coerce"
            ).dt.strftime("%d/%m/%Y")

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
        "Grupo",
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

    return (
        df_encontrados
        .sort_values(
            by=["Candidato", "Edital", "Grupo", "Disciplina", "Posição"]
        )[colunas_layout]
    )

# ------------------------------------------------------
# CÁLCULO DE KPIs
# ------------------------------------------------------
def calcular_kpis(df_base: pd.DataFrame) -> dict:
    df_tmp = df_base.copy()

    df_tmp["Prazo para convocação"] = pd.to_datetime(
        df_tmp["Prazo para convocação"],
        errors="coerce"
    )

    hoje = pd.Timestamp.today().normalize()

    expirado_por_prazo = (
        (df_tmp["Status"] != "Convocado")
        & df_tmp["Prazo para convocação"].notna()
        & (df_tmp["Prazo para convocação"] < hoje)
    )

    expirado_por_obs = (
        df_tmp["Obs"]
        .fillna("")
        .str.contains("expirado para convocação", case=False)
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
st.subheader("Indicadores")

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

col1.metric("Total de candidatos", kpis["Total de candidatos"])
col2.metric("Convocados", kpis["Convocados"])
col3.metric("Aguardando convocação", kpis["Aguardando convocação"])
col4.metric("Expirados", kpis["Expirados"])
col5.metric("Outros status", kpis["Outros status"])

# ------------------------------------------------------
# BUSCA POR CANDIDATO
# ------------------------------------------------------
st.markdown("---")
st.subheader("Buscar candidato (todas as ocorrências)")

nome = st.text_input("Digite pelo menos 3 letras do nome:")

if nome and len(nome.strip()) >= 3:
    resultado = buscar_ocorrencias_candidato(nome.strip(), df)

    if resultado.empty:
        st.info("Nenhum candidato encontrado para essa busca.")
    else:
        st.dataframe(
            formatar_datas(resultado.copy()),
            width="stretch"
        )

elif nome:
    st.warning("Digite pelo menos 3 letras do nome.")

# ------------------------------------------------------
# FILTROS TIPO EXCEL (AJUSTADOS)
# ------------------------------------------------------
st.markdown("---")
st.subheader("Fila por Edital / Grupo / Disciplina")

# Sempre trabalhar com cópia limpa
df_filtrado = df.copy()

# ---- FILTRO EDITAL ----
opcoes_edital = ["(todos)"] + sorted(
    df_filtrado["Edital"].dropna().unique().tolist()
)
edital_sel = st.selectbox("Edital", options=opcoes_edital)

if edital_sel != "(todos)":
    df_filtrado = df_filtrado[df_filtrado["Edital"] == edital_sel]

# ---- FILTRO GRUPO (somente valores reais da coluna Grupo) ----
df_filtrado = df_filtrado[df_filtrado["Grupo"].notna()]

grupo_options = ["(todos)"] + sorted(
    df_filtrado["Grupo"].dropna().unique().tolist()
)
grupo_sel = st.selectbox("Grupo", options=grupo_options)

if grupo_sel != "(todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo"] == grupo_sel]

# ---- FILTRO DISCIPLINA ----
df_filtrado = df_filtrado[df_filtrado["Disciplina"].notna()]

disc_options = ["(todas)"] + sorted(
    df_filtrado["Disciplina"].dropna().unique().tolist()
)
disc_sel = st.selectbox("Disciplina", options=disc_options)

if disc_sel != "(todas)":
    df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_sel]

# ---- TRATAMENTO DA POSIÇÃO E EXIBIÇÃO ----
df_filtrado["Posição"] = pd.to_numeric(
    df_filtrado["Posição"],
    errors="coerce"
)

colunas_layout = [
    "Edital",
    "Grupo",
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

df_mostrar = (
    df_filtrado
    .sort_values(by="Posição", na_position="last")[colunas_layout]
    .copy()
)

df_mostrar = formatar_datas(df_mostrar)

st.dataframe(df_mostrar, width="stretch")
