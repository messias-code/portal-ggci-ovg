"""
=============================================================================
ARQUIVO: src/analise_contratos.py
DESCRIÇÃO:
    Motor de automação (Selenium + SQL) com consolidação e relatórios avançados.
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
DIR_EXPORTS_BASE = os.path.join(DIRETORIO_RAIZ, "exports_semestrais")
DIR_RELATORIO_ANUAL = os.path.join(DIRETORIO_RAIZ, "relatorio_anual")
DIR_RELATORIO_CONTRATOS = os.path.join(DIR_RELATORIO_ANUAL, "CONTRATOS")
DIR_RELATORIO_CONSOLIDADOS = os.path.join(DIR_RELATORIO_ANUAL, "DOCUMENTOS_CONSOLIDADOS")
PASTA_TEMP_PAGAMENTOS = os.path.join(DIRETORIO_RAIZ, "temp_downloads_pagamentos")
DIR_RELATORIO_PAGAMENTOS = os.path.join(DIRETORIO_RAIZ, "rel_pagamentos")

ARQUIVO_DIVERGENCIAS = os.path.join(DIR_RELATORIO_CONTRATOS, "rel_contratos_divergentes.xlsx")
ARQUIVO_SAIDA_CONTRATOS = os.path.join(DIR_RELATORIO_CONTRATOS, "rel_contratos.xlsx")
ARQUIVO_PAGAMENTOS_CONSOLIDADO = os.path.join(DIR_RELATORIO_PAGAMENTOS, "rel_pagamentos_consolidado.xlsx")
ARQUIVO_MASTER_CONSOLIDADO = os.path.join(DIR_RELATORIO_CONSOLIDADOS, "rel_documentos.xlsx")
ARQUIVO_ZIP_FINAL = os.path.join(DIR_RELATORIO_ANUAL, "relatorios_contratos.zip")

# CONFIGURAÇÃO OFICIAL DOS DOCUMENTOS
DOCS_TO_FETCH = [
    {
        "id": "CONTRATO",
        "nome": "Contratos",
        "xpath": "//div[@id='id_tab_documento_tipo_link']//label[contains(text(), 'CONTRATO DE PRESTAÇÃO')]"
    },
    {
        "id": "FINANCIAMENTO",
        "nome": "Financiamento",
        "xpath": '//*[@id="id_tab_documento_tipo_link"]/div[1]/table/tbody/tr/td/span[2]/span[1]/label'
    },
    {
        "id": "OUTROS_BENEF",
        "nome": "Outros Benef.",
        "xpath": '//*[@id="id_tab_documento_tipo_link"]/div[2]/table/tbody/tr/td/span[2]/span[1]/label'
    },
    {
        "id": "RIAF",
        "nome": "RIAF",
        "xpath": '//*[@id="id_tab_documento_tipo_link"]/div[4]/table/tbody/tr/td/span[2]/span[1]/label'
    }
]

def matar_driver_forca_bruta(driver):
    if not driver: return
    
    pid = None
    try: pid = driver.service.process.pid
    except: pass

    try: driver.quit()
    except: pass

    if pid:
        try:
            proc = psutil.Process(pid)
            for child in proc.children(recursive=True): 
                child.kill()
            proc.kill()
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
        self.target_progress = 0.0 
        self.logs = []
        
        self.docs_ativos = DOCS_TO_FETCH
        self.anos_ativos = ["2025", "2026"]
        self.semestres_ativos = []
        
        self.MAX_TENTATIVAS = 3
        self.lock = threading.Lock()
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
            if self.is_running and self.progress < self.target_progress:
                distancia = self.target_progress - self.progress
                passo = 1.5 if distancia > 15 else (1.0 if distancia > 5 else 0.5)
                self.progress += passo
                if self.progress > self.target_progress: self.progress = self.target_progress
            if self.status_final == "success": self.progress = 100

            return {
                "progress": int(self.progress),
                "logs": list(self.logs),
                "is_running": self.is_running,
                "arquivo_gerado": self.arquivo_gerado,
                "arquivo_principal": self.arquivo_principal,
                "status_final": self.status_final
            }

    def _garantir_pastas(self):
        for pasta in [DIR_EXPORTS_BASE, DIR_RELATORIO_ANUAL, DIR_RELATORIO_PAGAMENTOS, DIR_RELATORIO_CONTRATOS, DIR_RELATORIO_CONSOLIDADOS]:
            if not os.path.exists(pasta): os.makedirs(pasta, exist_ok=True)
        for doc in self.docs_ativos:
            pasta_doc = os.path.join(DIR_EXPORTS_BASE, doc['id'])
            if not os.path.exists(pasta_doc): os.makedirs(pasta_doc, exist_ok=True)
            pasta_rel = os.path.join(DIR_RELATORIO_ANUAL, doc['id'])
            if not os.path.exists(pasta_rel): os.makedirs(pasta_rel, exist_ok=True)

    def _limpar_conteudo_pasta(self, pasta):
        if os.path.exists(pasta):
            for filename in os.listdir(pasta):
                filepath = os.path.join(pasta, filename)
                try:
                    if os.path.isfile(filepath) or os.path.islink(filepath):
                        os.unlink(filepath)
                    elif os.path.isdir(filepath):
                        shutil.rmtree(filepath)
                except:
                    pass

    def start(self, config=None):
        if self.is_running: return
        
        if self.thread and self.thread.is_alive():
            self.stop()
            self.thread.join(timeout=3)
            
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
        
        hoje = datetime.datetime.now()
        ano_atual = hoje.year
        mes_atual = hoje.month

        if config:
            docs_selecionados = config.get("docs", ["CONTRATO", "FINANCIAMENTO", "OUTROS_BENEF", "RIAF"])
            anos_selecionados = config.get("anos", ["2025", "2026"])
            sems_selecionados = config.get("semestres", ["1", "2"])
        else:
            docs_selecionados = ["CONTRATO", "FINANCIAMENTO", "OUTROS_BENEF", "RIAF"]
            anos_selecionados = ["2025", "2026"]
            sems_selecionados = ["1", "2"]

        self.docs_ativos = [d for d in DOCS_TO_FETCH if d['id'] in docs_selecionados]
        self.anos_ativos = anos_selecionados
        
        self.semestres_ativos = []
        for ano in anos_selecionados:
            ano_int = int(ano)
            for sem in sems_selecionados:
                sem_int = int(sem)
                if ano_int > ano_atual: continue
                if ano_int == ano_atual and sem_int == 2 and mes_atual < 8: continue
                
                label = f"{ano}-{sem}"
                self.semestres_ativos.append({"label": label, "value": f"{label}##@@{label}"})

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
            self.log("🧹 [SISTEMA] Higienizando diretórios de execuções anteriores...", "gray")
            
            pastas_alvo = [DIR_EXPORTS_BASE, DIR_RELATORIO_ANUAL, DIR_RELATORIO_PAGAMENTOS, DIR_RELATORIO_CONTRATOS, DIR_RELATORIO_CONSOLIDADOS]
            for pasta in pastas_alvo:
                self._limpar_conteudo_pasta(pasta)
                
            time.sleep(1.0) 
            self._garantir_pastas()
            
            self.log("⚙️ [SISTEMA] Iniciando módulo de automação com configurações selecionadas...", "white")
            self.update_progress(2)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for dados in self.semestres_ativos:
                    futures.append(executor.submit(self._worker_contratos_retry, dados))
                futures.append(executor.submit(self._worker_pagamentos))
                
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set(): break
                    try: future.result()
                    except Exception as e: 
                        if not self.stop_event.is_set(): self.log(f"⚙️ [ERRO] Falha em thread: {e}", "red")

            if self.stop_event.is_set():
                self.is_running = False
                return

            self.log("⚙️ [SISTEMA] Iniciando consolidação e cruzamento de dados...", "#FFCE54")
            self.target_progress = 45 
            sucesso = self.consolidar_contratos_e_pendencias_com_correcao()
            
            if sucesso:
                self.log("📂 [SISTEMA] Compactando relatórios finais em formato ZIP...", "cyan")
                self.target_progress = 100
                
                with zipfile.ZipFile(ARQUIVO_ZIP_FINAL, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(DIR_RELATORIO_ANUAL):
                        for file in files:
                            if file != os.path.basename(ARQUIVO_ZIP_FINAL): 
                                file_path = os.path.join(root, file)
                                zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                    for root, dirs, files in os.walk(DIR_EXPORTS_BASE):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                    for root, dirs, files in os.walk(DIR_RELATORIO_PAGAMENTOS):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, DIRETORIO_RAIZ))
                
                self.arquivo_gerado = ARQUIVO_ZIP_FINAL
                self.arquivo_principal = ARQUIVO_MASTER_CONSOLIDADO

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
        ano_str = nome.split('-')[0]
        ano_int = int(ano_str) if ano_str.isdigit() else 2025
        
        docs_para_baixar = []
        for doc in self.docs_ativos:
            if doc['id'] == 'RIAF' and ano_int < 2026:
                self.log(f"⚠️ [{nome}] {doc['nome']} disponível apenas a partir de 2026. Ignorando.", "gray")
                continue
            docs_para_baixar.append(doc)
            
        if not docs_para_baixar:
            self.log(f"✅ [{nome}] Sem documentos válidos para o período.", "#A0D468")
            self.update_progress(10)
            return True

        docs_baixados_nesta_sessao = set()
        
        for tentativa in range(1, self.MAX_TENTATIVAS + 1):
            if self.stop_event.is_set(): break
            try:
                if tentativa == 1: self.log(f"⚙️ [{nome}] Acessando portal e aplicando filtros...", "cyan")
                else: self.log(f"⚙️ [{nome}] Tentativa {tentativa}: Reiniciando extração...", "yellow")
                
                resultado = self._contratos_navegador(dados_semestre, docs_baixados_nesta_sessao, docs_para_baixar)
                
                if resultado == "SKIPPED":
                    self.log(f"✅ [{nome}] Verificação concluída (Sem dados na base).", "#A0D468")
                    self.update_progress(10)
                    return True
                elif resultado == True:
                    self.log(f"✅ [{nome}] Planilhas processadas com sucesso!", "#A0D468")
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

    def _contratos_navegador(self, dados_semestre, docs_baixados_nesta_sessao, docs_para_baixar):
        if self.stop_event.is_set(): return False
        
        nome_semestre = dados_semestre['label']
        valor_semestre = dados_semestre['value']

        uid_pasta = str(int(time.time() * 1000))[-6:]
        pasta_temp_thread = os.path.join(DIR_EXPORTS_BASE, f"temp_ext_{nome_semestre}_{uid_pasta}")
        os.makedirs(pasta_temp_thread, exist_ok=True)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") 
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--unsafely-treat-insecure-origin-as-secure=http://10.237.1.11')
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_argument("--log-level=3")
        
        prefs = {
            "download.default_directory": os.path.abspath(pasta_temp_thread),
            "download.prompt_for_download": False,
            "directory_upgrade": True,
            "safebrowsing.enabled": False, 
            "safebrowsing.disable_download_protection": True
        }
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': os.path.abspath(pasta_temp_thread)
        })
        
        with self.lock:
            self.active_drivers.append(driver)

        wait = WebDriverWait(driver, 180)
        baixou_algo = False

        try:
            if self.stop_event.is_set(): raise Exception("Cancelado")
            driver.get("http://10.237.1.11/pbu")
            
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#id_sc_field_login"))).send_keys("ihan.santos")
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))).send_keys("M@vis-08")
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#login1 > form > div.submit > input"))).click()
            self.update_progress(2)
            
            if self.stop_event.is_set(): raise Exception("Cancelado")
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#item_163"))).click()

            for doc in docs_para_baixar:
                if doc['id'] in docs_baixados_nesta_sessao: continue
                
                driver.switch_to.default_content()
                menu_item = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#item_165")))
                driver.execute_script("arguments[0].click();", menu_item)

                nome_iframe_aba = "menu_item_165_iframe"
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, nome_iframe_aba)))

                if self.stop_event.is_set(): raise Exception("Cancelado")
                el_drop = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#SC_semestre")))
                selecao = Select(el_drop)
                try: selecao.select_by_value(valor_semestre)
                except: 
                    try: selecao.select_by_visible_text(nome_semestre)
                    except:
                        self.log(f"⚠️ [{nome_semestre}] Semestre indisponível no portal. Ignorando.", "yellow")
                        return "SKIPPED"

                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#sc_b_pesq_bot"))).click()
                expand = "#div_int_documento_tipo .dn-expand-button"
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, expand))).click()
                time.sleep(1)
                
                try:
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, doc['xpath']))).click()
                except:
                    self.log(f"⚠️ [{nome_semestre}] Filtro '{doc['nome']}' ausente. Pulando...", "yellow")
                    continue

                try:
                    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI.blockOverlay")))
                    time.sleep(0.5) 
                except: pass

                try:
                    empty_msg = driver.find_elements(By.XPATH, "//*[contains(text(), 'Registros não encontrados') or contains(text(), 'Nenhum registro')]")
                    if empty_msg and any(e.is_displayed() for e in empty_msg):
                        self.log(f"⚠️ [{nome_semestre}] Sem dados processados para {doc['nome']}. Pulando...", "yellow")
                        continue
                except: pass

                self.log(f"⚙️ [{nome_semestre}] Gerando {doc['nome']}...", "gray")

                if self.stop_event.is_set(): raise Exception("Cancelado")
                wait.until(EC.element_to_be_clickable((By.ID, "sc_btgp_btn_group_1_top"))).click()
                time.sleep(0.5)
                wait.until(EC.element_to_be_clickable((By.ID, "xls_top"))).click()

                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "TB_iframeContent")))
                time.sleep(1) 
                
                btn_bok = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#bok")))
                driver.execute_script("arguments[0].click();", btn_bok)

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

                # [SENIOR FIX] Pausa para o Event Binding: ScriptCase precisa de tempo para acoplar a função de download
                time.sleep(1.5) 
                
                # Tenta o clique nativo primeiro (garante ativação de eventos JS)
                try:
                    btn_baixar.click()
                except:
                    driver.execute_script("arguments[0].click();", btn_baixar)
                
                arquivo_encontrado = None
                for checagem in range(240):
                    if self.stop_event.is_set(): break 
                    if not os.path.exists(pasta_temp_thread): break
                    arquivos = os.listdir(pasta_temp_thread)
                    
                    validos = [f for f in arquivos if f.endswith(('.xlsx', '.xls')) and not f.endswith('.crdownload') and not f.endswith('.tmp')]
                    if validos:
                        arquivo_encontrado = os.path.join(pasta_temp_thread, validos[0])
                        break
                    
                    # [SENIOR FIX] Gatilho de Resiliência: Se após 15s o arquivo nem começou a baixar, ele repete o clique!
                    if checagem == 15 and len(arquivos) == 0:
                        try: driver.execute_script("arguments[0].click();", btn_baixar)
                        except: pass

                    time.sleep(1)

                if arquivo_encontrado:
                    time.sleep(1.5) 
                    nome_final = f"export_{doc['id']}_{nome_semestre}.xlsx"
                    caminho_final = os.path.join(DIR_EXPORTS_BASE, doc['id'], nome_final)
                    
                    if os.path.exists(caminho_final): os.remove(caminho_final)
                    shutil.move(arquivo_encontrado, caminho_final)
                    
                    docs_baixados_nesta_sessao.add(doc['id'])
                    baixou_algo = True
                    
                    for f in os.listdir(pasta_temp_thread):
                        try: os.remove(os.path.join(pasta_temp_thread, f))
                        except: pass
                else:
                    raise Exception("Download travou ou não foi concluído no tempo limite.")

            if baixou_algo:
                return True
            else:
                return "SKIPPED"

        except Exception as e:
            raise e
        finally:
            with self.lock:
                if driver in self.active_drivers:
                    self.active_drivers.remove(driver)
            matar_driver_forca_bruta(driver)
            
            if 'pasta_temp_thread' in locals() and os.path.exists(pasta_temp_thread):
                try: shutil.rmtree(pasta_temp_thread, ignore_errors=True)
                except: pass

    def _worker_pagamentos(self):
        driver = None
        pasta_temp_pgto_local = None
        try:
            if self.stop_event.is_set(): return
            self.log("⚙️ [Base Auxiliar] Acessando sistema financeiro...", "cyan")
            self.update_progress(2)
            
            ua = UserAgent()
            opcoes = webdriver.ChromeOptions()
            opcoes.add_argument(f"user-agent={ua.chrome}")
            opcoes.add_argument("--headless=new") 
            opcoes.add_argument("--window-size=1920,1080")
            opcoes.add_argument('--ignore-certificate-errors')
            opcoes.add_argument('--unsafely-treat-insecure-origin-as-secure=http://10.237.1.11')
            opcoes.add_argument("--disable-blink-features=AutomationControlled") 
            opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])

            uid_pasta = str(int(time.time() * 1000))[-6:]
            pasta_temp_pgto_local = os.path.join(DIR_RELATORIO_PAGAMENTOS, f"temp_pgto_{uid_pasta}")
            os.makedirs(pasta_temp_pgto_local, exist_ok=True)
            
            prefs = {
                "download.default_directory": os.path.abspath(pasta_temp_pgto_local), 
                "download.prompt_for_download": False, 
                "directory_upgrade": True,
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True
            }
            opcoes.add_experimental_option("prefs", prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opcoes)
            
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': os.path.abspath(pasta_temp_pgto_local)
            })
            
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
            
            anos = self.anos_ativos
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

                self.log(f"⚙️ [Base Auxiliar] Processando pacotes de {ano}...", "gray")
                
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
                        arquivo_encontrado = WebDriverWait(driver, 15).until(lambda d: [f for f in os.listdir(pasta_temp_pgto_local) if f.endswith(('.xls', '.xlsx')) and not f.endswith('.crdownload') and not f.endswith('.tmp')])
                        if arquivo_encontrado:
                            nome_arq = arquivo_encontrado[0]
                            origem = os.path.join(pasta_temp_pgto_local, nome_arq)
                            novo_nome = f"relatorio_{mes_valor}_{ano}.xls"
                            destino = os.path.join(f_path, novo_nome)
                            if os.path.exists(destino): os.remove(destino)
                            shutil.move(origem, destino)
                            for f in os.listdir(pasta_temp_pgto_local):
                                try: os.remove(os.path.join(pasta_temp_pgto_local, f))
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
                self.update_progress(0.2)
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
                
                self.update_progress(1.6)
                self.log("✅ [Base Auxiliar] Relatórios financeiros processados.", "#A0D468")

        except Exception as e:
            if self.stop_event.is_set():
                self.log("⚙️ [Base Auxiliar] Processo cancelado.", "yellow")
            else:
                self.log(f"⚙️ [Base Auxiliar] Erro na extração: {e}", "red")
        finally:
            if driver: 
                with self.lock:
                    if driver in self.active_drivers:
                        self.active_drivers.remove(driver)
                matar_driver_forca_bruta(driver)
            if pasta_temp_pgto_local and os.path.exists(pasta_temp_pgto_local): 
                try: shutil.rmtree(pasta_temp_pgto_local, ignore_errors=True)
                except: pass

    # =========================================================================
    # LÓGICA DE CONSOLIDAÇÃO PRINCIPAL
    # =========================================================================

    def consolidar_contratos_e_pendencias_com_correcao(self):
        if self.stop_event.is_set(): return False
        
        self.log("📂 [MERGE] Lendo dados exportados...", "cyan")
        self.target_progress = 50
        
        dict_raw_dfs = {}
        tipos_ativos = [d['id'] for d in self.docs_ativos]
        
        for doc_type in tipos_ativos:
            padrao = os.path.join(DIR_EXPORTS_BASE, doc_type, f"export_{doc_type}_*.xlsx")
            
            arquivos = glob.glob(padrao)
            lista_t = []
            for arq in arquivos:
                try:
                    dt = pd.read_excel(arq, dtype=str)
                    sem = os.path.basename(arq).replace(f"export_{doc_type}_", "").replace(".xlsx", "").replace("-", "/")
                    if "Semestre" in dt.columns: dt.drop(columns=["Semestre"], inplace=True)
                    dt.insert(0, "Semestre", sem)
                    if 'Inscrição' in dt.columns: dt['Inscrição'] = dt['Inscrição'].str.replace('.', '', regex=False).str.strip()
                    lista_t.append(dt)
                except: pass
                
            dfs_v = [d.dropna(axis=1, how='all') for d in lista_t if not d.empty]
            df_concat = pd.concat(dfs_v, ignore_index=True) if dfs_v else pd.DataFrame()
            
            if not df_concat.empty:
                for col in ['Inscrição', 'CPF', 'Gemini CPF']:
                    if col in df_concat.columns: df_concat[col] = df_concat[col].apply(converter_para_numero_real).astype('Int64')
                if 'Data Processamento' in df_concat.columns:
                    df_concat['Data Processamento'] = pd.to_datetime(df_concat['Data Processamento'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
                for col in ['Mensalidade S/ Desconto', 'Mensalidade C/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Gemini Mensalidade C/ Desconto']:
                    if col in df_concat.columns: df_concat[col] = pd.to_numeric(df_concat[col], errors='coerce').fillna(0.0)
                    else: df_concat[col] = 0.0
                df_concat['Dif. s/Desc.'] = df_concat['Mensalidade S/ Desconto'] - df_concat['Gemini Mensalidade S/ Desconto']
                df_concat['Dif. c/Desc.'] = np.where(df_concat['Gemini Mensalidade C/ Desconto'] != 0, df_concat['Mensalidade C/ Desconto'] - df_concat['Gemini Mensalidade C/ Desconto'], 0)
                if 'Status Gemini' in df_concat.columns: df_concat.rename(columns={'Status Gemini': 'IA_status'}, inplace=True)
                if 'Faculdade' in df_concat.columns: df_concat['Faculdade'] = df_concat['Faculdade'].apply(padronizar_texto)
                
            dict_raw_dfs[doc_type] = df_concat

        ordem_base = [
            'IA_status', 'Status Vínculo', 'Mudou IES?', 'IES Anterior', 'Mudou Bolsa?', 'Bolsa Anterior',
            'Semestre', 'Gemini Semestre', 'Inscrição', 'Bolsista', 'CPF', 'Gemini CPF', 'Gemini Inconsistencias', 
            'Faculdade', 'Curso', 'Mensalidade S/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Dif. s/Desc.', 
            'Mensalidade C/ Desconto', 'Gemini Mensalidade C/ Desconto', 'Dif. c/Desc.', 'Documento Tipo', 'Data Processamento'
        ]
        
        ordem_master = [
            'IA_status', 'Status Vínculo', 'Mudou IES?', 'IES Anterior', 'Mudou Bolsa?', 'Bolsa Anterior', 
            'Semestre', 'Gemini Semestre', 'Inscrição', 'Bolsista', 'CPF', 'Gemini CPF', 'Gemini Inconsistencias', 
            'Faculdade', 'Curso', 'tipo_bolsa_final', 'tipo_pagto', 'qtd_pagtos', 'valor_ultima_bolsa_paga', 
            'Mensalidade S/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Dif. s/Desc.', 
            'Mensalidade C/ Desconto', 'Gemini Mensalidade C/ Desconto', 'Dif. c/Desc.', 'Documento Tipo', 'Data Processamento'
        ]

        self.log("⚙️ [ANÁLISE] Identificando mudanças de trajetória escolar e estruturando arquivos...", "cyan")
        self.target_progress = 65

        df_todas_pendencias = []

        if os.path.exists(ARQUIVO_PAGAMENTOS_CONSOLIDADO):
            df_pag = pd.read_excel(ARQUIVO_PAGAMENTOS_CONSOLIDADO)
            if all(c in df_pag.columns for c in ['UNI_CODIGO', 'UNI_CPF', 'INS_NOME', 'SEMESTRE']):
                df_pag['INS_NOME'] = df_pag['INS_NOME'].apply(padronizar_texto)
                df_pag.sort_values(by=['UNI_CODIGO', 'SEMESTRE'], inplace=True)
                
                df_pag['PREV_BOLSA'] = df_pag.groupby('UNI_CODIGO')['TIPO_BOLSA'].shift(1)
                df_pag['PREV_IES'] = df_pag.groupby('UNI_CODIGO')['INS_NOME'].shift(1)
                def get_flag_mudanca(curr, prev): return "NÃO" if pd.isna(prev) else ("SIM" if curr != prev else "NÃO")
                def get_prev_value(curr, prev): return "-" if pd.isna(prev) else (prev if curr != prev else "-")
                df_pag['FLAG_BOLSA'] = df_pag.apply(lambda x: get_flag_mudanca(x['TIPO_BOLSA'], x['PREV_BOLSA']), axis=1)
                df_pag['ANT_BOLSA'] = df_pag.apply(lambda x: get_prev_value(x['TIPO_BOLSA'], x['PREV_BOLSA']), axis=1)
                df_pag['FLAG_IES'] = df_pag.apply(lambda x: get_flag_mudanca(x['INS_NOME'], x['PREV_IES']), axis=1)
                df_pag['ANT_IES'] = df_pag.apply(lambda x: get_prev_value(x['INS_NOME'], x['PREV_IES']), axis=1)

                df_pag['K_ID'] = df_pag['UNI_CODIGO'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_pag['K_SEM'] = df_pag['SEMESTRE'].astype(str).str.strip()
                df_pag['KEY_STR'] = df_pag['K_ID'] + "_" + df_pag['K_SEM']

                map_flag_bolsa = df_pag.drop_duplicates('KEY_STR', keep='last').set_index('KEY_STR')['FLAG_BOLSA'].to_dict()
                map_ant_bolsa = df_pag.drop_duplicates('KEY_STR', keep='last').set_index('KEY_STR')['ANT_BOLSA'].to_dict()
                map_flag_ies = df_pag.drop_duplicates('KEY_STR', keep='last').set_index('KEY_STR')['FLAG_IES'].to_dict()
                map_ant_ies = df_pag.drop_duplicates('KEY_STR', keep='last').set_index('KEY_STR')['ANT_IES'].to_dict()
                
                inscricoes_2026 = set(df_pag[df_pag['SEMESTRE'].astype(str).str.startswith('2026')]['K_ID'])

                df_pag_unique = df_pag.drop_duplicates(subset=['K_ID', 'K_SEM'], keep='last')
                mapa_ies_correcao = dict(zip(zip(df_pag_unique['K_ID'], df_pag_unique['K_SEM']), df_pag_unique['INS_NOME']))
                
                def corrigir_ies(row):
                    chave = (str(row['Inscrição']), str(row['Semestre']))
                    if chave in mapa_ies_correcao:
                        nova_ies = padronizar_texto(mapa_ies_correcao[chave])
                        if nova_ies: return nova_ies
                    return row['Faculdade']

                def aplicar_flags_vectorizado(df_target):
                    if df_target.empty: return df_target
                    temp_key = df_target['Inscrição'].astype(str) + '_' + df_target['Semestre'].astype(str)
                    df_target['Mudou IES?'] = temp_key.map(map_flag_ies).fillna("NÃO")
                    df_target['IES Anterior'] = temp_key.map(map_ant_ies).fillna("-")
                    df_target['Mudou Bolsa?'] = temp_key.map(map_flag_bolsa).fillna("NÃO")
                    df_target['Bolsa Anterior'] = temp_key.map(map_ant_bolsa).fillna("-")
                    df_target['Status Vínculo'] = df_target['Inscrição'].astype(str).apply(lambda x: 'ATIVO' if x in inscricoes_2026 else 'DESLIGADO')
                    return df_target

                self.log("📝 [ANÁLISE] Estruturando relatórios de pendências e divergências...", "cyan")

                mapa_nomes_docs = {
                    'CONTRATO': 'CONTRATO DE PRESTAÇÃO DE SERVIÇOS EDUCACIONAIS OU COMPROVANTE DE MATRÍCULA',
                    'FINANCIAMENTO': 'COMPROVANTE DE FINANCIAMENTO',
                    'OUTROS_BENEF': 'COMPROVANTE OUTROS BENEFÍCIOS',
                    'RIAF': 'RIAF – RESUMO DE INFORMAÇÕES ACADÊMICAS E FINANCEIRAS'
                }

                for doc_type in tipos_ativos:
                    df_atual = dict_raw_dfs.get(doc_type, pd.DataFrame())
                    nome_doc_oficial = mapa_nomes_docs.get(doc_type, doc_type)
                    
                    if not df_atual.empty:
                        df_atual['Documento Tipo'] = nome_doc_oficial
                    
                    if doc_type == 'CONTRATO':
                        arq_div = ARQUIVO_DIVERGENCIAS
                        arq_saida = ARQUIVO_SAIDA_CONTRATOS
                        aba_div_1 = "contratos_divergentes"
                        aba_div_2 = "pendentes_divergentes"
                        aba_saida = "rel_contratos_consolidado"
                    else:
                        pasta_dest = os.path.join(DIR_RELATORIO_ANUAL, doc_type)
                        if not os.path.exists(pasta_dest): os.makedirs(pasta_dest, exist_ok=True)
                        arq_div = os.path.join(pasta_dest, f"rel_{doc_type.lower()}_divergentes.xlsx")
                        arq_saida = os.path.join(pasta_dest, f"rel_{doc_type.lower()}.xlsx")
                        aba_div_1 = f"{doc_type.lower()[:15]}_div"
                        aba_div_2 = f"pendentes_div"
                        aba_saida = f"rel_{doc_type.lower()[:15]}_cons"

                    if not df_atual.empty:
                        df_atual_div = df_atual.copy()
                        df_atual_div['K_ID_DIV'] = df_atual_div['Inscrição'].astype(str).str.replace('.', '', regex=False).str.strip()
                        df_atual_div['K_CPF_DIV'] = df_atual_div['CPF'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False).str.strip().str.zfill(11)
                        df_atual_div['K_INS_DIV'] = df_atual_div['Faculdade']
                        df_atual_div['K_SEM_DIV'] = df_atual_div['Semestre'].astype(str).str.strip()
                        df_atual_div['KEY_DIV'] = df_atual_div['K_ID_DIV'] + "_" + df_atual_div['K_CPF_DIV'] + "_" + df_atual_div['K_INS_DIV'] + "_" + df_atual_div['K_SEM_DIV']
                        
                        set_atual_div = set(df_atual_div['KEY_DIV'])
                        
                        df_pag_diff = df_pag.copy()
                        df_pag_diff['K_CPF_DIV'] = df_pag_diff['UNI_CPF'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False).str.strip().str.zfill(11)
                        df_pag_diff['KEY_DIV'] = df_pag_diff['K_ID'] + "_" + df_pag_diff['K_CPF_DIV'] + "_" + df_pag_diff['INS_NOME'] + "_" + df_pag_diff['K_SEM']
                        
                        df_diff_div = df_pag_diff[~df_pag_diff['KEY_DIV'].isin(set_atual_div)].copy()
                        
                        if doc_type == 'RIAF':
                            df_diff_div = df_diff_div[df_diff_div['SEMESTRE'].astype(str).str[:4] >= '2026']
                        
                        df_pendentes_div = pd.DataFrame()
                        if not df_diff_div.empty:
                            df_pendentes_div['Semestre'] = df_diff_div['SEMESTRE']
                            df_pendentes_div['Inscrição'] = df_diff_div['UNI_CODIGO'].apply(converter_para_numero_real).astype('Int64')
                            df_pendentes_div['CPF'] = df_diff_div['UNI_CPF'].apply(converter_para_numero_real).astype('Int64')
                            df_pendentes_div['Faculdade'] = df_diff_div['INS_NOME']
                            for col_nome in ['UNI_NOME', 'NOME', 'ALUNO', 'NOME_ALUNO', 'BOLSISTA']:
                                if col_nome in df_diff_div.columns: df_pendentes_div['Bolsista'] = df_diff_div[col_nome]; break
                            for col_curso in ['CUR_NOME', 'CURSO', 'NOME_CURSO']:
                                if col_curso in df_diff_div.columns: df_pendentes_div['Curso'] = df_diff_div[col_curso]; break
                            df_pendentes_div['IA_status'] = 'Ausentes'
                            df_pendentes_div['Documento Tipo'] = nome_doc_oficial
                            df_pendentes_div.drop_duplicates(subset=['Inscrição', 'Semestre', 'Faculdade'], inplace=True)
                        
                        df_atual_div = aplicar_flags_vectorizado(df_atual_div)
                        df_pendentes_div = aplicar_flags_vectorizado(df_pendentes_div)
                        
                        writer_div = pd.ExcelWriter(arq_div, engine='xlsxwriter')
                        col_exist_cdiv = [c for c in ordem_base if c in df_atual_div.columns]
                        self._aplicar_estilo_tabela(writer_div, df_atual_div[col_exist_cdiv], aba_div_1)
                        if not df_pendentes_div.empty:
                            col_exist_pdiv = [c for c in ordem_base if c in df_pendentes_div.columns]
                            self._aplicar_estilo_tabela(writer_div, df_pendentes_div[col_exist_pdiv], aba_div_2)
                        writer_div.close()

                        df_atual['Faculdade'] = df_atual.apply(corrigir_ies, axis=1)
                        df_atual['KEY_EXISTENCIA'] = df_atual['Inscrição'].astype(str) + "_" + df_atual['Semestre'].astype(str)
                        atual_existentes = set(df_atual['KEY_EXISTENCIA'])
                        
                        df_diff = df_pag[~df_pag['KEY_STR'].isin(atual_existentes)].copy()
                        
                        if doc_type == 'RIAF':
                            df_diff = df_diff[df_diff['SEMESTRE'].astype(str).str[:4] >= '2026']
                        
                        df_pendentes_atual = pd.DataFrame()
                        if not df_diff.empty:
                            df_pendentes_atual['Semestre'] = df_diff['SEMESTRE']
                            df_pendentes_atual['Inscrição'] = df_diff['UNI_CODIGO'].apply(converter_para_numero_real).astype('Int64')
                            df_pendentes_atual['CPF'] = df_diff['UNI_CPF'].apply(converter_para_numero_real).astype('Int64')
                            df_pendentes_atual['Faculdade'] = df_diff['INS_NOME']
                            for col_nome in ['UNI_NOME', 'NOME', 'ALUNO', 'NOME_ALUNO', 'BOLSISTA']:
                                if col_nome in df_diff.columns: df_pendentes_atual['Bolsista'] = df_diff[col_nome]; break
                            for col_curso in ['CUR_NOME', 'CURSO', 'NOME_CURSO']:
                                if col_curso in df_diff.columns: df_pendentes_atual['Curso'] = df_diff[col_curso]; break
                            df_pendentes_atual['IA_status'] = 'Ausentes'
                            df_pendentes_atual['Documento Tipo'] = nome_doc_oficial
                            df_pendentes_atual.drop_duplicates(subset=['Inscrição', 'Semestre'], inplace=True)
                            
                        df_atual = aplicar_flags_vectorizado(df_atual)
                        df_pendentes_atual = aplicar_flags_vectorizado(df_pendentes_atual)
                            
                        writer_cont = pd.ExcelWriter(arq_saida, engine='xlsxwriter')
                        df_final_atual = pd.concat([df_atual, df_pendentes_atual], ignore_index=True) if not df_pendentes_atual.empty else df_atual.copy()
                        col_exist_cont = [c for c in ordem_base if c in df_final_atual.columns]
                        self._aplicar_estilo_tabela(writer_cont, df_final_atual[col_exist_cont], aba_saida)
                        writer_cont.close()
                        
                        dict_raw_dfs[doc_type] = df_atual.drop(columns=['KEY_EXISTENCIA'], errors='ignore')
                        if not df_pendentes_atual.empty:
                            df_todas_pendencias.append(df_pendentes_atual)

        self.target_progress = 75

        self.log("🔗 [SQL] Acessando DB e coletando informações...", "cyan")
        self.target_progress = 85
        
        lista_master = []
        for t, d in dict_raw_dfs.items():
            if not d.empty: lista_master.append(d)
        if df_todas_pendencias:
            lista_master.extend(df_todas_pendencias)
            
        if lista_master:
            df_master = pd.concat(lista_master, ignore_index=True)
            inscricoes_unicas = df_master['Inscrição'].dropna().astype(str).unique().tolist()
            
            DB_HOST, DB_USER, DB_PASS, DB_NAME = "10.237.1.16", "bi_ovg", "bi_ovg@#$124as65", "sibu"
            df_sql = pd.DataFrame()
            if inscricoes_unicas:
                try:
                    ids_formatados = ",".join(inscricoes_unicas)
                    query_otimizada = f"SELECT * FROM sibu.PY_financeiro_calculado_semestre_IM WHERE uni_codigo IN ({ids_formatados})"
                    db_engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}')
                    df_sql = pd.read_sql(query_otimizada, db_engine)
                    df_sql['uni_codigo'] = df_sql['uni_codigo'].astype(str).str.replace('.', '', regex=False).str.strip()
                    df_sql['semestre'] = df_sql['semestre'].astype(str).str.strip()
                    df_sql = self._contratos_normalizar_sql(df_sql)
                    df_sql['uni_codigo'] = df_sql['uni_codigo'].apply(converter_para_numero_real).astype('Int64')
                except: pass
                
            self.log("🔄 [MERGE] Cruzando dados e aplicando regras de negocio...", "cyan")
            self.target_progress = 95
            
            if not df_sql.empty:
                df_master = pd.merge(df_master, df_sql, left_on=['Inscrição', 'Semestre'], right_on=['uni_codigo', 'semestre'], how='left')
                df_master.drop(columns=['uni_codigo'], errors='ignore', inplace=True)
                
                cols_to_fill = ['tipo_bolsa_final']
                for col in cols_to_fill:
                    if col in df_master.columns:
                        df_master[col] = df_master[col].replace(['', None, '0', 0, '[NULL]'], np.nan)
                        df_master[col] = df_master.groupby('Inscrição')[col].transform(lambda x: x.ffill().bfill())
                        if col == 'tipo_bolsa_final': df_master[col] = df_master[col].fillna("SEM DADOS")
                
                df_master['qtd_pagtos'] = df_master['qtd_pagtos'].fillna(0)
                df_master['valor_ultima_bolsa_paga'] = df_master['valor_ultima_bolsa_paga'].fillna(0.0)
                if 'tipo_pagto' in df_master.columns: df_master['tipo_pagto'] = df_master['tipo_pagto'].fillna("")

            col_exist_master = [c for c in ordem_master if c in df_master.columns]
            df_master = df_master[col_exist_master]

            self.log("📊 [RELATÓRIO] Gerando resumo quantitativo por IES e Semestre...", "cyan")
            resumo_data = []
            
            for (ies, semestre), group in df_master.groupby(['Faculdade', 'Semestre']):
                tot_benef = group['Inscrição'].nunique()
                ativos = group[group['Status Vínculo'] == 'ATIVO']['Inscrição'].nunique()
                desligados = group[group['Status Vínculo'] == 'DESLIGADO']['Inscrição'].nunique()
                
                row = {
                    'IES': ies,
                    'Semestre': semestre,
                    'Total Beneficiários': tot_benef,
                    'Ativos': ativos,
                    'Desligados': desligados
                }
                
                for doc_k, doc_name in mapa_nomes_docs.items():
                    if doc_k in tipos_ativos:
                        mask_doc = group['Documento Tipo'] == doc_name
                        enviados = group[mask_doc & (group['IA_status'] != 'Ausentes')]['Inscrição'].nunique()
                        pendentes = group[mask_doc & (group['IA_status'] == 'Ausentes')]['Inscrição'].nunique()
                        
                        short_name = doc_k
                        if doc_k == 'OUTROS_BENEF': short_name = 'BENEFÍCIOS'
                        
                        row[f'Env. {short_name}'] = enviados
                        row[f'Pend. {short_name}'] = pendentes
                    
                resumo_data.append(row)
                
            df_resumo = pd.DataFrame(resumo_data)
            if not df_resumo.empty:
                df_resumo.sort_values(by=['IES', 'Semestre'], ascending=[True, True], inplace=True)

            writer_master = pd.ExcelWriter(ARQUIVO_MASTER_CONSOLIDADO, engine='xlsxwriter')
            self._aplicar_estilo_tabela(writer_master, df_master, "rel_documentos_consolidados")
            
            if not df_resumo.empty:
                self._aplicar_estilo_tabela(writer_master, df_resumo, "Resumo_Quantitativo")
                
            writer_master.close()

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
        
        if 'tipo_bolsa_final' in df_merged.columns:
            df_merged['tipo_bolsa_final'] = df_merged.groupby(col_id)['tipo_bolsa_final'].ffill().bfill()
            
        valores_para_zerar = {'qtd_pagtos': 0, 'valor_ultima_bolsa_paga': 0.0, 'tipo_pagto': ""}
        df_merged.fillna(valores_para_zerar, inplace=True)
        if 'tipo_bolsa_final' in df_merged.columns:
            df_merged['tipo_bolsa_final'] = df_merged['tipo_bolsa_final'].fillna("SEM DADOS")
        return df_merged

    def _aplicar_estilo_tabela(self, writer, df, nome_aba):
        nome_aba_excel = nome_aba[:31]

        df.to_excel(writer, sheet_name=nome_aba_excel, startrow=1, header=False, index=False)
        ws = writer.sheets[nome_aba_excel]
        
        ws.set_tab_color('#FF8C00')
        
        (mx_r, mx_c) = df.shape
        if mx_r == 0:
            ws.write_row(0, 0, df.columns)
            return
            
        ws.add_table(0, 0, mx_r, mx_c - 1, {
            'columns': [{'header': c} for c in df.columns], 
            'style': 'Table Style Medium 9', 
            'name': f'Tab_{nome_aba_excel.replace(" ", "_").replace(".", "")[:20]}' 
        })
        
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
                ws.conditional_format(1, i, mx_r, i, {'type': 'text', 'criteria': 'begins with', 'value': 'A', 'format': fmt_invalido})