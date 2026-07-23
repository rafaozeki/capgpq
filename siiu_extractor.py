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
import time
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
            texto = "\\n".join(page.extract_text() or "" for page in pdf.pages)
            
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

def extract_student_data(login, senha, query, programa, baixar_historico=False, baixar_comprovante=False):
    """
    Executa a extração de dados do SIIU via Selenium.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Roda em modo invisível
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configura pasta temporária de downloads
    download_dir = os.path.join(os.getcwd(), "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Limpa downloads antigos
    for f in glob.glob(os.path.join(download_dir, "*.pdf")):
        try: os.remove(f)
        except: pass
        
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Inicializa o driver
    try:
        if sys.platform.startswith('linux'):
            # No Streamlit Cloud (Linux), usa o chromium instalado via apt-get
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Localmente (Windows/Mac), usa o webdriver_manager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        return {"status": "error", "message": f"Erro ao iniciar o Chrome/Selenium: {str(e)}"}
        
    try:
        # 1. Navegar diretamente para a página alvo (Isso forçará o redirecionamento para o Login caso deslogado)
        target_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
        driver.get(target_url)
        time.sleep(3)
        
        # 2. Verifica se foi redirecionado para login e faz o login
        if "login" in driver.current_url.lower():
            try:
                # O login da UNIFESP usa um form padrão. O botão tem texto "Entrar".
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' or contains(@name, 'login') or contains(@id, 'usuario')]"))
                )
                password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                
                username_field.clear()
                username_field.send_keys(login)
                
                password_field.clear()
                password_field.send_keys(senha)
                
                # Procura o botão de entrar (pelo texto "Entrar" que vimos no log)
                btn_entrar = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar') or contains(@value, 'Entrar') or contains(., 'Entrar')]")
                driver.execute_script("arguments[0].click();", btn_entrar)
                
                # Aguarda até que a URL volte para a página alvo (login concluído com sucesso)
                WebDriverWait(driver, 20).until(
                    lambda d: "login" not in d.current_url.lower()
                )
                time.sleep(2) # Pequena pausa após o carregamento
            except Exception as e:
                page_text = driver.find_element(By.TAG_NAME, "body").text[:200] if driver.find_elements(By.TAG_NAME, "body") else ""
                return {"status": "error", "message": f"Falha ao realizar login. URL: {driver.current_url}. Body: {page_text}. Erro: {e}"}

        # 3. Preencher os campos de busca
        try:
            # Aguarda a tabela/campos carregarem
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "areas_prin_codigo"))
            )
            
            # Mapeamento especial para Pós-Doutorado
            if programa == "Pós-Doutorado":
                programa_busca = "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS"
            else:
                programa_busca = programa

            if programa_busca != "Todos os Programas":
                select_programa = Select(driver.find_element(By.ID, "areas_prin_codigo"))
                # Seleciona pelo texto exato que recebemos do usuário
                selected = False
                # Tenta correspondência exata primeiro (ignorando espaços extras)
                for option in select_programa.options:
                    if programa_busca.upper() == option.text.strip().upper():
                        select_programa.select_by_visible_text(option.text)
                        selected = True
                        break
                        
                # Se não achou exato, tenta parcial
                if not selected:
                    for option in select_programa.options:
                        # Evitar casar 'Letras' com 'Filosofia, Letras e Ciências Humanas' se houver outro mais específico
                        if programa_busca.upper() in option.text.upper():
                            select_programa.select_by_visible_text(option.text)
                            selected = True
                            break
                            
                if selected:
                    # O site recarrega a página ao selecionar o programa!
                    time.sleep(3)
                    # Re-aguarda o elemento após o refresh
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "areas_prin_codigo"))
                    )
            
            # Buscaremos o input de busca (nome provável: descricao)
            search_input = driver.find_element(By.XPATH, "//input[@name='descricao' or @id='descricao' or contains(@placeholder, 'Nome') or @type='text']")
            search_input.clear()
            search_input.send_keys(query)
            
            # Clica em Pesquisar (buscando o botão pelo texto)
            btn_pesquisar = driver.find_element(By.XPATH, "//button[contains(text(), 'Pesquisar') or contains(., 'Pesquisar')]")
            driver.execute_script("arguments[0].click();", btn_pesquisar)
            
            # Aguarda a tabela carregar
            time.sleep(4)
        except Exception as e:
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text[:400]
            except:
                page_text = "N/A"
            return {"status": "error", "message": f"Falha ao preencher a busca na página de discentes. URL: {driver.current_url}. Pagina: {page_text}. Erro: {e}"}
            
        # 4. Extrair resultados
        try:
            # Tenta raspar a tabela que aparece
            # Pelo log anterior, as colunas são: Matrícula, Nome, Curso, Ingresso, Nível, Situação
            table_rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            
            if not table_rows or len(table_rows) == 0:
                 return {"status": "error", "message": "Nenhum aluno encontrado ou a tabela demorou muito para carregar."}
                 
            # Extrai o primeiro resultado encontrado
            first_row = table_rows[0]
            cols = first_row.find_elements(By.TAG_NAME, "td")
            
            if len(cols) > 0:
                matricula = cols[0].text.strip() if len(cols) > 0 else ""
                nome = cols[1].text.strip() if len(cols) > 1 else ""
                curso = cols[2].text.strip() if len(cols) > 2 else ""
                ingresso = cols[3].text.strip() if len(cols) > 3 else ""
                nivel = cols[4].text.strip() if len(cols) > 4 else ""
                situacao = cols[5].text.strip() if len(cols) > 5 else ""
            else:
                return {"status": "error", "message": "A tabela retornada está vazia."}
                
            # Extrair o link do botão "Abrir Histórico" na mesma linha
            try:
                historico_btn = first_row.find_element(By.XPATH, ".//a[contains(@data-original-title, 'Histórico') or contains(@href, 'historico')]")
                historico_url = historico_btn.get_attribute("href")
            except:
                historico_url = None
                    
            if not historico_url:
                try:
                    debug_row_html = first_row.get_attribute("outerHTML")
                except:
                    debug_row_html = "Erro ao pegar outerHTML"
                
        except Exception as e:
            return {"status": "error", "message": f"Falha ao extrair dados da tabela. Erro: {e}"}

        # 5. Navegar para a página do Histórico e Baixar PDFs
        historico_dados = []
        html_info = {}
        pdf_historico_path = None
        pdf_comprovante_path = None
        
        if historico_url:
            try:
                driver.get(historico_url)
                time.sleep(3)
                
                # Tentar extrair uma tabela de resumo do histórico
                # Vamos pegar todas as tabelas e extrair a primeira que parecer ter disciplinas
                try:
                    tabelas = driver.find_elements(By.TAG_NAME, "table")
                    if tabelas:
                        # Extrai a primeira tabela como dicionário (forma simplificada)
                        rows = tabelas[0].find_elements(By.TAG_NAME, "tr")
                        for r in rows[1:]: # Ignora cabeçalho
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
                    pass # Se falhar a tabela, não impede o download
                    
                # Extração baseada no texto completo da página web (como fazemos no PDF)
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    prorr_match = re.search(r"Prorrogação:\s*([^\n]+)", page_text, re.I)
                    if prorr_match: html_info['prorrogacao'] = prorr_match.group(1).strip()
                        
                    ano_match = re.search(r"Ano:\s*([^\n]+)", page_text, re.I)
                    if ano_match: html_info['ano_tese'] = ano_match.group(1).strip()
                        
                    # Aqui podemos ter cuidado, pois 'Situação:' pode casar com a situação do aluno.
                    # Mas vamos tentar buscar a última situação da página ou a que vem perto da banca
                    sit_match = re.search(r"Situação(?:\s*da\s*Tese)?:\s*([^\n]+)", page_text, re.I)
                    if sit_match: html_info['situacao_tese'] = sit_match.group(1).strip()
                        
                    membros_match = re.search(r"Membros\s*da\s*banca.*?(?:\nTipo de participação\n)?(.*?)\n(?:Idiomas|Total de créditos|Para a soma)", page_text, re.I | re.DOTALL)
                    if membros_match:
                        banca_raw = membros_match.group(1).strip()
                        html_info['membros_banca'] = banca_raw.replace("\n", ", ")
                        
                    tese_match = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador|\nAno|Ano)", page_text, re.I | re.DOTALL)
                    if tese_match: html_info['titulo_tese'] = tese_match.group(1).replace('\n', ' ').strip()
                        
                    orientador_match = re.search(r"Orientador(?:a)?.*?\nNome:\s*([^\n]+)", page_text, re.I)
                    if orientador_match: html_info['orientador'] = orientador_match.group(1).strip()
                    
                    l1_match = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([^\n]+)", page_text, re.I)
                    if l1_match: html_info['lingua_1'] = l1_match.group(1).strip()
                    
                    l2_match = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([^\n]+)", page_text, re.I)
                    if l2_match: html_info['lingua_2'] = l2_match.group(1).strip()
                    
                    ct_match = re.search(r"Total\s*de\s*créditos\s*obtidos:\s*(\d+)", page_text, re.I)
                    if ct_match: html_info['creditos_total'] = ct_match.group(1).strip()
                except:
                    pass
                
                
                # Download Histórico
                if baixar_historico:
                    try:
                        btn_imprimir = driver.find_element(By.XPATH, "//a[contains(@href, 'secretaria-imprimir')]")
                        href_imprimir = btn_imprimir.get_attribute("href")
                        # Se abrir em nova aba, podemos simplesmente navegar para lá para forçar o download
                        driver.get(href_imprimir)
                        time.sleep(5) # Aguarda download
                        
                        # Pega o arquivo mais recente na pasta
                        pdfs = glob.glob(os.path.join(download_dir, "*.pdf"))
                        if pdfs:
                            pdf_historico_path = max(pdfs, key=os.path.getctime)
                    except Exception as e:
                        pass # Falha ao baixar
                        
                # Download Comprovante
                if baixar_comprovante:
                    try:
                        btn_comprov = driver.find_element(By.XPATH, "//a[contains(@href, 'comprovante-matricula')]")
                        href_comprov = btn_comprov.get_attribute("href")
                        driver.get(href_comprov)
                        time.sleep(5) # Aguarda download
                        
                        pdfs = glob.glob(os.path.join(download_dir, "*.pdf"))
                        if pdfs:
                            # Filtra para não pegar o mesmo do histórico
                            pdfs = [p for p in pdfs if p != pdf_historico_path]
                            if pdfs:
                                pdf_comprovante_path = max(pdfs, key=os.path.getctime)
                            elif not pdf_historico_path and pdfs:
                                pdf_comprovante_path = max(pdfs, key=os.path.getctime)
                    except Exception as e:
                        pass
            except Exception as e:
                # O erro no acesso ao histórico não deve apagar os dados básicos
                pass

        # Faz o parse dos PDFs gerados se existirem
        pdf_info = {}
        if pdf_historico_path:
            pdf_info.update(parse_pdf_data(pdf_historico_path))
        if pdf_comprovante_path and not pdf_info: # Se falhou histórico, tenta do comprovante
            pdf_info.update(parse_pdf_data(pdf_comprovante_path))
            
        pdf_info.update(html_info)
            
        aluno_final = {
            "nome": nome,
            "ra": matricula,
            "programa": curso,
            "situacao_siiu": situacao,
            "ingresso": pdf_info.get("ingresso_data", ingresso), # Usa a data se achou no PDF
            "nivel": nivel
        }
        aluno_final.update(pdf_info)

        debug_text_final = page_text[:2000] if 'page_text' in locals() else (debug_row_html if 'debug_row_html' in locals() else "Nenhum page_text capturado")
        
        return {
            "status": "success",
            "message": "Dados extraídos com sucesso da tabela de busca e do PDF.",
            "aluno_info": aluno_final,
            "historico": historico_dados,
            "pdf_historico": pdf_historico_path,
            "pdf_comprovante": pdf_comprovante_path,
            "debug_url": historico_url,
            "debug_text": debug_text_final
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        return {"status": "error", "message": f"Erro crítico na execução do robô: {str(e)}\n{error_trace}"}
    finally:
        driver.quit()
