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

# Remover "ampla concorrência" da lista
funcoes_str = [f for f in funcoes_str if "ampla concorrência" not in f.lower()]

funcao_options = ["(todos)"] + sorted(funcoes_str)
funcao_sel = st.selectbox("💼 Função", options=funcao_options)

if funcao_sel != "(todos)":
    df_filtrado = df_filtrado[
        df_filtrado["Função"].astype(str) == funcao_sel
    ]

# ---- FILTRO DISCIPLINA (CORRIGIDO - REMOVER "posição por cotas") ----
df_filtrado = df_filtrado[df_filtrado["Disciplina"].notna()]

disc_validas = df_filtrado["Disciplina"].dropna().unique().tolist()
# Remover "posição por cotas" da lista (case insensitive)
disc_validas = [d for d in disc_validas if "posição por cotas" not in d.lower()]

disc_options = ["(todas)"] + sorted(disc_validas)
disc_sel = st.selectbox("📚 Disciplina", options=disc_options)

if disc_sel != "(todas)":
    df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_sel]

# ---- FILTRO STATUS (CORRIGIDO - REMOVER "data da convocação") ----
status_validos = df_filtrado["Status"].dropna().unique().tolist()
# Remover "data da convocação" da lista (case insensitive)
status_validos = [s for s in status_validos if "data da convocação" not in s.lower()]

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