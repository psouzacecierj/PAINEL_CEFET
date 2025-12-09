import pandas as pd
import streamlit as st

st.set_page_config(page_title="CCR – CEFET", layout="wide")

# --- Logo + Título ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    st.image("logo-cecierj.png", width="stretch")
with col_titulo:
    st.title("Controle de Cadastro de Reserva – CEFET")

# === 1. Ler base ===
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1-tCbTdcdXZBAdvmcJ0WEsztPgxC8-EBz/export?format=xlsx"
    df = pd.read_excel(url)
    return df


df = carregar_dados()

# === 2. Buscar grupo por candidato ===
def buscar_grupo_por_candidato(nome_parcial: str, df_base: pd.DataFrame) -> pd.DataFrame:
    mask_nome = df_base["Candidato"].str.contains(nome_parcial, case=False, na=False)
    df_encontrados = df_base[mask_nome]

    if df_encontrados.empty:
        return pd.DataFrame()

    linha_ref = df_encontrados.iloc[0]
    edital_ref = linha_ref["Edital"]
    grupo_ref = linha_ref["Grupo"]
    disc_ref = linha_ref["Disciplina"]

    mask_grupo = (
        (df_base["Edital"] == edital_ref) &
        (df_base["Grupo"] == grupo_ref) &
        (df_base["Disciplina"] == disc_ref)
    )

    colunas_layout = [
        "Edital", "Grupo", "Disciplina", "Posição",
        "Candidato", "Titulação", "Status",
        "Prazo para convocação", "Validade pagamento bolsa",
        "Data convocação", "Obs",
    ]

    df_grupo = (
        df_base[mask_grupo]
        .sort_values(by="Posição", ascending=True)[colunas_layout]
    )
    return df_grupo

# === 3. Cálculo de KPIs ===
def calcular_kpis(df_base: pd.DataFrame) -> dict:
    df_tmp = df_base.copy()
    df_tmp["Prazo para convocação"] = pd.to_datetime(df_tmp["Prazo para convocação"], errors="coerce")
    hoje = pd.Timestamp.today().normalize()

    expirado_por_prazo = (
        (df_tmp["Status"] != "Convocado") &
        df_tmp["Prazo para convocação"].notna() &
        (df_tmp["Prazo para convocação"] < hoje)
    )

    expirado_por_obs = df_tmp["Obs"].fillna("").str.contains("expirado para convocação", case=False)

    expirados_mask = expirado_por_prazo | expirado_por_obs

    total = len(df_tmp)
    convocados = (df_tmp["Status"] == "Convocado").sum()
    aguardando = (
        (df_tmp["Status"] == "Aguardando convocação") &
        (~expirados_mask)
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

# -------------------------------------------------------------------
# 4. KPIs na tela

st.markdown("---")

kpis = calcular_kpis(df)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total de candidatos", kpis["Total de candidatos"])
with col2:
    st.metric("Convocados", kpis["Convocados"])
with col3:
    st.metric("Aguardando convocação", kpis["Aguardando convocação"])
with col4:
    st.metric("Expirados", kpis["Expirados"])
with col5:
    st.metric("Outros status", kpis["Outros status"])

st.markdown("---")

# === 5. Busca por candidato ===
st.subheader("Buscar candidato (fila da mesma vaga)")
nome = st.text_input("Digite pelo menos 3 letras do nome:")

if nome and len(nome.strip()) >= 3:
    resultado = buscar_grupo_por_candidato(nome.strip(), df)

    if resultado.empty:
        st.info("Nenhum candidato encontrado para essa busca.")
    else:
        df_mostrar = resultado.copy()
        for col in ["Prazo para convocação", "Validade pagamento bolsa", "Data convocação"]:
            if col in df_mostrar.columns:
                df_mostrar[col] = pd.to_datetime(df_mostrar[col], errors="coerce")

        st.dataframe(df_mostrar, width="stretch")

elif nome:
    st.warning("Digite pelo menos 3 letras do nome.")

st.markdown("---")

# === 6. Filtros tipo Excel ===
st.subheader("Fila por Edital / Grupo / Disciplina")

# Seleção de Edital
edital_sel = st.selectbox(
    "Edital",
    options=sorted(df["Edital"].dropna().unique())
)

df_edital = df[df["Edital"] == edital_sel].copy()

df_edital["Grupo"] = df_edital["Grupo"].astype(str)

grupo_options = ["(todos)"] + sorted(df_edital["Grupo"].dropna().unique().tolist())

grupo_sel = st.selectbox("Grupo", options=grupo_options)

df_filtrado = df_edital.copy()
if grupo_sel != "(todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo"] == grupo_sel]

# Garantir Disciplina como texto
df_filtrado["Disciplina"] = df_filtrado["Disciplina"].astype(str)

disc_options = ["(todas)"] + sorted(df_filtrado["Disciplina"].dropna().unique().tolist())

disc_sel = st.selectbox("Disciplina", options=disc_options)

if disc_sel != "(todas)":
    df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_sel]

colunas_layout = [
    "Edital", "Grupo", "Disciplina", "Posição",
    "Candidato", "Titulação", "Status",
    "Prazo para convocação", "Validade pagamento bolsa",
    "Data convocação", "Obs",
]

df_mostrar = df_filtrado.sort_values(by="Posição", ascending=True)[colunas_layout].copy()

for col in ["Prazo para convocação", "Validade pagamento bolsa", "Data convocação"]:
    if col in df_mostrar.columns:
        df_mostrar[col] = pd.to_datetime(df_mostrar[col], errors="coerce")

st.dataframe(df_mostrar, width="stretch")