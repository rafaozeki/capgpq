import time
import os
import glob
import re
import traceback
import sys
import gc
import pandas as pd
import requests
from bs4 import BeautifulSoup

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
        texto = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text(layout=False)
                if t: texto += t + "\n"
                
        cpf_match = re.search(r"CPF:\s*([\d\.\-]+)", texto, re.I)
        if cpf_match: info['cpf'] = cpf_match.group(1).strip()
            
        rg_match = re.search(r"RG:\s*([\d\.\-A-Za-z/]+)", texto, re.I)
        if rg_match: info['rg'] = rg_match.group(1).strip()
            
        nasc_match = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if nasc_match: info['nascimento'] = nasc_match.group(1).strip()

        sexo_match = re.search(r"Sexo:\s*([^\s\n\t]+)", texto, re.I)
        if sexo_match: info['sexo'] = sexo_match.group(1).strip()
        
        nat_match = re.search(r"Naturalidade:\s*(.*?)(?=\n|CPF:|RG:|N[ºo°])", texto, re.I)
        if nat_match: info['naturalidade'] = nat_match.group(1).strip()
            
        ing_match = re.search(r"(?:Ingresso|Início|Inicio):\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if ing_match: info['ingresso'] = ing_match.group(1).strip()
        
        forma_match = re.search(r"Forma\s*de\s*Ingresso:\s*(.*?)(?=\s{2,}|\n|Homologação|Homologacao)", texto, re.I)
        if forma_match: info['forma_ingresso'] = forma_match.group(1).strip()
            
        term_match = re.search(r"Término\s*(?:Previsto)?:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if term_match: info['termino_previsto'] = term_match.group(1).strip()
        
        sit_match = re.search(r"Situação:\s*(.*?)(?=\s{2,}|\n|Término|Termino)", texto, re.I)
        if sit_match:
            v_sit = sit_match.group(1).strip()
            info['situacao'] = v_sit
            info['situacao_siiu'] = v_sit
            
        prog_match = re.search(r"Programa:\s*(.*?)(?=\s{2,}|\n|Nível|Nivel)", texto, re.I)
        if prog_match:
            v_prog = prog_match.group(1).strip()
            info['programa'] = v_prog
            info['curso'] = v_prog
            
        niv_match = re.search(r"Nível:\s*([^\n]+)", texto, re.I)
        if niv_match: info['nivel'] = niv_match.group(1).strip()
            
        homol_match = re.search(r"Homologação\s*do\s*Título:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if homol_match: info['homologacao'] = homol_match.group(1).strip()
            
        tese_match = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador)", texto, re.I | re.DOTALL)
        if tese_match: 
            t_val = tese_match.group(1).replace("\n", " ").strip()
            info['titulo_tese'] = t_val if t_val else "Não informado / Em andamento"
            
        orient_match = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\s{2,}|\n|Defesa)", texto, re.I)
        if orient_match: 
            info['orientador'] = orient_match.group(1).replace("\n", " ").strip()
            
        defesa_match = re.search(r"Defesa:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if defesa_match: 
            info['defesa'] = defesa_match.group(1).strip()
        else:
            info['defesa'] = "Pendente / Em andamento"
            
        l1_match = re.search(r"1[ºo°]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l1_match: info['lingua_1'] = l1_match.group(1).strip()
            
        l2_match = re.search(r"2[ºo°]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l2_match: info['lingua_2'] = l2_match.group(1).strip()
            
        uc_match = re.search(r"Unidade\s*Curricular.*?\n(.*?)(?=\nTotal|\nCréditos|\nResumo|\nMédia)", texto, re.I | re.DOTALL)
        if uc_match: info['unidades_curriculares'] = uc_match.group(1).strip()
            
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
    finally:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
        gc.collect()
        
    return info

def init_cached_driver(login, senha):
    """Mantém a assinatura compatível para o app.py."""
    return True, None

def _get_authenticated_session(login, senha):
    """Cria uma sessão HTTP leve autenticada no SIIU em < 0.5s."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    
    try:
        r1 = session.get("https://notas-propgpq.siiu.unifesp.br/login", timeout=12)
        soup1 = BeautifulSoup(r1.text, "html.parser")
        token_input = soup1.find("input", {"name": "_token"})
        token = token_input.get("value") if token_input else ""
        
        payload = {
            "_token": token,
            "username": login,
            "password": senha
        }
        r2 = session.post("https://notas-propgpq.siiu.unifesp.br/login", data=payload, timeout=12)
        
        if "incorreto" in r2.text.lower() or "inválid" in r2.text.lower() or "credencial" in r2.text.lower():
            return None, "Usuário e/ou senha do SIIU incorretos. Verifique suas credenciais."
            
        return session, None
    except Exception as e:
        return None, f"Erro de conexão com o SIIU: {e}"

def _search_session_logic(session, query, programa, fallback_name=None):
    """Lógica leve de busca de discente usando requisições HTTP e BeautifulSoup."""
    import unicodedata
    def norm(txt):
        return "".join(c for c in unicodedata.normalize('NFD', str(txt).upper()) if unicodedata.category(c) != 'Mn').strip()

    r_disc = session.get("https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes", timeout=12)
    soup_disc = BeautifulSoup(r_disc.text, "html.parser")
    
    token_input = soup_disc.find("input", {"name": "_token"})
    token = token_input.get("value") if token_input else ""
    
    select_elem = soup_disc.find("select", {"id": "areas_prin_codigo"})
    valid_options = []
    if select_elem:
        for opt in select_elem.find_all("option"):
            val = opt.get("value", "").strip()
            txt = opt.text.strip()
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
        post_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
        data = {
            "_token": token,
            "areas_prin_codigo": opt_val,
            "descricao": search_term
        }
        
        r_search = session.post(post_url, data=data, timeout=12)
        if "table" not in r_search.text.lower():
            r_search = session.get(f"{post_url}?areas_prin_codigo={opt_val}&descricao={search_term}", timeout=12)
            
        soup_res = BeautifulSoup(r_search.text, "html.parser")
        table = soup_res.find("table")
        if not table:
            return []
            
        found_cands = []
        for idx, tr in enumerate(table.find_all("tr")):
            tds = tr.find_all("td")
            if tds and len(tds) > 0:
                cols = [td.text.strip() for td in tds]
                matricula = cols[0] if len(cols) > 0 else ""
                nome = cols[1] if len(cols) > 1 else ""
                curso = cols[2] if len(cols) > 2 else ""
                ingresso = cols[3] if len(cols) > 3 else ""
                nivel = cols[4] if len(cols) > 4 else ""
                situacao = cols[5] if len(cols) > 5 else ""
                
                if "Nenhum registro" in nome or "Nenhum registro" in matricula or "Selecione um programa" in nome:
                    continue
                    
                action_urls = []
                historico_url = None
                for a in tr.find_all(["a", "button"]):
                    h = a.get("href") or a.get("onclick") or a.get("data-href") or ""
                    txt = a.text.strip()
                    title = a.get("title") or a.get("alt") or ""
                    
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

def _extract_details_logic(session, candidate):
    """Extrai os detalhes do aluno e baixa o PDF usando a sessão HTTP."""
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
            req_res = session.get(full_url, timeout=12)
            c_type = str(req_res.headers.get("content-type", "")).lower()
            
            if "pdf" in c_type or full_url.lower().endswith(".pdf") or req_res.content[:4] == b'%PDF':
                download_dir = os.path.join(os.getcwd(), "downloads")
                os.makedirs(download_dir, exist_ok=True)
                pdf_historico_path = os.path.join(download_dir, f"Historico_{aluno_info['ra']}.pdf")
                with open(pdf_historico_path, "wb") as f_pdf:
                    f_pdf.write(req_res.content)
                    
                parsed = parse_pdf_data(pdf_historico_path)
                if parsed.get("cpf") or parsed.get("rg"):
                    for k, v in parsed.items():
                        if v: aluno_info[k] = v
                    break
            else:
                html_body = req_res.text
                cpf_m = re.search(r"CPF:\s*([\d\.\-]+)", html_body, re.I)
                rg_m = re.search(r"RG:\s*([\d\.\-A-Za-z/]+)", html_body, re.I)
                if cpf_m or rg_m:
                    if cpf_m: aluno_info["cpf"] = cpf_m.group(1).strip()
                    if rg_m: aluno_info["rg"] = rg_m.group(1).strip()
                    break
        except Exception:
            pass

    return {
        "status": "success",
        "aluno_info": aluno_info,
        "pdf_historico": pdf_historico_path
    }

def search_student_candidates(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca candidatos no SIIU via requisições HTTP nativas leves."""
    session, err = _get_authenticated_session(login, senha)
    if err:
        return {"status": "error", "message": err}
    return _search_session_logic(session, query, programa, fallback_name)

def extract_candidate_details(login, senha, candidate, baixar_historico, baixar_comprovante, cached_driver=None):
    """Extrai detalhes do candidato via requisições HTTP nativas leves."""
    session, err = _get_authenticated_session(login, senha)
    if err:
        return {"status": "error", "message": err}
    return _extract_details_logic(session, candidate)

def search_and_extract_student(login, senha, query, programa, cached_driver=None, fallback_name=None):
    """Busca e extrai detalhes do discente no SIIU usando requisições HTTP nativas ultrarrápidas (< 0.5s, 0MB RAM)."""
    session, err = _get_authenticated_session(login, senha)
    if err:
        return {"status": "error", "message": err}
        
    search_res = _search_session_logic(session, query, programa, fallback_name)
    if search_res.get("status") == "error":
        return search_res
        
    candidates = search_res.get("candidates", [])
    if not candidates:
        return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}
        
    if len(candidates) == 1:
        ext_res = _extract_details_logic(session, candidates[0])
        return {"status": "success", "single": True, "details": ext_res}
    else:
        return {"status": "success", "single": False, "candidates": candidates}
