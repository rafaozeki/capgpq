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
            
        rg_match = re.search(r"RG:\s*([\d\.\-A-Za-z/]+)", texto, re.I)
        if rg_match: info['rg'] = rg_match.group(1).strip()
            
        nasc_match = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if nasc_match: info['nascimento'] = nasc_match.group(1).strip()
            
        ing_match = re.search(r"(?:Ingresso|Início|Inicio):\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if ing_match: info['ingresso'] = ing_match.group(1).strip()
            
        term_match = re.search(r"Término\s*(?:Previsto)?:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
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

import gc

def _run_with_playwright_page(login, senha, task_fn):
    """Executa a task_fn(page) em um contexto de baixíssima memória (low-end device mode)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--no-first-run",
                "--no-zygote",
                "--enable-low-end-device-mode",
                "--force-low-end-device-mode",
                "--disable-site-isolation-trials",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",
                "--disable-component-extensions-with-background-pages",
                "--disable-features=TranslateUI,BlinkGenPropertyTrees,IsolateOrigins,site-per-process,AudioServiceOutOfProcess",
                "--disable-ipc-flooding-protection",
                "--disable-renderer-backgrounding",
                "--mute-audio",
                "--js-flags=--max-old-space-size=64",
                "--blink-settings=imagesEnabled=false"
            ]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 800, "height": 600},
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
                    
                action_urls = []
                historico_url = None
                try:
                    all_clickable = row.locator("a, button, [onclick], [data-href]").all()
                    for el in all_clickable:
                        h = el.get_attribute("href") or el.get_attribute("onclick") or el.get_attribute("data-href") or ""
                        txt = el.inner_text().strip()
                        title = el.get_attribute("title") or el.get_attribute("alt") or ""
                        
                        if h and h != "#":
                            if "location" in str(h) or "href" in str(h):
                                m = re.search(r"['\"]([^'\"]+)['\"]", str(h))
                                if m: h = m.group(1)
                            action_urls.append(h)
                            
                            combined = (str(h) + " " + txt + " " + title).lower()
                            if any(k in combined for k in ["historico", "pdf", "imprimir", "relatorio", "visualizar"]) and not historico_url:
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

    if selected_option:
        visited_ppgs.add(selected_option[1])
        cands = do_search_in_option(selected_option, query)
        if cands:
            return {"status": "success", "candidates": cands}

    for txt, val, _ in valid_options:
        if val in visited_ppgs:
            continue
        visited_ppgs.add(val)
        cands = do_search_in_option((txt, val), query)
        if cands:
            return {"status": "success", "candidates": cands}

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
    """Lógica interna de extração de detalhes testando todas as URLs e botões de ação da tabela."""
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

    # 1. Tenta acessar/baixar através das URLs da ação
    for target_url in urls_to_try:
        if not target_url or target_url == "#":
            continue
            
        full_url = target_url if target_url.startswith("http") else f"https://notas-propgpq.siiu.unifesp.br{target_url if target_url.startswith('/') else '/' + target_url}"
        
        try:
            with page.expect_download(timeout=5000) as download_info:
                page.goto(full_url, timeout=20000)
            download = download_info.value
            download_dir = os.path.join(os.getcwd(), "downloads")
            os.makedirs(download_dir, exist_ok=True)
            pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
            download.save_as(pdf_historico_path)
            if os.path.exists(pdf_historico_path):
                parsed = parse_pdf_data(pdf_historico_path)
                if parsed.get("cpf") or parsed.get("rg"):
                    for k, v in parsed.items():
                        if v: aluno_info[k] = v
                    break
        except Exception:
            try:
                page.goto(full_url, timeout=20000)
                page.wait_for_timeout(1500)
                b_text = page.locator("body").inner_text()
                if "CPF" in b_text or "RG" in b_text:
                    break
            except Exception:
                pass

    # 2. Se não conseguiu os dados via URL direta, re-pesquisa e clica nos botões da tabela
    if not aluno_info.get("cpf") and not aluno_info.get("rg"):
        try:
            page.goto("https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes", timeout=25000)
            page.wait_for_selector("#areas_prin_codigo", timeout=15000)
            
            search_res = _search_page_logic(page, aluno_info['ra'] or aluno_info['nome'], aluno_info.get('curso', ''))
            
            rows = page.locator("table tbody tr").all()
            if rows:
                row = rows[0]
                clickables = row.locator("td:last-child a, td:last-child button, a, button, [onclick]").all()
                
                for click_target in clickables:
                    close_sweetalert_overlays(page)
                    try:
                        with page.expect_download(timeout=5000) as dl_info:
                            click_target.click(force=True)
                        dl = dl_info.value
                        download_dir = os.path.join(os.getcwd(), "downloads")
                        os.makedirs(download_dir, exist_ok=True)
                        pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
                        dl.save_as(pdf_historico_path)
                        if os.path.exists(pdf_historico_path):
                            parsed = parse_pdf_data(pdf_historico_path)
                            if parsed.get("cpf") or parsed.get("rg"):
                                for k, v in parsed.items():
                                    if v: aluno_info[k] = v
                                break
                    except Exception:
                        try:
                            with page.context.expect_page(timeout=5000) as new_p_info:
                                click_target.click(force=True)
                            new_page = new_p_info.value
                            new_page.wait_for_timeout(2000)
                            b_txt = new_page.locator("body").inner_text()
                            if "CPF" in b_txt or "RG" in b_txt:
                                page = new_page
                                break
                        except Exception:
                            try:
                                click_target.click(force=True)
                                page.wait_for_timeout(1500)
                                b_txt = page.locator("body").inner_text()
                                if "CPF" in b_txt or "RG" in b_txt:
                                    break
                            except Exception:
                                pass
        except Exception as e_re:
            print(f"Aviso no fallback de clique discente: {e_re}")

    # 3. Extrair dados do PDF se baixado
    if pdf_historico_path and os.path.exists(pdf_historico_path):
        parsed_pdf = parse_pdf_data(pdf_historico_path)
        for k, v in parsed_pdf.items():
            if v and not aluno_info.get(k):
                aluno_info[k] = v

    # 4. Extrair texto da página atual (se HTML)
    try:
        body_text = page.locator("body").inner_text()
        
        cpf_m = re.search(r"CPF:\s*([\d\.\-]+)", body_text, re.I)
        if cpf_m and not aluno_info.get("cpf"): aluno_info["cpf"] = cpf_m.group(1).strip()
        
        rg_m = re.search(r"RG:\s*([\d\.\-A-Za-z/]+)", body_text, re.I)
        if rg_m and not aluno_info.get("rg"): aluno_info["rg"] = rg_m.group(1).strip()
        
        nasc_m = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if nasc_m and not aluno_info.get("nascimento"): aluno_info["nascimento"] = nasc_m.group(1).strip()
        
        term_m = re.search(r"Término\s*(?:Previsto)?:\s*([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if term_m and not aluno_info.get("termino_previsto"): aluno_info["termino_previsto"] = term_m.group(1).strip()
        
        homol_m = re.search(r"Homologação\s*do\s*Título:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", body_text, re.I)
        if homol_m and not aluno_info.get("homologacao"): aluno_info["homologacao"] = homol_m.group(1).strip()
        
        orient_m = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\nDefesa|Defesa)", body_text, re.I | re.DOTALL)
        if orient_m and not aluno_info.get("orientador"): aluno_info["orientador"] = orient_m.group(1).replace("\n", " ").strip()
        
        l1_m = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", body_text, re.I)
        if l1_m and not aluno_info.get("lingua_1"): aluno_info["lingua_1"] = l1_m.group(1).strip()
        
        l2_m = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", body_text, re.I)
        if l2_m and not aluno_info.get("lingua_2"): aluno_info["lingua_2"] = l2_m.group(1).strip()
    except Exception as e_parse:
        print(f"Aviso na extração HTML: {e_parse}")

    return {
        "status": "success",
        "aluno_info": aluno_info,
        "pdf_historico": pdf_historico_path,
        "pdf_comprovante": pdf_comprovante_path
    }

def extract_candidate_details(login, senha, candidate, baixar_historico, baixar_comprovante, cached_driver=None):
    """Extrai detalhes do candidato no SIIU."""
    def _task(page):
        return _extract_page_logic(page, candidate, baixar_historico, baixar_comprovante)
    return _run_with_playwright_page(login, senha, _task)

def search_and_extract_student(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca e extrai os detalhes do discente em uma ÚNICA sessão do Playwright para economizar RAM."""
    def _task(page):
        search_res = _search_page_logic(page, query, programa, fallback_name)
        if search_res.get("status") == "error":
            return search_res
            
        candidates = search_res.get("candidates", [])
        if not candidates:
            return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}
            
        if len(candidates) == 1:
            ext_res = _extract_page_logic(page, candidates[0], True, True)
            return {"status": "success", "single": True, "details": ext_res}
        else:
            return {"status": "success", "single": False, "candidates": candidates}
            
    return _run_with_playwright_page(login, senha, _task)

