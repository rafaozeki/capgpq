import os
import pickle
import json
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _find_file(filename):
    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "app", filename),
        os.path.join(os.path.dirname(BASE_DIR), filename)
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None

def get_credentials():
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            return creds
    except Exception:
        pass
        
    token_str = None
    try:
        if "google_oauth_token" in st.secrets:
            token_str = st.secrets["google_oauth_token"]
        elif os.environ.get("google_oauth_token"):
            token_str = os.environ.get("google_oauth_token")
    except Exception:
        token_str = os.environ.get("google_oauth_token")

    if token_str:
        try:
            token_info = json.loads(token_str)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            
            if creds:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                if creds.valid:
                    return creds
        except Exception as e:
            print(f"Erro ao autenticar via google_oauth_token: {e}")

    creds = None
    token_pickle_path = _find_file('token.pickle')
    if token_pickle_path:
        try:
            with open(token_pickle_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception:
            pass
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_json_path = _find_file('credentials.json')
            if not creds_json_path:
                raise FileNotFoundError("Arquivo credentials.json não encontrado.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_json_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        save_pickle_path = token_pickle_path or os.path.join(BASE_DIR, 'token.pickle')
        try:
            with open(save_pickle_path, 'wb') as token:
                pickle.dump(creds, token)
        except Exception:
            pass
            
    return creds

def get_sheets():
    """Busca todas as planilhas (Google Sheets) acessíveis pelo usuário."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    query = "mimeType='application/vnd.google-apps.spreadsheet'"
    results = service.files().list(q=query, pageSize=100, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items

@st.cache_data(ttl=300, show_spinner=False, max_entries=5)
def get_sheet_data(spreadsheet_id, range_name='Respostas ao formulário 1'):
    """Busca os dados de uma planilha e aba específicos com cache temporário de 5 minutos e fallback automático."""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    sheet = service.spreadsheets()
    
    clean_range = str(range_name).strip("'")
    target_range = f"'{clean_range}'"
    
    try:
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=target_range).execute()
        return result.get('values', [])
    except Exception as e:
        try:
            meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = meta.get('sheets', [])
            if sheets:
                first_tab_name = sheets[0]['properties']['title']
                fallback_range = f"'{first_tab_name}'"
                result = sheet.values().get(spreadsheetId=spreadsheet_id, range=fallback_range).execute()
                return result.get('values', [])
        except Exception:
            pass
        raise e

def col_num_to_letter(n):
    """Converte um índice de coluna (0 = A, 1 = B) para a letra correspondente"""
    string = ""
    while n >= 0:
        string = chr((n % 26) + 65) + string
        n = (n // 26) - 1
    return string

def update_sheet_cell(spreadsheet_id, sheet_name, row_index, col_index, new_value):
    """Atualiza uma célula específica da planilha e limpa o cache de dados."""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    
    col_letter = col_num_to_letter(col_index)
    cell_range = f"'{sheet_name}'!{col_letter}{row_index}"
    
    body = {
        'values': [[new_value]]
    }
    
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, 
        range=cell_range,
        valueInputOption="USER_ENTERED", 
        body=body
    ).execute()
    
    try:
        get_sheet_data.clear()
    except Exception:
        pass
        
    return result
