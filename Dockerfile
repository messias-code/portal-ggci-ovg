# =============================================================================
# ARQUIVO: Dockerfile
# DESCRIÇÃO: Imagem da Aplicação Python + Google Chrome para Selenium
# =============================================================================
FROM python:3.11-slim

# Evita interações travadas durante instalações no Linux
ENV DEBIAN_FRONTEND=noninteractive

# Define o diretório de trabalho dentro do Container
WORKDIR /app

# 1. Instala utilitários de sistema e o Google Chrome (Essencial para o Selenium)
RUN apt-get update && apt-get install -y wget gnupg2 curl unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Copia os requisitos e instala bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia todo o código fonte do projeto
COPY . .

# 4. Expõe as portas do Dash (Garante tanto 8085 quanto 8051 se for WSL)
EXPOSE 8085
EXPOSE 8051

# 5. Comando de inicialização
CMD ["python", "app.py"]