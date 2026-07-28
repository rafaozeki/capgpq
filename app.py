import streamlit as st
import json
import os
import re
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# --- DIRETIVA PORTÁTIL: Verificação Automática de Pacotes no Ambiente Portátil ---
def auto_verify_portable_environment():
    """Garante que todas as dependências essenciais (pdfplumber, pypdf, etc.) estejam instaladas no ambiente Python portátil."""
    import importlib.util, subprocess, sys
    pkgs = {"pdfplumber": "pdfplumber", "pypdf": "pypdf", "playwright": "playwright", "pandas": "pandas", "altair": "altair"}
    missing = [pkg for mod, pkg in pkgs.items() if importlib.util.find_spec(mod) is None]
    if missing:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing + ["--quiet"])
        except Exception:
            pass

auto_verify_portable_environment()

from google_api import get_sheets, get_sheet_data, update_sheet_cell

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_app_file(filename):
    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "app", filename),
        os.path.join(os.path.dirname(BASE_DIR), filename)
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return os.path.join(BASE_DIR, filename)

CONFIG_FILE = find_app_file('config.json')

PPG_MAPPING_SIIU = {
    "CIENCIAS SOCIAIS": "CIÊNCIAS SOCIAIS",
    "EDUCACAO": "EDUCAÇÃO",
    "EDUCACAO E SAUDE": "EDUCAÇÃO E SAÚDE NA INFÂNCIA E ADOLESCÊNCIA",
    "EDUCACAO E SAUDE NA INFANCIA E NA ADOLESCENCIA": "EDUCAÇÃO E SAÚDE NA INFÂNCIA E ADOLESCÊNCIA",
    "EDUCACAO E SAUDE NA INFANCIA E ADOLESCENCIA": "EDUCAÇÃO E SAÚDE NA INFÂNCIA E ADOLESCÊNCIA",
    "FILOSOFIA": "FILOSOFIA",
    "HISTORIA": "HISTÓRIA",
    "HISTORIA DA ARTE": "HISTÓRIA DA ARTE",
    "LETRAS": "LETRAS",
    "PROFHISTORIA - MESTRADO PROFISSIONAL": "ENSINO DE HISTÓRIA",
    "PROFHISTORIA - DOUTORADO PROFISSIONAL": "ENSINO DE HISTÓRIA",
    "PROFHISTORIA": "ENSINO DE HISTÓRIA",
    "ENSINO DE HISTORIA": "ENSINO DE HISTÓRIA",
    "POS-DOUTORADO": "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS"
}

KEYWORDS = [
    "nome", "matrícula", "documento de identificação", "órgão emissor", 
    "estado de emissão", "data de emissão", "data de nascimento", "telefone", "celular", 
    "e-mail", "cep", "logradouro", "número", "bairro", "cidade", "estado", 
    "complemento", "programa de pós", "rg", "rne", "tipo de benefício", "rua", 
    "situação", "prazo", "nível", "ano de ingresso", "processo sei", "naturalidade", 
    "homologação", "observações", "pendências", "orcid", "secretário", "lattes",
    "tipo de solicitação", "data para execução", "nº do processo", "unidade", 
    "carimbo", "data da demanda", "processo recebido por", "recebido em"
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;1,400&display=swap');

html, body, [class*="css"]  {
    font-family: 'Merriweather', serif !important;
}

.info-title {
    font-family: 'Merriweather', serif !important;
    font-weight: 700 !important;
    color: #174C33 !important;
    font-size: 0.90rem;
    margin-bottom: 2px;
    margin-top: 10px;
}

.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f4f8f5;
    text-align: center;
    padding: 10px;
    font-size: 0.9rem;
    color: #174C33;
    border-top: 2px solid #82bf24;
    z-index: 1000;
}

[data-testid="stSidebar"] {
    border-right: 4px solid #82bf24 !important;
}

[data-testid="stExpander"] {
    border: 1px solid #d9e5df;
    border-radius: 6px;
    box-shadow: 0px 2px 4px rgba(23, 76, 51, 0.08);
}

/* Restauração das cores dos botões para o padrão UNIFESP Verde Escuro #174C33 com hover em Verde Folha #82bf24 */
button[data-testid="stBaseButton-primary"], 
button[data-testid="stBaseButton-secondary"], 
div.stButton > button, 
div.stDownloadButton > button {
    background-color: #174C33 !important;
    color: #ffffff !important;
    border: 1px solid #174C33 !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    transition: all 0.2s ease-in-out !important;
}

button[data-testid="stBaseButton-primary"]:hover, 
button[data-testid="stBaseButton-secondary"]:hover, 
div.stButton > button:hover, 
div.stDownloadButton > button:hover {
    background-color: #82bf24 !important;
    color: #ffffff !important;
    border-color: #82bf24 !important;
}
</style>
"""

def get_secret(key, default=""):
    """Retorna uma chave do st.secrets ou os.environ com segurança sem estourar erro caso secrets.toml não exista."""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)

DEFAULT_CONFIG = {
    "1agccixes8ld6ecxGavMOxEd0R4Efnp6lDtruJ2tjOUM": {
        "name": "Requisição de Passe Escolar - EMTU UNIFESP (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "EMTU - Requisição de Passe Escolar"
    },
    "1IUxi5NEoxcBn7y9s9euUcALmINoE29of7NkaLcYZUbk": {
        "name": "Solicitação de Declaração de Conclusão (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Declaração de Conclusão de Curso"
    },
    "14zUk4m1WI6JK7mIg5v1T0shMsmWzwM2sd9MH-ApFfkI": {
        "name": "SEI - Diplomas - Gerenciamento (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Solicitações de Diplomas"
    },
    "1bvpgCyLUw8C7c_yX54EWe3CPv_5JsfMC-OdNJj3wYdg": {
        "name": "Formulário SPTrans Estudante (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "SPTrans Estudante"
    },
    "1ourQvwY79sEVqvSB_ip7vKO0LrraAZk9F6sf6UB8Sjk": {
        "name": "SEI - DISCENTE - LIBERAÇÃO DE USUÁRIO EXTERNO (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Liberação de Usuário Externo (Discente)"
    },
    "1Vrcu5Fcd9D2_NwJ2M4RvR-DlFYSh44TMlilHNCJTDWw": {
        "name": "SEI - LIBERAÇÃO DE USUÁRIO EXTERNO - DOCENTE (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Liberação de Usuário Externo (Docente)"
    },
    "11Te_uPZUBtW4qYI6-NHEBJN4DKTGOtexSpjMMV8A6wE": {
        "name": "Requisição de Passe Escolar  UNIFESP- SPTrans (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "SPTrans - Requisição de Passe Escolar"
    },
    "1V0dREdi3XmimuIu8u4YceqwJWDlQe7amfL6RkO2AeO0": {
        "name": "Controle de Processos - SEI (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Controle de Processos SEI"
    },
    "18vB8bsZLPDrNLX54Ub8vaE3w56pZfhX2pS2F-LYvhkw": {
        "name": "Membros - Bancas de Defesas - cadastro - SIIU (respostas)",
        "aba": "Respostas ao formulário 1",
        "tipo": "Cadastro - Membros de Bancas de Defesa"
    }
}

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.cache_resource(show_spinner="Autenticando no SIIU (apenas 1 vez por servidor)...")
def init_cached_driver(login, senha):
    import siiu_extractor
    driver, erro = siiu_extractor.init_cached_driver(login, senha)
    return driver, erro

def extract_relevant_data(row, header):
    extracted = {}
    row_padded = row + [''] * (len(header) - len(row))
    for col, val in zip(header, row_padded):
        col_clean = str(col).strip()
        col_lower = col_clean.lower()
        if any(kw in col_lower for kw in KEYWORDS):
            val_clean = str(val).strip()
            if val_clean:
                extracted[col_clean] = val_clean
    return extracted

def sort_and_format_card_data(relevant_data):
    """
    Formata e ordena os campos dos cards para Controle de Processos SEI e demais demandas.
    Ordem obrigatória:
    1. Tipo de solicitação
    2. Unidade
    3. Situação (triagem)
    4. Nº do Processo
    5. Data para Execução
    6. Observações
    ...demais campos.
    Também renomeia 'Endereço de e-mail' / 'E-mail' para 'Processo recebido por' e 'Carimbo de data/hora' para 'Recebido em'.
    """
    formatted_items = []
    
    for original_key, val in relevant_data.items():
        k_norm = original_key.strip()
        k_low = k_norm.lower()
        
        display_label = k_norm
        if "e-mail" in k_low or "email" in k_low:
            display_label = "Processo recebido por"
        elif "carimbo" in k_low:
            display_label = "Recebido em"
            
        formatted_items.append({
            "original_key": original_key,
            "display_label": display_label,
            "val": val
        })
        
    priority_order = [
        "tipo de solicitação",
        "tipo de solicitacao",
        "unidade",
        "situação (triagem)",
        "situacao (triagem)",
        "situação",
        "situacao",
        "nº do processo",
        "n° do processo",
        "numero do processo",
        "processo sei",
        "data para execução",
        "data para execucao",
        "observações",
        "observacoes"
    ]
    
    def get_priority(item):
        lbl_low = item["display_label"].lower()
        for idx, p in enumerate(priority_order):
            if p in lbl_low:
                return idx
        return 999
        
    formatted_items.sort(key=get_priority)
    return formatted_items

def generate_printable_report_html(df_report, title_name):
    """Gera documento HTML responsivo e formatado para impressão (A4 / PDF) com acionamento automático de window.print()."""
    html_cols = "".join([f"<th>{col}</th>" for col in df_report.columns])
    
    rows_html = []
    for idx, row in df_report.iterrows():
        cells = "".join([f"<td>{str(val) if val is not None else ''}</td>" for val in row.values])
        rows_html.append(f"<tr>{cells}</tr>")
    html_rows = "\n".join(rows_html)
    
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Demandas - UNIFESP EFLCH</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&display=swap');
        body {{
            font-family: 'Merriweather', 'Helvetica Neue', Arial, sans-serif;
            margin: 20px;
            color: #174C33;
            background-color: #ffffff;
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #174C33;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #174C33;
            font-size: 20px;
        }}
        .header p {{
            margin: 4px 0 0 0;
            color: #615c5c;
            font-size: 13px;
        }}
        .meta {{
            font-size: 12px;
            margin-bottom: 15px;
            color: #333333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-top: 10px;
        }}
        th, td {{
            border: 1px solid #cccccc;
            padding: 6px 8px;
            text-align: left;
            word-wrap: break-word;
        }}
        th {{
            background-color: #174C33;
            color: #ffffff;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9fbf9;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            font-size: 10px;
            color: #888888;
            border-top: 1px solid #eeeeee;
            padding-top: 8px;
        }}
        @media print {{
            @page {{
                size: A4 landscape;
                margin: 10mm;
            }}
            body {{
                margin: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>UNIFESP — Relatório de Demandas ({title_name})</h1>
        <p>Painel de Controle - CaPGPq-EFLCH | Gerado em: {now_str}</p>
    </div>
    
    <div class="meta">
        <strong>Total de Registros:</strong> {len(df_report)} item(ns)
    </div>
    
    <table>
        <thead>
            <tr>{html_cols}</tr>
        </thead>
        <tbody>
            {html_rows}
        </tbody>
    </table>
    
    <div class="footer">
        Relatório oficial gerado pelo Painel de Controle CaPGPq-EFLCH — UNIFESP
    </div>
    
    <script>
        window.onload = function() {{
            window.print();
        }};
    </script>
</body>
</html>"""
    return html_doc

def parse_date_br(date_str):
    if not date_str or not str(date_str).strip():
        return None
    val_str = str(date_str).strip().split(" ")[0]
    
    formats = [
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
        "%m/%d/%Y", "%d/%m/%y", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
            
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if pd.notnull(dt):
            return dt.date()
    except Exception:
        pass
        
    return None

def check_password():
    """Retorna True se o usuário digitou a senha correta."""
    if st.session_state.get("password_correct"):
        return True

    st.markdown("<h1 style='text-align: center; color: #174C33; font-family: \"Merriweather\", serif; font-weight: 800; font-size: 2.0rem; margin-bottom: 0px;'>Painel de Controle - CAPGPQ - EFLCH</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #615c5c; font-size: 1.1rem; margin-top: 5px; margin-bottom: 25px;'>🔒 Acesso Restrito</h3>", unsafe_allow_html=True)
    
    try:
        senha_correta = st.secrets.get("app_password", "cafezinho")
    except Exception:
        senha_correta = "cafezinho"
        
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login_form"):
            senha_digitada = st.text_input("Digite a senha de acesso ao Painel de Controle:", type="password")
            submit_btn = st.form_submit_button("Entrar", use_container_width=True)
            
        if submit_btn or senha_digitada:
            if senha_digitada == senha_correta:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Senha incorreta. Tente novamente.")
            
    return False

def main():
    st.set_page_config(page_title="Painel de Controle - CaPGPq-EFLCH", page_icon="🎓", layout="wide")
    
    # Exige a senha antes de renderizar o resto do aplicativo
    if not check_password():
        return
        
    st.markdown(CSS, unsafe_allow_html=True)
    
    config = load_json(CONFIG_FILE)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Estatísticas"
    
    st.sidebar.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #174C33; font-family: 'Merriweather', serif; font-weight: 800; font-size: 2.2rem; margin-bottom: 0px;">UNIFESP</h1>
            <p style="color: #615c5c; font-size: 0.95rem; margin-top: -10px;">Painel de Controle - CaPGPq-EFLCH</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 1. Painel de Controle
    st.sidebar.markdown("**Painel de Controle:**")
    panel_btn_type = "primary" if st.session_state.current_page == "Estatísticas" else "secondary"
    if st.sidebar.button("📊 Estatísticas", type=panel_btn_type, use_container_width=True):
        st.session_state.current_page = "Estatísticas"
        
    links_btn_type = "primary" if st.session_state.current_page == "🔗 Links Úteis" else "secondary"
    if st.sidebar.button("🔗 Links Úteis", type=links_btn_type, use_container_width=True):
        st.session_state.current_page = "🔗 Links Úteis"
        
    polare_btn_type = "primary" if st.session_state.current_page == "📝 Polare" else "secondary"
    if st.sidebar.button("📝 Polare", type=polare_btn_type, use_container_width=True):
        st.session_state.current_page = "📝 Polare"
        
    academic_btn_type = "primary" if st.session_state.current_page == "🎓 Análise de Históricos" else "secondary"
    if st.sidebar.button("🎓 Análise de Históricos", type=academic_btn_type, use_container_width=True):
        st.session_state.current_page = "🎓 Análise de Históricos"
        
    st.sidebar.divider()
    
    # 2. Módulos das planilhas
    demand_options = []
    if config:
        st.sidebar.markdown("**Módulos:**")
        for sheet_id, info in config.items():
            demand_options.append(info.get('tipo', 'Demanda'))
        demand_options = sorted(list(set(demand_options)))
            
    for option in demand_options:
        btn_type = "primary" if st.session_state.current_page == option else "secondary"
        if st.sidebar.button(option, type=btn_type, use_container_width=True):
            st.session_state.current_page = option
            
    st.sidebar.divider()
    
    # 3. Configurações
    config_btn_type = "primary" if st.session_state.current_page == "⚙️ Configurações" else "secondary"
    if st.sidebar.button("⚙️ Configurações", type=config_btn_type, use_container_width=True):
        st.session_state.current_page = "⚙️ Configurações"
    
    page = st.session_state.current_page
    
    if page == "⚙️ Configurações":
        show_config_page(config)
    elif page == "Estatísticas":
        show_dashboard(config)
    elif page == "🔗 Links Úteis":
        show_links_page()
    elif page == "📝 Polare":
        show_polare_page()
    elif page == "🎓 Análise de Históricos":
        show_academic_analysis()
    else:
        selected_sheet_id = None
        selected_info = None
        for sid, info in config.items():
            if info.get('tipo') == page:
                selected_sheet_id = sid
                selected_info = info
                break
        if selected_sheet_id:
            show_demand_page(selected_sheet_id, selected_info)
            
    # Footer
    st.markdown(
        '<div class="footer">Criado por Rafael Kenji Ozeki e Janilton Alves Borborema | Versão 0.5 | Data: 21/07/2026</div>', 
        unsafe_allow_html=True
    )
    # Espaço extra para não sobrepor o footer
    st.markdown("<br><br><br>", unsafe_allow_html=True)

def show_polare_page():
    st.title("📝 Polare - Lançamento de Atividades")
    st.write("Gere facilmente o texto padronizado para lançamento no Polare.")
    st.divider()
    
    SHEET_ID = "1ItSWcAfXdp9oFQNy-I5AOpfpYCkq_GL68i-BeT_pLa4"
    ABA = "POLARE - ATIVIDADES"
    
    try:
        data = get_sheet_data(SHEET_ID, ABA)
    except Exception as e:
        st.error(f"Erro ao acessar a planilha do Polare. Verifique se você tem permissão de acesso a ela. Detalhes: {e}")
        return
        
    if not data:
        st.warning("Planilha vazia ou não encontrada.")
        return
        
    # Encontrar a linha do cabeçalho
    header_idx = -1
    for i, row in enumerate(data):
        if len(row) > 1 and "CATEGORIA" in str(row[1]).upper():
            header_idx = i
            break
            
    if header_idx == -1:
        st.error("Não foi possível encontrar o cabeçalho (coluna CATEGORIA) na planilha.")
        return
        
    header = [str(c).strip().upper() for c in data[header_idx]]
    rows = data[header_idx + 1:]
    
    # Índices das colunas
    idx_cat = header.index("CATEGORIA") if "CATEGORIA" in header else -1
    idx_nom = header.index("NOMENCLATURA NO POLARE") if "NOMENCLATURA NO POLARE" in header else -1
    idx_tit = header.index("TÍTULO DA ATIVIDADE") if "TÍTULO DA ATIVIDADE" in header else -1
    idx_res = header.index("RESUMO DA ATIVIDADE") if "RESUMO DA ATIVIDADE" in header else -1
    idx_sub = header.index("SUBATIVIDADES") if "SUBATIVIDADES" in header else -1
    
    if -1 in [idx_cat, idx_nom, idx_tit]:
        st.error("As colunas 'CATEGORIA', 'NOMENCLATURA NO POLARE' ou 'TÍTULO DA ATIVIDADE' não foram encontradas.")
        return
        
    # Construir dataframe limpo
    df_data = []
    for row in rows:
        row_padded = row + [''] * (len(header) - len(row))
        cat = str(row_padded[idx_cat]).strip()
        nom = str(row_padded[idx_nom]).strip()
        tit = str(row_padded[idx_tit]).strip()
        res = str(row_padded[idx_res]).strip() if idx_res != -1 else ""
        sub = str(row_padded[idx_sub]).strip() if idx_sub != -1 else ""
        
        if cat and nom and tit: # Ignorar linhas vazias
            df_data.append({"Categoria": cat, "Nomenclatura": nom, "Titulo": tit, "Resumo": res, "Subatividades": sub})
            
    df = pd.DataFrame(df_data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categorias = sorted(df["Categoria"].unique().tolist())
        cat_selecionada = st.selectbox("1. Categoria", categorias)
        
    with col2:
        df_filtrado_cat = df[df["Categoria"] == cat_selecionada]
        nomenclaturas = sorted(df_filtrado_cat["Nomenclatura"].unique().tolist())
        nom_selecionada = st.selectbox("2. Nomenclatura no Polare", nomenclaturas)
        
    with col3:
        df_filtrado_nom = df_filtrado_cat[df_filtrado_cat["Nomenclatura"] == nom_selecionada]
        titulos = sorted(df_filtrado_nom["Titulo"].unique().tolist())
        tit_selecionado = st.selectbox("3. Título da Atividade", titulos)
        
    # Pegar os dados da atividade final
    atividade_final = df_filtrado_nom[df_filtrado_nom["Titulo"] == tit_selecionado].iloc[0]
    
    st.divider()
    
    res_c1, res_c2 = st.columns([1, 1])
    
    with res_c1:
        st.markdown('<div class="info-title">Detalhes da Atividade</div>', unsafe_allow_html=True)
        st.write(f"**Resumo:** {atividade_final['Resumo']}")
                
    with res_c2:
        st.markdown('<div class="info-title">Gerar Lançamento</div>', unsafe_allow_html=True)
        
        lista_sub = []
        if atividade_final['Subatividades']:
            # Divide as subatividades por linhas se houver
            lista_sub = [s.strip() for s in str(atividade_final['Subatividades']).split('\n') if s.strip() and len(s.strip()) > 2]
            
        sub_selecionadas = []
        if lista_sub:
            sub_selecionadas = st.multiselect("Selecionar Subatividades (Opcional):", options=lista_sub)
            
        nome_solicitante = st.text_input("Nome do Solicitante (opcional):", placeholder="Ex: Rafael Kenji Ozeki")
        processo_sei = st.text_input("Número do Processo SEI (opcional):", placeholder="Ex: 23089.027493/2025-64")
        
        # Montar o texto final
        texto_final = tit_selecionado
        if sub_selecionadas:
            texto_final += " - " + " / ".join(sub_selecionadas)
        if nome_solicitante:
            texto_final += f": {nome_solicitante.strip()}"
        if processo_sei:
            texto_final += f" (processo SEI {processo_sei.strip()})"
            
        st.caption("Texto padronizado gerado (clique no ícone para copiar):")
        st.code(texto_final, language="text")

def show_links_page():
    st.title("🔗 Links Úteis")
    st.write("Acesso rápido aos sistemas e páginas da Unifesp.")
    st.divider()
    
    c1, c2, c3 = st.columns([1, 6, 1]) # Centralizar os botões
    with c2:
        st.link_button("🌐 PROPGPQ", "https://proreitoria.unifesp.br/propgpq/", use_container_width=True)
        st.link_button("🌐 EFLCH", "https://campus.unifesp.br/gru/", use_container_width=True)
        st.link_button("🌐 SIIU - Sistema Integrado de Informações Universitárias", "https://siiu.unifesp.br/", use_container_width=True)
        st.link_button("🌐 Área Exclusiva das CEPG", "https://procdados.epm.br/dpd/pg/", use_container_width=True)
        st.link_button("🌐 SUA Unifesp", "https://sua.unifesp.br/", use_container_width=True)
        st.link_button("🌐 Sistema de Atendimento SUA", "https://atendimento.unifesp.br/", use_container_width=True)
        st.link_button("🌐 Editor Joomla CaPGPq", "https://admin-ppg.unifesp.br/guarulhos/informes/solicitacao-de-documentos-academicos#emissao-de-diplomas-solicitacao-realizada-remotamente-pelo-a-discente-egress", use_container_width=True)

def get_row_date(row_padded, header):
    """Extrai e converte a data da linha priorizando a coluna de carimbo automático do formulário (evita colunas manuais vazias)."""
    for idx, col in enumerate(header):
        c_low = str(col).lower()
        if "carimbo" in c_low or "timestamp" in c_low:
            v = row_padded[idx] if idx < len(row_padded) else ""
            d = parse_date_br(v)
            if d:
                return d, str(v)
                
    for idx, col in enumerate(header):
        c_low = str(col).lower()
        if "data" in c_low and "cadastro" not in c_low:
            v = row_padded[idx] if idx < len(row_padded) else ""
            d = parse_date_br(v)
            if d:
                return d, str(v)
                
    for idx, col in enumerate(header):
        c_low = str(col).lower()
        if "data" in c_low:
            v = row_padded[idx] if idx < len(row_padded) else ""
            d = parse_date_br(v)
            if d:
                return d, str(v)
                
    return None, ""

def show_dashboard(config):
    st.title("📊 Estatísticas")
    st.write("Visão geral de todas as suas demandas recebidas.")
    
    if not config:
        st.info("Nenhuma demanda configurada. Acesse as Configurações para começar.")
        return
        
    st.divider()
    st.write("📅 **Filtro de Período**")
    f_col1, f_col2 = st.columns([2, 2])
    with f_col1:
        filtro_selecao = st.selectbox(
            "Visualizar estatísticas de:", 
            ["Desde o Início (Geral)", "Apenas Hoje", "Últimos 7 dias", "Mês Atual", "Últimos 6 meses", "Escolher um Período Específico"]
        )
        
    data_inicio, data_fim = None, None
    hoje = datetime.now().date()
    
    if filtro_selecao == "Apenas Hoje":
        data_inicio = hoje
        data_fim = hoje
    elif filtro_selecao == "Últimos 7 dias":
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
    elif filtro_selecao == "Mês Atual":
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    elif filtro_selecao == "Últimos 6 meses":
        data_inicio = (hoje.replace(day=1) - timedelta(days=165)).replace(day=1)
        data_fim = hoje
    elif filtro_selecao == "Escolher um Período Específico":
        with f_col2:
            st.caption("Digite as datas manualmente (formato: DD/MM/AAAA)")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                str_inicio = st.text_input("Data Início:", value=(hoje - timedelta(days=7)).strftime("%d/%m/%Y"))
            with col_d2:
                str_fim = st.text_input("Data Fim:", value=hoje.strftime("%d/%m/%Y"))
            
            parsed_inicio = parse_date_br(str_inicio)
            parsed_fim = parse_date_br(str_fim)
            
            if parsed_inicio:
                data_inicio = parsed_inicio.date() if isinstance(parsed_inicio, datetime) else parsed_inicio
            else:
                data_inicio = hoje - timedelta(days=7)
                
            if parsed_fim:
                data_fim = parsed_fim.date() if isinstance(parsed_fim, datetime) else parsed_fim
            else:
                data_fim = hoje
        
    total_atividades = 0
    atividades_por_tipo = {}
    atividades_por_ppg = {}
    
    PPGS_OFICIAIS = [
        "Ensino de História", "Educação e Saúde", "Ciências Sociais", 
        "Educação", "Filosofia", "História", "História da Arte", "Letras"
    ]
    
    for ppg in PPGS_OFICIAIS:
        atividades_por_ppg[ppg] = 0
    atividades_por_ppg["Não Identificado"] = 0

    import unicodedata
    def norm(txt):
        return "".join(c for c in unicodedata.normalize('NFD', str(txt).upper()) if unicodedata.category(c) != 'Mn').strip()

    def normalize_ppg(raw_ppg_name):
        if not raw_ppg_name:
            return "Não Identificado"
        p_norm = norm(raw_ppg_name)
        for k, v in PPG_MAPPING_SIIU.items():
            if k in p_norm or p_norm in k:
                if "HISTORIA DA ARTE" in v: return "História da Arte"
                elif "HISTORIA" in v: return "Ensino de História" if "ENSINO" in v else "História"
                elif "SOCIAIS" in v: return "Ciências Sociais"
                elif "SAUDE" in v: return "Educação e Saúde"
                elif "EDUCACAO" in v: return "Educação"
                elif "FILOSOFIA" in v: return "Filosofia"
                elif "LETRAS" in v: return "Letras"
        for p_of in PPGS_OFICIAIS:
            if norm(p_of) in p_norm or p_norm in norm(p_of):
                return p_of
        return "Não Identificado"
    
    try:
        for sheet_id, info in config.items():
            tipo = info.get('tipo', 'Outros')
            if tipo not in atividades_por_tipo:
                atividades_por_tipo[tipo] = 0
            
            try:
                data = get_sheet_data(sheet_id, info.get('aba', 'Respostas ao formulário 1'))
                if data and len(data) > 1:
                    header = data[0]
                    rows = data[1:]
                    
                    ppg_col_index = None
                    for i, col in enumerate(header):
                        c_low = str(col).lower()
                        if "programa" in c_low or "ppg" in c_low or "curso" in c_low:
                            ppg_col_index = i
                            break
                            
                    for row in rows:
                        row_padded = row + [''] * (len(header) - len(row))
                        data_da_linha, valor_data_completo = get_row_date(row_padded, header)
                        
                        if filtro_selecao != "Desde o Início (Geral)":
                            if data_da_linha and data_inicio and data_fim:
                                d_cmp = data_da_linha.date() if isinstance(data_da_linha, datetime) else data_da_linha
                                if not (data_inicio <= d_cmp <= data_fim):
                                    continue
                            elif not data_da_linha:
                                continue
                                
                        total_atividades += 1
                        atividades_por_tipo[tipo] += 1
                        
                        if ppg_col_index is not None and len(row) > ppg_col_index:
                            valor_ppg = str(row_padded[ppg_col_index]).strip()
                            ppg_normalizado = normalize_ppg(valor_ppg)
                            if ppg_normalizado in atividades_por_ppg:
                                atividades_por_ppg[ppg_normalizado] += 1
                            else:
                                atividades_por_ppg["Não Identificado"] += 1
            except Exception as e_sheet:
                print(f"Aviso ao ler planilha {sheet_id}: {e_sheet}")
    except Exception as e_dash:
        print(f"Aviso no dashboard: {e_dash}")
                
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Solicitações Recebidas no Período", total_atividades)
        
    st.divider()
    
    # Gráficos em colunas
    st.write("### Exibição dos Dados")
    tipo_viz = st.radio("Selecione o formato de visualização:", ["Lista Corrida", "Gráfico de Barras", "Gráfico de Pizza"], horizontal=True)
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Volume por Tipo de Demanda")
        if sum(atividades_por_tipo.values()) > 0:
            df_chart = pd.DataFrame(list(atividades_por_tipo.items()), columns=["Demanda", "Quantidade"])
            df_chart = df_chart.sort_values(by="Quantidade", ascending=False)
            
            if tipo_viz == "Lista Corrida":
                for _, row in df_chart.iterrows():
                    st.markdown(f"- **{row['Demanda']}:** {row['Quantidade']}")
            elif tipo_viz == "Gráfico de Barras":
                chart1 = alt.Chart(df_chart).mark_bar(size=25, color="#174C33", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                    x=alt.X('Demanda', title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Quantidade', title='Solicitações', axis=alt.Axis(tickMinStep=1)),
                    tooltip=['Demanda', 'Quantidade']
                ).properties(height=350)
                st.altair_chart(chart1, use_container_width=True)
            else: # Pizza
                chart1 = alt.Chart(df_chart).mark_arc(innerRadius=40).encode(
                    theta=alt.Theta(field="Quantidade", type="quantitative"),
                    color=alt.Color(field="Demanda", type="nominal", scale=alt.Scale(scheme='greens')),
                    tooltip=['Demanda', 'Quantidade']
                ).properties(height=350)
                st.altair_chart(chart1, use_container_width=True)
        else:
            st.info("Sem dados para este período.")
            
    with c2:
        st.subheader("Volume por PPG")
        # Remover 'Não Identificado' se for zero
        if atividades_por_ppg.get("Não Identificado") == 0:
            del atividades_por_ppg["Não Identificado"]
            
        if sum(atividades_por_ppg.values()) > 0:
            df_ppg = pd.DataFrame(list(atividades_por_ppg.items()), columns=["Programa", "Solicitações"])
            df_ppg = df_ppg.sort_values(by="Solicitações", ascending=False)
            
            if tipo_viz == "Lista Corrida":
                for _, row in df_ppg.iterrows():
                    st.markdown(f"- **{row['Programa']}:** {row['Solicitações']}")
            elif tipo_viz == "Gráfico de Barras":
                chart2 = alt.Chart(df_ppg).mark_bar(size=25, color="#2E8B57", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                    x=alt.X('Programa', title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Solicitações', title='Solicitações', axis=alt.Axis(tickMinStep=1)),
                    tooltip=['Programa', 'Solicitações']
                ).properties(height=350)
                st.altair_chart(chart2, use_container_width=True)
            else: # Pizza
                chart2 = alt.Chart(df_ppg).mark_arc(innerRadius=40).encode(
                    theta=alt.Theta(field="Solicitações", type="quantitative"),
                    color=alt.Color(field="Programa", type="nominal", scale=alt.Scale(scheme='greens')),
                    tooltip=['Programa', 'Solicitações']
                ).properties(height=350)
                st.altair_chart(chart2, use_container_width=True)
        else:
            st.info("Sem dados para este período.")
            
    st.divider()
    st.subheader("📄 Relatório de Produtividade")
    st.write("Gere um relatório abrangente das demandas processadas no período para impressão.")
    
    total = total_atividades
    if total == 0:
        st.warning("Não há demandas no período selecionado para gerar o relatório.")
    else:
        media_por_servidor = total / 2
        
        if data_inicio and data_fim:
            dias = (data_fim - data_inicio).days + 1
        else:
            dias = 30 # fallback
            
        semanas = max(1, dias / 7)
        demandas_por_semana = total / semanas
        
        html_report = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Relatório de Produtividade</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
                h1 {{ color: #174C33; border-bottom: 2px solid #82bf24; padding-bottom: 10px; }}
                h2 {{ color: #2E8B57; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                .metric {{ font-size: 1.2em; margin-bottom: 10px; }}
                .highlight {{ font-weight: bold; color: #174C33; background-color: #e8f5e9; padding: 2px 6px; border-radius: 4px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f4f8f5; color: #174C33; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                @media print {{
                    .no-print {{ display: none !important; }}
                }}
            </style>
        </head>
        <body>
            <h1>Relatório de Desempenho e Demanda do Setor</h1>
            <p class="metric"><strong>Período Analisado:</strong> {dias} dias ({semanas:.1f} semanas)</p>
            
            <h2>1. Visão Geral de Carga de Trabalho</h2>
            <ul>
                <li class="metric"><strong>Total de Demandas Solicitadas:</strong> {total}</li>
                <li class="metric"><strong>Média por Servidor:</strong> {media_por_servidor:.1f} demandas (Equipe de 2)</li>
                <li class="metric"><strong>Volume Semanal do Setor:</strong> {demandas_por_semana:.1f} demandas/semana</li>
                <li class="metric"><strong>Capacidade Máxima do Setor:</strong> 80 horas/semana</li>
            </ul>
            
            <h2>2. Análise de Disponibilidade</h2>
            <p>Baseado no volume de <span class="highlight">{demandas_por_semana:.1f} demandas semanais</span> frente às 80 horas de força de trabalho disponíveis na secretaria:</p>
            <p>A média de tempo que a equipe tem disponível para dedicar a CADA solicitação (sem que a fila acumule) é de aproximadamente <span class="highlight">{(80/demandas_por_semana):.1f} horas</span>.</p>
            <p><em>* Nota: Esta média engloba todo o tempo da jornada, devendo também comportar atendimentos avulsos, reuniões e rotinas administrativas indiretas.</em></p>
            
            <h2>3. Distribuição das Demandas</h2>
            <table>
                <tr><th>Tipo de Demanda</th><th>Quantidade</th><th>Porcentagem</th></tr>
        """
        
        if sum(atividades_por_tipo.values()) > 0:
            sorted_tipos = sorted(atividades_por_tipo.items(), key=lambda item: item[1], reverse=True)
            for tipo, qtd in sorted_tipos:
                perc = (qtd/total)*100
                html_report += f"<tr><td>{tipo}</td><td>{qtd}</td><td>{perc:.1f}%</td></tr>"
                
        html_report += f"""
            </table>
            <br><br><br><br>
            <hr>
            <p style="text-align:center; font-size:0.85em; color:#777;">Relatório gerado pelo Automador CaPGPq-EFLCH em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <div class="no-print" style="text-align: center; margin-top: 30px; margin-bottom: 50px;">
                <button onclick="window.print()" style="padding: 12px 24px; background-color: #174C33; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1.1em; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🖨️ Imprimir Este Relatório</button>
                <p style="margin-top: 10px; color: #666; font-size: 0.9em;">(Ou pressione Ctrl+P)</p>
            </div>
        </body>
        </html>
        """
        
        import streamlit.components.v1 as components
        import json
        
        safe_html_report = json.dumps(html_report)
        
        js_button = f"""
        <html>
        <head>
            <style>
                .btn {{
                    display: block;
                    width: 100%;
                    padding: 0.5rem 1rem;
                    background-color: #174C33;
                    color: white;
                    border: none;
                    border-radius: 0.5rem;
                    cursor: pointer;
                    font-family: "Source Sans Pro", sans-serif;
                    font-size: 1rem;
                    text-align: center;
                }}
                .btn:hover {{
                    background-color: #0e3020;
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0;">
            <button class="btn" onclick="openReport()">📄 Gerar Relatório em Nova Aba</button>
            <script>
            function openReport() {{
                const htmlContent = {safe_html_report};
                const newWindow = window.open('', '_blank');
                newWindow.document.write(htmlContent);
                newWindow.document.close();
            }}
            </script>
        </body>
        </html>
        """
        components.html(js_button, height=60)


def show_config_page(config):
    st.title("⚙️ Configurações de Planilhas")
    st.info("Gerencie quais planilhas do seu Google Drive deseja monitorar.")
    
    try:
        all_sheets = get_sheets()
    except Exception as e:
        st.error("Erro ao acessar Google Drive! Se você re-autorizou o aplicativo, o console do Python/Terminal deve ter aberto uma nova aba para você confirmar as permissões.")
        return
        
    if not all_sheets:
        st.warning("Nenhuma planilha encontrada.")
        return
        
    for sheet in all_sheets:
        sheet_id = sheet['id']
        sheet_name = sheet['name']
        is_monitored = sheet_id in config
        
        with st.expander(f"{'✅' if is_monitored else '📁'} {sheet_name}", expanded=is_monitored):
            monitor = st.checkbox(f"Monitorar '{sheet_name}'", value=is_monitored, key=f"mon_{sheet_id}")
            
            aba_padrao = config.get(sheet_id, {}).get('aba', 'Respostas ao formulário 1') if is_monitored else 'Respostas ao formulário 1'
            tipo_padrao = config.get(sheet_id, {}).get('tipo', 'Nova Demanda') if is_monitored else 'Nova Demanda'
            
            aba = st.text_input("Nome da Aba", value=aba_padrao, key=f"aba_{sheet_id}")
            tipo = st.text_input("Nome da Demanda no Menu Lateral (ex: Diplomas, Bilhetes)", value=tipo_padrao, key=f"tipo_{sheet_id}")
            
            if st.button("Salvar Configuração", key=f"btn_{sheet_id}"):
                if monitor:
                    config[sheet_id] = {"name": sheet_name, "aba": aba, "tipo": tipo}
                else:
                    if sheet_id in config:
                        del config[sheet_id]
                save_json(config, CONFIG_FILE)
                st.success("Configurações salvas com sucesso!")
                st.rerun()

def show_academic_analysis():
    st.title("🎓 Análise de Históricos Acadêmicos")
    st.write("Esta ferramenta permite raspar dados do SIIU para avaliar a situação atual de um discente.")
    
    st.divider()
    st.subheader("1. Credenciais do SIIU")
    
    login_siiu = st.session_state.get('login_siiu', '')
    senha_siiu = st.session_state.get('senha_siiu', '')
    
    if login_siiu and senha_siiu:
        st.success("✅ Credenciais informadas com sucesso! Você já pode realizar a busca.")
        with st.expander("🔑 Credenciais do SIIU (Clique para alterar usuário ou senha)", expanded=False):
            with st.form("form_login_siiu_alt"):
                c1, c2 = st.columns(2)
                with c1:
                    u_alt = st.text_input("Usuário:", value=login_siiu)
                with c2:
                    p_alt = st.text_input("Senha:", type="password", value=senha_siiu)
                if st.form_submit_button("Atualizar Credenciais"):
                    if u_alt and p_alt:
                        st.session_state['login_siiu'] = u_alt
                        st.session_state['senha_siiu'] = p_alt
                        st.success("Credenciais atualizadas com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha usuário e senha.")
    else:
        st.info("Suas credenciais não serão salvas. Elas são usadas apenas temporariamente para o robô acessar o sistema em seu nome.")
        with st.form("form_login_siiu"):
            c1, c2 = st.columns(2)
            with c1:
                login_siiu = st.text_input("Usuário:", value="")
            with c2:
                senha_siiu = st.text_input("Senha:", type="password", value="")
                
            if st.form_submit_button("Efetuar Login / Salvar Credenciais"):
                if login_siiu and senha_siiu:
                    st.session_state['login_siiu'] = login_siiu
                    st.session_state['senha_siiu'] = senha_siiu
                    st.success("✅ Credenciais informadas com sucesso! Você já pode realizar a busca.")
                    st.rerun()
                else:
                    st.warning("⚠️ Preencha usuário e senha para efetuar login.")
        
    st.divider()
    st.subheader("2. Busca de Aluno")
    
    col_busca1, col_busca2 = st.columns(2)
    with col_busca1:
        termo_busca = st.text_input("Nome, CPF ou RA do aluno:")
    with col_busca2:
        programa = st.selectbox(
            "Programa de Pós-Graduação (Obrigatório no SIIU):", 
            [
                "Todos os Programas", 
                "Ciências Sociais", 
                "Educação", 
                "Educação e Saúde", 
                "Filosofia", 
                "História", 
                "História da Arte", 
                "Letras", 
                "ProfHistória - Mestrado Profissional",
                "ProfHistória - Doutorado Profissional",
                "Pós-Doutorado"
            ]
        )
        
    st.write("---")

    if st.button("Pesquisar no SIIU", type="primary"):
        if not login_siiu or not senha_siiu:
            st.error("Por favor, insira suas credenciais do SIIU para permitir o acesso do robô.")
        elif not termo_busca:
            st.error("Por favor, digite o Nome, CPF ou RA do aluno.")
        else:
            with st.spinner("Buscando discente(s) no SIIU... Aguarde..."):
                try:
                    import siiu_extractor
                    cached_driver, erro_login = init_cached_driver(login_siiu, senha_siiu)
                    
                    if erro_login or not cached_driver:
                        st.error(f"Erro ao autenticar no SIIU: {erro_login}")
                        init_cached_driver.clear()
                    else:
                        search_res = siiu_extractor.search_and_extract_student(login_siiu, senha_siiu, termo_busca, programa, cached_driver=cached_driver)
                        
                        if search_res.get("status") == "error":
                            st.session_state['siiu_candidatos'] = None
                            st.session_state['resultado_siiu'] = search_res
                            st.rerun()
                        elif search_res.get("single"):
                            st.session_state['resultado_siiu'] = search_res.get("details")
                            st.session_state['siiu_candidatos'] = None
                            st.rerun()
                        else:
                            st.session_state['siiu_candidatos'] = search_res.get("candidates", [])
                            st.session_state['resultado_siiu'] = None
                            st.rerun()
                except Exception as e:
                    st.session_state['siiu_candidatos'] = None
                    st.session_state['resultado_siiu'] = {"status": "error", "message": f"Ocorreu um erro na execução do robô: {e}"}
                    st.rerun()
                    
    # Se houver múltiplos candidatos pendentes de escolha
    if st.session_state.get('siiu_candidatos'):
        candidates = st.session_state['siiu_candidatos']
        st.write("---")
        st.warning(f"⚠️ Encontramos **{len(candidates)} registros** para a sua pesquisa. Escolha qual deseja extrair:")
        
        cand_options = {}
        for c in candidates:
            label = f"📌 {c['nome']} — {c['nivel']} em {c['curso']} (RA: {c['matricula']} | Situação: {c['situacao']} | Ingresso: {c['ingresso']})"
            cand_options[label] = c
            
        selected_label = st.radio("Selecione o vínculo do aluno:", list(cand_options.keys()))
        selected_cand = cand_options[selected_label]
        
        if st.button("Confirmar Seleção e Extrair Dados", type="primary"):
            with st.spinner(f"Extraindo dados do registro selecionado (RA {selected_cand['matricula']})..."):
                try:
                    import siiu_extractor
                    cached_driver, erro_login = init_cached_driver(login_siiu, senha_siiu)
                    res_ext = siiu_extractor.extract_candidate_details(login_siiu, senha_siiu, selected_cand, True, True, cached_driver=cached_driver)
                    if res_ext.get("status") == "error":
                        st.error(f"Erro na extração: {res_ext.get('message')}")
                    else:
                        st.success("Raspagem concluída com sucesso!")
                        st.session_state['resultado_siiu'] = res_ext
                        st.session_state['siiu_candidatos'] = None
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao extrair registro selecionado: {e}")
                    
    # Exibir os dados extraídos se existirem no session_state
    if st.session_state.get('resultado_siiu'):
        resultado = st.session_state['resultado_siiu']
        
        if resultado.get("status") == "error":
            st.error(f"❌ {resultado.get('message', 'Ocorreu um erro na busca do SIIU.')}")
        else:
            aluno_info = resultado.get('aluno_info') or resultado.get('details', {}).get('aluno_info') or {}
            
            if not aluno_info:
                st.warning("⚠️ Não foi possível carregar as informações do discente.")
            else:
                st.write("### Resultado da Extração Bruta:")
                st.info("Passe o mouse sobre a caixa de texto de cada informação abaixo e clique no ícone que aparecerá no canto superior direito para copiar!")
                
                st.write("#### 👤 Dados Pessoais")
                dp_col1, dp_col2, dp_col3 = st.columns(3)
                with dp_col1:
                    st.markdown("**Nome do aluno:**")
                    st.code(aluno_info.get('nome', ''), language="text")
                    st.markdown("**Nascimento:**")
                    st.code(aluno_info.get('nascimento', 'Pendente...'), language="text")
                with dp_col2:
                    st.markdown("**Sexo:**")
                    st.code(aluno_info.get('sexo', 'Pendente...'), language="text")
                    st.markdown("**Naturalidade:**")
                    st.code(aluno_info.get('naturalidade', 'Pendente...'), language="text")
                with dp_col3:
                    st.markdown("**CPF:**")
                    st.code(aluno_info.get('cpf', 'Pendente...'), language="text")
                    st.markdown("**RG/RNE:**")
                    st.code(aluno_info.get('rg', 'Pendente...'), language="text")

                st.write("#### 🎓 Dados Acadêmicos")
                da_col1, da_col2, da_col3 = st.columns(3)
                with da_col1:
                    st.markdown("**Matrícula:**")
                    st.code(aluno_info.get('ra', '') or aluno_info.get('matricula', ''), language="text")
                    st.markdown("**Início:**")
                    st.code(aluno_info.get('ingresso', ''), language="text")
                    st.markdown("**Forma de Ingresso:**")
                    st.code(aluno_info.get('forma_ingresso', 'Pendente...'), language="text")
                    
                with da_col2:
                    st.markdown("**Programa:**")
                    st.code(aluno_info.get('programa', '') or aluno_info.get('curso', ''), language="text")
                    st.markdown("**Término previsto:**")
                    st.code(aluno_info.get('termino_previsto', 'Pendente...'), language="text")
                    st.markdown("**Prorrogação:**")
                    st.code(aluno_info.get('prorrogacao', 'Pendente...'), language="text")
                    
                with da_col3:
                    st.markdown("**Nível:**")
                    st.code(aluno_info.get('nivel', ''), language="text")
                    st.markdown("**Situação:**")
                    st.code(aluno_info.get('situacao_siiu', '') or aluno_info.get('situacao', ''), language="text")
                    st.markdown("**Observações:**")
                    st.code(aluno_info.get('observacoes', ''), language="text")
                    
                st.write("#### 🏛️ Dados da Banca")
                db_col1, db_col2, db_col3 = st.columns(3)
                
                with db_col1:
                    st.markdown("**Título da Tese:**")
                    st.code(aluno_info.get('titulo_tese', 'Pendente...'), language="text")
                    st.markdown("**Situação:**")
                    st.code(aluno_info.get('situacao_tese', 'Pendente...'), language="text")
                    st.markdown("**1º Língua Estrangeira:**")
                    st.code(aluno_info.get('lingua_1', 'Pendente...'), language="text")
                    
                with db_col2:
                    st.markdown("**Ano:**")
                    st.code(aluno_info.get('ano_tese', 'Pendente...'), language="text")
                    st.markdown("**Orientador:**")
                    st.code(aluno_info.get('orientador', 'Pendente...'), language="text")
                    st.markdown("**Defesa:**")
                    st.code(aluno_info.get('defesa', 'Pendente...'), language="text")
                    st.markdown("**2º Língua Estrangeira:**")
                    st.code(aluno_info.get('lingua_2', 'Pendente...'), language="text")
                    
                with db_col3:
                    st.markdown("**Membros da Banca:**")
                    st.code(aluno_info.get('membros_banca', 'Pendente...'), language="text")
                    st.markdown("**Homologação do Título:**")
                    st.code(aluno_info.get('homologacao', 'Pendente...'), language="text")
                    
                st.write("#### 📚 Histórico de Unidades Curriculares:")
                list_hist = resultado.get("historico") or aluno_info.get("historico") or (resultado.get("details", {}).get("historico") if isinstance(resultado.get("details"), dict) else None)
                if list_hist:
                    df_hist = pd.DataFrame(list_hist)
                    st.dataframe(df_hist, width='stretch')
                else:
                    st.warning("Nenhum histórico de disciplinas encontrado.")
                    
                cr_col1, cr_col2 = st.columns(2)
                with cr_col1:
                    st.markdown("**Total de Créditos:**")
                    st.code(aluno_info.get('creditos_total', 'Pendente...'), language="text")
                with cr_col2:
                    st.markdown("**Créditos Necessários:**")
                    st.code(aluno_info.get('creditos_necessarios', 'Pendente...'), language="text")
            
                st.write("---")
                st.write("#### 🔍 Análise do Histórico")
                pendencias = []
                info = aluno_info
                
                # 1. Total de Créditos vs Créditos Necessários
                try:
                    total_cred = int(info.get('creditos_total', '0'))
                    nec_cred = int(info.get('creditos_necessarios', '0'))
                    if total_cred < nec_cred:
                        pendencias.append(f"O aluno possui créditos insuficientes. (Total: {total_cred}, Necessários: {nec_cred})")
                except:
                    pass
                    
                # 2. Homologação do Título pendente
                if "Pendente" in info.get('homologacao', 'Pendente'):
                    pendencias.append("Homologação de título pendente.")
                    
                # 3. Defesa pendente
                if "Pendente" in info.get('defesa', 'Pendente'):
                    pendencias.append("Defesa pendente.")
                    
                # 4. 1º Língua Estrangeira pendente
                if "Pendente" in info.get('lingua_1', 'Pendente'):
                    pendencias.append("1º Língua estrangeira pendente.")
                    
                # 5/6. 2º Língua Estrangeira no Doutorado
                if "DOUTORADO" in info.get('nivel', '').upper():
                    if "Pendente" in info.get('lingua_2', 'Pendente'):
                        pendencias.append("2º Língua estrangeira pendente.")
                        
                if pendencias:
                    for p in pendencias:
                        st.error(f"⚠️ {p}")
                else:
                    st.success("✅ Nenhuma pendência encontrada com base na análise automatizada.")
            
        # Sessão de Downloads
        pdf_h_path = resultado.get("pdf_historico")
        pdf_c_path = resultado.get("pdf_comprovante")
        
        has_h = pdf_h_path and os.path.exists(pdf_h_path) and os.path.getsize(pdf_h_path) > 100
        has_c = pdf_c_path and os.path.exists(pdf_c_path) and os.path.getsize(pdf_c_path) > 100

        if has_h or has_c:
            st.write("---")
            st.write("#### 📄 Documentos Gerados")
            d_col1, d_col2 = st.columns(2)
            
            if has_h:
                try:
                    with open(pdf_h_path, "rb") as f:
                        pdf_data = f.read()
                    with d_col1:
                        st.download_button(label="Baixar Histórico (PDF)", data=pdf_data, file_name=f"Histórico_{resultado['aluno_info'].get('nome', 'Aluno')}.pdf", mime="application/pdf", type="primary", key="btn_down_hist")
                except Exception as e:
                    st.error(f"Erro ao ler PDF do Histórico: {e}")
                    
            if has_c:
                try:
                    with open(pdf_c_path, "rb") as f:
                        pdf_data2 = f.read()
                    with d_col2:
                        st.download_button(label="Baixar Comprovante (PDF)", data=pdf_data2, file_name=f"Comprovante_{resultado['aluno_info'].get('nome', 'Aluno')}.pdf", mime="application/pdf", type="primary", key="btn_down_comp")
                except Exception as e:
                    st.error(f"Erro ao ler PDF do Comprovante: {e}")
        # Debug da Leitura do PDF em Tempo Real
        if resultado.get("debug_pdf"):
            dbg = resultado["debug_pdf"]
            with st.expander("🐞 Debug da Leitura de PDF (Acompanhamento em Tempo Real)", expanded=True):
                st.write(f"**Caminho do Arquivo:** `{dbg.get('pdf_path', 'N/A')}`")
                st.write(f"**Existe em Disco:** `{'Sim ✅' if dbg.get('exists') else 'Não ❌'}`")
                st.write(f"**Tamanho em Bytes:** `{dbg.get('size_bytes', 0)} bytes`")
                
                st.write("---")
                st.write("##### 🔍 Campos Extraídos do PDF pelo Robô:")
                st.json(dbg.get("parsed_fields", {}))
                
                st.write("---")
                st.write("##### 📄 Texto Bruto Lido do PDF pelo pdfplumber / pypdf:")
                r_txt = dbg.get("raw_text", "")
                if r_txt:
                    st.code(r_txt, language="text")
                else:
                    st.warning("⚠️ Nenhum texto pôde ser lido do PDF. O arquivo pode estar vazio ou ter sido salvo incorretamente.")

        with st.expander("🛠️ Debug Geral (Para enviar ao desenvolvedor)"):
            st.write("Se os dados acima estiverem incompletos, copie o texto abaixo e envie para o desenvolvedor analisar:")
            st.code(f"URL: {resultado.get('debug_url', 'N/A')}\n\nPAGE_TEXT:\n{resultado.get('debug_text', 'N/A')}", language="text")

def extract_transport_fields(row_padded, header):
    """Extrai todos os campos relevantes da linha da planilha usando busca flexível por palavras-chave."""
    import unicodedata
    def find_val(keywords, exclude=[]):
        for i, col in enumerate(header):
            c_low = str(col).lower().strip()
            c_norm = "".join(c for c in unicodedata.normalize('NFD', c_low) if unicodedata.category(c) != 'Mn')
            
            if any(ex in c_norm for ex in exclude):
                continue
            
            matched = False
            for kw in keywords:
                kw_norm = "".join(c for c in unicodedata.normalize('NFD', kw.lower()) if unicodedata.category(c) != 'Mn')
                if len(kw_norm) <= 3:
                    pattern = r'\b' + re.escape(kw_norm) + r'\b'
                    if re.search(pattern, c_norm):
                        matched = True
                        break
                else:
                    if kw_norm in c_norm:
                        matched = True
                        break
                        
            if matched and i < len(row_padded):
                v = str(row_padded[i]).strip()
                if v:
                    return v, str(col).strip(), i
        return "", "", None

    fields = {}
    
    # 1. Matrícula
    val, col, idx = find_val(["matrícula", "matricula", "ra"])
    fields['matricula'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 2. Nome
    val, col, idx = find_val(["nome"], exclude=["programa", "curso", "mãe", "mae", "pai"])
    fields['nome'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 3. CPF
    val, col, idx = find_val(["cpf"])
    fields['cpf'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 4. RG
    val, col, idx = find_val(["rg", "rne", "identificação", "identificacao", "documento"], exclude=["órgão", "orgao", "emissor", "estado", "emissão", "emissao", "tipo"])
    fields['rg'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 5. Órgão emissor
    val, col, idx = find_val(["órgão", "orgao", "emissor"])
    fields['orgao_emissor'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 6. Estado de emissão
    val, col, idx = find_val(["estado de emissão", "estado de emissao", "uf de emissão", "uf de emissao", "uf emissão", "uf emissao"], exclude=["residência", "residencia"])
    fields['uf_rg'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 7. Data de nascimento
    val, col, idx = find_val(["nascimento", "data de nascimento"])
    fields['nascimento'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 8. Término do Curso
    val, col, idx = find_val(["término do curso", "termino do curso", "término", "termino", "conclusão", "conclusao"], exclude=["cadastramento", "efetivação", "efetivacao", "sistema", "emtu"])
    fields['termino_curso'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 9. Telefones
    val, col, idx = find_val(["residencial", "fixo"])
    fields['tel_res'] = {"val": val, "col_name": col, "col_idx": idx}
    
    val, col, idx = find_val(["celular", "zap", "whatsapp"])
    fields['tel_cel'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 10. Email
    val, col, idx = find_val(["e-mail", "email"])
    fields['email'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 11. CEP
    val, col, idx = find_val(["cep"])
    fields['cep'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 12. Rua / Logradouro
    val, col, idx = find_val(["logradouro", "rua", "endereço", "endereco"])
    fields['rua'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 13. Número
    val, col, idx = find_val(["número", "numero", "nº", "n°"], exclude=["matricula", "rg", "cpf", "documento", "telefone", "celular"])
    fields['numero'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 14. Bairro
    val, col, idx = find_val(["bairro"])
    fields['bairro'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 15. Cidade
    val, col, idx = find_val(["cidade", "município", "municipio"])
    fields['cidade'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 16. Estado
    val, col, idx = find_val(["estado", "uf"], exclude=["emissão", "emissao", "rg"])
    fields['estado'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 17. Complemento
    val, col, idx = find_val(["complemento"])
    fields['complemento'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 18. Programa / PPG
    val, col, idx = find_val(["programa", "ppg", "curso"])
    fields['ppg'] = {"val": val, "col_name": col, "col_idx": idx}
    
    # 19. EMTU adicionais
    val, col, idx = find_val(["frequência", "frequencia"])
    fields['frequencia'] = {"val": val, "col_name": col, "col_idx": idx}
    
    val, col, idx = find_val(["período", "periodo", "turno"])
    fields['periodo'] = {"val": val, "col_name": col, "col_idx": idx}

    val, col, idx = find_val(["benefício", "beneficio", "tipo"])
    fields['beneficio'] = {"val": val, "col_name": col, "col_idx": idx}
    
    val, col, idx = find_val(["situação", "situacao"], exclude=["cadastral"])
    fields['situacao'] = {"val": val, "col_name": col, "col_idx": idx}

    val, col, idx = find_val(["situação cadastral", "situacao cadastral"])
    fields['sit_cadastral'] = {"val": val, "col_name": col, "col_idx": idx}

    val, col, idx = find_val(["carimbo", "data do cadastro", "data de cadastro"])
    fields['data_cadastro'] = {"val": val, "col_name": col, "col_idx": idx}

    return fields

def check_field_match(val_planilha, val_siiu, check_type="text"):
    """Compara dois valores e retorna se batem (True/False)."""
    if not val_planilha or not val_siiu:
        return False
    s1 = str(val_planilha).strip().upper()
    s2 = str(val_siiu).strip().upper()
    
    if s1 == s2:
        return True
        
    if check_type == "digits":
        d1 = re.sub(r"\D", "", s1)
        d2 = re.sub(r"\D", "", s2)
        return d1 == d2 and len(d1) > 0

    if check_type == "date":
        p1 = parse_date_br(s1)
        p2 = parse_date_br(s2)
        if p1 and p2:
            return p1 == p2

    if len(s1) > 3 and len(s2) > 3:
        if s1 in s2 or s2 in s1:
            return True
            
    return False

def show_demand_page(sheet_id, info):
    st.title(f"{info['tipo']}")
    
    col_t1, col_t2 = st.columns([8, 2])
    with col_t1:
        st.caption(f"Planilha: {info['name']}")
    with col_t2:
        # Botão direto para a planilha no Google
        st.link_button("🌐 Acessar Planilha", f"https://docs.google.com/spreadsheets/d/{sheet_id}", use_container_width=True)
            
    try:
        data = get_sheet_data(sheet_id, info['aba'])
    except Exception as e:
        st.error("Erro de Autenticação: O aplicativo precisa que você refaça o login no navegador para poder editar planilhas.")
        return
        
    if not data or len(data) < 2:
        st.info("Nenhuma solicitação encontrada nesta planilha ainda.")
        return
        
    header = data[0]
    rows = data[1:]
    
    st.divider()
    
    hoje = datetime.now().date()

    # Mapeamento prévio de linhas para relatórios, previsão e filtros simultâneos
    all_tipos_solicitacao = set()
    rows_parsed = []
    
    for reversed_idx, row in enumerate(reversed(rows)):
        idx_real = len(rows) - reversed_idx + 1
        row_padded = row + [''] * (len(header) - len(row))
        data_linha, val_data_comp = get_row_date(row_padded, header)
        rel_data = extract_relevant_data(row_padded, header)
        
        tipo_solic_val = ""
        for k, v in rel_data.items():
            if "tipo de solicitação" in k.lower() or "tipo de solicitacao" in k.lower():
                tipo_solic_val = str(v).strip()
                if tipo_solic_val:
                    all_tipos_solicitacao.add(tipo_solic_val)
                    
        data_exec_val = ""
        data_exec_parsed = None
        for k, v in rel_data.items():
            if "data para execução" in k.lower() or "data para execucao" in k.lower() or "prazo de execução" in k.lower():
                data_exec_val = str(v).strip()
                data_exec_parsed = parse_date_br(data_exec_val)
                
        rows_parsed.append({
            "idx_real": idx_real,
            "row_padded": row_padded,
            "data_linha": data_linha,
            "val_data_comp": val_data_comp,
            "rel_data": rel_data,
            "tipo_solic": tipo_solic_val,
            "data_exec_val": data_exec_val,
            "data_exec_parsed": data_exec_parsed
        })

    st.write("🔍 **Filtros Avançados de Busca e Período**")
    
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        filtro_selecao = st.selectbox(
            "1. Período de Solicitação:", 
            ["Todas as Atividades", "Últimos 7 dias", "Apenas Hoje", "Mês Atual", "Últimos 6 meses", "Escolher Período Customizado"]
        )
        
    tipos_opcoes = ["Todos os Tipos de Solicitação"] + sorted(list(all_tipos_solicitacao))
    with f_col2:
        filtro_tipo_solic = st.selectbox(
            "2. Tipo de Solicitação:",
            tipos_opcoes
        )
        
    with f_col3:
        filtro_execucao = st.selectbox(
            "3. Data para Execução / Urgência:",
            ["Todas as Datas de Execução", "🚨 Urgentes (Próximas de vencer / Vencidas <= 7 dias)", "⚠️ Médio Prazo (8 a 30 dias)", "Escolher Período de Execução"]
        )
        
    # Sub-filtros de data customizada se selecionados
    data_inicio_solic, data_fim_solic = None, None
    if filtro_selecao == "Apenas Hoje":
        data_inicio_solic, data_fim_solic = hoje, hoje
    elif filtro_selecao == "Últimos 7 dias":
        data_inicio_solic, data_fim_solic = hoje - timedelta(days=7), hoje
    elif filtro_selecao == "Mês Atual":
        data_inicio_solic, data_fim_solic = hoje.replace(day=1), hoje
    elif filtro_selecao == "Últimos 6 meses":
        data_inicio_solic, data_fim_solic = (hoje.replace(day=1) - timedelta(days=165)).replace(day=1), hoje
    elif filtro_selecao == "Escolher Período Customizado":
        cf_c1, cf_c2 = st.columns(2)
        with cf_c1:
            data_inicio_solic = st.date_input("Início da Solicitação:", value=hoje - timedelta(days=30))
        with cf_c2:
            data_fim_solic = st.date_input("Fim da Solicitação:", value=hoje)

    data_inicio_exec, data_fim_exec = None, None
    if filtro_execucao == "Escolher Período de Execução":
        fe_c1, fe_c2 = st.columns(2)
        with fe_c1:
            data_inicio_exec = st.date_input("Início da Execução:", value=hoje)
        with fe_c2:
            data_fim_exec = st.date_input("Fim da Execução:", value=hoje + timedelta(days=30))

    # Filtragem Simultânea das Demandas
    filtered_items = []
    for item in rows_parsed:
        # A. Filtro por Período de Solicitação
        if filtro_selecao != "Todas as Atividades":
            d_l = item["data_linha"]
            if d_l and data_inicio_solic and data_fim_solic:
                d_cmp = d_l.date() if isinstance(d_l, datetime) else d_l
                if not (data_inicio_solic <= d_cmp <= data_fim_solic):
                    continue
            elif not d_l:
                continue

        # B. Filtro por Tipo de Solicitação
        if filtro_tipo_solic != "Todos os Tipos de Solicitação":
            if item["tipo_solic"].strip().lower() != filtro_tipo_solic.strip().lower():
                continue

        # C. Filtro por Data para Execução / Urgência
        d_ex = item["data_exec_parsed"]
        if filtro_execucao == "🚨 Urgentes (Próximas de vencer / Vencidas <= 7 dias)":
            if not d_ex:
                continue
            dias_r = (d_ex - hoje).days
            if dias_r > 7:
                continue
        elif filtro_execucao == "⚠️ Médio Prazo (8 a 30 dias)":
            if not d_ex:
                continue
            dias_r = (d_ex - hoje).days
            if not (8 <= dias_r <= 30):
                continue
        elif filtro_execucao == "Escolher Período de Execução":
            if d_ex and data_inicio_exec and data_fim_exec:
                if not (data_inicio_exec <= d_ex <= data_fim_exec):
                    continue
            elif not d_ex:
                continue

        filtered_items.append(item)

    # Painel de Relatório Completo & Previsão de Demandas
    with st.expander("📊 Relatório Completo & Previsão de Demandas (Clique para expandir)", expanded=False):
        st.write("### 📈 Painel Executivo e Previsão de Demandas")
        st.caption("Gere um relatório abrangente contendo todas as informações da planilha no período e tipo selecionados.")
        
        col_rep1, col_rep2, col_rep3 = st.columns(3)
        with col_rep1:
            st.metric("Total de Demandas Filtradas", f"{len(filtered_items)} registro(s)")
            
        urgentes_count = sum(1 for it in filtered_items if it["data_exec_parsed"] and (it["data_exec_parsed"] - hoje).days <= 7)
        with col_rep2:
            st.metric("Demandas Urgentes (<= 7 dias)", f"{urgentes_count} demanda(s)")
            
        medio_count = sum(1 for it in filtered_items if it["data_exec_parsed"] and 8 <= (it["data_exec_parsed"] - hoje).days <= 30)
        with col_rep3:
            st.metric("Demandas Médio Prazo (8-30 dias)", f"{medio_count} demanda(s)")

        st.divider()
        st.write("#### 📥 Exportar Relatório Completo (Contendo 100% das Informações da Planilha)")
        
        if filtered_items:
            report_data = []
            for it in filtered_items:
                r_dict = {}
                row_p = it["row_padded"]
                for idx_c, col_name in enumerate(header):
                    r_dict[str(col_name).strip()] = row_p[idx_c] if idx_c < len(row_p) else ""
                
                d_ex = it["data_exec_parsed"]
                if d_ex:
                    dias_r = (d_ex - hoje).days
                    r_dict["[Previsão] Dias para Execução"] = dias_r
                    r_dict["[Previsão] Nível de Urgência"] = "CRÍTICO (Vencida/Urgente)" if dias_r <= 7 else ("MÉDIO" if dias_r <= 30 else "REGULAR")
                else:
                    r_dict["[Previsão] Dias para Execução"] = "N/A"
                    r_dict["[Previsão] Nível de Urgência"] = "Não informada"
                    
                report_data.append(r_dict)
                
            df_report = pd.DataFrame(report_data)
            csv_bytes = df_report.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            
            st.dataframe(df_report, use_container_width=True, height=250)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.download_button(
                    label="📥 Baixar Relatório Completo (CSV / Excel)",
                    data=csv_bytes,
                    file_name=f"Relatorio_Demandas_{info['tipo'].replace(' ', '_')}_{hoje.strftime('%d_%m_%Y')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_dl_report_{sheet_id}"
                )
                
            with b_col2:
                import base64
                html_print = generate_printable_report_html(df_report, info['tipo'])
                b64_print = base64.b64encode(html_print.encode('utf-8')).decode('utf-8')
                data_url_print = f"data:text/html;base64,{b64_print}"
                
                st.markdown(
                    f"""
                    <a href="{data_url_print}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: #174C33; 
                            color: #ffffff; 
                            border: 1px solid #174C33; 
                            padding: 9px 16px; 
                            border-radius: 6px; 
                            font-weight: 600; 
                            font-family: 'Merriweather', serif; 
                            cursor: pointer; 
                            width: 100%;
                            transition: all 0.2s ease-in-out;
                        " onmouseover="this.style.backgroundColor='#82bf24'; this.style.borderColor='#82bf24';" onmouseout="this.style.backgroundColor='#174C33'; this.style.borderColor='#174C33';">
                            🖨️ Imprimir Relatório
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("Nenhuma demanda encontrada com a combinação atual de filtros.")

    st.divider()

    count = 0
    # Processar de trás pra frente as demandas filtradas
    for item in filtered_items:
        idx_real_na_planilha = item["idx_real"]
        row_padded = item["row_padded"]
        valor_data_completo = item["val_data_comp"]
        count += 1
        nome_col = next((c for c in header if "nome" in str(c).lower() and "programa" not in str(c).lower()), None)
        nome_val = row_padded[header.index(nome_col)] if nome_col else f"Solicitante (Linha {idx_real_na_planilha})"
        if not str(nome_val).strip():
            nome_val = f"Solicitante da Linha {idx_real_na_planilha}"
            
        with st.expander(f"👤 **{nome_val}** - 🕒 Solicitado em: {valor_data_completo}"):
            relevant_data = extract_relevant_data(row_padded, header)
            card_items = sort_and_format_card_data(relevant_data)
            
            if not card_items:
                st.warning("Não encontrei campos padrão nesta planilha.")
            else:
                num_colunas = 3
                
                for i in range(0, len(card_items), num_colunas):
                    cols = st.columns(num_colunas)
                    for j in range(num_colunas):
                        if i + j < len(card_items):
                            item = card_items[i+j]
                            disp_label = item["display_label"]
                            orig_key = item["original_key"]
                            val = item["val"]
                            
                            if val and str(val).strip():
                                with cols[j]:
                                    st.markdown(f'<div class="info-title">{disp_label}</div>', unsafe_allow_html=True)
                                    
                                    inner_c1, inner_c2 = st.columns([4, 1])
                                    with inner_c1:
                                        st.code(val, language="text")
                                    with inner_c2:
                                        with st.popover("✏️"):
                                            st.write(f"Editar **{disp_label}**")
                                            novo_valor = st.text_input("Novo valor:", value=str(val), key=f"inp_{idx_real_na_planilha}_{orig_key}")
                                            if st.button("Salvar na Planilha", key=f"btn_{idx_real_na_planilha}_{orig_key}"):
                                                try:
                                                    coluna_index = header.index(orig_key)
                                                    update_sheet_cell(sheet_id, info['aba'], idx_real_na_planilha, coluna_index, novo_valor)
                                                    st.success("Salvo com sucesso! A página irá recarregar.")
                                                    st.rerun()
                                                except Exception as err:
                                                    st.error(f"Erro ao salvar: {err}")

            # ASSISTENTE DE BILHETE DE TRANSPORTE (EMTU / SPTRANS)
            tipo_str = (str(info.get('tipo', '')) + " " + str(info.get('name', ''))).upper()
            is_sptrans = "SPTRANS" in tipo_str
            is_emtu = "EMTU" in tipo_str
            is_transporte = is_sptrans or is_emtu

            if is_transporte:
                modulo_nome = "SPTrans" if is_sptrans else "EMTU"
                st.divider()
                st.markdown(f"### 🚌 Assistente de Conferência e Cadastro — **{modulo_nome}**")
                
                tf = extract_transport_fields(row_padded, header)
                
                # Tenta obter credenciais da sessão ou de secrets/ambiente com segurança
                login_siiu = st.session_state.get('login_siiu', '') or get_secret('login_siiu', '')
                senha_siiu = st.session_state.get('senha_siiu', '') or get_secret('senha_siiu', '')

                if not login_siiu or not senha_siiu:
                    st.info("🔑 **Informe suas credenciais do SIIU (usadas apenas temporariamente na memória desta sessão):**")
                    with st.form(f"form_cred_trans_{idx_real_na_planilha}"):
                        col_cr1, col_cr2 = st.columns(2)
                        with col_cr1:
                            u_input = st.text_input("Usuário SIIU:", value=login_siiu)
                        with col_cr2:
                            p_input = st.text_input("Senha SIIU:", value=senha_siiu, type="password")
                            
                        if st.form_submit_button("Usar nesta Sessão"):
                            if u_input and p_input:
                                st.session_state['login_siiu'] = u_input
                                st.session_state['senha_siiu'] = p_input
                                st.success("Credenciais mantidas temporariamente na memória da sessão!")
                                st.rerun()
                            else:
                                st.error("Preencha usuário e senha.")
                
                # Botão para disparar conferência no SIIU
                key_check_btn = f"btn_chk_{idx_real_na_planilha}"
                state_key_res = f"siiu_res_{idx_real_na_planilha}"
                
                col_ac1, col_ac2 = st.columns([3, 2])
                with col_ac1:
                    if st.button(f"🔍 Conferir com SIIU & Gerar Sequência ({modulo_nome})", key=key_check_btn, type="primary"):
                        # Prioridade de busca: 1º Matrícula (RA), 2º CPF, 3º Nome
                        nome_busca = tf['matricula']['val'] or tf['cpf']['val'] or tf['nome']['val']
                        nome_fallback = tf['nome']['val'] if (tf['nome']['val'] and nome_busca != tf['nome']['val']) else ""
                        ppg_busca = tf['ppg']['val'] or "Todos os Programas"
                        
                        if not login_siiu or not senha_siiu:
                            st.error("Por favor, preencha suas credenciais do SIIU acima antes de conferir.")
                        elif not nome_busca:
                            st.error("Não foi possível identificar o Nome, CPF ou Matrícula do aluno nesta linha da planilha.")
                        else:
                            with st.spinner(f"Conferindo histórico de '{nome_busca}' no SIIU..."):
                                try:
                                    import siiu_extractor
                                    cached_driver, err_drv = init_cached_driver(login_siiu, senha_siiu)
                                    if err_drv or not cached_driver:
                                        st.error(f"Erro de autenticação no SIIU: {err_drv}")
                                    else:
                                        s_res = siiu_extractor.search_and_extract_student(
                                            login_siiu, senha_siiu, 
                                            nome_busca, ppg_busca, 
                                            cached_driver=cached_driver,
                                            fallback_name=nome_fallback
                                        )
                                        if s_res.get("status") == "error":
                                            st.session_state[state_key_res] = s_res
                                            st.session_state[f"cands_{idx_real_na_planilha}"] = None
                                            st.rerun()
                                        elif s_res.get("single"):
                                            st.session_state[state_key_res] = s_res.get("details")
                                            st.session_state[f"cands_{idx_real_na_planilha}"] = None
                                            st.rerun()
                                        else:
                                            st.session_state[f"cands_{idx_real_na_planilha}"] = s_res.get("candidates", [])
                                            st.session_state[state_key_res] = None
                                            st.rerun()
                                except Exception as ex_siiu:
                                    st.error(f"Erro na conferência do SIIU: {ex_siiu}")

                # Se houver múltiplos candidatos pendentes
                if st.session_state.get(f"cands_{idx_real_na_planilha}"):
                    cands = st.session_state[f"cands_{idx_real_na_planilha}"]
                    st.warning(f"⚠️ Encontramos **{len(cands)} registros** no SIIU. Selecione o vínculo desejado:")
                    c_opts = {f"📌 {c['nome']} — {c['nivel']} em {c['curso']} (RA: {c['matricula']} | Situação: {c['situacao']} | Ingresso: {c['ingresso']})": c for c in cands}
                    selected_c_lbl = st.radio("Vínculo:", list(c_opts.keys()), key=f"rad_cand_{idx_real_na_planilha}")
                    selected_c_obj = c_opts[selected_c_lbl]
                    
                    if st.button("Confirmar Vínculo para Conferência", key=f"btn_conf_c_{idx_real_na_planilha}", type="primary"):
                        with st.spinner("Extraindo dados do vínculo selecionado..."):
                            try:
                                import siiu_extractor
                                cached_driver, err_drv = init_cached_driver(login_siiu, senha_siiu)
                                ext_res = siiu_extractor.extract_candidate_details(login_siiu, senha_siiu, selected_c_obj, True, True, cached_driver=cached_driver)
                                st.session_state[state_key_res] = ext_res
                                st.session_state[f"cands_{idx_real_na_planilha}"] = None
                                st.rerun()
                            except Exception as ex_conf:
                                st.error(f"Erro ao extrair vínculo: {ex_conf}")

                # Exibir resultado da conferência
                res_siiu = st.session_state.get(state_key_res)
                if res_siiu:
                    if res_siiu.get("status") == "error":
                        st.error(f"❌ {res_siiu.get('message')}")
                    elif res_siiu.get("status") == "success":
                        ainfo = res_siiu.get("aluno_info", {})
                        st.markdown("#### 📊 Resultado da Conferência (Planilha vs. SIIU)")
                    
                        # Definição dos campos a conferir conforme solicitação do usuário
                        if is_sptrans:
                            check_specs = [
                                ("MATRÍCULA", tf['matricula']['val'], ainfo.get('ra', '') or ainfo.get('matricula', ''), "digits", tf['matricula']['col_name'], tf['matricula']['col_idx']),
                                ("TÉRMINO DO CURSO", tf['termino_curso']['val'], ainfo.get('termino_previsto', ''), "date", tf['termino_curso']['col_name'], tf['termino_curso']['col_idx']),
                                ("Nome completo", tf['nome']['val'], ainfo.get('nome', ''), "text", tf['nome']['col_name'], tf['nome']['col_idx']),
                                ("RG / Documento", tf['rg']['val'], ainfo.get('rg', ''), "text", tf['rg']['col_name'], tf['rg']['col_idx']),
                                ("Órgão emissor RG", tf['orgao_emissor']['val'], ainfo.get('rg', ''), "text", tf['orgao_emissor']['col_name'], tf['orgao_emissor']['col_idx']),
                                ("Estado de emissão RG", tf['uf_rg']['val'], ainfo.get('rg', ''), "text", tf['uf_rg']['col_name'], tf['uf_rg']['col_idx']),
                                ("CPF", tf['cpf']['val'], ainfo.get('cpf', ''), "digits", tf['cpf']['col_name'], tf['cpf']['col_idx']),
                                ("Data de nascimento", tf['nascimento']['val'], ainfo.get('nascimento', ''), "date", tf['nascimento']['col_name'], tf['nascimento']['col_idx']),
                            ]
                        else: # EMTU
                            check_specs = [
                                ("NÚMERO DE MATRÍCULA", tf['matricula']['val'], ainfo.get('ra', '') or ainfo.get('matricula', ''), "digits", tf['matricula']['col_name'], tf['matricula']['col_idx']),
                                ("Nome completo", tf['nome']['val'], ainfo.get('nome', ''), "text", tf['nome']['col_name'], tf['nome']['col_idx']),
                                ("CPF", tf['cpf']['val'], ainfo.get('cpf', ''), "digits", tf['cpf']['col_name'], tf['cpf']['col_idx']),
                                ("RG ou RNE", tf['rg']['val'], ainfo.get('rg', ''), "text", tf['rg']['col_name'], tf['rg']['col_idx']),
                                ("Término do Curso", tf['termino_curso']['val'], ainfo.get('termino_previsto', ''), "date", tf['termino_curso']['col_name'], tf['termino_curso']['col_idx']),
                            ]
                            
                        # Tabela de Conferência
                        for label_campo, val_plan, val_siiu, ctype, col_n, col_i in check_specs:
                            is_ok = check_field_match(val_plan, val_siiu, check_type=ctype)
                            status_str = "✅ Batendo" if is_ok else "⚠️ Divergência"
                            color_bg = "#e6f4ea" if is_ok else "#fef7e0"
                            
                            st.markdown(f"""
                            <div style="background-color: {color_bg}; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 4px solid {'#34a853' if is_ok else '#fbbc04'};">
                                <strong>{status_str} — {label_campo}:</strong><br/>
                                📄 Planilha: <code>{val_plan or 'Vazio'}</code> | 🏛️ SIIU: <code>{val_siiu or 'Não informado'}</code>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if not is_ok and val_siiu:
                                if col_i is None and col_n:
                                    for idx_h, col_h in enumerate(header):
                                        if str(col_h).strip().lower() == str(col_n).strip().lower():
                                            col_i = idx_h
                                            break
                                if col_i is None and ("término" in label_campo.lower() or "termino" in label_campo.lower()):
                                    for idx_h, col_h in enumerate(header):
                                        ch_low = str(col_h).lower()
                                        if ("término" in ch_low or "termino" in ch_low or "conclusã" in ch_low) and "cadastramento" not in ch_low:
                                            col_i = idx_h
                                            break

                                if col_i is not None:
                                    btn_fix_k = f"btn_fix_{idx_real_na_planilha}_{col_i}"
                                    if st.button(f"✏️ Atualizar Planilha com '{val_siiu}'", key=btn_fix_k):
                                        try:
                                            update_sheet_cell(sheet_id, info['aba'], idx_real_na_planilha, col_i, val_siiu)
                                            st.success("Planilha atualizada com sucesso! Recarregando...")
                                            st.rerun()
                                        except Exception as e_upd:
                                            st.error(f"Erro ao atualizar planilha: {e_upd}")
                                        
                        st.divider()
                        st.markdown(f"### 📋 Sequência de Cópia para Cadastro no Portal **{modulo_nome}**")
                        st.info("Passe o mouse sobre os blocos abaixo para copiar os dados na ordem exata de preenchimento do portal!")
                        
                        if is_sptrans:
                            seq_sptrans = [
                                ("1. Matrícula", tf['matricula']['val'] or ainfo.get('ra', '')),
                                ("2. RG", tf['rg']['val'] or ainfo.get('rg', '')),
                                ("3. CPF", tf['cpf']['val'] or ainfo.get('cpf', '')),
                                ("4. Data de Nascimento", tf['nascimento']['val'] or ainfo.get('nascimento', '')),
                                ("5. Telefone Residencial", tf['tel_res']['val']),
                                ("6. Telefone Celular", tf['tel_cel']['val']),
                                ("7. Endereço de E-mail", tf['email']['val']),
                                ("8. CEP", tf['cep']['val']),
                                ("9. RUA (Logradouro)", tf['rua']['val']),
                                ("10. Número", tf['numero']['val']),
                                ("11. Bairro", tf['bairro']['val']),
                                ("12. Cidade", tf['cidade']['val']),
                                ("13. Estado", tf['estado']['val']),
                                ("14. Complemento", tf['complemento']['val']),
                            ]
                            
                            seq_cols = st.columns(2)
                            for idx_seq, (l_seq, v_seq) in enumerate(seq_sptrans):
                                with seq_cols[idx_seq % 2]:
                                    st.markdown(f"**{l_seq}:**")
                                    st.code(v_seq or "Não informado", language="text")
                                    
                        else: # EMTU
                            seq_emtu = [
                                ("1. CPF", tf['cpf']['val'] or ainfo.get('cpf', '')),
                                ("2. Nome Completo", tf['nome']['val'] or ainfo.get('nome', '')),
                                ("3. RG", tf['rg']['val'] or ainfo.get('rg', '')),
                                ("4. CEP", tf['cep']['val']),
                                ("5. Programa de Pós-Graduação", tf['ppg']['val'] or ainfo.get('programa', '')),
                                ("6. Frequência", tf['frequencia']['val']),
                                ("7. Período do curso", tf['periodo']['val']),
                                ("8. Término do curso", tf['termino_curso']['val'] or ainfo.get('termino_previsto', '')),
                            ]
                            
                            seq_cols = st.columns(2)
                            for idx_seq, (l_seq, v_seq) in enumerate(seq_emtu):
                                with seq_cols[idx_seq % 2]:
                                    st.markdown(f"**{l_seq}:**")
                                    st.code(v_seq or "Não informado", language="text")

                            st.write("---")
                            st.markdown("#### 📌 Outros Campos Complementares (EMTU)")
                            comp_emtu = [
                                ("SITUAÇÃO", tf['situacao']['val']),
                                ("Tipo de benefício", tf['beneficio']['val']),
                                ("RUA", tf['rua']['val']),
                                ("Número", tf['numero']['val']),
                                ("Bairro", tf['bairro']['val']),
                                ("Cidade", tf['cidade']['val']),
                                ("Estado", tf['estado']['val']),
                                ("Complemento", tf['complemento']['val']),
                                ("Endereço de e-mail", tf['email']['val']),
                                ("Situação cadastral", tf['sit_cadastral']['val']),
                                ("Data do Cadastro", tf['data_cadastro']['val']),
                            ]
                            c_cols = st.columns(3)
                            for idx_comp, (lc, vc) in enumerate(comp_emtu):
                                with c_cols[idx_comp % 3]:
                                    st.markdown(f"**{lc}:**")
                                    st.code(vc or "Não informado", language="text")

    if count == 0:
        st.info("Nenhuma atividade encontrada para o filtro selecionado.")

if __name__ == "__main__":
    main()
