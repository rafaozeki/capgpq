import streamlit as st
import json
import os
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from google_api import get_sheets, get_sheet_data, update_sheet_cell

CONFIG_FILE = 'config.json'

KEYWORDS = [
    "nome", "matrícula", "documento de identificação", "órgão emissor", 
    "estado de emissão", "data de emissão", "data de nascimento", "telefone", "celular", 
    "e-mail", "cep", "logradouro", "número", "bairro", "cidade", "estado", 
    "complemento", "programa de pós", "rg", "rne", "tipo de benefício", "rua", 
    "situação", "prazo", "nível", "ano de ingresso", "processo sei", "naturalidade", 
    "homologação", "observações", "pendências", "orcid", "secretário", "lattes"
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
</style>
"""

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extract_relevant_data(row_data, header):
    extracted = {}
    for col_name, value in zip(header, row_data):
        col_lower = str(col_name).lower()
        if any(kw in col_lower for kw in KEYWORDS):
            extracted[col_name] = value
    return extracted

def parse_date_br(date_str):
    try:
        date_part = str(date_str).strip().split(" ")[0]
        return datetime.strptime(date_part, "%d/%m/%Y").date()
    except:
        return None

def check_password():
    """Retorna True se o usuário digitou a senha correta."""
    if st.session_state.get("password_correct"):
        return True

    st.markdown("<h2 style='text-align: center; color: #174C33;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
    
    try:
        senha_correta = st.secrets.get("app_password", "unifesp2026")
    except Exception:
        senha_correta = "unifesp2026"
        
    with st.form("login_form"):
        senha_digitada = st.text_input("Digite a senha para acessar o Automador CaPGPq-EFLCH:", type="password")
        submit_btn = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        
    if submit_btn or senha_digitada:
        if senha_digitada == senha_correta:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Senha incorreta. Tente novamente.")
            
    return False

def main():
    st.set_page_config(page_title="Automador CaPGPq-EFLCH", page_icon="🎓", layout="wide")
    
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
            <p style="color: #615c5c; font-size: 0.95rem; margin-top: -10px;">Automador CaPGPq-EFLCH</p>
        </div>
        """, unsafe_allow_html=True
    )
    
    # Adicionando Painel de Controle e Links Úteis
    st.sidebar.markdown("**Painel de Controle:**")
    panel_btn_type = "primary" if st.session_state.current_page == "Estatísticas" else "secondary"
    if st.sidebar.button("📊 Estatísticas", type=panel_btn_type, use_container_width=True):
        st.session_state.current_page = "Estatísticas"
        st.rerun()
        
    links_btn_type = "primary" if st.session_state.current_page == "🔗 Links Úteis" else "secondary"
    if st.sidebar.button("🔗 Links Úteis", type=links_btn_type, use_container_width=True):
        st.session_state.current_page = "🔗 Links Úteis"
        st.rerun()
        
    polare_btn_type = "primary" if st.session_state.current_page == "📝 Polare" else "secondary"
    if st.sidebar.button("📝 Polare", type=polare_btn_type, use_container_width=True):
        st.session_state.current_page = "📝 Polare"
        st.rerun()
        
    academic_btn_type = "primary" if st.session_state.current_page == "🎓 Análise de Históricos" else "secondary"
    if st.sidebar.button("🎓 Análise de Históricos", type=academic_btn_type, use_container_width=True):
        st.session_state.current_page = "🎓 Análise de Históricos"
        st.rerun()
        
    st.sidebar.divider()
    
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
            st.rerun()
            
    st.sidebar.divider()
    
    config_btn_type = "primary" if st.session_state.current_page == "⚙️ Configurações" else "secondary"
    if st.sidebar.button("⚙️ Configurações", type=config_btn_type, use_container_width=True):
        st.session_state.current_page = "⚙️ Configurações"
        st.rerun()
    
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
        data_inicio = hoje - timedelta(days=180)
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
    
    try:
        for sheet_id, info in config.items():
            tipo = info['tipo']
            atividades_por_tipo[tipo] = 0
            
            data = get_sheet_data(sheet_id, info['aba'])
            if data and len(data) > 1:
                header = data[0]
                rows = data[1:]
                
                # Identificar coluna de data
                data_col_index = None
                for i, col in enumerate(header):
                    if "carimbo" in str(col).lower() or str(col).strip().lower() == "data":
                        data_col_index = i
                        break
                
                # Procurar pela coluna de PPG
                ppg_col_index = None
                for i, col in enumerate(header):
                    if "programa" in str(col).lower() or "ppg" in str(col).lower():
                        ppg_col_index = i
                        break
                        
                for row in rows:
                    row_padded = row + [''] * (len(header) - len(row))
                    
                    # Filtrar por data
                    valor_data_completo = row_padded[data_col_index] if data_col_index is not None else ""
                    data_da_linha = parse_date_br(valor_data_completo)
                    
                    if filtro_selecao != "Desde o Início (Geral)":
                        if data_da_linha and data_inicio and data_fim:
                            if not (data_inicio <= data_da_linha <= data_fim):
                                continue # Fora do filtro
                        elif not data_da_linha:
                            # Se não encontrou data e não é filtro geral, esconde.
                            continue
                            
                    total_atividades += 1
                    atividades_por_tipo[tipo] += 1
                    
                    if ppg_col_index is not None and len(row) > ppg_col_index:
                        valor_ppg = str(row_padded[ppg_col_index]).strip()
                        encontrou = False
                        for ppg_oficial in PPGS_OFICIAIS:
                            # Se encontrar o nome do PPG oficial na string preenchida
                            if ppg_oficial.lower() in valor_ppg.lower():
                                atividades_por_ppg[ppg_oficial] += 1
                                encontrou = True
                                break
                        if not encontrou:
                            atividades_por_ppg["Não Identificado"] += 1
                    else:
                        atividades_por_ppg["Não Identificado"] += 1
                
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
            
            # Montagem do HTML para o Relatório
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
            
    except Exception as e:
        st.error(f"Não foi possível carregar os dados. Verifique a autenticação ou sua conexão. Detalhes: {e}")


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
    st.info("Suas credenciais não serão salvas. Elas são usadas apenas temporariamente para o robô acessar o sistema em seu nome.")
    
    c1, c2 = st.columns(2)
    with c1:
        login_siiu = st.text_input("Usuário:")
    with c2:
        senha_siiu = st.text_input("Senha:", type="password")
        
    if st.button("Efetuar Login"):
        if login_siiu and senha_siiu:
            st.session_state['siiu_logged_in'] = True
            st.success("✅ Credenciais informadas com sucesso! Você já pode realizar a busca.")
        else:
            st.warning("⚠️ Preencha usuário e senha para efetuar login.")
        
    st.divider()
    st.subheader("2. Busca de Aluno")
    
    col_busca1, col_busca2 = st.columns(2)
    with col_busca1:
        termo_busca = st.text_input("Nome, CPF ou RA do aluno:")
    with col_busca2:
        # Puxamos os programas dinamicamente se quisermos, ou deixamos estático por enquanto
        programa = st.selectbox(
            "Programa de Pós-Graduação (Obrigatório no SIIU):", 
            [
                "Todos os Programas", 
                "CIÊNCIAS SOCIAIS", 
                "EDUCAÇÃO", 
                "EDUCAÇÃO E SAÚDE NA INFÂNCIA E NA ADOLESCÊNCIA", 
                "ENSINO DE HISTÓRIA", 
                "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS", 
                "FILOSOFIA", 
                "HISTÓRIA", 
                "HISTÓRIA DA ARTE", 
                "LETRAS", 
                "Pós-Doutorado"
            ]
        )
        
    st.write("---")
    
    @st.cache_resource(show_spinner="Autenticando no SIIU (apenas 1 vez por servidor)...")
    def init_cached_driver(login, senha):
        import siiu_extractor
        driver, erro = siiu_extractor.init_cached_driver(login, senha)
        return driver, erro

    if st.button("Pesquisar e Extrair Dados do SIIU", type="primary"):
        if not login_siiu or not senha_siiu:
            st.error("Por favor, insira suas credenciais do SIIU para permitir o acesso do robô.")
        elif not termo_busca:
            st.error("Por favor, digite o Nome, CPF ou RA do aluno.")
        else:
            with st.spinner("Iniciando robô (Selenium)... Isso pode levar alguns segundos..."):
                try:
                    import siiu_extractor
                    cached_driver, erro_login = init_cached_driver(login_siiu, senha_siiu)
                    
                    if erro_login or not cached_driver:
                        resultado = {"status": "error", "message": erro_login or "Falha crítica na sessão"}
                        init_cached_driver.clear()
                    else:
                        resultado = siiu_extractor.extract_student_data(login_siiu, senha_siiu, termo_busca, programa, True, True, cached_driver=cached_driver)
                    
                    if resultado.get("status") == "error":
                        st.error(f"O robô encontrou um problema: {resultado.get('message')}")
                        st.session_state['resultado_siiu'] = None
                    else:
                        st.success("Raspagem concluída!")
                        st.session_state['resultado_siiu'] = resultado
                        
                except Exception as e:
                    st.error(f"Ocorreu um erro durante a execução do robô: {e}")
                    st.session_state['resultado_siiu'] = None
                    
    # Exibir os dados extraídos se existirem no session_state
    if st.session_state.get('resultado_siiu'):
        resultado = st.session_state['resultado_siiu']
        
        # Exibir os dados extraídos
        st.write("### Resultado da Extração Bruta:")
        st.info("Passe o mouse sobre a caixa de texto de cada informação abaixo e clique no ícone que aparecerá no canto superior direito para copiar!")
        
        st.write("#### 👤 Dados Pessoais")
        dp_col1, dp_col2, dp_col3 = st.columns(3)
        with dp_col1:
            st.markdown("**Nome do aluno:**")
            st.code(resultado['aluno_info'].get('nome', ''), language="text")
            st.markdown("**Nascimento:**")
            st.code(resultado['aluno_info'].get('nascimento', 'Pendente...'), language="text")
        with dp_col2:
            st.markdown("**Sexo:**")
            st.code(resultado['aluno_info'].get('sexo', 'Pendente...'), language="text")
            st.markdown("**Naturalidade:**")
            st.code(resultado['aluno_info'].get('naturalidade', 'Pendente...'), language="text")
        with dp_col3:
            st.markdown("**CPF:**")
            st.code(resultado['aluno_info'].get('cpf', 'Pendente...'), language="text")
            st.markdown("**RG/RNE:**")
            st.code(resultado['aluno_info'].get('rg', 'Pendente...'), language="text")

        st.write("#### 🎓 Dados Acadêmicos")
        da_col1, da_col2, da_col3 = st.columns(3)
        with da_col1:
            st.markdown("**Matrícula:**")
            st.code(resultado['aluno_info'].get('ra', ''), language="text")
            st.markdown("**Início:**")
            st.code(resultado['aluno_info'].get('ingresso', ''), language="text")
            st.markdown("**Forma de Ingresso:**")
            st.code(resultado['aluno_info'].get('forma_ingresso', 'Pendente...'), language="text")
            
        with da_col2:
            st.markdown("**Programa:**")
            st.code(resultado['aluno_info'].get('programa', ''), language="text")
            st.markdown("**Término previsto:**")
            st.code(resultado['aluno_info'].get('termino_previsto', 'Pendente...'), language="text")
            st.markdown("**Prorrogação:**")
            st.code(resultado['aluno_info'].get('prorrogacao', 'Pendente...'), language="text")
            
        with da_col3:
            st.markdown("**Nível:**")
            st.code(resultado['aluno_info'].get('nivel', ''), language="text")
            st.markdown("**Situação:**")
            st.code(resultado['aluno_info'].get('situacao_siiu', ''), language="text")
            st.markdown("**Observações:**")
            st.code(resultado['aluno_info'].get('observacoes', ''), language="text")
            
        st.write("#### 🏛️ Dados da Banca")
        db_col1, db_col2, db_col3 = st.columns(3)
        
        with db_col1:
            st.markdown("**Título da Tese:**")
            st.code(resultado['aluno_info'].get('titulo_tese', 'Pendente...'), language="text")
            st.markdown("**Situação:**")
            st.code(resultado['aluno_info'].get('situacao_tese', 'Pendente...'), language="text")
            st.markdown("**1º Língua Estrangeira:**")
            st.code(resultado['aluno_info'].get('lingua_1', 'Pendente...'), language="text")
            
        with db_col2:
            st.markdown("**Ano:**")
            st.code(resultado['aluno_info'].get('ano_tese', 'Pendente...'), language="text")
            st.markdown("**Orientador:**")
            st.code(resultado['aluno_info'].get('orientador', 'Pendente...'), language="text")
            st.markdown("**Defesa:**")
            st.code(resultado['aluno_info'].get('defesa', 'Pendente...'), language="text")
            st.markdown("**2º Língua Estrangeira:**")
            st.code(resultado['aluno_info'].get('lingua_2', 'Pendente...'), language="text")
            
        with db_col3:
            st.markdown("**Membros da Banca:**")
            st.code(resultado['aluno_info'].get('membros_banca', 'Pendente...'), language="text")
            st.markdown("**Homologação do Título:**")
            st.code(resultado['aluno_info'].get('homologacao', 'Pendente...'), language="text")
            
        st.write("#### 📚 Histórico de Unidades Curriculares:")
        if resultado.get("historico"):
            df_hist = pd.DataFrame(resultado["historico"])
            st.dataframe(df_hist, width='stretch')
        else:
            st.warning("Nenhum histórico encontrado na tabela da página web.")
            
        cr_col1, cr_col2 = st.columns(2)
        with cr_col1:
            st.markdown("**Total de Créditos:**")
            st.code(resultado['aluno_info'].get('creditos_total', 'Pendente...'), language="text")
        with cr_col2:
            st.markdown("**Créditos Necessários:**")
            st.code(resultado['aluno_info'].get('creditos_necessarios', 'Pendente...'), language="text")
            
        st.write("---")
        st.write("#### 🔍 Análise do Histórico")
        pendencias = []
        info = resultado['aluno_info']
        
        # 1. Total de Créditos vs Créditos Necessários
        try:
            total_cred = int(info.get('creditos_total', '0'))
            nec_cred = int(info.get('creditos_necessarios', '0'))
            if total_cred < nec_cred:
                pendencias.append(f"O aluno possui créditos insuficientes. (Total: {total_cred}, Necessários: {nec_cred})")
        except:
            pass # Ignora se não puder converter para inteiro
            
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
        if resultado.get("pdf_historico") or resultado.get("pdf_comprovante"):
            st.write("---")
            st.write("#### 📄 Documentos Gerados")
            d_col1, d_col2 = st.columns(2)
            
            if resultado.get("pdf_historico"):
                try:
                    with open(resultado["pdf_historico"], "rb") as f:
                        pdf_data = f.read()
                    with d_col1:
                        st.download_button(label="Baixar Histórico (PDF)", data=pdf_data, file_name=f"Histórico_{resultado['aluno_info'].get('nome', 'Aluno')}.pdf", mime="application/pdf", type="primary", key="btn_down_hist")
                except Exception as e:
                    st.error(f"Erro ao ler PDF do Histórico: {e}")
                    
            if resultado.get("pdf_comprovante"):
                try:
                    with open(resultado["pdf_comprovante"], "rb") as f:
                        pdf_data2 = f.read()
                    with d_col2:
                        st.download_button(label="Baixar Comprovante (PDF)", data=pdf_data2, file_name=f"Comprovante_{resultado['aluno_info'].get('nome', 'Aluno')}.pdf", mime="application/pdf", type="primary", key="btn_down_comp")
                except Exception as e:
                    st.error(f"Erro ao ler PDF do Comprovante: {e}")
                    
        with st.expander("🛠️ Debug (Para enviar ao desenvolvedor)"):
            st.write("Se os dados acima estiverem incompletos, copie o texto abaixo e envie para o desenvolvedor analisar:")
            st.code(f"URL: {resultado.get('debug_url', 'N/A')}\n\nPAGE_TEXT:\n{resultado.get('debug_text', 'N/A')}", language="text")

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
    
    data_col_index = None
    for i, col in enumerate(header):
        if "carimbo" in str(col).lower() or str(col).strip().lower() == "data":
            data_col_index = i
            break
            
    st.divider()
    
    st.write("📅 **Filtro de Período**")
    f_col1, f_col2 = st.columns([2, 2])
    with f_col1:
        filtro_selecao = st.selectbox(
            "Visualizar atividades de:", 
            ["Últimos 7 dias", "Apenas Hoje", "Mês Atual", "Últimos 6 meses", "Todas as Atividades", "Escolher uma Data Específica"]
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
        data_inicio = hoje - timedelta(days=180)
        data_fim = hoje
    elif filtro_selecao == "Escolher uma Data Específica":
        with f_col2:
            data_especifica = st.date_input("Selecione o dia:", value=hoje)
            data_inicio = data_especifica
            data_fim = data_especifica
    
    count = 0
    # Processar de trás pra frente
    for reversed_idx, row in enumerate(reversed(rows)):
        idx_real_na_planilha = len(rows) - reversed_idx + 1 # +1 pq o cabeçalho é a linha 1
        
        row_padded = row + [''] * (len(header) - len(row))
        
        valor_data_completo = row_padded[data_col_index] if data_col_index is not None else ""
        data_da_linha = parse_date_br(valor_data_completo)
        
        if data_da_linha and data_inicio and data_fim:
            if not (data_inicio <= data_da_linha <= data_fim):
                continue
        elif filtro_selecao != "Todas as Atividades" and not data_da_linha:
            continue
            
        count += 1
        nome_col = next((c for c in header if "nome" in str(c).lower() and "programa" not in str(c).lower()), None)
        nome_val = row_padded[header.index(nome_col)] if nome_col else f"Solicitante (Linha {idx_real_na_planilha})"
        if not str(nome_val).strip():
            nome_val = f"Solicitante da Linha {idx_real_na_planilha}"
            
        with st.expander(f"👤 **{nome_val}** - 🕒 Solicitado em: {valor_data_completo}"):
            relevant_data = extract_relevant_data(row_padded, header)
            
            if not relevant_data:
                st.warning("Não encontrei campos padrão nesta planilha.")
            else:
                keys = list(relevant_data.keys())
                num_colunas = 3
                
                for i in range(0, len(keys), num_colunas):
                    cols = st.columns(num_colunas)
                    for j in range(num_colunas):
                        if i + j < len(keys):
                            key = keys[i+j]
                            val = relevant_data[key]
                            
                            if val and str(val).strip():
                                with cols[j]:
                                    # Aplicando a classe CSS pro título verde escuro e Merriweather
                                    st.markdown(f'<div class="info-title">{key}</div>', unsafe_allow_html=True)
                                    
                                    # Linha interna para o st.code e o botão de editar
                                    inner_c1, inner_c2 = st.columns([4, 1])
                                    with inner_c1:
                                        st.code(val, language="text")
                                    with inner_c2:
                                        # Popover para editar este campo específico
                                        with st.popover("✏️"):
                                            st.write(f"Editar **{key}**")
                                            novo_valor = st.text_input("Novo valor:", value=str(val), key=f"inp_{idx_real_na_planilha}_{key}")
                                            if st.button("Salvar na Planilha", key=f"btn_{idx_real_na_planilha}_{key}"):
                                                try:
                                                    coluna_index = header.index(key)
                                                    update_sheet_cell(sheet_id, info['aba'], idx_real_na_planilha, coluna_index, novo_valor)
                                                    st.success("Salvo com sucesso! A página irá recarregar.")
                                                    st.rerun()
                                                except Exception as err:
                                                    st.error(f"Erro ao salvar: {err}")

    if count == 0:
        st.info("Nenhuma atividade encontrada para o filtro selecionado.")

if __name__ == "__main__":
    main()
