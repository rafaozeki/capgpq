import os
import sys
import time
import glob
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

def get_siiu_session(login, senha):
    """
    Usa Selenium apenas para logar e retorna um requests.Session autenticado.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    
    try:
        if sys.platform.startswith('linux'):
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        return None, f"Erro ao iniciar Chrome: {e}"
        
    try:
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
            
        # Extrair cookies para o requests
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            
        driver.quit()
        return session, None
    except Exception as e:
        driver.quit()
        return None, f"Falha no login híbrido: {e}"

def parse_pdf_data(pdf_path):
    info = {}
    if not pdfplumber or not pdf_path or not os.path.exists(pdf_path):
        return info
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t: texto += t + "\n"
            
        sexo_match = re.search(r"Sexo:\s*([A-Za-z]+)", texto, re.I)
        if sexo_match: info['sexo'] = sexo_match.group(1).strip()
            
        cpf_match = re.search(r"CPF:\s*([\d\.\-]+)", texto, re.I)
        if cpf_match: info['cpf'] = cpf_match.group(1).strip()
            
        nasc_match = re.search(r"Nascimento:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if nasc_match: info['nascimento'] = nasc_match.group(1).strip()
            
        nat_match = re.search(r"Naturalidade:\s*([^\n]+)", texto, re.I)
        if nat_match: info['naturalidade'] = nat_match.group(1).strip()
            
        rg_match = re.search(r"RG/RNE:\s*([A-Za-z\d\.\-]+)", texto, re.I)
        if rg_match: info['rg'] = rg_match.group(1).strip()
            
        tp_match = re.search(r"Término\s*previsto:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if tp_match: info['termino_previsto'] = tp_match.group(1).strip()
            
        ht_match = re.search(r"Homologação\s*do\s*título(?:/Trabalho)?:\s*([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if ht_match: info['homologacao'] = ht_match.group(1).strip()
            
        tese_match = re.search(r"Título\s*da\s*Tese:\s*(.*?)(?=\nOrientador|Orientador)", texto, re.I | re.DOTALL)
        if tese_match: info['titulo_tese'] = tese_match.group(1).replace("\n", " ").strip()
            
        orient_match = re.search(r"Orientador[\(a\)]*:\s*(.*?)(?=\nDefesa|Defesa)", texto, re.I | re.DOTALL)
        if orient_match: info['orientador'] = orient_match.group(1).replace("\n", " ").strip()
            
        defesa_match = re.search(r"Defesa:\s*.*?([\d]{2}/[\d]{2}/[\d]{4})", texto, re.I)
        if defesa_match: info['defesa'] = defesa_match.group(1).strip()
        else: info['defesa'] = "Pendente"
            
        l1_match = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l1_match: info['lingua_1'] = l1_match.group(1).strip()
            
        l2_match = re.search(r"2[ºo]\s*Língua\s*Estrangeira:\s*([A-Za-zÀ-ÿ]+)", texto, re.I)
        if l2_match: info['lingua_2'] = l2_match.group(1).strip()
            
        uc_match = re.search(r"Unidade\s*Curricular.*?\n(.*?)(?=\nTotal|\nCréditos|\nResumo|\nMédia)", texto, re.I | re.DOTALL)
        if uc_match: info['unidades_curriculares'] = uc_match.group(1).strip()
            
        ct_match = re.search(r"Total\s*de\s*Créditos:\s*(\d+)", texto, re.I)
        if ct_match: info['creditos_total'] = ct_match.group(1).strip()
            
        cn_match = re.search(r"Créditos\s*Necessários\s*para\s*o\s*[A-Z]+:\s*(\d+)", texto, re.I)
        if cn_match: info['creditos_necessarios'] = cn_match.group(1).strip()
            
        obs_match = re.search(r"Obs(?:ervações)?:\s*([^\n]+)", texto, re.I)
        if obs_match: info['observacoes'] = obs_match.group(1).strip()
            
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        
    return info

def extract_student_data_hybrid(session, query, programa, baixar_historico=False, baixar_comprovante=False):
    """
    Usa requests para buscar dados do aluno instantaneamente.
    """
    base_url = "https://notas-propgpq.siiu.unifesp.br/portal-secretaria/discentes"
    
    # 1. Pegar IDs dos programas
    resp = session.get(base_url)
    if resp.status_code != 200:
        return {"status": "error", "message": "Falha ao acessar painel discentes via API."}
        
    soup = BeautifulSoup(resp.text, 'html.parser')
    select = soup.find('select', id='areas_prin_codigo')
    program_id = ""
    
    if select and programa and programa != "Todos os Programas":
        programa_busca = "ESCOLA DE FILOSOFIA, LETRAS E CIÊNCIAS HUMANAS" if programa == "Pós-Doutorado" else programa
        for option in select.find_all('option'):
            if option.text and programa_busca.upper() in option.text.upper():
                program_id = option.get('value', '')
                break
                
    # 2. Fazer a busca
    params = {
        "descricao": query,
        "areas_prin_codigo": program_id,
        "comboCursosPg": 0,
        "comboNivel": 0,
        "comboSitAcad": 0,
        "item": 10
    }
    resp_search = session.get(base_url, params=params)
    soup_search = BeautifulSoup(resp_search.text, 'html.parser')
    
    # Encontrar links do aluno na tabela
    links = soup_search.find_all('a', href=True)
    historico_url = None
    comprovante_url = None
    
    for link in links:
        if 'historico/' in link['href']:
            historico_url = link['href']
        if 'comprovante-matricula/' in link['href']:
            comprovante_url = link['href']
            
    if not historico_url:
        debug_html = soup_search.get_text()[:2000]
        return {"status": "error", "message": f"Nenhum histórico encontrado para esta busca. Verifique se o nome/matrícula ou programa estão corretos. (Debug: {debug_html})"}
        
    if not historico_url.startswith("http"):
        historico_url = "https://notas-propgpq.siiu.unifesp.br" + historico_url
        
    if comprovante_url and not comprovante_url.startswith("http"):
        comprovante_url = "https://notas-propgpq.siiu.unifesp.br" + comprovante_url
        
    # 3. Ler o histórico web para dados básicos
    resp_hist = session.get(historico_url)
    page_text = BeautifulSoup(resp_hist.text, 'html.parser').get_text(separator='\n')
    
    html_info = {}
    try:
        nome_match = re.search(r"Portal da Secretaria\n(.*?)\s*\(", page_text)
        if nome_match: html_info['nome'] = nome_match.group(1).strip()
        
        mat_match = re.search(r"Matrícula:\s*(\d+)", page_text, re.I)
        if mat_match: html_info['matricula'] = mat_match.group(1).strip()
        
        curso_match = re.search(r"Curso:\s*[\d]+.*?-\s*(.*?)\n", page_text, re.I)
        if curso_match: html_info['curso'] = curso_match.group(1).strip()
        
        sit_match = re.search(r"Situação:\s*(.*?)\n", page_text, re.I)
        if sit_match: html_info['situacao'] = sit_match.group(1).strip()
        
        ori_match = re.search(r"Orientador(?:a)?.*?\nNome:\s*([^\n]+)", page_text, re.I | re.DOTALL)
        if ori_match: html_info['orientador'] = ori_match.group(1).strip()
        
        banca_match = re.search(r"Membros\s*da\s*banca.*?(?:Tipo de participação\n)?(.*?)\n(?:Idiomas|Total de créditos|Para a soma)", page_text, re.I | re.DOTALL)
        if banca_match:
            lines = [line.strip() for line in banca_match.group(1).split('\n') if line.strip() and "TITULAR" not in line.upper() and "SUPLENTE" not in line.upper()]
            if lines: html_info['membros_banca'] = ", ".join(lines)
            
        l1_match = re.search(r"1[ºo]\s*Língua\s*Estrangeira:\s*([^\n]+)", page_text, re.I)
        if l1_match: html_info['lingua_1'] = l1_match.group(1).strip()
        
        ct_match = re.search(r"Total\s*de\s*créditos\s*obtidos:\s*(\d+)", page_text, re.I)
        if ct_match: html_info['creditos_total'] = ct_match.group(1).strip()
    except:
        pass
        
    # 4. Baixar PDFs via Requests
    download_dir = os.path.join(os.getcwd(), "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)
    pdf_historico_path = None
    pdf_comprovante_path = None
    
    if baixar_historico:
        # Encontrar o botão imprimir dentro da página de histórico
        soup_hist = BeautifulSoup(resp_hist.text, 'html.parser')
        btn_imprimir = soup_hist.find('a', href=re.compile(r'secretaria-imprimir'))
        if btn_imprimir:
            pdf_url = btn_imprimir['href']
            if not pdf_url.startswith("http"):
                pdf_url = "https://notas-propgpq.siiu.unifesp.br" + pdf_url
            pdf_resp = session.get(pdf_url)
            if pdf_resp.status_code == 200:
                pdf_historico_path = os.path.join(download_dir, f"historico_{int(time.time())}.pdf")
                with open(pdf_historico_path, 'wb') as f:
                    f.write(pdf_resp.content)
                    
    if baixar_comprovante and comprovante_url:
        pdf_resp = session.get(comprovante_url)
        if pdf_resp.status_code == 200:
            pdf_comprovante_path = os.path.join(download_dir, f"comprovante_{int(time.time())}.pdf")
            with open(pdf_comprovante_path, 'wb') as f:
                f.write(pdf_resp.content)
                
    pdf_info = parse_pdf_data(pdf_historico_path)
    if not html_info.get("orientador") and pdf_info.get("orientador"):
        html_info['orientador'] = pdf_info['orientador']
    if not html_info.get("lingua_1") and pdf_info.get("lingua_1"):
        html_info['lingua_1'] = pdf_info['lingua_1']
    if not html_info.get("creditos_total") and pdf_info.get("creditos_total"):
        html_info['creditos_total'] = pdf_info['creditos_total']
        
    html_info.update({k: v for k, v in pdf_info.items() if k not in html_info})
    
    return {
        "status": "success",
        "matricula": html_info.get("matricula", "Pendente"),
        "nome": html_info.get("nome", "Pendente"),
        "curso": html_info.get("curso", "Pendente"),
        "sexo": html_info.get("sexo", "Pendente"),
        "cpf": html_info.get("cpf", "Pendente"),
        "nascimento": html_info.get("nascimento", "Pendente"),
        "naturalidade": html_info.get("naturalidade", "Pendente"),
        "rg": html_info.get("rg", "Pendente"),
        "orientador": html_info.get("orientador", "Pendente"),
        "titulo_tese": html_info.get("titulo_tese", "Pendente"),
        "membros_banca": html_info.get("membros_banca", "Pendente"),
        "termino_previsto": html_info.get("termino_previsto", "Pendente"),
        "homologacao": html_info.get("homologacao", "Pendente"),
        "defesa": html_info.get("defesa", "Pendente"),
        "situacao": html_info.get("situacao", "Pendente"),
        "lingua_1": html_info.get("lingua_1", "Pendente"),
        "lingua_2": html_info.get("lingua_2", "Pendente"),
        "creditos_necessarios": html_info.get("creditos_necessarios", "Pendente"),
        "creditos_total": html_info.get("creditos_total", "Pendente"),
        "unidades_curriculares": html_info.get("unidades_curriculares", "Pendente"),
        "observacoes": html_info.get("observacoes", ""),
        "historico_path": pdf_historico_path,
        "comprovante_path": pdf_comprovante_path,
        "debug_info": "Extração Híbrida Super Rápida via Requests!"
    }
