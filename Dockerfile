FROM python:3.11-slim

# Evita arquivos de cache e buffer no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala o Chromium e o Chromedriver compatível diretamente pelo sistema
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do servidor
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o projeto para o servidor
COPY . .

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando para manter o Streamlit rodando
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
