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

def parse_pdf_data(pdf_path):
    info = {}
    if not pdfplumber or not pdf_path or not os.path.exists(pdf_path):
        return info
        
    try:
        texto = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: texto += t + "\n"
                
        cpf_match = re.search(r"CPF:\s*([\d\.\-]+)", texto, re.I)
        if cpf_match: info['cpf'] = cpf_match.group(1).strip()
            
        rg_match = re.search(r"RG:\s*([^\n]+)", texto, re.I)
        if rg_match: info['rg'] = rg_match.group(1).strip()
            
        nasc_match = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if nasc_match: info['nascimento'] = nasc_match.group(1).strip()
            
        ing_match = re.search(r"Ingresso:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if ing_match: info['ingresso'] = ing_match.group(1).strip()
            
        term_match = re.search(r"Término\s*Previsto:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if term_match: info['termino_previsto'] = term_match.group(1).strip()
            
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

def init_cached_driver(login, senha):
    """Mantém a assinatura compatível para o app.py."""
    return True, None

def _run_with_playwright_page(login, senha, task_fn):
    """Executa a task_fn(page) em um contexto isolado do Playwright dentro da thread atual."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--blink-settings=imagesEnabled=false"]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto("https://notas-propgpq.siiu.unifesp.br/login", timeout=30000)
            page.fill("#username", login)
            page.fill("#password", senha)
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)
            
            body_text = page.locator("body").inner_text()
            if "incorreto" in body_text.lower() or "inválid" in body_text.lower() or "credencial" in body_text.lower():
                return {"status": "error", "message": "Usuário e/ou senha do SIIU incorretos. Verifique suas credenciais."}
                
            page.goto("https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes", timeout=25000)
            page.wait_for_selector("#areas_prin_codigo", timeout=15000)
            
            return task_fn(page)
        except Exception as e:
            return {"status": "error", "message": f"Erro na busca: {e}"}
        finally:
            browser.close()

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
    
    mapped_target = None
    for k, v in PPG_MAPPING_SIIU.items():
        if k in p_norm or p_norm in k:
            mapped_target = v
            break
            
    target_name = mapped_target or prog_raw
    t_norm = norm(target_name)
    
    selected_option = None
    if t_norm and t_norm != "TODOS OS PROGRAMAS":
        for txt, val, txt_norm in valid_options:
            if txt_norm == t_norm or t_norm in txt_norm or txt_norm in t_norm:
                selected_option = (txt, val)
                break
                
    if not selected_option and valid_options:
        selected_option = (valid_options[0][0], valid_options[0][1])

    visited_ppgs = set()

    def do_search_in_option(opt_tuple, search_term):
        opt_txt, opt_val = opt_tuple
        try:
            select_elem.select_option(value=opt_val)
        except Exception:
            select_elem.select_option(label=opt_txt)
        page.wait_for_timeout(500)
        
        close_sweetalert_overlays(page)
        
        search_input = page.locator("input[name='descricao'], input#descricao, input[placeholder*='Nome']").first
        search_input.fill(search_term)
        
        close_sweetalert_overlays(page)
        
        btn_pesquisar = page.locator("button:has-text('Pesquisar')").first
        try:
            btn_pesquisar.click(force=True)
        except Exception:
            page.evaluate("el => el.click()", btn_pesquisar.element_handle())
        
        page.wait_for_timeout(1200)
        
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
                    
                historico_url = None
                try:
                    a_elems = row.locator("a").all()
                    for a_el in a_elems:
                        h = a_el.get_attribute("href") or a_el.get_attribute("onclick") or a_el.get_attribute("data-href")
                        if h and h != "#":
                            if "location" in str(h) or "href" in str(h):
                                m = re.search(r"['\"]([^'\"]+)['\"]", str(h))
                                if m: h = m.group(1)
                            historico_url = h
                            break
                    if not historico_url:
                        btn_elems = row.locator("button, [onclick], [data-href]").all()
                        for btn_el in btn_elems:
                            h = btn_el.get_attribute("onclick") or btn_el.get_attribute("data-href") or btn_el.get_attribute("href")
                            if h and h != "#":
                                if "location" in str(h) or "href" in str(h):
                                    m = re.search(r"['\"]([^'\"]+)['\"]", str(h))
                                    if m: h = m.group(1)
                                historico_url = h
                                break
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
                    "historico_url": historico_url
                })
        return found_cands

    # 1. Pesquisa na opção de PPG principal
    if selected_option:
        visited_ppgs.add(selected_option[1])
        cands = do_search_in_option(selected_option, query)
        if cands:
            return {"status": "success", "candidates": cands}

    # 2. Varredura de fallback em todos os demais PPGs da instituição
    for txt, val, _ in valid_options:
        if val in visited_ppgs:
            continue
        visited_ppgs.add(val)
        cands = do_search_in_option((txt, val), query)
        if cands:
            return {"status": "success", "candidates": cands}

    # 3. Fallback adicional se query for RA/CPF e tivermos o Nome do aluno
    if fallback_name and query != fallback_name:
        for txt, val, _ in valid_options:
            cands = do_search_in_option((txt, val), fallback_name)
            if cands:
                return {"status": "success", "candidates": cands}

    return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}

def search_student_candidates(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca os candidatos no SIIU em um ambiente isolado de thread do Playwright."""
    def _task(page):
        return _search_page_logic(page, query, programa, fallback_name)
    return _run_with_playwright_page(login, senha, _task)

def _extract_page_logic(page, candidate, baixar_historico, baixar_comprovante):
    """Lógica interna de extração de detalhes em uma página já autenticada do Playwright."""
    historico_url = candidate.get("historico_url")
    if historico_url:
        if not historico_url.startswith("http"):
            historico_url = f"https://notas-propgpq.siiu.unifesp.br{historico_url if historico_url.startswith('/') else '/' + historico_url}"
        try:
            page.goto(historico_url, timeout=25000)
            page.wait_for_timeout(2000)
        except Exception as e_nav:
            print(f"Aviso na navegação do histórico: {e_nav}")

    aluno_info = {
        "matricula": candidate.get("matricula", ""),
        "ra": candidate.get("matricula", ""),
        "nome": candidate.get("nome", ""),
        "curso": candidate.get("curso", ""),
        "ingresso": candidate.get("ingresso", ""),
        "nivel": candidate.get("nivel", ""),
        "situacao": candidate.get("situacao", "")
    }

    try:
        body_text = page.locator("body").inner_text()
        
        cpf_m = re.search(r"CPF:\s*([\d\.\-]+)", body_text, re.I)
        if cpf_m: aluno_info["cpf"] = cpf_m.group(1).strip()
        
        rg_m = re.search(r"RG:\s*([^\n]+)", body_text, re.I)
        if rg_m: aluno_info["rg"] = rg_m.group(1).strip()
        
        nasc_m = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if nasc_m: aluno_info["nascimento"] = nasc_m.group(1).strip()
        
        term_m = re.search(r"Término\s*Previsto:\s*([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if term_m: aluno_info["termino_previsto"] = term_m.group(1).strip()
        
        homol_m = re.search(r"Homologação\s*do\s*Título:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if homol_m: aluno_info["homologacao"] = homol_m.group(1).strip()
        
        orient_m = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\nDefesa|Defesa)", body_text, re.I | re.DOTALL)
        if orient_m: aluno_info["orientador"] = orient_m.group(1).replace("\n", " ").strip()
        
        l1_m = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", body_text, re.I)
        if l1_m: aluno_info["lingua_1"] = l1_m.group(1).strip()
        
        l2_m = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", body_text, re.I)
        if l2_m: aluno_info["lingua_2"] = l2_m.group(1).strip()
    except Exception as e_parse:
        print(f"Aviso na extração de texto do discente: {e_parse}")

    return {
        "status": "success",
        "aluno_info": aluno_info
    }

def extract_candidate_details(login, senha, candidate, baixar_historico, baixar_comprovante, cached_driver=None):
    """Extrai detalhes do candidato no SIIU."""
    def _task(page):
        return _extract_page_logic(page, candidate, baixar_historico, baixar_comprovante)
    return _run_with_playwright_page(login, senha, _task)
