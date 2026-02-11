"""
=============================================================================
ARQUIVO: src/analise_contratos.py
DESCRIÇÃO:
    Motor de automação (Selenium + SQL).
    
    VERSÃO GOLD (PERFORMANCE MÁXIMA):
    1. Paralelismo Agressivo: Delay reduzido para 1.5s (Abrem juntos).
    2. Barra Suave: Progresso granular (incrementos de 1% a cada etapa).
    3. UX: Logs mantidos e timeout de segurança ativo.
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
import platform
import tempfile
import random
from xlsxwriter.utility import xl_col_to_name
from urllib.parse import quote_plus
from sqlalchemy import create_engine

# --- SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# ADICIONE ESTA LINHA PARA SUMIR COM O AVISO:
pd.set_option('future.no_silent_downcasting', True)

# CONSTANTES
DIRETORIO_RAIZ = os.getcwd()
DIR_EXPORTS = os.path.join(DIRETORIO_RAIZ, "exports_semestrais", "CONTRATOS")
DIR_RELATORIO_FINAL = os.path.join(DIRETORIO_RAIZ, "relatorio_anual", "CONTRATOS")
ARQUIVO_SAIDA = os.path.join(DIR_RELATORIO_FINAL, "relatorio_anual_contratos.xlsx")

for pasta in [DIR_EXPORTS, DIR_RELATORIO_FINAL]:
    if not os.path.exists(pasta):
        os.makedirs(pasta, exist_ok=True)

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
        self.logs = []
        self.semestres = [
            {"label": "2025-1", "value": "2025-1##@@2025-1"},
            {"label": "2025-2", "value": "2025-2##@@2025-2"},
            {"label": "2026-1", "value": "2026-1##@@2026-1"},
        ]
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.arquivo_gerado = None
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
            self.progress += amount
            if self.progress > 99: self.progress = 99

    def get_status(self):
        with self.lock:
            return {
                "progress": int(self.progress),
                "logs": list(self.logs),
                "is_running": self.is_running,
                "arquivo_gerado": self.arquivo_gerado,
                "status_final": self.status_final
            }

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.progress = 0
        self.logs = [] 
        self.arquivo_gerado = None
        self.status_final = ""
        self.active_drivers = []
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run_process)
        self.thread.start()

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.log("!!! PARANDO FORÇADAMENTE !!!", "red")
            with self.lock:
                for driver in self.active_drivers:
                    try: driver.quit()
                    except: pass
                self.active_drivers = []

    def _run_process(self):
        try:
            self.log("🚀 MÓDULO INICIADO (Modo Turbo)", "white")
            
            # --- FASE 1: DOWNLOAD PARALELO (0% -> 80%) ---
            # A responsabilidade de atualizar a barra agora é das threads individuais
            # para dar a sensação de 1% a 1%.
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Delay mínimo (1.5s) apenas para não colidir o driver inicial
                futures = {
                    executor.submit(self._baixar_semestre_safe, s, idx): s 
                    for idx, s in enumerate(self.semestres)
                }
                
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set(): break
                    sem = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self.log(f"❌ Erro em {sem['label']}: {e}", "red")

            if self.stop_event.is_set():
                self.is_running = False
                return

            # --- FASE 2: CONSOLIDAÇÃO (80% -> 100%) ---
            self.progress = 80 # Garante sincronia antes da fase final
            self.log("📦 CONSOLIDANDO DADOS...", "#FFCE54")
            
            sucesso = self._gerar_relatorio_final_formatado()
            
            elapsed = time.time() - self.start_time
            tempo_fmt = str(datetime.timedelta(seconds=int(elapsed)))

            if sucesso:
                self.progress = 100
                self.status_final = "success"
                self.arquivo_gerado = ARQUIVO_SAIDA
                self.log(f"🏆 FINALIZADO EM {tempo_fmt}", "#A0D468")
            else:
                self.status_final = "error"
                self.log("❌ Falha na geração do relatório.", "red")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log(f"🔥 Erro Crítico: {str(e)}", "red")
                self.status_final = "error"
        finally:
            self.is_running = False
            with self.lock:
                for driver in self.active_drivers:
                    try: driver.quit()
                    except: pass
                self.active_drivers = []

    def _baixar_semestre_safe(self, semestre, index):
        MAX_RETRIES = 3
        nome = semestre['label']
        
        # Delay reduzido para 1.5s (Quase simultâneo, mas seguro)
        delay = index * 1.5
        if delay > 0:
            time.sleep(delay)

        for i in range(1, MAX_RETRIES + 1):
            if self.stop_event.is_set(): return
            try:
                self.log(f"▶️ [{nome}] Iniciando...", "cyan")
                self._selenium_download(semestre)
                self.log(f"✅ [{nome}] Download OK!", "#A0D468")
                return
            except Exception as e:
                if self.stop_event.is_set(): return
                self.log(f"⚠️ [{nome}] Falha: {str(e)[:50]}...", "yellow")
                if i == MAX_RETRIES: 
                    self.log(f"❌ [{nome}] DESISTINDO.", "red")
                    raise e
                time.sleep(5)

    def _executor_clique(self, driver, elemento):
        driver.execute_script("arguments[0].click();", elemento)

    def _selenium_download(self, semestre):
        # Cada etapa incrementa um pouquinho a barra
        # Total de etapas ~8. Total Threads 3. 
        # (8 * 3 * 3%) = ~72%. Perfeito para cobrir até os 80%.
        STEP_VAL = 3 
        
        pasta_temp = os.path.join(DIR_EXPORTS, f"temp_{semestre['label']}")
        if os.path.exists(pasta_temp): shutil.rmtree(pasta_temp)
        os.makedirs(pasta_temp)

        user_data_dir = tempfile.mkdtemp()

        # PREFS ANTI-BLOQUEIO
        prefs = {
            "download.default_directory": pasta_temp,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True, 
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }

        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless=new") 
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument('--ignore-certificate-errors')
        opts.add_argument('--unsafely-treat-insecure-origin-as-secure=http://10.237.1.11')
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--log-level=3")
        
        if platform.system() == "Linux":
            opts.binary_location = "/usr/bin/google-chrome"
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-software-rasterizer")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--remote-debugging-port=0") 

        opts.add_argument(f"--user-data-dir={user_data_dir}")
        opts.add_experimental_option("prefs", prefs)

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(180)
            
            with self.lock:
                self.active_drivers.append(driver)

            wait = WebDriverWait(driver, 180)
            label = f"[{semestre['label']}]"

            # 1. ACESSO
            try: driver.get("http://10.237.1.11/pbu")
            except: 
                time.sleep(2)
                driver.get("http://10.237.1.11/pbu")
            self.update_progress(STEP_VAL)
            
            # 2. LOGIN
            self._check_stop()
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#id_sc_field_login"))).send_keys("ihan.santos")
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))).send_keys("M@vis-08")
            btn_login = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#login1 > form > div.submit > input")))
            self._executor_clique(driver, btn_login)
            self.update_progress(STEP_VAL)
            
            # 3. MENU
            self._check_stop()
            btn_menu1 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#item_163")))
            self._executor_clique(driver, btn_menu1)
            time.sleep(0.5)
            btn_menu2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#item_165")))
            self._executor_clique(driver, btn_menu2)
            
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "menu_item_165_iframe")))
            
            # 4. FILTRO
            self._check_stop()
            el_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#SC_semestre")))
            sel = Select(el_select)
            try: sel.select_by_value(semestre['value'])
            except: sel.select_by_visible_text(semestre['label'])
            
            btn_pesq = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#sc_b_pesq_bot")))
            self._executor_clique(driver, btn_pesq)
            self.update_progress(STEP_VAL)
            time.sleep(2)
            
            # 5. DOCUMENTO
            self._check_stop()
            self.log(f"{label} 📄 Solicitando Relatório...", "gray")
            try:
                btn_expand = driver.find_element(By.CSS_SELECTOR, "#div_int_documento_tipo .dn-expand-button")
                self._executor_clique(driver, btn_expand)
                time.sleep(0.5)
            except: pass
            
            lbl_contrato = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'CONTRATO DE PRESTAÇÃO')]")))
            self._executor_clique(driver, lbl_contrato)
            self.update_progress(STEP_VAL)
            
            try:
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI.blockOverlay")))
            except: pass
            time.sleep(1)

            # 6. EXPORTAR
            self._check_stop()
            btn_grp = wait.until(EC.presence_of_element_located((By.ID, "sc_btgp_btn_group_1_top")))
            self._executor_clique(driver, btn_grp)
            
            btn_xls = wait.until(EC.presence_of_element_located((By.ID, "xls_top")))
            self._executor_clique(driver, btn_xls)
            self.update_progress(STEP_VAL)
            
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "TB_iframeContent")))
            btn_ok = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#bok")))
            self._executor_clique(driver, btn_ok)

            # 7. DOWNLOAD WAIT
            self.log(f"{label} ⬇️ Baixando arquivo...", "cyan")
            inicio = time.time()
            clicado = False
            
            while time.time() - inicio < 300:
                self._check_stop()
                try:
                    driver.switch_to.default_content()
                    try: driver.switch_to.frame("menu_item_165_iframe")
                    except: pass
                    try: driver.switch_to.frame("TB_iframeContent")
                    except: pass
                    
                    btns = driver.find_elements(By.XPATH, "//*[@id='idBtnDown'] | //a[contains(., 'Baixar')]")
                    if btns:
                        self._executor_clique(driver, btns[0])
                        clicado = True
                        self.update_progress(STEP_VAL)
                        break
                except: pass
                time.sleep(2)
            
            if not clicado: raise Exception("Botão de download não apareceu (5 min).")

            # 8. VALIDAÇÃO INTELIGENTE
            tempo_espera = 0
            while tempo_espera < 240:
                self._check_stop()
                if not os.path.exists(pasta_temp): 
                    time.sleep(1); tempo_espera +=1; continue

                arquivos = os.listdir(pasta_temp)
                
                # Ignora temporários
                if any(f.endswith('.crdownload') or f.endswith('.tmp') for f in arquivos):
                    time.sleep(1)
                    tempo_espera += 1
                    continue
                
                finais = [f for f in arquivos if f.endswith('.xlsx') or f.endswith('.xls')]
                if finais:
                    time.sleep(1)
                    shutil.move(os.path.join(pasta_temp, finais[0]), os.path.join(DIR_EXPORTS, f"export_{semestre['label']}.xlsx"))
                    shutil.rmtree(pasta_temp)
                    self.update_progress(5) # Bônus de conclusão
                    return True
                
                time.sleep(1)
                tempo_espera += 1
            
            raise Exception("Timeout: Arquivo travou no download.")

        except Exception as e:
            raise e
        finally:
            if driver:
                with self.lock:
                    if driver in self.active_drivers:
                        self.active_drivers.remove(driver)
                try: driver.quit()
                except: pass
            try: shutil.rmtree(user_data_dir, ignore_errors=True)
            except: pass

    def _check_stop(self):
        if self.stop_event.is_set():
            raise Exception("Interrompido pelo usuário")

    def _gerar_relatorio_final_formatado(self):
        try:
            self.log("🔗 Conectando ao Banco de Dados...", "cyan")
            self.update_progress(3)
            
            DB_USER, DB_PASS = "bi_ovg", quote_plus("bi_ovg@#$124as65")
            connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@10.237.1.16/sibu"
            eng = create_engine(connection_string)
            
            df_sql = pd.read_sql("SELECT * FROM sibu.PY_financeiro_calculado_semestre_IM", eng)
            if not df_sql.empty:
                df_sql['uni_codigo'] = df_sql['uni_codigo'].astype(str).str.replace('.', '', regex=False).str.strip()
                df_sql['semestre'] = df_sql['semestre'].astype(str).str.strip()
                df_sql = self._normalizar_semestres_faltantes_sql(df_sql)

            self.log("📂 Carregando Excel...", "cyan")
            dfs = []
            files = glob.glob(os.path.join(DIR_EXPORTS, "export_*.xlsx"))
            files.sort()
            
            if not files:
                self.log("⚠️ Nenhum arquivo Excel.", "yellow")
                return False

            for f in files:
                sem = os.path.basename(f).replace("export_","").replace(".xlsx","").replace("-","/")
                try:
                    d = pd.read_excel(f, dtype={'CPF': str, 'Gemini CPF': str, 'Inscrição': str})
                    if "Semestre" in d.columns: d.drop(columns=["Semestre"], inplace=True)
                    d.insert(0, "Semestre", sem)
                    if 'Inscrição' in d.columns:
                        d['Inscrição'] = d['Inscrição'].astype(str).str.replace('.','', regex=False).str.strip()
                    dfs.append(d)
                except Exception as ex:
                    self.log(f"Erro ler {sem}: {ex}", "red")

            if not dfs: return False
            
            df_final = pd.concat(dfs, ignore_index=True)
            self.update_progress(3)
            
            def limpar_cpf(v):
                if pd.isna(v) or str(v).strip() == '': return ""
                s = str(v).replace('.0', '')
                s = ''.join(filter(str.isdigit, s))
                return s.zfill(11)

            if 'CPF' in df_final.columns: df_final['CPF'] = df_final['CPF'].apply(limpar_cpf)
            if 'Gemini CPF' in df_final.columns: df_final['Gemini CPF'] = df_final['Gemini CPF'].apply(limpar_cpf)

            self.log("🔄 Cruzando informações...", "cyan")
            if not df_sql.empty:
                df_final = pd.merge(df_final, df_sql, left_on=['Inscrição','Semestre'], right_on=['uni_codigo','semestre'], how='left')
                df_final.drop(columns=['uni_codigo'], errors='ignore', inplace=True)
            
            df_final.sort_values(by=['Inscrição', 'Semestre'], ascending=[True, True], inplace=True)

            cols_to_fill = ['tipo_bolsa_final']
            for col in cols_to_fill:
                if col in df_final.columns:
                    df_final[col] = df_final[col].replace(['', None, '0', 0, '[NULL]'], np.nan)
                    df_final[col] = df_final.groupby('Inscrição')[col].transform(lambda x: x.ffill().bfill())
                    if col == 'tipo_bolsa_final':
                         df_final[col] = df_final[col].fillna("SEM DADOS")

            df_final['qtd_pagtos'] = df_final['qtd_pagtos'].fillna(0)
            df_final['valor_ultima_bolsa_paga'] = df_final['valor_ultima_bolsa_paga'].fillna(0.0)
            if 'tipo_pagto' in df_final.columns:
                df_final['tipo_pagto'] = df_final['tipo_pagto'].fillna("")

            cols_financeiras = ['Mensalidade S/ Desconto', 'Mensalidade C/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Gemini Mensalidade C/ Desconto']
            for col in cols_financeiras:
                if col in df_final.columns: df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0.0)
                else: df_final[col] = 0.0

            df_final['Dif. s/Desc.'] = df_final['Mensalidade S/ Desconto'] - df_final['Gemini Mensalidade S/ Desconto']
            df_final['Dif. c/Desc.'] = np.where(df_final['Gemini Mensalidade C/ Desconto'] != 0, df_final['Mensalidade C/ Desconto'] - df_final['Gemini Mensalidade C/ Desconto'], 0)

            if 'Status Gemini' in df_final.columns: df_final.rename(columns={'Status Gemini': 'IA_status'}, inplace=True)

            ordem = ['IA_status', 'Semestre', 'Gemini Semestre', 'Inscrição', 'Bolsista', 'CPF', 'Gemini CPF', 'Gemini Inconsistencias', 
                     'Faculdade', 'Curso', 
                     'tipo_bolsa_final', 'tipo_pagto', 
                     'qtd_pagtos', 'valor_ultima_bolsa_paga', 'Mensalidade S/ Desconto', 'Gemini Mensalidade S/ Desconto', 'Dif. s/Desc.', 
                     'Mensalidade C/ Desconto', 'Gemini Mensalidade C/ Desconto', 'Dif. c/Desc.', 'Documento Tipo', 'Data Processamento']
            
            colunas_existentes = [c for c in ordem if c in df_final.columns]
            df_final = df_final[colunas_existentes]

            self.log("🎨 Formatando Excel...", "cyan")
            self.update_progress(5)
            
            writer = pd.ExcelWriter(ARQUIVO_SAIDA, engine='xlsxwriter')
            workbook = writer.book
            
            fmt_texto = workbook.add_format({'num_format': '@'}) 
            fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
            fmt_inteiro = workbook.add_format({'num_format': '0'})
            fmt_alerta = workbook.add_format({'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
            fmt_valido = workbook.add_format({'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
            fmt_invalido = workbook.add_format({'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})

            anos_unicos = sorted(df_final['Semestre'].str.split('/').str[0].unique())

            for ano in anos_unicos:
                df_aba = df_final[df_final['Semestre'].str.startswith(str(ano))].copy()
                nome_aba = f"Contratos {ano}"
                
                df_aba.to_excel(writer, sheet_name=nome_aba, startrow=1, header=False, index=False)
                worksheet = writer.sheets[nome_aba]
                
                (max_row, max_col) = df_aba.shape
                
                worksheet.add_table(0, 0, max_row, max_col - 1, {
                    'columns': [{'header': c} for c in df_aba.columns], 
                    'style': 'Table Style Medium 9', 
                    'name': f'Tabela_{ano}'
                })

                lista_cols_moeda = cols_financeiras + ['Dif. s/Desc.', 'Dif. c/Desc.', 'valor_ultima_bolsa_paga']
                faixas_cpfs = []

                for i, col in enumerate(df_aba.columns):
                    largura = 15
                    try:
                        largura = max(df_aba[col].astype(str).map(len).max(), len(str(col))) + 2
                        largura = min(largura, 60)
                    except: pass

                    if col in lista_cols_moeda: worksheet.set_column(i, i, largura, fmt_moeda)
                    elif col == 'qtd_pagtos': worksheet.set_column(i, i, largura, fmt_inteiro)
                    elif 'CPF' in col or col == 'Inscrição':
                        worksheet.set_column(i, i, largura + 3, fmt_texto)
                        faixas_cpfs.append(f"{xl_col_to_name(i)}2:{xl_col_to_name(i)}{max_row+1}")
                    else: worksheet.set_column(i, i, largura)

                    if col in ['Dif. s/Desc.', 'Dif. c/Desc.']:
                        worksheet.conditional_format(1, i, max_row, i, {'type': 'cell', 'criteria': '!=', 'value': 0, 'format': fmt_alerta})
                    
                    if col == 'IA_status':
                        worksheet.conditional_format(1, i, max_row, i, {'type': 'text', 'criteria': 'begins with', 'value': 'V', 'format': fmt_valido})
                        worksheet.conditional_format(1, i, max_row, i, {'type': 'text', 'criteria': 'begins with', 'value': 'I', 'format': fmt_invalido})

                if faixas_cpfs:
                    worksheet.ignore_errors({'number_stored_as_text': ' '.join(faixas_cpfs)})

            writer.close()
            return True
            
        except Exception as e:
            self.log(f"Erro formatando Excel: {e}", "red")
            return False

    def _normalizar_semestres_faltantes_sql(self, df):
        if df.empty: return df
        df['uni_codigo'] = df['uni_codigo'].astype(str).str.strip()
        col_id, col_sem = 'uni_codigo', 'semestre'
        semestres_obrigatorios = ['2025/1', '2025/2']
        
        alunos = df[col_id].unique()
        index = pd.MultiIndex.from_product([alunos, semestres_obrigatorios], names=[col_id, col_sem])
        df_skeleton = pd.DataFrame(index=index).reset_index()
        
        df_merged = pd.merge(df_skeleton, df, on=[col_id, col_sem], how='left')
        
        col_copia = ['tipo_bolsa_final']
        if 'tipo_bolsa_final' in df_merged.columns:
            df_merged[col_copia] = df_merged.groupby(col_id)[col_copia].ffill().bfill()
            df_merged['tipo_bolsa_final'] = df_merged['tipo_bolsa_final'].fillna("SEM DADOS")
        
        vals_zerar = {'qtd_pagtos': 0, 'valor_ultima_bolsa_paga': 0.0, 'tipo_pagto': ""}
        df_merged.fillna(vals_zerar, inplace=True)
        return df_merged