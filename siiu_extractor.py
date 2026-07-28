import time
import os
import glob
import re
import traceback
import sys
import gc
import pandas as pd
from playwright.sync_api import sync_playwright

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

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

def close_sweetalert_overlays(page):
    """Fecha modais e sobreposições do SweetAlert (swal-overlay) que cobrem os botões do SIIU."""
    try:
        page.evaluate("""
            try {
                if (typeof swal !== 'undefined' && swal.close) swal.close();
                if (typeof Swal !== 'undefined' && Swal.close) Swal.close();
                const overlays = document.querySelectorAll('.swal-overlay, .swal2-container');
                overlays.forEach(el => el.remove());
            } catch(e) {}
        """)
    except Exception:
        pass

def parse_text_data(texto_full):
    """Extrai todos os dados de cabeçalho e tabela de disciplinas a partir de uma string de texto bruto."""
    info = {}
    if not texto_full or not texto_full.strip():
        return info

    texto_norm = re.sub(r'[ \t]+', ' ', texto_full)

    # 1. Dados Pessoais e Acadêmicos do Cabeçalho
    nome_m = re.search(r"Nome:\s*(.*?)(?=\n|Sexo:|Nasc|CPF|RG)", texto_norm, re.I)
    if nome_m: info['nome'] = nome_m.group(1).strip()
    
    sexo_m = re.search(r"Sexo:\s*([^\s\n\t\|]+)", texto_norm, re.I)
    if sexo_m: info['sexo'] = sexo_m.group(1).strip()
    
    nasc_m = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto_norm, re.I)
    if nasc_m: info['nascimento'] = nasc_m.group(1).strip()
    
    nat_m = re.search(r"Naturalidade:\s*(.*?)(?=\n|CPF:|RG:|N[ºo°]|\s{2,}|\||$)", texto_norm, re.I)
    if nat_m: info['naturalidade'] = nat_m.group(1).strip()
    
    cpf_m = re.search(r"(?:CPF|C\.P\.F\.)[\s:\ºn]*([\d\.\-]+)", texto_norm, re.I)
    if not cpf_m:
        cpf_m = re.search(r"\b(\d{3}\.\d{3}\.\d{3}\-\d{2})\b", texto_norm)
    if cpf_m: info['cpf'] = cpf_m.group(1).strip()
    
    rg_m = re.search(r"(?:RG|RNE)[\s:\ºn]*([\d\.\-A-Za-z/]+)", texto_norm, re.I)
    if rg_m: info['rg'] = rg_m.group(1).strip()
    
    mat_m = re.search(r"N[ºo°]\s*da\s*Matricula:\s*([\d]+)", texto_norm, re.I)
    if mat_m: info['ra'] = mat_m.group(1).strip()
    
    ing_m = re.search(r"(?:Início|Inicio):\s*([\d]{2}/[\d]{2}/[\d]{4})", texto_norm, re.I)
    if ing_m: info['ingresso'] = ing_m.group(1).strip()
    
    sit_m = re.search(r"Situação:\s*(.*?)(?=\s{2,}|\n|Término|Termino|Forma|\||$)", texto_norm, re.I)
    if sit_m:
        v_sit = sit_m.group(1).strip()
        info['situacao'] = v_sit
        info['situacao_siiu'] = v_sit
    
    term_m = re.search(r"Término\s*Previsto:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto_norm, re.I)
    if term_m: info['termino_previsto'] = term_m.group(1).strip()
    
    forma_m = re.search(r"Forma\s*de\s*Ingresso:\s*(.*?)(?=\s{2,}|\n|Homologação|Homologacao|Programa|\||$)", texto_norm, re.I)
    if forma_m: info['forma_ingresso'] = forma_m.group(1).strip()
    
    prog_m = re.search(r"Programa:\s*(.*?)(?=\s{2,}|\n|Nível|Nivel|Reconhecido|\||$)", texto_norm, re.I)
    if prog_m:
        v_prog = prog_m.group(1).strip()
        info['programa'] = v_prog
        info['curso'] = v_prog
    
    niv_m = re.search(r"Nível:\s*([^\n\|]+)", texto_norm, re.I)
    if niv_m: info['nivel'] = niv_m.group(1).strip()
    
    homol_m = re.search(r"Homologação\s*do\s*Título:\s*(.*?)(?=\n|Programa:|Nível:|Título|\s{2,}|\||$)", texto_norm, re.I)
    if homol_m: 
        h_val = homol_m.group(1).strip()
        info['homologacao'] = h_val if h_val else "Pendente"
    
    tese_m = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador|Defesa|\||$)", texto_norm, re.I | re.DOTALL)
    if tese_m: 
        t_val = tese_m.group(1).replace("\n", " ").strip()
        info['titulo_tese'] = t_val if t_val else "Não informado / Em andamento"
    
    orient_m = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\s{2,}|\n|Defesa|1[ºo°]|\||$)", texto_norm, re.I)
    if orient_m: info['orientador'] = orient_m.group(1).replace("\n", " ").strip()
    
    defesa_m = re.search(r"Defesa:\s*(.*?)(?=\s{2,}|\n|1[ºo°]|2[ºo°]|\||$)", texto_norm, re.I)
    if defesa_m:
        v_def = defesa_m.group(1).strip()
        info['defesa'] = v_def if v_def else "Pendente / Em andamento"
        
    l1_m = re.search(r"1[ºo°]\s*Língua\s*Estrangeira:\s*(.*?)(?=\s{2,}|\n|2[ºo°]|Graduação|\||$)", texto_norm, re.I)
    if l1_m: 
        l1_val = l1_m.group(1).strip()
        info['lingua_1'] = l1_val if l1_val else "Pendente"
    
    l2_m = re.search(r"2[ºo°]\s*Língua\s*Estrangeira:\s*(.*?)(?=\s{2,}|\n|Graduação|Unidade|\||$)", texto_norm, re.I)
    if l2_m: 
        l2_val = l2_m.group(1).strip()
        info['lingua_2'] = l2_val if l2_val else "Pendente"
    
    cred_t_m = re.search(r"Total\s*de\s*créditos:\s*([\d]+)", texto_norm, re.I)
    if cred_t_m: info['creditos_total'] = cred_t_m.group(1).strip()
    
    cred_n_m = re.search(r"Créditos\s*necessários\s*para\s*o\s*(?:MESTRADO|DOUTORADO):\s*([\d]+)", texto_norm, re.I)
    if cred_n_m: info['creditos_necessarios'] = cred_n_m.group(1).strip()

    # 2. Extração de Tabela de Disciplinas (Unidades Curriculares)
    hist_disciplinas = []
    lines = texto_norm.split("\n")
    in_uc = False
    for line in lines:
        if "Unidade Curricular" in line and "Ano" in line:
            in_uc = True
            continue
        if in_uc:
            if "Total de créditos" in line or "Legenda:" in line:
                in_uc = False
                break
            m_uc = re.search(r"^(.*?)\s+([\d]{4})\s+([\d]{1,3})\s+([A-D])\s+([\d]+)$", line.strip())
            if m_uc:
                hist_disciplinas.append({
                    "Unidade Curricular": m_uc.group(1).strip(),
                    "Ano": m_uc.group(2).strip(),
                    "Frequência (%)": m_uc.group(3).strip(),
                    "Conceito": m_uc.group(4).strip(),
                    "Créditos": m_uc.group(5).strip()
                })
    if hist_disciplinas:
        info["historico"] = hist_disciplinas
        
    return info

def parse_pdf_data(pdf_path):
    info = {}
    if not pdf_path or not os.path.exists(pdf_path):
        return info
        
    raw_texts = []
    
    # 1. Extração via pdfplumber (layout=False, layout=True e tabelas)
    if pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for p in pdf.pages:
                    t1 = p.extract_text(layout=False)
                    if t1: raw_texts.append(t1)
                    t2 = p.extract_text(layout=True)
                    if t2: raw_texts.append(t2)
                    
                    try:
                        tables = p.extract_tables()
                        for tbl in tables:
                            for r in tbl:
                                if r:
                                    raw_texts.append(" | ".join(str(c).strip() for c in r if c))
                    except Exception:
                        pass
        except Exception as e:
            print(f"Erro no pdfplumber: {e}")
            
    # 2. Fallback via pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        for p in reader.pages:
            t = p.extract_text()
            if t: raw_texts.append(t)
    except Exception:
        pass

    texto_full = "\n".join(raw_texts)
    return parse_text_data(texto_full)

def init_cached_driver(login, senha):
    """Mantém a assinatura compatível para o app.py."""
    return True, None

def _run_with_playwright_page(login, senha, task_fn):
    """Executa a task_fn(page) em um contexto do Playwright com suporte a PDF e janelas do Chrome."""
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    with sync_playwright() as p:
        # Abrir o navegador Chromium visível (ou headless configurável) sem flags restritivas de PDF
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run"
            ]
        )
        context = browser.new_context(
            accept_downloads=True,
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto("https://notas-propgpq.siiu.unifesp.br/login", timeout=30000, wait_until="domcontentloaded")
            page.fill("#username", login)
            page.fill("#password", senha)
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)
            
            body_text = page.locator("body").inner_text()
            if "incorreto" in body_text.lower() or "inválid" in body_text.lower() or "credencial" in body_text.lower():
                return {"status": "error", "message": "Usuário e/ou senha do SIIU incorretos. Verifique suas credenciais."}
                
            page.goto("https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes", timeout=25000, wait_until="domcontentloaded")
            page.wait_for_selector("#areas_prin_codigo", timeout=15000)
            
            res = task_fn(page)
            return res
        except Exception as e:
            return {"status": "error", "message": f"Erro na busca: {e}"}
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            gc.collect()

def _search_page_logic(page, query, programa, fallback_name=None):
    """Lógica interna de busca com suporte inteligente a seleção de PPG e varredura de fallback."""
    page.wait_for_selector("#areas_prin_codigo", timeout=15000)
    select_elem = page.locator("#areas_prin_codigo")
    
    import unicodedata
    def norm(txt):
        return "".join(c for c in unicodedata.normalize('NFD', str(txt).upper()) if unicodedata.category(c) != 'Mn').strip()

    options_elements = select_elem.locator("option").all()
    valid_options = []
    for opt in options_elements:
        txt = opt.inner_text().strip()
        val = opt.get_attribute("value") or ""
        txt_norm = norm(txt)
        if txt and "SELECIONE" not in txt_norm and val not in ("0", ""):
            valid_options.append((txt, val, txt_norm))

    prog_raw = (programa or "").strip()
    p_norm = norm(prog_raw)
    
    selected_option = None
    if p_norm and p_norm not in ("TODOS", "TODOS OS PROGRAMAS"):
        mapped_target = PPG_MAPPING_SIIU.get(p_norm)
        if not mapped_target:
            for k, v in PPG_MAPPING_SIIU.items():
                if k in p_norm or p_norm in k:
                    mapped_target = v
                    break
        target = norm(mapped_target or prog_raw)
        
        # Pass 1: Igualdade exata de nome de PPG
        for txt, val, txt_norm in valid_options:
            if txt_norm == target:
                selected_option = (txt, val)
                break
                
        # Pass 2: Palavra isolada exata (ex: "LETRAS" em "PROGRAMA DE POS-GRADUACAO EM LETRAS", ignorando unidade guarda-chuva)
        if not selected_option:
            for txt, val, txt_norm in valid_options:
                if re.search(r'\b' + re.escape(target) + r'\b', txt_norm) and "ESCOLA DE FILOSOFIA" not in txt_norm:
                    selected_option = (txt, val)
                    break

        # Pass 3: Substring fallback
        if not selected_option:
            for txt, val, txt_norm in valid_options:
                if target in txt_norm:
                    selected_option = (txt, val)
                    break
                
        # Pass 4: Busca por interseção de palavras chave
        if not selected_option:
            target_words = set(target.split()) - {"DE", "EM", "E", "DO", "DA", "DOS", "DAS", "PROGRAMA", "POS", "GRADUACAO", "PPG"}
            best_match = None
            best_score = 0
            for txt, val, txt_norm in valid_options:
                opt_words = set(txt_norm.split())
                overlap = len(target_words.intersection(opt_words))
                if overlap > best_score:
                    best_score = overlap
                    best_match = (txt, val)
            if best_match and best_score > 0:
                selected_option = best_match

    def do_search_in_option(opt_tuple, search_term):
        opt_txt, opt_val = opt_tuple
        try:
            select_elem.select_option(value=opt_val)
        except Exception:
            select_elem.select_option(label=opt_txt)
        page.wait_for_timeout(400)
        
        close_sweetalert_overlays(page)
        
        search_input = page.locator("input[name='descricao'], input#descricao, input[placeholder*='Nome']").first
        if search_input.count() > 0:
            search_input.fill(search_term)
            try:
                search_input.press("Enter")
            except Exception:
                pass
        
        close_sweetalert_overlays(page)
        
        btn_pesquisar = page.locator("button:has-text('Pesquisar'), [data-filter-pesquisar], button[type='submit']").first
        if btn_pesquisar.count() > 0:
            try:
                btn_pesquisar.click(force=True)
            except Exception:
                try:
                    page.evaluate("el => el.click()", btn_pesquisar.element_handle())
                except Exception:
                    pass
        
        page.wait_for_timeout(2000)
        
        rows = page.locator("table tbody tr").all()
        found_cands = []
        
        for idx, row in enumerate(rows):
            cols = row.locator("td").all_text_contents()
            if cols and len(cols) > 0:
                matricula = cols[0].strip() if len(cols) > 0 else ""
                nome = cols[1].strip() if len(cols) > 1 else ""
                curso = cols[2].strip() if len(cols) > 2 else ""
                ingresso = cols[3].strip() if len(cols) > 3 else ""
                nivel = cols[4].strip() if len(cols) > 4 else ""
                situacao = cols[5].strip() if len(cols) > 5 else ""
                
                if "Nenhum registro" in nome or "Nenhum registro" in matricula or "Selecione um programa" in nome:
                    continue
                    
                action_urls = []
                historico_url = None
                try:
                    all_clickable = row.locator("a, button, [onclick], [data-href]").all()
                    for el in all_clickable:
                        h = el.get_attribute("href") or el.get_attribute("onclick") or el.get_attribute("data-href") or ""
                        txt = el.inner_text().strip()
                        title = el.get_attribute("title") or el.get_attribute("data-original-title") or el.get_attribute("alt") or ""
                        
                        if h and h != "#":
                            if "location" in str(h) or "href" in str(h):
                                m = re.search(r"['\"]([^'\"]+)['\"]", str(h))
                                if m: h = m.group(1)
                            action_urls.append(h)
                            
                            combined = (str(h) + " " + txt + " " + title).lower()
                            if any(k in combined for k in ["historico", "pdf", "imprimir", "relatorio", "visualizar", "abrir histórico"]) and not historico_url:
                                historico_url = h
                    if not historico_url and action_urls:
                        historico_url = action_urls[0]
                except Exception:
                    pass
                    
                found_cands.append({
                    "idx": idx,
                    "matricula": matricula,
                    "nome": nome,
                    "curso": curso,
                    "ingresso": ingresso,
                    "nivel": nivel,
                    "situacao": situacao,
                    "historico_url": historico_url,
                    "action_urls": action_urls
                })
        return found_cands

    # Se um PPG específico foi solicitado pelo usuário, buscar EXCLUSIVAMENTE nele
    if selected_option:
        cands = do_search_in_option(selected_option, query)
        if cands:
            return {"status": "success", "candidates": cands}
        elif fallback_name and query != fallback_name:
            cands_fb = do_search_in_option(selected_option, fallback_name)
            if cands_fb:
                return {"status": "success", "candidates": cands_fb}
        return {"status": "error", "message": f"Nenhum aluno encontrado no programa '{selected_option[0]}' para os critérios informados."}

    # Se a busca foi para 'TODOS OS PROGRAMAS', varrer as opções disponíveis
    visited_ppgs = set()
    for txt, val, _ in valid_options:
        if val in visited_ppgs:
            continue
        visited_ppgs.add(val)
        cands = do_search_in_option((txt, val), query)
        if cands:
            return {"status": "success", "candidates": cands}

    try:
        dbg_url = page.url
        dbg_text = page.locator("body").inner_text()[:1000]
    except Exception:
        dbg_url = "N/A"
        dbg_text = "N/A"

    return {
        "status": "error",
        "message": "Nenhum aluno encontrado para os critérios informados.",
        "debug_url": dbg_url,
        "debug_text": dbg_text
    }

def _extract_page_logic(page, candidate, baixar_historico, baixar_comprovante):
    """Lógica interna de extração de detalhes navegando e baixando o PDF do Histórico."""
    aluno_info = {
        "matricula": candidate.get("matricula", ""),
        "ra": candidate.get("matricula", ""),
        "nome": candidate.get("nome", ""),
        "curso": candidate.get("curso", ""),
        "ingresso": candidate.get("ingresso", ""),
        "nivel": candidate.get("nivel", ""),
        "situacao": candidate.get("situacao", "")
    }
    
    pdf_historico_path = None
    pdf_comprovante_path = None
    
    urls_to_try = []
    if candidate.get("historico_url"):
        urls_to_try.append(candidate.get("historico_url"))
    for u in candidate.get("action_urls", []):
        if u not in urls_to_try:
            urls_to_try.append(u)

    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Pegar apenas a URL principal do histórico/discente para evitar navegações secundárias rápidas (404)
    target_url = candidate.get("historico_url") or (candidate.get("action_urls")[0] if candidate.get("action_urls") else None)
    if not target_url or target_url == "#":
        return {
            "status": "error",
            "message": "URL do discente não encontrada."
        }
        
    full_url = target_url if target_url.startswith("http") else f"https://notas-propgpq.siiu.unifesp.br{target_url if target_url.startswith('/') else '/' + target_url}"
    
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    try:
        # 1. Navegar via Chromium para a página principal de detalhes do discente
        page.goto(full_url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # 2. Extrair dados da seção "Dados da Banca" diretamente do HTML da página do aluno
        try:
            html_text = page.locator("body").inner_text()
            
            tese_html = re.search(r"(?:Título\s*da\s*Tese|Título\s*da\s*Dissertação)[\s:]*(.*?)(?=\n|Ano:|Orientador|Membros|Situação)", html_text, re.I)
            if tese_html and tese_html.group(1).strip():
                aluno_info['titulo_tese'] = tese_html.group(1).strip()
                
            ano_html = re.search(r"Ano[\s:]*([\d]{4})", html_text, re.I)
            if ano_html:
                aluno_info['ano_tese'] = ano_html.group(1).strip()
                
            membros_html = re.search(r"Membros\s*da\s*Banca[\s:]*(.*?)(?=\n|Homologação|Orientador|Situação)", html_text, re.I | re.DOTALL)
            if membros_html and membros_html.group(1).strip():
                aluno_info['membros_banca'] = membros_html.group(1).replace("\n", ", ").strip()
                
            sit_tese_html = re.search(r"Situação\s*da\s*Tese[\s:]*(.*?)(?=\n|Orientador|Homologação)", html_text, re.I)
            if sit_tese_html and sit_tese_html.group(1).strip():
                aluno_info['situacao_tese'] = sit_tese_html.group(1).strip()
                
            orient_html = re.search(r"Orientador[\(a\)]*[\s:]*(.*?)(?=\s{2,}|\n|Homologação|Defesa|Membros)", html_text, re.I)
            if orient_html and orient_html.group(1).strip():
                aluno_info['orientador'] = orient_html.group(1).strip()
                
            homol_html = re.search(r"Homologação\s*do\s*Título[\s:]*(.*?)(?=\n|1[ºo°]|Defesa|Orientador)", html_text, re.I)
            if homol_html and homol_html.group(1).strip():
                aluno_info['homologacao'] = homol_html.group(1).strip()
                
            l1_html = re.search(r"1[ºo°]\s*Língua\s*Estrangeira[\s:]*(.*?)(?=\s{2,}|\n|2[ºo°]|Defesa)", html_text, re.I)
            if l1_html and l1_html.group(1).strip():
                aluno_info['lingua_1'] = l1_html.group(1).strip()
                
            l2_html = re.search(r"2[ºo°]\s*Língua\s*Estrangeira[\s:]*(.*?)(?=\s{2,}|\n|Defesa|Membros)", html_text, re.I)
            if l2_html and l2_html.group(1).strip():
                aluno_info['lingua_2'] = l2_html.group(1).strip()
                
            defesa_html = re.search(r"Defesa[\s:]*.*?([\d]{2}/[\d]{2}/[\d]{4})", html_text, re.I)
            if defesa_html:
                aluno_info['defesa'] = defesa_html.group(1).strip()
        except Exception as e_html:
            print(f"Aviso ao ler HTML da banca: {e_html}")

        current_url = page.url
        base_url = current_url.split("?")[0].rstrip("/")
        pdf_imprimir_url = base_url if base_url.endswith("secretaria-imprimir") else f"{base_url}/secretaria-imprimir"
        pdf_comprovante_url = f"{base_url}/comprovante-matricula?aluno={aluno_info['ra']}"

        pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
        pdf_comprovante_path = os.path.join(download_dir, f"Comprovante_{aluno_info['ra']}.pdf")

        headers_ref = {
            "Referer": full_url,
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # 1. Tentar download do Histórico via expect_download oficial do Chrome ao clicar em Imprimir
        try:
            close_sweetalert_overlays(page)
            imprimir_btn = page.locator("a[href*='secretaria-imprimir'], a:has-text('Imprimir'), button:has-text('Imprimir')").first
            if imprimir_btn.count() > 0:
                try:
                    with page.expect_download(timeout=5000) as dl_info:
                        imprimir_btn.click(force=True)
                    dl = dl_info.value
                    dl.save_as(pdf_historico_path)
                except Exception:
                    pass
        except Exception as e_dl:
            print(f"Aviso expect_download: {e_dl}")

        # 2. Se o expect_download não capturou, baixar os bytes do PDF com Referer da sessão ativa
        if not os.path.exists(pdf_historico_path) or os.path.getsize(pdf_historico_path) < 100:
            try:
                res_h = page.context.request.get(pdf_imprimir_url, headers=headers_ref, timeout=15000)
                h_bytes = res_h.body()
                if len(h_bytes) > 200:
                    with open(pdf_historico_path, "wb") as f_h:
                        f_h.write(h_bytes)
            except Exception as e_h:
                print(f"Aviso context.request historico: {e_h}")

        # 3. Baixar também os bytes do Comprovante de Matrícula
        try:
            res_c = page.context.request.get(pdf_comprovante_url, headers=headers_ref, timeout=12000)
            c_bytes = res_c.body()
            if len(c_bytes) > 200:
                with open(pdf_comprovante_path, "wb") as f_c:
                    f_c.write(c_bytes)
        except Exception as e_c:
            print(f"Aviso context.request comprovante: {e_c}")

        # 4. Ler o arquivo PDF salvo em downloads/ usando o pdfplumber e popular aluno_info
        if os.path.exists(pdf_historico_path) and os.path.getsize(pdf_historico_path) > 100:
            parsed = parse_pdf_data(pdf_historico_path)
            if parsed:
                for k, v in parsed.items():
                    if v: aluno_info[k] = v

        if os.path.exists(pdf_comprovante_path) and os.path.getsize(pdf_comprovante_path) > 100:
            parsed_c = parse_pdf_data(pdf_comprovante_path)
            if parsed_c:
                for k, v in parsed_c.items():
                    if v and not aluno_info.get(k): aluno_info[k] = v

        # 5. Abrir as abas visíveis no Chrome para o usuário visualizar e pausar 3 segundos antes de encerrar
        try:
            close_sweetalert_overlays(page)
            if baixar_comprovante:
                page.evaluate(f"window.open('{pdf_comprovante_url}', '_blank');")
            if baixar_historico:
                page.evaluate(f"window.open('{pdf_imprimir_url}', '_blank');")
            page.wait_for_timeout(3000)
        except Exception:
            pass

    except Exception as e_proc:
        print(f"Erro ao processar discente: {e_proc}")

    # Passo 6: Ler os dados do arquivo PDF baixado usando o pdfplumber
    if pdf_historico_path and os.path.exists(pdf_historico_path) and os.path.getsize(pdf_historico_path) > 100:
        parsed = parse_pdf_data(pdf_historico_path)
        if parsed:
            for k, v in parsed.items():
                if v: aluno_info[k] = v

    return {
        "status": "success",
        "aluno_info": aluno_info,
        "pdf_historico": pdf_historico_path,
        "pdf_comprovante": pdf_comprovante_path,
        "historico": aluno_info.get("historico", [])
    }

def search_student_candidates(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca candidatos no SIIU via Playwright."""
    def _task(page):
        return _search_page_logic(page, query, programa, fallback_name)
    return _run_with_playwright_page(login, senha, _task)

def extract_candidate_details(login, senha, candidate, baixar_historico, baixar_comprovante, cached_driver=None):
    """Extrai detalhes do candidato no SIIU via Playwright."""
    def _task(page):
        return _extract_page_logic(page, candidate, baixar_historico, baixar_comprovante)
    return _run_with_playwright_page(login, senha, _task)

def search_and_extract_student(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca e extrai detalhes do discente no SIIU em uma ÚNICA sessão do Playwright."""
    def _task(page):
        search_res = _search_page_logic(page, query, programa, fallback_name)
        if search_res.get("status") == "error":
            return search_res
            
        candidates = search_res.get("candidates", [])
        if not candidates:
            return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}
            
        if len(candidates) == 1:
            ext_res = _extract_page_logic(page, candidates[0], True, True)
            a_info = ext_res.get("aluno_info", {})
            return {
                "status": "success",
                "single": True,
                "details": ext_res,
                "aluno_info": a_info,
                "historico": a_info.get("historico", [])
            }
        else:
            return {"status": "success", "single": False, "candidates": candidates}
            
    return _run_with_playwright_page(login, senha, _task)
