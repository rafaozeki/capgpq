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

def get_credentials():
    # 1. Verifica se estamos rodando na nuvem (Streamlit Cloud) via Service Account
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            return creds
    except Exception:
        pass # Ignora erro caso o arquivo secrets.toml não exista localmente

    # 2. Caso contrário, usa o fluxo local (OAuth com credentials.json)
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("Arquivo credentials.json não encontrado. Por favor, coloque-o na raiz do projeto (se rodando local) ou configure os Secrets no Streamlit Cloud.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def get_sheets():
    """Busca todas as planilhas (Google Sheets) acessíveis pelo usuário."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    query = "mimeType='application/vnd.google-apps.spreadsheet'"
    results = service.files().list(q=query, pageSize=100, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items

def get_sheet_data(spreadsheet_id, range_name='Página1'):
    """Busca os dados de uma planilha e aba específicos."""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    return values

def col_num_to_letter(n):
    """Converte um índice de coluna (0 = A, 1 = B) para a letra correspondente"""
    string = ""
    while n >= 0:
        string = chr((n % 26) + 65) + string
        n = (n // 26) - 1
    return string

def update_sheet_cell(spreadsheet_id, sheet_name, row_index, col_index, new_value):
    """Atualiza uma célula específica da planilha"""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
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
    
    return result
