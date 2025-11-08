import pandas as pd
import requests
import os
import zipfile
from datetime import datetime
import io
import config

class ColetorDadosCVM:
    
    def __init__(self):
        self.url_base = config.URL_BASE_DFP_CVM
        self.diretorio_saida_raw = config.CAMINHO_RAW_BALANCOS_CVM
        
        os.makedirs(self.diretorio_saida_raw, exist_ok=True)
        print(f"ColetorDadosCVM iniciado. Saída em: {self.diretorio_saida_raw}")

    # --- MÉTODO ATUALIZADO (NÃO DESCOMPACTA MAIS) ---
    def baixar_demonstrativos(self, ano, tipo_doc="DFP"):
        """
        Baixa os arquivos .ZIP da CVM, se ainda não existirem.
        NÃO descompacta mais, para poupar espaço em disco na nuvem.
        """
        
        url = f"{self.url_base}{tipo_doc.upper()}/DADOS/{tipo_doc.lower()}_cia_aberta_{ano}.zip"
        nome_arquivo_zip = f"{tipo_doc.lower()}_cia_aberta_{ano}.zip"
        self.caminho_saida_zip = os.path.join(self.diretorio_saida_raw, nome_arquivo_zip)
        
        print(f"\nVerificando arquivo ZIP para {tipo_doc} {ano}...")
        
        # 1. Se o ZIP já existe, não faz nada.
        if os.path.exists(self.caminho_saida_zip):
            print(f"Arquivo ZIP de {ano} já existe. Pulando download.")
            return True # Sucesso, o arquivo está pronto

        # 2. Se não, baixa o arquivo
        try:
            resposta = requests.get(url, stream=True)
            resposta.raise_for_status() 

            print(f"Baixando de {url}...")
            with open(self.caminho_saida_zip, 'wb') as f:
                for pedaco in resposta.iter_content(chunk_size=8192):
                    f.write(pedaco)
            print(f"Arquivo ZIP salvo em: {self.caminho_saida_zip}")
            return True # Sucesso

        except requests.exceptions.RequestException as e:
            print(f"ERRO ao baixar o arquivo: {e}")
            return False