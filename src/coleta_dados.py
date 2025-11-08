import pandas as pd
import requests
import os
import zipfile
from datetime import datetime
import io
import config # <-- IMPORTA A NOSSA CONFIGURAÇÃO

class ColetorDadosCVM:
    
    def __init__(self):
        self.url_base = config.URL_BASE_DFP_CVM
        self.diretorio_saida_raw = config.CAMINHO_RAW_BALANCOS_CVM
        
        os.makedirs(self.diretorio_saida_raw, exist_ok=True)
        print(f"ColetorDadosCVM iniciado. Saída em: {self.diretorio_saida_raw}")

    def baixar_demonstrativos(self, ano, tipo_doc="DFP", deletar_zip=True):
        url = f"{self.url_base}{tipo_doc.upper()}/DADOS/{tipo_doc.lower()}_cia_aberta_{ano}.zip"
        nome_arquivo_zip = f"{tipo_doc.lower()}_cia_aberta_{ano}.zip"
        caminho_saida_zip = os.path.join(self.diretorio_saida_raw, nome_arquivo_zip)
        
        print(f"\nIniciando processo para {tipo_doc} {ano}...")
        
        caminho_csv_verificacao = os.path.join(self.diretorio_saida_raw, f"{tipo_doc.lower()}_cia_aberta_dre_con_{ano}.csv")
        if os.path.exists(caminho_csv_verificacao):
            print(f"Dados de {ano} já parecem estar descompactados. Pulando download.")
            return True 

        try:
            resposta = requests.get(url, stream=True)
            resposta.raise_for_status() 

            print(f"Baixando de {url}...")
            with open(caminho_saida_zip, 'wb') as f:
                for pedaco in resposta.iter_content(chunk_size=8192):
                    f.write(pedaco)
            print(f"Arquivo salvo em: {caminho_saida_zip}")

        except requests.exceptions.RequestException as e:
            print(f"ERRO ao baixar o arquivo: {e}")
            return False 

        try:
            print(f"Descompactando {caminho_saida_zip}...")
            with zipfile.ZipFile(caminho_saida_zip, 'r') as zip_ref:
                zip_ref.extractall(self.diretorio_saida_raw)
            print(f"Arquivos de {ano} descompactados com sucesso.")
            
        except zipfile.BadZipFile:
            print(f"ERRO: O arquivo baixado não é um ZIP válido: {caminho_saida_zip}")
            return False

        if deletar_zip:
            try:
                os.remove(caminho_saida_zip)
                print(f"Arquivo ZIP {caminho_saida_zip} deletado.")
            except OSError as e:
                print(f"ERRO ao deletar o ZIP: {e}")
                
        return True