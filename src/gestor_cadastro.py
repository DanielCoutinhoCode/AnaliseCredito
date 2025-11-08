import pandas as pd
import requests
import os
import sys
from datetime import datetime, timedelta
import config # <-- IMPORTA A NOSSA CONFIGURAÇÃO

class GestorCadastro:
    
    def __init__(self):
        # Usa as constantes do config.py
        self.url_cadastro_cvm = config.URL_CADASTRO_CVM
        self.diretorio_cadastro_raw = config.CAMINHO_RAW_CADASTRO_CVM
        self.caminho_arquivo_cvm = config.ARQUIVO_CADASTRO_CVM
        self.caminho_mapa_ticker = config.ARQUIVO_MAPA_TICKER_CNPJ
        
        self.df_cadastro_cvm = None 
        self.df_mapa_ticker = None 
        
        os.makedirs(self.diretorio_cadastro_raw, exist_ok=True)
        print("GestorCadastro iniciado.")

    def _carregar_mapa_ticker(self):
        if self.df_mapa_ticker is not None:
            return True 
            
        try:
            self.df_mapa_ticker = pd.read_csv(
                self.caminho_mapa_ticker,
                sep=';', 
                encoding='utf-8-sig', 
                header=None, 
                names=['CNPJ', 'TICKER', 'NOME_EMPRESA'] 
            )
            self.df_mapa_ticker['TICKER'] = self.df_mapa_ticker['TICKER'].astype(str).str.strip()
            self.df_mapa_ticker['CNPJ'] = self.df_mapa_ticker['CNPJ'].astype(str).str.strip()
            print("Mapa Ticker <-> CNPJ carregado com sucesso.")
            return True
        except FileNotFoundError:
            print(f"ERRO CRÍTICO: Mapa Ticker <-> CNPJ não encontrado em: {self.caminho_mapa_ticker}")
            return False
        except Exception as e:
            print(f"ERRO ao ler o mapa Ticker <-> CNPJ: {e}")
            return False

    def _baixar_cadastro_cvm_se_necessario(self):
        precisa_baixar = True
        if os.path.exists(self.caminho_arquivo_cvm):
            data_modificacao = datetime.fromtimestamp(os.path.getmtime(self.caminho_arquivo_cvm))
            if data_modificacao.date() == datetime.now().date():
                precisa_baixar = False
                print("Usando arquivo de cadastro CVM (cache de hoje).")
        
        if precisa_baixar:
            print(f"Baixando novo arquivo de cadastro CVM de: {self.url_cadastro_cvm}")
            try:
                response = requests.get(self.url_cadastro_cvm)
                response.raise_for_status()
                with open(self.caminho_arquivo_cvm, 'wb') as f:
                    f.write(response.content)
                print(f"Arquivo de cadastro CVM salvo em: {self.caminho_arquivo_cvm}")
            except requests.exceptions.RequestException as e:
                print(f"ERRO CRÍTICO: Falha ao baixar o arquivo de cadastro CVM: {e}")
                return False
        return True

    def _carregar_cadastro_cvm(self):
        if self.df_cadastro_cvm is not None:
            return True 
        if not self._baixar_cadastro_cvm_se_necessario():
            return False
        try:
            self.df_cadastro_cvm = pd.read_csv(
                self.caminho_arquivo_cvm,
                sep=';',
                encoding='latin1'
            )
            self.df_cadastro_cvm = self.df_cadastro_cvm[self.df_cadastro_cvm['SIT'] == 'ATIVO'].copy()
            print(f"Cadastro CVM (CNPJ -> Setor) carregado e filtrado. Total de {len(self.df_cadastro_cvm)} empresas ativas.")
            return True
        except FileNotFoundError:
            print(f"ERRO: Arquivo de cadastro CVM {self.caminho_arquivo_cvm} não encontrado.")
            return False
        except Exception as e:
            print(f"ERRO ao ler o arquivo de cadastro CVM: {e}")
            return False

    def encontrar_cnpj_por_ticker(self, ticker):
        if not self._carregar_mapa_ticker(): 
            return None
        try:
            cnpj = self.df_mapa_ticker.loc[self.df_mapa_ticker['TICKER'] == ticker.upper(), 'CNPJ'].iloc[0]
            return cnpj
        except IndexError:
            print(f"AVISO: Ticker {ticker} não encontrado no 'mapa_ticker_cnpj.csv'.")
            return None
        except Exception as e:
            print(f"ERRO ao procurar CNPJ por Ticker: {e}")
            return None
            
    def encontrar_ticker_por_cnpj(self, cnpj_alvo):
        if not self._carregar_mapa_ticker():
            return None
        try:
            ticker = self.df_mapa_ticker.loc[self.df_mapa_ticker['CNPJ'] == cnpj_alvo, 'TICKER'].iloc[0]
            return ticker
        except IndexError:
            return None
        except Exception as e:
            print(f"ERRO ao procurar Ticker por CNPJ: {e}")
            return None

    def encontrar_setor_por_cnpj(self, cnpj_alvo):
        if not self._carregar_cadastro_cvm(): 
            return None
        try:
            setor = self.df_cadastro_cvm.loc[self.df_cadastro_cvm['CNPJ_CIA'] == cnpj_alvo, 'SETOR_ATIV'].iloc[0]
            return setor
        except IndexError:
            print(f"AVISO: CNPJ {cnpj_alvo} não encontrado no cadastro CVM de empresas ativas.")
            return None
        except Exception as e:
            print(f"ERRO ao procurar setor por CNPJ: {e}")
            return None
            
    def encontrar_pares_por_setor(self, setor):
        if not self._carregar_cadastro_cvm(): 
            return None
        try:
            df_pares = self.df_cadastro_cvm[self.df_cadastro_cvm['SETOR_ATIV'] == setor].copy()
            df_pares['NOME_FINAL'] = df_pares['DENOM_COMERC'].fillna(df_pares['DENOM_SOCIAL'])
            pares_dict = dict(zip(df_pares['NOME_FINAL'], df_pares['CNPJ_CIA']))
            return pares_dict
        except Exception as e:
            print(f"ERRO ao procurar pares por setor: {e}")
            return None