"""
=============================================================================
ARQUIVO: src/analise_contratos.py
DESCRIÇÃO:
    Motor de automação (Selenium + SQL).
=============================================================================
"""
import os
import time
import shutil
import glob
import pandas as pd
import numpy as np
import threading
import concurrent.futures
import datetime
import tempfile
import unicodedata
import psutil
import zipfile
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from fake_useragent import UserAgent

# --- SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

pd.set_option('future.no_silent_downcasting', True)

# CONSTANTES E DIRETÓRIOS
DIRETORIO_RAIZ = os.getcwd()
DIR_EXPORTS = os.path.join(DIRETORIO_RAIZ, "exports_semestrais", "CONTRATOS")
DIR_RELATORIO_FINAL = os.path.join(DIRETORIO_RAIZ, "relatorio_anual", "CONTRATOS")
PASTA_TEMP_PAGAMENTOS = os.path.join(DIRETORIO_RAIZ, "temp_downloads_pagamentos")
DIR_RELATORIO_PAGAMENTOS = os.path.join(DIRETORIO_RAIZ, "rel_pagamentos")

ARQUIVO_DIVERGENCIAS = os.path.join(DIR_RELATORIO_FINAL, "relatorio_divergencias_contratos.xlsx")
ARQUIVO_SAIDA_CONTRATOS = os.path.join(DIR_RELATORIO_FINAL, "relatorio_anual_de_contratos.xlsx")
ARQUIVO_PAGAMENTOS_CONSOLIDADO = os.path.join(DIR_RELATORIO_PAGAMENTOS, "consolidada", "rel_pagamentos_anual_consolidado.xlsx")
ARQUIVO_ZIP_FINAL = os.path.join(DIR_RELATORIO_FINAL, "relatorios_contratos.zip")

def matar_driver_forca_bruta(driver):
    if driver:
        try:
            pid = driver.service.process.pid
            proc = psutil.Process(pid)
            for child in proc.children(recursive=True): 
                child.kill()
            proc.kill()
        except: pass
        try: driver.quit()
        except: pass

def padronizar_texto(texto):
    if pd.isna(texto): return ""
    txt = str(texto).upper().strip()
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    txt = txt.replace('-', ' ') 
    return ' '.join(txt.split())

def converter_para_numero_real(valor):
    if pd.isna(valor): return pd.NA
    s = str(valor).strip().split('.')[0]
    s = ''.join(filter(str.isdigit, s))
    if not s: return pd.NA
    return int(s)


class AutomacaoContratos:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutomacaoContratos, cls).__new__(cls)
            cls._instance.inicializar()
        return cls._instance

    def inicializar(self):
        self.is_running = False
        self.progress = 0.0
        self.target_progress = 0.0 # Controla o destino visual da barra (Efeito fluido)
        self.logs = []
        self.semestres = [
            {"label": "2025-1", "value": "2025-1##@@2025-1"},
            {"label": "2025-2", "value": "2025-2##@@2025-2"},
            {"label": "2026-1", "value": "2026-1##@@2026-1"},
        ]
        self.MAX_TENTATIVAS = 3
        self.lock = threading.Lock()
        self.download_lock = threading.Lock() 
        self.stop_event = threading.Event()
        self.thread = None
        self.arquivo_gerado = None
        self.arquivo_principal = None
        self.status_final = ""
        self.active_drivers = []
        self.start_time = None

    def log(self, msg, color="#F08EB3"):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        with self.lock:
            self.logs.append({"msg": f"{timestamp} {msg}", "color": color})
            if len(self.logs) > 200: self.logs.pop(0)

    def update_progress(self, amount):
        with self.lock:
            self.target_progress += amount
            if self.target_progress > 99: 
                self.target_progress = 99

    def get_status(self):
        with self.lock:
            # INTERPOLAÇÃO VISUAL: Avança a barra de forma fluida rumo ao target_progress sem pausar o Python!
            if self.is_running and self.progress < self.target_progress:
                distancia = self.target_progress - self.progress
                if distancia > 15:
                    passo = 1.5
                elif distancia > 5:
                    passo = 1.0
                else:
                    passo = 0.5
                
                self.progress += passo
                if self.progress > self.target_progress:
                    self.progress = self.target_progress
            
            if self.status_final == "success":
                self.progress = 100

            return {
                "progress": int(self.progress),
                "logs": list(self.logs),
                "is_running": self.is_running,
                "arquivo_gerado": self.arquivo_gerado,
                "arquivo_principal": self.arquivo_principal,
                "status_final": self.status_final
            }

    def _garantir_pastas(self):
        for pasta in [DIR_EXPORTS, DIR_RELATORIO_FINAL, PASTA_TEMP_PAGAMENTOS, DIR_RELATORIO_PAGAMENTOS]:
            if not os.path.exists(pasta):
                os.makedirs(pasta, exist_ok=True)

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.progress = 0.0
        self.target_progress = 0.0
        self.logs = [] 
        self.arquivo_gerado = None
        self.arquivo_principal = None
        self.status_final = ""
        self.active_drivers = []
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run_process)
        self.thread.start()

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.log("⚙️ [USUÁRIO] Parada imediata solicitada. Abortando...", "yellow")
            self.is_running = False 
            self.status_final = "error"
            
            def _kill_drivers():
                with self.lock:
                    drivers_copy = self.active_drivers.copy()
                    self.active_drivers.clear()
                for driver in drivers_copy:
                    matar_driver_forca_bruta(driver)
                    
            threading.Thread(target=_kill_drivers).start()

    def _run_process(self):
        try:
            self._garantir_pastas()
            self.log("⚙️ [SISTEMA] Iniciando módulo de automação...", "white")
            self.update_progress(2)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for dados in self.semestres:
                    futures.append(executor.submit(self._worker_contratos_retry, dados))
                
                futures.append(executor.submit(self._worker_pagamentos))
                
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set(): break
                    try: future.result()
                    except Exception as e: 
                        if not self.stop_event.is_set():
                            pass

            if self.stop_event.is_set():
                self.is_running = False
                return

            self.log("⚙️ [SISTEMA] Iniciando consolidação e cruzamento de dados...", "#FFCE54")
            self.target_progress = 45 # Prepara o alvo para a fase final
            sucesso = self.consolidar_contratos_e_pendencias_com_correcao()
            
            if sucesso:
                self.log("📂 [SISTEMA] Compactando relatórios finais em formato ZIP...", "cyan")
                self.target_progress = 100
                
                with zipfile.ZipFile(ARQUIVO_ZIP_FINAL, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(DIR_RELATORIO_FINAL):
                        for file in files:
                            if file != os.path.basename(ARQUIVO_ZIP_FINAL): 
                                file_path = os.path.join(root, file)
                                zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                    
                    for root, dirs, files in os.walk(DIR_EXPORTS):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                            
                    for root, dirs, files in os.walk(DIR_RELATORIO_PAGAMENTOS):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                
                self.arquivo_gerado = ARQUIVO_ZIP_FINAL
                self.arquivo_principal = ARQUIVO_SAIDA_CONTRATOS

            self._limpar_temporarios()

            elapsed = time.time() - self.start_time
            tempo_fmt = str(datetime.timedelta(seconds=int(elapsed)))

            if sucesso:
                self.progress = 100
                self.status_final = "success"
                self.log(f"🏆 [SUCESSO] Processo finalizado em {tempo_fmt}", "#A0D468")
            else:
                self.status_final = "error"
                self.log("⚙️ [ERRO] Falha na geração do relatório final.", "red")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log(f"⚙️ [CRÍTICO] Erro inesperado: {str(e)}", "red")
                self.status_final = "error"
        finally:
            self.is_running = False
            with self.lock:
                for driver in self.active_drivers:
                    matar_driver_forca_bruta(driver)
                self.active_drivers = []

    # =========================================================================
    # WORKERS DE EXTRAÇÃO
    # =========================================================================

    def _worker_contratos_retry(self, dados_semestre):
        nome = dados_semestre['label']
        for tentativa in range(1, self.MAX_TENTATIVAS + 1):
            if self.stop_event.is_set(): break
            try:
                if tentativa == 1:
                    self.log(f"⚙️ [{nome}] Acessando portal e aplicando filtros...", "cyan")
                else:
                    self.log(f"⚙️ [{nome}] Tentativa {tentativa}: Reiniciando extração...", "yellow")
                
                sucesso = self._contratos_navegador(dados_semestre)
                if sucesso:
                    self.log(f"✅ [{nome}] Planilha salva com sucesso!", "#A0D468")
                    self.update_progress(10) 
                    return True
            except Exception as e:
                if self.stop_event.is_set():
                    self.log(f"⚙️ [{nome}] Extração cancelada.", "yellow")
                    return False
                
                if tentativa < self.MAX_TENTATIVAS:
                    self.log(f"⚙️ [{nome}] Erro ao baixar ({str(e)}), repetindo...", "yellow")
                    time.sleep(3)
                else:
                    self.log(f"⚙️ [{nome}] Falha crítica de extração.", "red")
                    return False

    def _contratos_navegador(self, dados_semestre):
        if self.stop_event.is_set(): return False
        
        nome_semestre = dados_semestre['label']
        valor_semestre = dados_semestre['value']
        
        pasta_temp = os.path.join(DIR_EXPORTS, f"temp_{nome_semestre}")
        if not os.path.exists(pasta_temp): os.makedirs(pasta_temp, exist_ok=True)
        for f in os.listdir(pasta_temp):
            try: os.remove(os.path.join(pasta_temp, f))
            except: pass

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") 
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--unsafely-treat-insecure-origin-as-secure=http://10.237.1.11')
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_argument("--log-level=3")

        prefs = {
            "download.default_directory": pasta_temp, 
            "download.prompt_for_download": False, 
            "profile.default_content_setting_values.automatic_downloads": 1, 
            "credentials_enable_service": False, 
            "profile.password_manager_enabled": False
        }
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        with self.lock:
            self.active_drivers.append(driver)

        wait = WebDriverWait(driver, 180)

        try:
            if self.stop_event.is_set(): raise Exception("Cancelado")
            driver.get("http://10.237.1.11/pbu")
            
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#id_sc_field_login"))).send_keys("ihan.santos")
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))).send_keys("M@vis-08")
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#login1 > form > div.submit > input"))).click()
            
            if self.stop_event.is_set(): raise Exception("Cancelado")
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#item_163"))).click()
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#item_165"))).click()
            ActionChains(driver).move_by_offset(0, 0).perform()

            nome_iframe_aba = "menu_item_165_iframe"
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, nome_iframe_aba)))

            if self.stop_event.is_set(): raise Exception("Cancelado")
            el_drop = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#SC_semestre")))
            selecao = Select(el_drop)
            try: selecao.select_by_value(valor_semestre)
            except: selecao.select_by_visible_text(nome_semestre)

            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#sc_b_pesq_bot"))).click()
            expand = "#div_int_documento_tipo .dn-expand-button"
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, expand))).click()
            time.sleep(1)
            
            txt_alvo = "CONTRATO DE PRESTAÇÃO DE SERVIÇOS EDUCACIONAIS"
            xp_opt = f"//div[@id='id_tab_documento_tipo_link']//label[contains(text(), '{txt_alvo}')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xp_opt))).click()

            try:
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI.blockOverlay")))
                time.sleep(0.5) 
            except: pass

            self.log(f"⚙️ [{nome_semestre}] Sistema gerando relatório. Aguardando liberação...", "gray")

            if self.stop_event.is_set(): raise Exception("Cancelado")
            wait.until(EC.element_to_be_clickable((By.ID, "sc_btgp_btn_group_1_top"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "xls_top"))).click()

            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "TB_iframeContent")))
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#bok"))).click()

            inicio = time.time()
            btn_baixar = None
            while (time.time() - inicio) < 300:
                if self.stop_event.is_set(): raise Exception("Cancelado")
                try:
                    driver.switch_to.default_content()
                    try: driver.switch_to.frame(nome_iframe_aba)
                    except: pass
                    try: driver.switch_to.frame("TB_iframeContent")
                    except: pass

                    els = driver.find_elements(By.XPATH, "//*[@id='idBtnDown'] | //a[contains(., 'Baixar')]")
                    if els and els[0].is_displayed():
                        btn_baixar = els[0]
                        break
                    time.sleep(1)
                except: time.sleep(1)

            if not btn_baixar: raise Exception("Botão de baixar não apareceu no tempo limite.")

            with self.download_lock:
                driver.execute_script("arguments[0].click();", btn_baixar)
                
                arquivo_encontrado = None
                # REDUZIDO O TEMPO MAX DE ESPERA DE DOWNLOAD (60 segundos)
                # Assim a fila anda rápido e evita o gargalo de 4 minutos visto nos logs.
                for _ in range(60):
                    if self.stop_event.is_set(): break 

                    if not os.path.exists(pasta_temp): break
                    arquivos = os.listdir(pasta_temp)
                    validos = [f for f in arquivos if f.endswith(('.xlsx', '.xls')) and not f.startswith('.')]
                    if validos:
                        arquivo_encontrado = os.path.join(pasta_temp, validos[0])
                        break
                    time.sleep(1)

                if arquivo_encontrado:
                    time.sleep(1.5) 
                    nome_final = f"export_{nome_semestre}.xlsx"
                    caminho_final = os.path.join(DIR_EXPORTS, nome_final)
                    if os.path.exists(caminho_final): os.remove(caminho_final)
                    shutil.move(arquivo_encontrado, caminho_final)
                    shutil.rmtree(pasta_temp, ignore_errors=True)
                    return True
                else:
                    raise Exception("Download travou ou não foi concluído no tempo limite.")

        except Exception as e:
            raise e
        finally:
            with self.lock:
                if driver in self.active_drivers:
                    self.active_drivers.remove(driver)
            matar_driver_forca_bruta(driver)


    def _worker_pagamentos(self):
        driver = None
        try:
            if self.stop_event.is_set(): return
            self.log("⚙️ [Base Auxiliar] Acessando sistema financeiro...", "cyan")
            self.update_progress(2)
            
            ua = UserAgent()
            agente = ua.chrome
            opcoes = webdriver.ChromeOptions()
            opcoes.add_argument(f"user-agent={agente}")
            opcoes.add_argument("--headless=new") 
            opcoes.add_argument("--window-size=1920,1080")
            opcoes.add_argument('--ignore-certificate-errors')
            opcoes.add_argument('--unsafely-treat-insecure-origin-as-secure=http://10.237.1.11')
            opcoes.add_argument("--disable-blink-features=AutomationControlled") 
            opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])

            if not os.path.exists(PASTA_TEMP_PAGAMENTOS): os.makedirs(PASTA_TEMP_PAGAMENTOS, exist_ok=True)
            prefs = {"download.default_directory": PASTA_TEMP_PAGAMENTOS, "download.prompt_for_download": False, "directory_upgrade": True}
            opcoes.add_experimental_option("prefs", prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opcoes)
            
            with self.lock:
                self.active_drivers.append(driver)
            
            driver.get("http://10.237.1.11/bolsa/")
            main_window = driver.current_window_handle 

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="usuario"]'))).send_keys("ihan.santos")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="senha"]'))).send_keys("Mavis08")
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="conteudo"]/form/fieldset/p[3]/input'))).click()

            if self.stop_event.is_set(): return

            financeiro = '//*[@id="cssmenu"]/ul/li[4]/a/span' 
            ActionChains(driver).move_to_element(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, financeiro)))).perform()
            fin_gestao = '//*[@id="cssmenu"]/ul/li[4]/ul/li[1]/a' 
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, fin_gestao))).click()
            fin_rel = '//*[@id="cssmenu"]/ul/li[1]/a/span' 
            ActionChains(driver).move_to_element(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, fin_rel)))).perform()
            rel_pgto = '//*[@id="cssmenu"]/ul/li[1]/ul/li[2]/a'        
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, rel_pgto))).click()
            
            anos = ['2025', '2026'] 
            for ano in anos:       
                f_path = os.path.join(DIR_RELATORIO_PAGAMENTOS, ano)
                if not os.path.exists(f_path): os.makedirs(f_path, exist_ok=True)
            
            hoje = datetime.datetime.now()
            ano_atual = hoje.year
            mes_atual = hoje.month

            for ano in anos:
                if self.stop_event.is_set(): break
                ano_int = int(ano)
                if ano_int > ano_atual: continue
                f_path = os.path.join(DIR_RELATORIO_PAGAMENTOS, ano)

                self.log(f"⚙️ [Base Auxiliar] Processando e baixando pacotes de {ano}...", "gray")
                
                for m in range(1, 13):
                    if self.stop_event.is_set(): break
                    if ano_int == ano_atual and m >= mes_atual: break 

                    mes_valor = str(m).zfill(2)
                    self.update_progress(0.4)
                    
                    xpath_ano = f'//*[@id="ano"]/option[text()="{ano}"]'
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_ano))).click()
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="formato"]/option[2]'))).click()
                    xpath_mes = f'//*[@id="mes"]/option[@value="{mes_valor}"]'
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_mes))).click()
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '/html/body/form/fieldset/p[4]/input'))).click()
                    
                    time.sleep(1) 
                    if len(driver.window_handles) > 1:
                        for handle in driver.window_handles:
                            if handle != main_window:
                                driver.switch_to.window(handle)
                                driver.close()
                        driver.switch_to.window(main_window)

                    try:
                        arquivo_encontrado = WebDriverWait(driver, 15).until(lambda d: [f for f in os.listdir(PASTA_TEMP_PAGAMENTOS) if f.endswith(('.xls', '.xlsx')) and not f.startswith('.')])
                        if arquivo_encontrado:
                            nome_arq = arquivo_encontrado[0]
                            origem = os.path.join(PASTA_TEMP_PAGAMENTOS, nome_arq)
                            novo_nome = f"relatorio_{mes_valor}_{ano}.xls"
                            destino = os.path.join(f_path, novo_nome)
                            if os.path.exists(destino): os.remove(destino)
                            shutil.move(origem, destino)
                            for f in os.listdir(PASTA_TEMP_PAGAMENTOS):
                                try: os.remove(os.path.join(PASTA_TEMP_PAGAMENTOS, f))
                                except: pass
                    except: pass 
            
            if self.stop_event.is_set(): return
            
            with self.lock:
                if driver in self.active_drivers:
                    self.active_drivers.remove(driver)
            matar_driver_forca_bruta(driver)
            driver = None

            self.log("📋 [Base Auxiliar] Consolidando dados...", "#FFCE54")
            caminho_consolidada = os.path.join(DIR_RELATORIO_PAGAMENTOS, "consolidada")
            if not os.path.exists(caminho_consolidada): os.makedirs(caminho_consolidada, exist_ok=True)
            
            lista_dfs = []
            arquivos_totais = []
            for ano in anos:
                c_ano = os.path.join(DIR_RELATORIO_PAGAMENTOS, ano)
                if os.path.exists(c_ano):
                    arquivos_totais.extend([os.path.join(c_ano, f) for f in os.listdir(c_ano) if f.endswith('.xls')])
            
            for full_p in arquivos_totais:
                if self.stop_event.is_set(): break
                try:
                    df_temp = None
                    try: df_temp = pd.read_excel(full_p)
                    except:
                        try: 
                            dfs_html = pd.read_html(full_p, decimal=',', thousands='.', header=0)
                            if dfs_html: df_temp = dfs_html[0]
                        except: pass
                    
                    if df_temp is not None:
                        if 'UNI_CPF' in df_temp.columns: df_temp['UNI_CPF'] = df_temp['UNI_CPF'].astype(str).str.replace('*', '', regex=False)
                        if 'DATA_LANCAMENTO' in df_temp.columns:
                            try:
                                df_temp['DT'] = pd.to_datetime(df_temp['DATA_LANCAMENTO'], dayfirst=True, errors='coerce')
                                df_temp['SEMESTRE'] = df_temp['DT'].apply(lambda x: "" if pd.isnull(x) else f"{x.year}/{'1' if x.month <= 6 else '2'}")
                                df_temp.drop(columns=['DT'], inplace=True)
                            except: pass
                        lista_dfs.append(df_temp)
                except: pass
            
            if lista_dfs and not self.stop_event.is_set():
                df_u = pd.concat(lista_dfs, ignore_index=True)
                if 'UNI_CPF' in df_u.columns and 'TIPO_BOLSA' in df_u.columns:
                    try:
                        contagem = df_u.groupby('UNI_CPF')['TIPO_BOLSA'].nunique()
                        trocou = contagem[contagem > 1].index
                        df_u['TROCOU_BOLSA'] = df_u['UNI_CPF'].apply(lambda x: 'SIM' if x in trocou else 'NÃO')
                    except: pass
                
                if 'INS_NOME' in df_u.columns:
                    df_u['INS_NOME'] = df_u['INS_NOME'].apply(padronizar_texto)

                with pd.ExcelWriter(ARQUIVO_PAGAMENTOS_CONSOLIDADO, engine='openpyxl') as writer:
                    df_u.to_excel(writer, sheet_name='rel_pagamentos', index=False)
                
                self.log("✅ [Base Auxiliar] Relatórios financeiros processados.", "#A0D468")

        except Exception as e:
            pass
        finally:
            if driver: 
                with self.lock:
                    if driver in self.active_drivers:
                        self.active_drivers.remove(driver)
                matar_driver_forca_bruta(driver)
            if os.path.exists(PASTA_TEMP_PAGAMENTOS): 
                try: shutil.rmtree(PASTA_TEMP_PAGAMENTOS, ignore_errors=True)
                except: pass


    # =========================================================================
    # LÓGICA DE CONSOLIDAÇÃO PRINCIPAL E FORMATAÇÃO DE ARQUIVOS
    # =========================================================================

    def consolidar_contratos_e_pendencias_com_correcao(self):
        if self.stop_event.is_set(): return False
        
        self.log("📂 [MERGE] Lendo dados exportados...", "cyan")
        self.target_progress = 50
        padrao = os.path.join(DIR_EXPORTS, "export_*.xlsx")
        arquivos_excel = glob.glob(padrao)
        arquivos_excel.sort() 

        if not arquivos_excel:
            return False
            
        lista_dfs = []
        for arquivo in arquivos_excel:
            try:
                df_temp = pd.read_excel(arquivo, dtype=str)
                nome_arq = os.path.basename(arquivo)
                semestre = nome_arq.replace("export_", "").replace(".xlsx", "").replace("-", "/") 
                if "Semestre" in df_temp.columns: df_temp.drop(columns=["Semestre"], inplace=True)
                df_temp.insert(0, "Semestre", semestre)
                if 'Inscrição' in df_temp.columns: df_temp['Inscrição'] = df_temp['Inscrição'].str.replace('.', '', regex=False).str.strip()
                lista_dfs.append(df_temp)
            except: pass

        dfs_validos = [df.dropna(axis=1, how='all') for df in lista_dfs if not df.empty]
        if not dfs_validos: return False
        
        df_contratos = pd.concat(dfs_validos, ignore_index=True)
        
        colunas_numericas = ['Inscrição', 'CPF', 'Gemini CPF']
        for col in colunas_numericas:
            if col in df_contratos.columns: df_contratos[col] = df_contratos[col].apply(converter_para_numero_real).astype('Int64')

        if 'Data Processamento' in df_contratos.columns:
            df_contratos['Data Processamento'] = pd.to_datetime(df_contratos['Data Processamento'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y').fillna('')

        self.log("⚙️ [SQL] Acessando DB e coletando informações...", "cyan")
        self.target_progress = 68 # Prepara a barra de progresso para a consulta pesada (Sobe gradativo por 40s)
        
        DB_HOST, DB_USER, DB_PASS, DB_NAME = "10.237.1.16", "bi_ovg", "bi_ovg@#$124as65", "sibu"
        df_sql = pd.DataFrame()
        inscricoes_unicas = df_contratos['Inscrição'].dropna().astype(str).unique().tolist()
        
        try:
            if inscricoes_unicas:
                ids_formatados = ",".join(inscricoes_unicas)
                query_otimizada = f"SELECT * FROM sibu.PY_financeiro_calculado_semestre_IM WHERE uni_codigo IN ({ids_formatados})"
                
                db_engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}')
                df_sql = pd.read_sql(query_otimizada, db_engine)
                
                df_sql['uni_codigo'] = df_sql['uni_codigo'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_sql['semestre'] = df_sql['semestre'].astype(str).str.strip()
                df_sql = self._contratos_normalizar_sql(df_sql)
                df_sql['uni_codigo'] = df_sql['uni_codigo'].apply(converter_para_numero_real).astype('Int64')
        except Exception as e:
            pass
        
        self.log("🔄 [MERGE] Cruzando dados e aplicando regras de negocio...", "cyan")
        self.target_progress = 72
        
        if not df_sql.empty:
            df_contratos = pd.merge(df_contratos, df_sql, left_on=['Inscrição', 'Semestre'], right_on=['uni_codigo', 'semestre'], how='left')
            df_contratos.drop(columns=['uni_codigo'], errors='ignore', inplace=True)
            df_contratos.sort_values(by=['Inscrição', 'Semestre'], ascending=[True, True], inplace=True)
            
            cols_to_fill = ['tipo_bolsa_final']
            for col in cols_to_fill:
                if col in df_contratos.columns:
                    df_contratos[col] = df_contratos[col].replace(['', None, '0', 0, '[NULL]'], np.nan)
                    df_contratos[col] = df_contratos.groupby('Inscrição')[col].transform(lambda x: x.ffill().bfill())
                    if col == 'tipo_bolsa_final': df_contratos[col] = df_contratos[col].fillna("SEM DADOS")
            
            df_contratos['qtd_pagtos'] = df_contratos['qtd_pagtos'].fillna(0)
            df_contratos['valor_ultima_bolsa_paga'] = df_contratos['valor_ultima_bolsa_paga'].fillna(0.0)
            if 'tipo_pagto' in df_contratos.columns: df_contratos['tipo_pagto'] = df_contratos['tipo_pagto'].fillna("")

        cols_fin = ['Mensalidade S/ Desconto', 'Mensalidade C/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Gemini Mensalidade C/ Desconto']
        for col in cols_fin:
            if col in df_contratos.columns: df_contratos[col] = pd.to_numeric(df_contratos[col], errors='coerce').fillna(0.0)
            else: df_contratos[col] = 0.0

        df_contratos['Dif. s/Desc.'] = df_contratos['Mensalidade S/ Desconto'] - df_contratos['Gemini Mensalidade S/ Desconto']
        df_contratos['Dif. c/Desc.'] = np.where(df_contratos['Gemini Mensalidade C/ Desconto'] != 0, df_contratos['Mensalidade C/ Desconto'] - df_contratos['Gemini Mensalidade C/ Desconto'], 0)
        
        if 'Status Gemini' in df_contratos.columns: df_contratos.rename(columns={'Status Gemini': 'IA_status'}, inplace=True)

        if 'Faculdade' in df_contratos.columns:
            df_contratos['Faculdade'] = df_contratos['Faculdade'].apply(padronizar_texto)

        df_contratos['Mudou IES?'] = "N/A" 
        df_contratos['IES Anterior'] = "N/A"
        df_contratos['Mudou Bolsa?'] = "N/A"
        df_contratos['Bolsa Anterior'] = "N/A"

        ordem = ['IA_status', 'Mudou IES?', 'IES Anterior', 'Mudou Bolsa?', 'Bolsa Anterior', 'Semestre', 'Gemini Semestre', 'Inscrição', 'Bolsista', 'CPF', 'Gemini CPF', 'Gemini Inconsistencias', 
                    'Faculdade', 'Curso', 'tipo_bolsa_final', 'tipo_pagto', 'qtd_pagtos', 'valor_ultima_bolsa_paga', 
                    'Mensalidade S/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Dif. s/Desc.', 
                    'Mensalidade C/ Desconto', 'Gemini Mensalidade C/ Desconto', 'Dif. c/Desc.', 'Documento Tipo', 'Data Processamento']
        
        col_exist = [c for c in ordem if c in df_contratos.columns]
        df_contratos_div = df_contratos[col_exist].copy()
        
        df_pendentes = pd.DataFrame(columns=df_contratos.columns)
        df_pendentes_div = pd.DataFrame(columns=df_contratos_div.columns)
        
        self.log("⚙️ [ANÁLISE] Identificando mudanças de trajetória escolar...", "cyan")
        self.target_progress = 85
        
        if os.path.exists(ARQUIVO_PAGAMENTOS_CONSOLIDADO):
            df_pag = pd.read_excel(ARQUIVO_PAGAMENTOS_CONSOLIDADO)
            cols_req_pag = ['UNI_CODIGO', 'UNI_CPF', 'INS_NOME', 'SEMESTRE']
            
            if all(c in df_pag.columns for c in cols_req_pag):
                if 'INS_NOME' in df_pag.columns: df_pag['INS_NOME'] = df_pag['INS_NOME'].apply(padronizar_texto)
                df_pag.sort_values(by=['UNI_CODIGO', 'SEMESTRE'], inplace=True)

                df_pag['PREV_BOLSA'] = df_pag.groupby('UNI_CODIGO')['TIPO_BOLSA'].shift(1)
                df_pag['PREV_IES'] = df_pag.groupby('UNI_CODIGO')['INS_NOME'].shift(1)

                def get_flag_mudanca(curr, prev):
                    if pd.isna(prev): return "NÃO"
                    return "SIM" if curr != prev else "NÃO"

                def get_prev_value(curr, prev):
                    if pd.isna(prev): return "-"
                    return prev if curr != prev else "-"

                df_pag['FLAG_BOLSA'] = df_pag.apply(lambda x: get_flag_mudanca(x['TIPO_BOLSA'], x['PREV_BOLSA']), axis=1)
                df_pag['ANT_BOLSA'] = df_pag.apply(lambda x: get_prev_value(x['TIPO_BOLSA'], x['PREV_BOLSA']), axis=1)
                df_pag['FLAG_IES'] = df_pag.apply(lambda x: get_flag_mudanca(x['INS_NOME'], x['PREV_IES']), axis=1)
                df_pag['ANT_IES'] = df_pag.apply(lambda x: get_prev_value(x['INS_NOME'], x['PREV_IES']), axis=1)

                df_pag['KEY_MAP'] = list(zip(df_pag['UNI_CODIGO'].astype(str), df_pag['SEMESTRE'].astype(str)))
                
                map_flag_bolsa = dict(zip(df_pag['KEY_MAP'], df_pag['FLAG_BOLSA']))
                map_ant_bolsa = dict(zip(df_pag['KEY_MAP'], df_pag['ANT_BOLSA']))
                map_flag_ies = dict(zip(df_pag['KEY_MAP'], df_pag['FLAG_IES']))
                map_ant_ies = dict(zip(df_pag['KEY_MAP'], df_pag['ANT_IES']))

                df_pag['K_ID_DIV'] = df_pag['UNI_CODIGO'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_pag['K_CPF_DIV'] = df_pag['UNI_CPF'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False).str.strip().str.zfill(11)
                df_pag['K_INS_DIV'] = df_pag['INS_NOME'] 
                df_pag['K_SEM_DIV'] = df_pag['SEMESTRE'].astype(str).str.strip()
                df_pag['KEY_DIV'] = df_pag['K_ID_DIV'] + "_" + df_pag['K_CPF_DIV'] + "_" + df_pag['K_INS_DIV'] + "_" + df_pag['K_SEM_DIV']

                df_contratos_div['K_ID_DIV'] = df_contratos_div['Inscrição'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_contratos_div['K_CPF_DIV'] = df_contratos_div['CPF'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False).str.strip().str.zfill(11)
                df_contratos_div['K_INS_DIV'] = df_contratos_div['Faculdade'] 
                df_contratos_div['K_SEM_DIV'] = df_contratos_div['Semestre'].astype(str).str.strip()
                df_contratos_div['KEY_DIV'] = df_contratos_div['K_ID_DIV'] + "_" + df_contratos_div['K_CPF_DIV'] + "_" + df_contratos_div['K_INS_DIV'] + "_" + df_contratos_div['K_SEM_DIV']

                set_contratos_div = set(df_contratos_div['KEY_DIV'])
                df_diff_div = df_pag[~df_pag['KEY_DIV'].isin(set_contratos_div)].copy()
                
                self.log("📝 [ANÁLISE] Estruturando relatórios de pendências e divergências...", "cyan")
                self.target_progress = 90

                if not df_diff_div.empty:
                    df_pendentes_div['Semestre'] = df_diff_div['SEMESTRE']
                    df_pendentes_div['Inscrição'] = df_diff_div['UNI_CODIGO'].apply(converter_para_numero_real).astype('Int64')
                    df_pendentes_div['CPF'] = df_diff_div['UNI_CPF'].apply(converter_para_numero_real).astype('Int64')
                    df_pendentes_div['Faculdade'] = df_diff_div['INS_NOME']
                    
                    df_pendentes_div['Mudou IES?'] = "N/A"
                    df_pendentes_div['IES Anterior'] = "N/A"
                    df_pendentes_div['Mudou Bolsa?'] = "N/A"
                    df_pendentes_div['Bolsa Anterior'] = "N/A"

                    for col_nome in ['UNI_NOME', 'NOME', 'ALUNO', 'NOME_ALUNO', 'BOLSISTA']:
                        if col_nome in df_diff_div.columns: df_pendentes_div['Bolsista'] = df_diff_div[col_nome]; break
                    for col_curso in ['CUR_NOME', 'CURSO', 'NOME_CURSO']:
                        if col_curso in df_diff_div.columns: df_pendentes_div['Curso'] = df_diff_div[col_curso]; break
                    if 'TIPO_BOLSA' in df_diff_div.columns: df_pendentes_div['tipo_bolsa_final'] = df_diff_div['TIPO_BOLSA']
                    
                    df_pendentes_div['IA_status'] = 'X'
                    df_pendentes_div['Documento Tipo'] = 'NÃO ENVIOU CONTRATO DE PRESTAÇÃO DE SERVIÇOS EDUCACIONAIS OU COMPROVANTE DE MATRÍCULA'
                    
                    df_pendentes_div.drop_duplicates(subset=['Inscrição', 'Semestre', 'Faculdade'], inplace=True)

                df_contratos_div.drop(columns=['K_ID_DIV', 'K_CPF_DIV', 'K_INS_DIV', 'K_SEM_DIV', 'KEY_DIV'], inplace=True, errors='ignore')

                df_pag['K_ID'] = df_pag['UNI_CODIGO'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_pag['K_SEM'] = df_pag['SEMESTRE'].astype(str).str.strip()
                df_pag_unique = df_pag.drop_duplicates(subset=['K_ID', 'K_SEM'], keep='last')
                mapa_ies_correcao = dict(zip(zip(df_pag_unique['K_ID'], df_pag_unique['K_SEM']), df_pag_unique['INS_NOME']))
                
                def corrigir_ies(row):
                    chave = (str(row['Inscrição']), str(row['Semestre']))
                    if chave in mapa_ies_correcao:
                        nova_ies = padronizar_texto(mapa_ies_correcao[chave])
                        if nova_ies: return nova_ies
                    return row['Faculdade']

                df_contratos['Faculdade'] = df_contratos.apply(corrigir_ies, axis=1)
                
                def aplicar_flags(row):
                    chave = (str(row['Inscrição']), str(row['Semestre']))
                    return pd.Series([
                        map_flag_ies.get(chave, "NÃO"),
                        map_ant_ies.get(chave, "-"),
                        map_flag_bolsa.get(chave, "NÃO"),
                        map_ant_bolsa.get(chave, "-")
                    ])

                df_contratos[['Mudou IES?', 'IES Anterior', 'Mudou Bolsa?', 'Bolsa Anterior']] = df_contratos.apply(aplicar_flags, axis=1)

                df_contratos['KEY_EXISTENCIA'] = df_contratos['Inscrição'].astype(str) + "_" + df_contratos['Semestre'].astype(str)
                contratos_existentes = set(df_contratos['KEY_EXISTENCIA'])
                
                df_pag['KEY_EXISTENCIA'] = df_pag['K_ID'] + "_" + df_pag['K_SEM']
                
                df_diff = df_pag[~df_pag['KEY_EXISTENCIA'].isin(contratos_existentes)].copy()

                if not df_diff.empty:
                    df_pendentes['Semestre'] = df_diff['SEMESTRE']
                    df_pendentes['Inscrição'] = df_diff['UNI_CODIGO'].apply(converter_para_numero_real).astype('Int64')
                    df_pendentes['CPF'] = df_diff['UNI_CPF'].apply(converter_para_numero_real).astype('Int64')
                    df_pendentes['Faculdade'] = df_diff['INS_NOME']
                    
                    df_pendentes['Mudou IES?'] = df_diff['FLAG_IES']
                    df_pendentes['IES Anterior'] = df_diff['ANT_IES']
                    df_pendentes['Mudou Bolsa?'] = df_diff['FLAG_BOLSA']
                    df_pendentes['Bolsa Anterior'] = df_diff['ANT_BOLSA']

                    for col_nome in ['UNI_NOME', 'NOME', 'ALUNO', 'NOME_ALUNO', 'BOLSISTA']:
                        if col_nome in df_diff.columns: df_pendentes['Bolsista'] = df_diff[col_nome]; break
                    for col_curso in ['CUR_NOME', 'CURSO', 'NOME_CURSO']:
                        if col_curso in df_diff.columns: df_pendentes['Curso'] = df_diff[col_curso]; break
                    if 'TIPO_BOLSA' in df_diff.columns: df_pendentes['tipo_bolsa_final'] = df_diff['TIPO_BOLSA']
                    
                    df_pendentes['IA_status'] = 'X'
                    df_pendentes['Documento Tipo'] = 'NÃO ENVIOU CONTRATO DE PRESTAÇÃO DE SERVIÇOS EDUCACIONAIS OU COMPROVANTE DE MATRÍCULA'
                    
                    df_pendentes.drop_duplicates(subset=['Inscrição', 'Semestre'], inplace=True)
                
                df_contratos.drop(columns=['KEY_EXISTENCIA'], inplace=True, errors='ignore')

        self.log("🎨 [EXCEL] Aplicando estilização e salvando dados...", "cyan")
        self.target_progress = 98
        
        writer_div = pd.ExcelWriter(ARQUIVO_DIVERGENCIAS, engine='xlsxwriter')
        self._aplicar_estilo_tabela(writer_div, df_contratos_div, "divergencias")
        if not df_pendentes_div.empty:
            df_pendentes_div = df_pendentes_div[col_exist] if set(col_exist).issubset(df_pendentes_div.columns) else df_pendentes_div
            df_pend_div_clean = df_pendentes_div.dropna(axis=1, how='all')
            self._aplicar_estilo_tabela(writer_div, df_pend_div_clean, "pendencias divergentes")
        writer_div.close()
        
        writer = pd.ExcelWriter(ARQUIVO_SAIDA_CONTRATOS, engine='xlsxwriter')
        df_final_principal = df_contratos[col_exist].copy()
        
        if not df_pendentes.empty:
            df_pendentes = df_pendentes[col_exist] if set(col_exist).issubset(df_pendentes.columns) else df_pendentes
            df_p_clean = df_pendentes.dropna(axis=1, how='all')
            if not df_p_clean.empty:
                df_final_principal = pd.concat([df_final_principal, df_p_clean], ignore_index=True)
            
        self._aplicar_estilo_tabela(writer, df_final_principal, "CONTRATOS")
        writer.close()
        
        return True

    def _contratos_normalizar_sql(self, df):
        if df.empty: return df
        df['uni_codigo'] = df['uni_codigo'].astype(str).str.strip()
        col_id, col_semestre = 'uni_codigo', 'semestre'
        semestres_obrigatorios = ['2025/1', '2025/2', '2026/1'] 
        
        alunos_unicos = df[col_id].unique()
        index = pd.MultiIndex.from_product([alunos_unicos, semestres_obrigatorios], names=[col_id, col_semestre])
        df_skeleton = pd.DataFrame(index=index).reset_index()
        df_merged = pd.merge(df_skeleton, df, on=[col_id, col_semestre], how='left')
        colunas_para_copiar = ['tipo_bolsa_final'] 
        df_merged[colunas_para_copiar] = df_merged.groupby(col_id)[colunas_para_copiar].ffill().bfill()
        valores_para_zerar = {'qtd_pagtos': 0, 'valor_ultima_bolsa_paga': 0.0, 'tipo_pagto': ""}
        df_merged.fillna(valores_para_zerar, inplace=True)
        df_merged['tipo_bolsa_final'] = df_merged['tipo_bolsa_final'].fillna("SEM DADOS")
        return df_merged

    def _aplicar_estilo_tabela(self, writer, df, nome_aba):
        df.to_excel(writer, sheet_name=nome_aba, startrow=1, header=False, index=False)
        ws = writer.sheets[nome_aba]
        (mx_r, mx_c) = df.shape
        
        ws.add_table(0, 0, mx_r, mx_c - 1, {'columns': [{'header': c} for c in df.columns], 'style': 'Table Style Medium 9', 'name': f'Tab_{nome_aba.replace(" ", "_")}'})
        
        workbook = writer.book
        fmt_cpf_mask = workbook.add_format({'num_format': '00000000000'})
        fmt_numero_puro = workbook.add_format({'num_format': '0'})
        fmt_texto = workbook.add_format({'num_format': '@'}) 
        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
        fmt_inteiro = workbook.add_format({'num_format': '0'})
        fmt_alerta = workbook.add_format({'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
        fmt_valido = workbook.add_format({'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
        fmt_invalido = workbook.add_format({'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})

        cols_fin = ['Mensalidade S/ Desconto', 'Mensalidade C/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Gemini Mensalidade C/ Desconto', 'Dif. s/Desc.', 'Dif. c/Desc.', 'valor_ultima_bolsa_paga']

        for i, col in enumerate(df.columns):
            larg = len(str(col))
            try:
                amostra = df[col].head(20)
                if not amostra.empty:
                    max_len = amostra.apply(lambda x: len(str(x)) if pd.notnull(x) else 0).max()
                    larg = max(larg, max_len)
            except: pass
            larg = min(larg + 2, 60)

            if col in cols_fin: ws.set_column(i, i, larg, fmt_moeda)
            elif col == 'qtd_pagtos': ws.set_column(i, i, larg, fmt_inteiro)
            elif 'CPF' in col: ws.set_column(i, i, 16, fmt_cpf_mask)
            elif col == 'Inscrição': ws.set_column(i, i, larg, fmt_numero_puro)
            elif col == 'Data Processamento': ws.set_column(i, i, 14, fmt_texto)
            else: ws.set_column(i, i, larg)

            if col in ['Dif. s/Desc.', 'Dif. c/Desc.']:
                ws.conditional_format(1, i, mx_r, i, {'type': 'cell', 'criteria': '!=', 'value': 0, 'format': fmt_alerta})
            if col == 'IA_status':
                ws.conditional_format(1, i, mx_r, i, {'type': 'text', 'criteria': 'begins with', 'value': 'V', 'format': fmt_valido})
                ws.conditional_format(1, i, mx_r, i, {'type': 'text', 'criteria': 'begins with', 'value': 'I', 'format': fmt_invalido})
                ws.conditional_format(1, i, mx_r, i, {'type': 'text', 'criteria': 'begins with', 'value': 'X', 'format': fmt_invalido})

    def _limpar_temporarios(self):
        try:
            for pasta in [DIR_EXPORTS, DIR_RELATORIO_PAGAMENTOS, PASTA_TEMP_PAGAMENTOS]:
                if os.path.exists(pasta):
                    shutil.rmtree(pasta, ignore_errors=True)
        except: pass