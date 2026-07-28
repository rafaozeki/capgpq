import time
import os
import glob
import re
import traceback
import sys
import pandas as pd
from bs4 import BeautifulSoup
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

def parse_pdf_data(pdf_path):
    info = {}
    if not pdfplumber or not pdf_path or not os.path.exists(pdf_path):
        return info
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
            
        sexo_match = re.search(r"Sexo:\s*([A-Za-z]+)", texto, re.I)
        if sexo_match: info['sexo'] = sexo_match.group(1).strip()
            
        nasc_match = re.search(r"Nascimento:\s*([\d/]{8,10})", texto, re.I)
        if nasc_match: info['nascimento'] = nasc_match.group(1).strip()
            
        nat_match = re.search(r"Naturalidade:\s*([^\n]+)", texto, re.I)
        if nat_match: info['naturalidade'] = nat_match.group(1).strip()
            
        cpf_match = re.search(r"CPF:\s*([\d\.-]+)", texto, re.I)
        if cpf_match: info['cpf'] = cpf_match.group(1).strip()
            
        rg_match = re.search(r"(?:RG|RNE).*?:\s*([^\n]+)", texto, re.I)
        if rg_match: info['rg'] = rg_match.group(1).strip()
            
        inicio_match = re.search(r"Início:\s*([\d/]{8,10})", texto, re.I)
        if inicio_match: info['ingresso_data'] = inicio_match.group(1).strip()
        
        term_match = re.search(r"Término\s*previsto:\s*([\d/]{8,10})", texto, re.I)
        if term_match: info['termino_previsto'] = term_match.group(1).strip()
            
        forma_match = re.search(r"Forma\s*de\s*Ingresso:\s*([A-Za-z]+)", texto, re.I)
        if forma_match: info['forma_ingresso'] = forma_match.group(1).strip()
            
        homol_match = re.search(r"Homologação\s*do\s*Título:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if homol_match: info['homologacao'] = homol_match.group(1).strip()
            
        tese_match = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador)", texto, re.I | re.DOTALL)
        if tese_match: 
            info['titulo_tese'] = tese_match.group(1).replace("\n", " ").strip()
            
        orient_match = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\nDefesa|Defesa)", texto, re.I | re.DOTALL)
        if orient_match: 
            info['orientador'] = orient_match.group(1).replace("\n", " ").strip()
            
        defesa_match = re.search(r"Defesa:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if defesa_match: 
            info['defesa'] = defesa_match.group(1).strip()
        else:
            info['defesa'] = "Pendente"
            
        l1_match = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l1_match: info['lingua_1'] = l1_match.group(1).strip()
            
        l2_match = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l2_match: info['lingua_2'] = l2_match.group(1).strip()
            
        uc_match = re.search(r"Unidade\s*Curricular.*?\n(.*?)(?=\nTotal|\nCréditos|\nResumo|\nMédia)", texto, re.I | re.DOTALL)
        if uc_match: info['unidades_curriculares'] = uc_match.group(1).strip()
            
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        
    return info

# Gestor de sessão do Playwright
_playwright_instance = None
_browser_instance = None
_context_instance = None
_page_instance = None
_logged_in_user = None

def init_cached_driver(login, senha):
    """Inicializa ou reusa uma instância do Playwright autenticada no SIIU."""
    global _playwright_instance, _browser_instance, _context_instance, _page_instance, _logged_in_user
    
    if _page_instance and not _page_instance.is_closed() and _logged_in_user == login:
        try:
            _page_instance.url
            return _page_instance, None
        except Exception:
            pass
            
    try:
        if not _playwright_instance:
            _playwright_instance = sync_playwright().start()
            _browser_instance = _playwright_instance.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--blink-settings=imagesEnabled=false"]
            )
            
        if _context_instance:
            try: _context_instance.close()
            except Exception: pass
            
        _context_instance = _browser_instance.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        _page_instance = _context_instance.new_page()
        
        # Acessar tela de login
        _page_instance.goto("https://notas-propgpq.siiu.unifesp.br/login", timeout=30000)
        
        # Preencher formulário de login
        _page_instance.fill("#username", login)
        _page_instance.fill("#password", senha)
        _page_instance.click("button[type='submit']")
        _page_instance.wait_for_timeout(2000)
        
        body_text = _page_instance.locator("body").inner_text()
        if "incorreto" in body_text.lower() or "inválid" in body_text.lower() or "credencial" in body_text.lower():
            return None, "Usuário e/ou senha do SIIU incorretos. Verifique suas credenciais."
            
        _page_instance.goto("https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes", timeout=25000)
        _page_instance.wait_for_selector("#areas_prin_codigo", timeout=15000)
        
        _logged_in_user = login
        return _page_instance, None
        
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            error_msg = "Timeout no login. Verifique seu usuário e senha ou se o SIIU está fora do ar."
        return None, error_msg

def search_student_candidates(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca os candidatos no SIIU usando Playwright."""
    page = cached_driver
    if not page or page.is_closed():
        page, err = init_cached_driver(login, senha)
        if not page:
            return {"status": "error", "message": err}

    try:
        target_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
        if page.url != target_url:
            page.goto(target_url, timeout=20000)
            
        page.wait_for_selector("#areas_prin_codigo", timeout=15000)
        
        select_elem = page.locator("#areas_prin_codigo")
        selected = False
        
        import unicodedata
        def norm(txt):
            return "".join(c for c in unicodedata.normalize('NFD', str(txt).upper()) if unicodedata.category(c) != 'Mn').strip()

        prog_raw = (programa or "").strip()
        p_norm = norm(prog_raw)
        
        mapped_target = None
        for k, v in PPG_MAPPING_SIIU.items():
            if k in p_norm or p_norm in k:
                mapped_target = v
                break
                
        target_name = mapped_target or prog_raw
        t_norm = norm(target_name)
        
        options_texts = select_elem.locator("option").all_text_contents()
        
        if t_norm and t_norm != "TODOS OS PROGRAMAS":
            for opt_text in options_texts:
                if norm(opt_text) == t_norm:
                    select_elem.select_option(label=opt_text)
                    selected = True
                    break
                    
            if not selected:
                candidates_opt = [o for o in options_texts if t_norm in norm(o)]
                if candidates_opt:
                    best_opt = min(candidates_opt, key=len)
                    select_elem.select_option(label=best_opt)
                    selected = True

        if not selected:
            for opt_text in options_texts:
                if "SELECIONE" not in norm(opt_text) and opt_text.strip():
                    select_elem.select_option(label=opt_text)
                    selected = True
                    break

        if selected:
            page.wait_for_timeout(1000)
        
        search_input = page.locator("input[name='descricao'], input#descricao, input[placeholder*='Nome']").first
        search_input.fill(query)
        
        btn_pesquisar = page.locator("button:has-text('Pesquisar')").first
        btn_pesquisar.click()
        
        page.wait_for_timeout(1500)
        
        rows = page.locator("table tbody tr").all()
        candidates = []
        
        for idx, row in enumerate(rows):
            cols = row.locator("td").all_text_contents()
            if cols and len(cols) > 0:
                matricula = cols[0].strip() if len(cols) > 0 else ""
                nome = cols[1].strip() if len(cols) > 1 else ""
                curso = cols[2].strip() if len(cols) > 2 else ""
                ingresso = cols[3].strip() if len(cols) > 3 else ""
                nivel = cols[4].strip() if len(cols) > 4 else ""
                situacao = cols[5].strip() if len(cols) > 5 else ""
                
                if "Nenhum registro" in nome or "Nenhum registro" in matricula:
                    continue
                    
                historico_url = None
                try:
                    hist_link = row.locator("a[href*='historico']").first
                    if hist_link.count() > 0:
                        historico_url = hist_link.get_attribute("href")
                except Exception:
                    pass
                    
                candidates.append({
                    "idx": idx,
                    "matricula": matricula,
                    "nome": nome,
                    "curso": curso,
                    "ingresso": ingresso,
                    "nivel": nivel,
                    "situacao": situacao,
                    "historico_url": historico_url
                })

        if not candidates or len(candidates) == 0:
            if fallback_name and query != fallback_name:
                return search_student_candidates(login, senha, query=fallback_name, programa=programa, cached_driver=page, fallback_name=fallback_name)
            elif programa != "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS":
                return search_student_candidates(login, senha, query=query, programa="ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS", cached_driver=page, fallback_name=fallback_name)
            return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}

        return {"status": "success", "candidates": candidates, "cached_driver": page}

    except Exception as e:
        return {"status": "error", "message": f"Erro na busca: {e}"}

def extract_candidate_details(login, senha, candidate, baixar_historico=True, baixar_comprovante=True, cached_driver=None):
    """Extrai detalhes do candidato e efetua download de PDFs via Playwright."""
    page = cached_driver
    if not page or page.is_closed():
        page, err = init_cached_driver(login, senha)
        if not page:
            return {"status": "error", "message": err}

    try:
        historico_url = candidate.get("historico_url")
        if not historico_url:
            return {"status": "error", "message": "URL de histórico não encontrada para este discente."}

        if not historico_url.startswith("http"):
            historico_url = "https://notas-propgpq.siiu.unifesp.br" + historico_url

        page.goto(historico_url, timeout=25000)
        page.wait_for_selector("body", timeout=10000)
        
        debug_text = page.locator("body").inner_text()
        debug_url = page.url

        aluno_info = {
            "nome": candidate.get("nome", ""),
            "matricula": candidate.get("matricula", ""),
            "curso": candidate.get("curso", ""),
            "nivel": candidate.get("nivel", ""),
            "situacao": candidate.get("situacao", "")
        }

        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                label = tds[0].get_text(strip=True).replace(':', '')
                val = tds[1].get_text(strip=True)
                if label and val:
                    aluno_info[label] = val
                    
        for label_elem in soup.find_all(['label', 'span', 'strong']):
            txt = label_elem.get_text(strip=True).replace(':', '')
            next_sib = label_elem.next_sibling
            if next_sib and isinstance(next_sib, str) and next_sib.strip():
                aluno_info[txt] = next_sib.strip()

        pdf_hist_path = None
        pdf_comp_path = None

        temp_dir = os.path.join(os.getcwd(), "temp_downloads")
        os.makedirs(temp_dir, exist_ok=True)

        if baixar_historico:
            try:
                hist_btn = page.locator("a[href*='imprimir'], a[href*='pdf'], button:has-text('Histórico')")
                if hist_btn.count() > 0:
                    with page.expect_download(timeout=10000) as download_info:
                        hist_btn.first.click()
                    download = download_info.value
                    pdf_hist_path = os.path.join(temp_dir, f"Historico_{candidate.get('matricula')}.pdf")
                    download.save_as(pdf_hist_path)
            except Exception as e_pdf:
                print(f"Aviso download histórico: {e_pdf}")

        if baixar_comprovante:
            try:
                comp_btn = page.locator("a[href*='comprovante'], button:has-text('Comprovante')")
                if comp_btn.count() > 0:
                    with page.expect_download(timeout=10000) as download_info:
                        comp_btn.first.click()
                    download = download_info.value
                    pdf_comp_path = os.path.join(temp_dir, f"Comprovante_{candidate.get('matricula')}.pdf")
                    download.save_as(pdf_comp_path)
            except Exception as e_pdf2:
                print(f"Aviso download comprovante: {e_pdf2}")

        if pdf_hist_path and os.path.exists(pdf_hist_path):
            pdf_data = parse_pdf_data(pdf_hist_path)
            for k, v in pdf_data.items():
                if v and not aluno_info.get(k):
                    aluno_info[k] = v

        return {
            "status": "success",
            "aluno_info": aluno_info,
            "pdf_historico": pdf_hist_path,
            "pdf_comprovante": pdf_comp_path,
            "debug_url": debug_url,
            "debug_text": debug_text[:2000]
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        return {
            "status": "error",
            "message": f"Erro na extração de detalhes: {e}",
            "debug_text": error_trace
        }

def extract_student_data(login, senha, query, programa="Todos os Programas", baixar_historico=True, baixar_comprovante=True):
    """Wrapper legado para manter retrocompatibilidade."""
    s_res = search_student_candidates(login, senha, query, programa)
    if s_res.get("status") == "error":
        return s_res
    candidates = s_res.get("candidates", [])
    if not candidates:
        return {"status": "error", "message": "Nenhum aluno encontrado."}
    return extract_candidate_details(login, senha, candidates[0], baixar_historico, baixar_comprovante, cached_driver=s_res.get("cached_driver"))
