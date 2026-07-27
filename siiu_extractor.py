import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import traceback
import sys
import os
import glob
import re
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

def parse_pdf_data(pdf_path):
    info = {}
    if not pdfplumber or not pdf_path or not os.path.exists(pdf_path):
        return info
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
            
        # Tentar extrair Dados Pessoais
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
            
        # Tentar extrair Dados Acadêmicos
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
            
        # Tentar extrair as unidades curriculares pegando o bloco de texto
        uc_match = re.search(r"Unidade\s*Curricular.*?\n(.*?)(?=\nTotal|\nCréditos|\nResumo|\nMédia)", texto, re.I | re.DOTALL)
        if uc_match: info['unidades_curriculares'] = uc_match.group(1).strip()
            
        ct_match = re.search(r"Total\s*de\s*Créditos:\s*(\d+)", texto, re.I)
        if ct_match: info['creditos_total'] = ct_match.group(1).strip()
            
        cn_match = re.search(r"Créditos\s*Necessários\s*para\s*o\s*[A-Z]+:\s*(\d+)", texto, re.I)
        if cn_match: info['creditos_necessarios'] = cn_match.group(1).strip()
            
        # Observações
        obs_match = re.search(r"Obs(?:ervações)?:\s*([^\n]+)", texto, re.I)
        if obs_match: info['observacoes'] = obs_match.group(1).strip()
            
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        
    return info

def init_cached_driver(login, senha):
    """
    Inicializa o Chrome e faz o login, retornando o driver pronto para uso.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Roda em modo invisível
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.page_load_strategy = 'eager' # Não espera carregar scripts e CSS
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Desativa imagens
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    
    download_dir = os.path.join(os.getcwd(), "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        if sys.platform.startswith('linux'):
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
        target_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
        driver.get(target_url)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if "login" in driver.current_url.lower():
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' or contains(@name, 'login') or contains(@id, 'usuario')]"))
            )
            password_field = driver.find_element(By.XPATH, "//input[@type='password']")
            
            username_field.clear()
            username_field.send_keys(login)
            
            password_field.clear()
            password_field.send_keys(senha)
            
            btn_entrar = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar') or contains(@value, 'Entrar') or contains(., 'Entrar')]")
            driver.execute_script("arguments[0].click();", btn_entrar)
            
            WebDriverWait(driver, 20).until(
                lambda d: "login" not in d.current_url.lower()
            )
            
        return driver, None
    except Exception as e:
        return None, f"Erro ao iniciar Chrome ou logar: {e}"

def search_student_candidates(login, senha, query, programa, cached_driver=None):
    """
    Realiza a pesquisa de discente no SIIU e retorna a lista de TODOS os candidatos/vínculos encontrados.
    """
    driver = cached_driver
    if not driver:
        driver, err = init_cached_driver(login, senha)
        if not driver:
            return {"status": "error", "message": err}

    try:
        target_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
        if driver.current_url != target_url:
            driver.get(target_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "areas_prin_codigo"))
        )
        
        select_programa = Select(driver.find_element(By.ID, "areas_prin_codigo"))
        selected = False
        
        if programa == "Pós-Doutorado":
            programa_busca = "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS"
        else:
            programa_busca = programa or ""

        import unicodedata
        def norm(txt):
            return "".join(c for c in unicodedata.normalize('NFD', str(txt).upper()) if unicodedata.category(c) != 'Mn').strip()

        p_norm = norm(programa_busca)
        
        if p_norm and p_norm != "TODOS OS PROGRAMAS":
            # 1. Tenta correspondência exata
            for option in select_programa.options:
                if norm(option.text) == p_norm:
                    select_programa.select_by_visible_text(option.text)
                    selected = True
                    break
                    
            # 2. Tenta correspondência parcial
            if not selected:
                candidates_opt = []
                for option in select_programa.options:
                    opt_norm = norm(option.text)
                    if p_norm in opt_norm:
                        candidates_opt.append(option)
                if candidates_opt:
                    best_opt = min(candidates_opt, key=lambda o: len(o.text))
                    select_programa.select_by_visible_text(best_opt.text)
                    selected = True

        # Se ainda não selecionou nada (ex: "Todos os Programas" ou não encontrou), seleciona o primeiro programa válido (índice 1)
        # para que o SIIU não rejeite o formulário dizendo "Selecione um programa para iniciar a sua pesquisa"
        if not selected:
            for option in select_programa.options:
                val = option.get_attribute("value")
                txt = option.text.strip()
                if val and val != "0" and txt and "SELECIONE" not in norm(txt):
                    select_programa.select_by_visible_text(option.text)
                    selected = True
                    break

        if selected:
            time.sleep(1)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "areas_prin_codigo"))
            )
        
        search_input = driver.find_element(By.XPATH, "//input[@name='descricao' or @id='descricao' or contains(@placeholder, 'Nome') or @type='text']")
        search_input.clear()
        search_input.send_keys(query)
        
        btn_pesquisar = driver.find_element(By.XPATH, "//button[contains(text(), 'Pesquisar') or contains(., 'Pesquisar')]")
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'historico/')] | //td[contains(text(), 'Nenhum')]"))
            )
        except:
            time.sleep(2)

        table_rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        if not table_rows or len(table_rows) == 0:
            return {"status": "error", "message": "Nenhum aluno encontrado ou a tabela demorou muito para carregar."}

        candidates = []
        for idx, row in enumerate(table_rows):
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 0:
                matricula = cols[0].text.strip() if len(cols) > 0 else ""
                nome = cols[1].text.strip() if len(cols) > 1 else ""
                curso = cols[2].text.strip() if len(cols) > 2 else ""
                ingresso = cols[3].text.strip() if len(cols) > 3 else ""
                nivel = cols[4].text.strip() if len(cols) > 4 else ""
                situacao = cols[5].text.strip() if len(cols) > 5 else ""
                
                if "Nenhum registro" in nome or "Nenhum registro" in matricula:
                    continue

                try:
                    historico_btn = row.find_element(By.XPATH, ".//a[contains(@data-original-title, 'Histórico') or contains(@href, 'historico')]")
                    historico_url = historico_btn.get_attribute("href")
                except:
                    historico_url = None

                candidates.append({
                    "id": idx,
                    "matricula": matricula,
                    "nome": nome,
                    "curso": curso,
                    "ingresso": ingresso,
                    "nivel": nivel,
                    "situacao": situacao,
                    "historico_url": historico_url
                })

        if not candidates:
            return {"status": "error", "message": "Nenhum aluno encontrado para os critérios informados."}

        return {
            "status": "success",
            "candidates": candidates
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        return {"status": "error", "message": f"Erro crítico na busca: {str(e)}\n{error_trace}"}

def extract_candidate_details(login, senha, candidate, baixar_historico=False, baixar_comprovante=False, cached_driver=None):
    """
    Navega até o histórico de um candidato específico e extrai seus dados completos e PDFs.
    """
    download_dir = os.path.join(os.getcwd(), "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    for f in glob.glob(os.path.join(download_dir, "*.pdf")):
        try: os.remove(f)
        except: pass
        
    driver = cached_driver
    if not driver:
        driver, err = init_cached_driver(login, senha)
        if not driver:
            return {"status": "error", "message": err}

    try:
        historico_url = candidate.get("historico_url")
        matricula = candidate.get("matricula", "")
        nome = candidate.get("nome", "")
        curso = candidate.get("curso", "")
        ingresso = candidate.get("ingresso", "")
        nivel = candidate.get("nivel", "")
        situacao = candidate.get("situacao", "")

        historico_dados = []
        html_info = {}
        pdf_historico_path = None
        pdf_comprovante_path = None
        
        if historico_url:
            try:
                driver.get(historico_url)
                time.sleep(3)
                
                try:
                    tabelas = driver.find_elements(By.TAG_NAME, "table")
                    if tabelas:
                        rows = tabelas[0].find_elements(By.TAG_NAME, "tr")
                        for r in rows[1:]:
                            tds = r.find_elements(By.TAG_NAME, "td")
                            if len(tds) >= 5:
                                historico_dados.append({
                                    "Unidade Curricular": tds[0].text.strip(),
                                    "Período": tds[1].text.strip(),
                                    "Freq.(%)": tds[2].text.strip(),
                                    "Conceito": tds[3].text.strip(),
                                    "Créditos": tds[4].text.strip()
                                })
                except:
                    pass
                    
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    prorr_match = re.search(r"Prorrogação:\s*([^\n]+)", page_text, re.I)
                    if prorr_match: html_info['prorrogacao'] = prorr_match.group(1).strip()
                        
                    ano_match = re.search(r"Ano:\s*([^\n]+)", page_text, re.I)
                    if ano_match: html_info['ano_tese'] = ano_match.group(1).strip()
                        
                    sit_match = re.search(r"Situação(?:\s*da\s*Tese)?:\s*([^\n]+)", page_text, re.I)
                    if sit_match: html_info['situacao_tese'] = sit_match.group(1).strip()
                        
                    membros_match = re.search(r"Membros\s*da\s*banca.*?(?:\nTipo de participação\n)?(.*?)\n(?:Idiomas|Total de créditos|Para a soma)", page_text, re.I | re.DOTALL)
                    if membros_match:
                        banca_raw = membros_match.group(1).strip()
                        html_info['membros_banca'] = banca_raw.replace("\n", ", ")
                        
                    tese_match = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador|\nAno|Ano)", page_text, re.I | re.DOTALL)
                    if tese_match: html_info['titulo_tese'] = tese_match.group(1).replace('\n', ' ').strip()
                        
                    orientador_match = re.search(r"Orientador(?:a)?.*?\nNome:\s*([^\n]+)", page_text, re.I | re.DOTALL)
                    if orientador_match: html_info['orientador'] = orientador_match.group(1).strip()
                    
                    l1_match = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([^\n]+)", page_text, re.I)
                    if l1_match: html_info['lingua_1'] = l1_match.group(1).strip()
                    
                    l2_match = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([^\n]+)", page_text, re.I)
                    if l2_match: html_info['lingua_2'] = l2_match.group(1).strip()
                    
                    ct_match = re.search(r"Total\s*de\s*créditos\s*obtidos:\s*(\d+)", page_text, re.I)
                    if ct_match: html_info['creditos_total'] = ct_match.group(1).strip()
                except:
                    pass
                
                def esperar_download_concluir(pasta, tempo_maximo=15, arquivos_ignorados=[]):
                    tempo_inicial = time.time()
                    while time.time() - tempo_inicial < tempo_maximo:
                        pdfs_atuais = glob.glob(os.path.join(pasta, "*.pdf"))
                        pdfs_novos = [p for p in pdfs_atuais if p not in arquivos_ignorados]
                        
                        if pdfs_novos:
                            arquivos_incompletos = glob.glob(os.path.join(pasta, "*.crdownload"))
                            if not arquivos_incompletos:
                                return max(pdfs_novos, key=os.path.getctime)
                        
                        time.sleep(0.5)
                    return None
                
                pdfs_antigos = glob.glob(os.path.join(download_dir, "*.pdf"))
                
                if baixar_historico:
                    try:
                        btn_imprimir = driver.find_element(By.XPATH, "//a[contains(@href, 'secretaria-imprimir')]")
                        href_imprimir = btn_imprimir.get_attribute("href")
                        driver.get(href_imprimir)
                        
                        pdf_historico_path = esperar_download_concluir(download_dir, tempo_maximo=15, arquivos_ignorados=pdfs_antigos)
                        if pdf_historico_path:
                            pdfs_antigos.append(pdf_historico_path)
                    except Exception as e:
                        pass
                        
                if baixar_comprovante:
                    try:
                        btn_comprov = driver.find_element(By.XPATH, "//a[contains(@href, 'comprovante-matricula')]")
                        href_comprov = btn_comprov.get_attribute("href")
                        driver.get(href_comprov)
                        
                        pdf_comprovante_path = esperar_download_concluir(download_dir, tempo_maximo=15, arquivos_ignorados=pdfs_antigos)
                    except Exception as e:
                        pass
            except Exception as e:
                pass

        pdf_info = {}
        if pdf_historico_path:
            pdf_info.update(parse_pdf_data(pdf_historico_path))
        if pdf_comprovante_path and not pdf_info:
            pdf_info.update(parse_pdf_data(pdf_comprovante_path))
            
        pdf_info.update(html_info)
            
        aluno_final = {
            "nome": nome,
            "ra": matricula,
            "programa": curso,
            "situacao_siiu": situacao,
            "ingresso": pdf_info.get("ingresso_data", ingresso),
            "nivel": nivel
        }
        aluno_final.update(pdf_info)

        debug_text_final = page_text[:2000] if 'page_text' in locals() else "Nenhum page_text capturado"
        
        return {
            "status": "success",
            "message": "Dados extraídos com sucesso do candidato.",
            "aluno_info": aluno_final,
            "historico": historico_dados,
            "pdf_historico": pdf_historico_path,
            "pdf_comprovante": pdf_comprovante_path,
            "debug_url": historico_url,
            "debug_text": debug_text_final
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        return {"status": "error", "message": f"Erro crítico na extração do candidato: {str(e)}\n{error_trace}"}
    finally:
        if not cached_driver and driver:
            try: driver.quit()
            except: pass

def extract_student_data(login, senha, query, programa, baixar_historico=False, baixar_comprovante=False, cached_driver=None):
    """
    Função legada: busca candidatos e extrai o primeiro por padrão.
    """
    res = search_student_candidates(login, senha, query, programa, cached_driver=cached_driver)
    if res.get("status") == "error":
        return res
    candidates = res.get("candidates", [])
    if not candidates:
        return {"status": "error", "message": "Nenhum aluno encontrado."}
    return extract_candidate_details(login, senha, candidates[0], baixar_historico=baixar_historico, baixar_comprovante=baixar_comprovante, cached_driver=cached_driver)
