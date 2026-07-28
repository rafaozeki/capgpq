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

def parse_pdf_data(pdf_path):
    info = {}
    if not pdfplumber or not pdf_path or not os.path.exists(pdf_path):
        return info
        
    try:
        texto_raw = ""
        texto_layout = ""
        tables_text = ""
        tables_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t1 = page.extract_text(layout=False)
                if t1: texto_raw += t1 + "\n"
                
                t2 = page.extract_text(layout=True)
                if t2: texto_layout += t2 + "\n"
                
                try:
                    tables = page.extract_tables()
                    for tbl in tables:
                        if tbl:
                            tables_data.append(tbl)
                            for r in tbl:
                                if r:
                                    row_str = " | ".join(str(cell).strip() for cell in r if cell)
                                    tables_text += row_str + "\n"
                except Exception:
                    pass

        texto_combined = texto_raw + "\n" + texto_layout + "\n" + tables_text

        # 1. Varredura por Células de Tabelas (Key-Value)
        for tbl in tables_data:
            for r in tbl:
                if not r: continue
                for idx, cell in enumerate(r):
                    cell_str = str(cell).strip().upper()
                    if not cell_str: continue
                    
                    next_val = str(r[idx+1]).strip() if idx + 1 < len(r) and r[idx+1] else ""
                    
                    if ("CPF" in cell_str or "C.P.F" in cell_str) and next_val and not info.get("cpf"):
                        m = re.search(r"[\d\.\-]+", next_val)
                        if m: info["cpf"] = m.group(0)
                        
                    if ("RG" in cell_str or "RNE" in cell_str or "IDENTIDADE" in cell_str) and next_val and not info.get("rg"):
                        m = re.search(r"[\d\.\-A-Za-z/]+", next_val)
                        if m: info["rg"] = m.group(0)
                        
                    if ("NASCIMENTO" in cell_str or "NASC" in cell_str) and next_val and not info.get("nascimento"):
                        m = re.search(r"[\d]{2}/[\d]{2}/[\d]{4}", next_val)
                        if m: info["nascimento"] = m.group(0)

                    if "SEXO" in cell_str and next_val and not info.get("sexo"):
                        info["sexo"] = next_val

                    if "NATURALIDADE" in cell_str and next_val and not info.get("naturalidade"):
                        info["naturalidade"] = next_val

                    if "FORMA DE INGRESSO" in cell_str and next_val and not info.get("forma_ingresso"):
                        info["forma_ingresso"] = next_val

                    if ("TERMINO" in cell_str or "TÉRMINO" in cell_str or "CONCLUSÃO" in cell_str) and next_val and not info.get("termino_previsto"):
                        m = re.search(r"[\d]{2}/[\d]{2}/[\d]{4}", next_val)
                        if m: info["termino_previsto"] = m.group(0)

                    if "ORIENTADOR" in cell_str and next_val and not info.get("orientador"):
                        info["orientador"] = next_val.replace("\n", " ")

                    if "TÍTULO" in cell_str or "TITULO" in cell_str and next_val and not info.get("titulo_tese"):
                        info["titulo_tese"] = next_val.replace("\n", " ")

                    if "DEFESA" in cell_str and next_val and not info.get("defesa"):
                        m = re.search(r"[\d]{2}/[\d]{2}/[\d]{4}", next_val)
                        if m: info["defesa"] = m.group(0)

                    if "HOMOLOGAÇÃO" in cell_str or "HOMOLOGACAO" in cell_str and next_val and not info.get("homologacao"):
                        m = re.search(r"[\d]{2}/[\d]{2}/[\d]{4}", next_val)
                        if m: info["homologacao"] = m.group(0)

                    if "CRÉDITOS" in cell_str or "CREDITOS" in cell_str:
                        m_digits = re.findall(r"\d+", next_val)
                        if m_digits:
                            if "EXIGIDO" in cell_str or "NECESSÁRIO" in cell_str or "MINIMO" in cell_str:
                                info["creditos_necessarios"] = m_digits[0]
                            elif "TOTAL" in cell_str or "OBTIDO" in cell_str or "CURSADO" in cell_str:
                                info["creditos_total"] = m_digits[0]

        # 2. Regex de Fallback em Texto Combinado
        if not info.get('cpf'):
            cpf_match = re.search(r"(?:CPF|C\.P\.F\.)[\s:]*([\d\.\-]+)", texto_combined, re.I)
            if cpf_match:
                info['cpf'] = cpf_match.group(1).strip()
            else:
                cpf_raw = re.search(r"\b(\d{3}\.\d{3}\.\d{3}\-\d{2})\b", texto_combined)
                if cpf_raw: info['cpf'] = cpf_raw.group(1).strip()
            
        if not info.get('rg'):
            rg_match = re.search(r"(?:RG|RNE|Identidade)[\s:]*([\d\.\-A-Za-z/]+)", texto_combined, re.I)
            if rg_match: info['rg'] = rg_match.group(1).strip()
            
        if not info.get('nascimento'):
            nasc_match = re.search(r"(?:Nascimento|Nasc\.?)[\s:]*([\d]{2}/[\d]{2}/[\d]{4})", texto_combined, re.I)
            if nasc_match: info['nascimento'] = nasc_match.group(1).strip()

        if not info.get('sexo'):
            sexo_match = re.search(r"Sexo[\s:]*([^\s\n\t\|]+)", texto_combined, re.I)
            if sexo_match: info['sexo'] = sexo_match.group(1).strip()
        
        if not info.get('naturalidade'):
            nat_match = re.search(r"Naturalidade[\s:]*(.*?)(?=\n|CPF|RG|N[ºo°]|\||$)", texto_combined, re.I)
            if nat_match: info['naturalidade'] = nat_match.group(1).strip()
            
        if not info.get('ingresso'):
            ing_match = re.search(r"(?:Ingresso|Início|Inicio)[\s:]*([\d]{2}/[\d]{2}/[\d]{4})", texto_combined, re.I)
            if ing_match: info['ingresso'] = ing_match.group(1).strip()
        
        if not info.get('forma_ingresso'):
            forma_match = re.search(r"Forma\s*de\s*Ingresso[\s:]*(.*?)(?=\s{2,}|\n|Homologação|Homologacao|Término|Termino|\||$)", texto_combined, re.I)
            if forma_match: info['forma_ingresso'] = forma_match.group(1).strip()
            
        if not info.get('termino_previsto'):
            term_match = re.search(r"(?:Término|Termino|Conclusão|Conclusao)[\s:]*([\d]{2}/[\d]{2}/[\d]{4})", texto_combined, re.I)
            if term_match: info['termino_previsto'] = term_match.group(1).strip()
        
        if not info.get('situacao'):
            sit_match = re.search(r"Situação[\s:]*(.*?)(?=\s{2,}|\n|Término|Termino|\||$)", texto_combined, re.I)
            if sit_match:
                v_sit = sit_match.group(1).strip()
                info['situacao'] = v_sit
                info['situacao_siiu'] = v_sit
            
        if not info.get('programa'):
            prog_match = re.search(r"Programa[\s:]*(.*?)(?=\s{2,}|\n|Nível|Nivel|\||$)", texto_combined, re.I)
            if prog_match:
                v_prog = prog_match.group(1).strip()
                info['programa'] = v_prog
                info['curso'] = v_prog
            
        if not info.get('nivel'):
            niv_match = re.search(r"Nível[\s:]*([^\n\|]+)", texto_combined, re.I)
            if niv_match: info['nivel'] = niv_match.group(1).strip()
            
        if not info.get('homologacao'):
            homol_match = re.search(r"Homologação\s*do\s*Título[\s:]*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto_combined, re.I)
            if homol_match: info['homologacao'] = homol_match.group(1).strip()
            
        if not info.get('titulo_tese'):
            tese_match = re.search(r"(?:Título\s*da\s*Tese|Título\s*da\s*Dissertação)[\s:]*(.*?)(?=\nOrientador|Orientador|\||$)", texto_combined, re.I | re.DOTALL)
            if tese_match: 
                t_val = tese_match.group(1).replace("\n", " ").strip()
                info['titulo_tese'] = t_val if t_val else "Não informado / Em andamento"
            
        if not info.get('orientador'):
            orient_match = re.search(r"Orientador[\(a\)]*[\s:]*(.*?)(?=\s{2,}|\n|Defesa|\||$)", texto_combined, re.I)
            if orient_match: 
                info['orientador'] = orient_match.group(1).replace("\n", " ").strip()
            
        if not info.get('defesa'):
            defesa_match = re.search(r"Defesa[\s:]*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto_combined, re.I)
            if defesa_match: 
                info['defesa'] = defesa_match.group(1).strip()

        if not info.get('lingua_1'):
            l1_match = re.search(r"1[ºo°]\s*Língua\s*Estrangeira[\s:]*([A-Za-zÀ-ÿ\s]+)", texto_combined, re.I)
            if l1_match: info['lingua_1'] = l1_match.group(1).strip()
            
        if not info.get('lingua_2'):
            l2_match = re.search(r"2[ºo°]\s*Língua\s*Estrangeira[\s:]*([A-Za-zÀ-ÿ\s]+)", texto_combined, re.I)
            if l2_match: info['lingua_2'] = l2_match.group(1).strip()

        if not info.get('creditos_total'):
            cred_t_match = re.search(r"(?:Total\s*de\s*Créditos|Créditos\s*Obtidos)[\s:]*([\d]+)", texto_combined, re.I)
            if cred_t_match: info['creditos_total'] = cred_t_match.group(1).strip()

        if not info.get('creditos_necessarios'):
            cred_n_match = re.search(r"(?:Créditos\s*Exigidos|Créditos\s*Necessários)[\s:]*([\d]+)", texto_combined, re.I)
            if cred_n_match: info['creditos_necessarios'] = cred_n_match.group(1).strip()
            
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
    finally:
        gc.collect()
        
    return info

def init_cached_driver(login, senha):
    """Mantém a assinatura compatível para o app.py."""
    return True, None

def _run_with_playwright_page(login, senha, task_fn):
    """Executa a task_fn(page) em um contexto isolado e estável do Playwright com 64MB V8 limit."""
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
                "--disk-cache-size=1",
                "--media-cache-size=1",
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

    for target_url in urls_to_try:
        if not target_url or target_url == "#":
            continue
            
        full_url = target_url if target_url.startswith("http") else f"https://notas-propgpq.siiu.unifesp.br{target_url if target_url.startswith('/') else '/' + target_url}"
        
        try:
            req_res = page.request.get(full_url, timeout=10000)
            c_type = str(req_res.headers.get("content-type", "")).lower()
            body_bytes = req_res.body()
            
            if "pdf" in c_type or full_url.lower().endswith(".pdf") or body_bytes[:4] == b'%PDF':
                download_dir = os.path.join(os.getcwd(), "downloads")
                os.makedirs(download_dir, exist_ok=True)
                pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
                with open(pdf_historico_path, "wb") as f_pdf:
                    f_pdf.write(body_bytes)
                    
                parsed = parse_pdf_data(pdf_historico_path)
                if parsed:
                    for k, v in parsed.items():
                        if v: aluno_info[k] = v
                    break
            else:
                html_body = req_res.text()
                pdf_links = []
                
                # 1. Procurar secretaria-imprimir (Histórico Acadêmico)
                m_hist = re.findall(r'href=["\']([^"\']*secretaria-imprimir[^"\']*)["\']', html_body, re.I)
                for h in m_hist:
                    pdf_links.append((h, True))
                    
                # 2. Procurar comprovante-matricula (Comprovante)
                m_comp = re.findall(r'href=["\']([^"\']*comprovante-matricula[^"\']*)["\']', html_body, re.I)
                for h in m_comp:
                    pdf_links.append((h, False))
                    
                # 3. Procurar quaisquer links de PDF/imprimir
                m_any = re.findall(r'href=["\']([^"\']*(?:imprimir|pdf|historico)[^"\']*)["\']', html_body, re.I)
                for h in m_any:
                    if not any(h == pl[0] for pl in pdf_links) and h != full_url:
                        pdf_links.append((h, True))
                        
                for pdf_link, is_hist in pdf_links:
                    sub_url = pdf_link if pdf_link.startswith("http") else f"https://notas-propgpq.siiu.unifesp.br{pdf_link if pdf_link.startswith('/') else '/' + pdf_link}"
                    try:
                        sub_res = page.request.get(sub_url, timeout=10000)
                        sub_bytes = sub_res.body()
                        sub_ctype = str(sub_res.headers.get("content-type", "")).lower()
                        
                        if "pdf" in sub_ctype or sub_bytes[:4] == b'%PDF':
                            download_dir = os.path.join(os.getcwd(), "downloads")
                            os.makedirs(download_dir, exist_ok=True)
                            
                            fname = f"Historico_{aluno_info['ra']}.pdf" if is_hist else f"Comprovante_{aluno_info['ra']}.pdf"
                            out_p = os.path.join(download_dir, fname)
                            
                            with open(out_p, "wb") as f_pdf:
                                f_pdf.write(sub_bytes)
                                
                            if is_hist and not pdf_historico_path:
                                pdf_historico_path = out_p
                            elif not is_hist and not pdf_comprovante_path:
                                pdf_comprovante_path = out_p
                                
                            parsed = parse_pdf_data(out_p)
                            if parsed:
                                for k, v in parsed.items():
                                    if v: aluno_info[k] = v
                    except Exception as e_sub:
                        print(f"Erro ao baixar link de PDF sub-HTML {pdf_link}: {e_sub}")
                        
                if aluno_info.get("cpf") or aluno_info.get("rg"):
                    break
        except Exception as e_url:
            print(f"Erro ao processar URL {full_url}: {e_url}")

    if not aluno_info.get("cpf") and not aluno_info.get("rg"):
        try:
            rows = page.locator("table tbody tr").all()
            if rows:
                row = rows[0]
                clickables = row.locator("td:last-child a, td:last-child button, a, button, [onclick]").all()
                
                for click_target in clickables:
                    close_sweetalert_overlays(page)
                    try:
                        with page.expect_download(timeout=2500) as dl_info:
                            click_target.click(force=True)
                        dl = dl_info.value
                        download_dir = os.path.join(os.getcwd(), "downloads")
                        os.makedirs(download_dir, exist_ok=True)
                        pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
                        dl.save_as(pdf_historico_path)
                        if os.path.exists(pdf_historico_path):
                            parsed = parse_pdf_data(pdf_historico_path)
                            if parsed:
                                for k, v in parsed.items():
                                    if v: aluno_info[k] = v
                                break
                    except Exception:
                        pass
        except Exception as e_re:
            print(f"Aviso no fallback de clique discente: {e_re}")

    return {
        "status": "success",
        "aluno_info": aluno_info,
        "pdf_historico": pdf_historico_path,
        "pdf_comprovante": pdf_comprovante_path
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
            return {"status": "success", "single": True, "details": ext_res}
        else:
            return {"status": "success", "single": False, "candidates": candidates}
            
    return _run_with_playwright_page(login, senha, _task)
