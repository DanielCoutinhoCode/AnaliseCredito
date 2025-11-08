import pandas as pd
import os
import sys
import config
import numpy as np
import zipfile 
from coleta_dados import ColetorDadosCVM

class CalculadoraIndicadores:
    """
    OTIMIZAÇÃO 4 (Nuvem / Baixa Memória): 
    Esta classe agora lê os CSVs de dentro do ZIP em "chunks" (pedaços)
    para evitar carregar arquivos gigantes na RAM,
    prevenindo "crashes" de memória no Streamlit Cloud.
    """
    
    def __init__(self, coletor: ColetorDadosCVM):
        """
        Construtor. Recebe uma instância do ColetorDadosCVM.
        """
        self.diretorio_dados_raw = config.CAMINHO_RAW_BALANCOS_CVM
        self.MAPA_CONTAS = config.MAPA_CONTAS_CVM
        self.coletor = coletor
        
        print(f"CalculadoraIndicadores iniciada (Modo Baixa Memória).")
        
        # --- O CACHE DE DATAFRAME FOI REMOVIDO ---
        # (Não podemos guardar os DataFrames gigantes na RAM)
    
    # --- O MÉTODO _carregar_dados_do_ano FOI REMOVIDO ---

    def pegar_valor_conta(self, df_filtrado, cd_conta):
        """
        Método auxiliar (não muda)
        """
        try:
            valor = df_filtrado.loc[df_filtrado['CD_CONTA'] == cd_conta, 'VL_CONTA'].iloc[0]
            return valor
        except IndexError:
            raise ValueError(f"Conta essencial {cd_conta} não encontrada")
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao buscar conta {cd_conta}: {e}")

    # --- MÉTODO _ler_dados_do_zip (NOVO MÉTODO OTIMIZADO) ---
    def _ler_dados_do_zip(self, ano, cnpj, tipo_doc="DFP"):
        """
        Lógica de leitura de baixa memória:
        1. Garante que o ZIP do ano existe (baixa se necessário).
        2. Tenta ler os 3 arquivos (DRE, BPA, BPP) em PEDAÇOS (chunks) de dentro do ZIP,
           filtrando pelo CNPJ e 'ÚLTIMO' exercício.
        3. Tenta o fallback de CONSOLIDADO para INDIVIDUAL.
        """
        
        # 1. Garantir que o ZIP existe
        if not self.coletor.baixar_demonstrativos(ano, tipo_doc):
            print(f"Falha ao baixar o ZIP do ano {ano}. Cálculo para {cnpj} cancelado.")
            return None, None, None, None 
            
        caminho_zip = self.coletor.caminho_saida_zip
        
        try:
            zf = zipfile.ZipFile(caminho_zip)
        except Exception as e:
            print(f"ERRO: Não foi possível abrir o arquivo ZIP: {e}")
            return None, None, None, None
            
        # Nomes dos arquivos dentro do ZIP
        arquivos_por_tipo = {
            "CONSOLIDADO": {
                'dre': f"{tipo_doc.lower()}_cia_aberta_dre_con_{ano}.csv",
                'bpa': f"{tipo_doc.lower()}_cia_aberta_bpa_con_{ano}.csv",
                'bpp': f"{tipo_doc.lower()}_cia_aberta_bpp_con_{ano}.csv"
            },
            "INDIVIDUAL": {
                'dre': f"{tipo_doc.lower()}_cia_aberta_dre_ind_{ano}.csv",
                'bpa': f"{tipo_doc.lower()}_cia_aberta_bpa_ind_{ano}.csv",
                'bpp': f"{tipo_doc.lower()}_cia_aberta_bpp_ind_{ano}.csv"
            }
        }

        dre_df, bpa_df, bpp_df = None, None, None
        tipo_dados_usados = None
        
        # Loop de Tentativa (primeiro CON, depois IND)
        for tipo_tentativa in ["CONSOLIDADO", "INDIVIDUAL"]:
            
            if tipo_tentativa == "INDIVIDUAL":
                print(f"INFO: Dados CONSOLIDADOS não encontrados para {cnpj} no ano {ano}. Tentando INDIVIDUAIS...")
                
            nomes_arquivos = arquivos_por_tipo[tipo_tentativa]
            
            try:
                dfs_filtrados = {}
                
                # Loop pelos 3 arquivos (DRE, BPA, BPP)
                for tipo_arq, nome_arq in nomes_arquivos.items():
                    # Lista para guardar os pedaços filtrados
                    chunks_filtrados = []
                    
                    # Abre o arquivo CSV de dentro do ZIP
                    with zf.open(nome_arq) as f:
                        # Lê o CSV em pedaços (chunks) para poupar memória
                        with pd.read_csv(f, sep=';', encoding='latin1', chunksize=50000) as reader:
                            for chunk in reader:
                                # Filtra o pedaço
                                chunk_filtrado = chunk[
                                    (chunk['CNPJ_CIA'] == cnpj) & 
                                    (chunk['ORDEM_EXERC'] == 'ÚLTIMO')
                                ].copy()
                                
                                if not chunk_filtrado.empty:
                                    chunks_filtrados.append(chunk_filtrado)
                    
                    if not chunks_filtrados:
                        # Se não encontrou nada para este CNPJ/Ano neste arquivo,
                        # esta tentativa (CON ou IND) falhou.
                        raise FileNotFoundError(f"Dados não encontrados em {nome_arq}")
                        
                    # Se encontrou, junta os pedaços
                    dfs_filtrados[tipo_arq] = pd.concat(chunks_filtrados)

                # Se chegou aqui, encontrou os 3 arquivos (DRE, BPA, BPP)
                dre_df = dfs_filtrados['dre']
                bpa_df = dfs_filtrados['bpa']
                bpp_df = dfs_filtrados['bpp']
                tipo_dados_usados = tipo_tentativa
                
                # Se teve sucesso (CON ou IND), para o loop de tentativa
                break 
                
            except Exception as e:
                # Falha normal (ex: arquivo _con_ não existe, ou dados não encontrados)
                # print(f"DEBUG: Falha ao tentar {tipo_tentativa}: {e}")
                pass 

        zf.close() # Fechar o arquivo ZIP
        return dre_df, bpa_df, bpp_df, tipo_dados_usados
    # --- FIM DO NOVO MÉTODO ---


    # --- MÉTODO PÚBLICO ATUALIZADO (Chama o novo leitor) ---
    def calcular_indicadores_empresa(self, cnpj, ano):
        """
        Método PRINCIPAL. Agora lê direto do ZIP (em chunks).
        """
        
        # 1. Chamar o nosso novo leitor de ZIP (em chunks)
        dre_df, bpa_df, bpp_df, tipo_dados_usados = self._ler_dados_do_zip(ano, cnpj)

        # 2. Verificação
        if tipo_dados_usados is None:
            print(f"AVISO (Dados Faltantes): CNPJ {cnpj} não possui dados 'ÚLTIMO' (CON ou IND) para o ano {ano}.")
            return None
        
        print(f"INFO: Usando dados {tipo_dados_usados} para {cnpj} (Ano {ano}).")
            
        # 3. Detectar o Fator de Escala
        try:
            escala_moeda_texto = bpa_df['ESCALA_MOEDA'].iloc[0]
            fator_escala = 1.0
            if escala_moeda_texto == 'MIL':
                fator_escala = 1000.0
            elif escala_moeda_texto == 'MILHAO':
                fator_escala = 1000000.0
        except Exception as e:
            fator_escala = 1.0
            
        # 4. Extrair os valores
        try:
            contas = {}
            contas['ativo_circulante'] = self.pegar_valor_conta(bpa_df, self.MAPA_CONTAS['ATIVO_CIRCULANTE']) * fator_escala
            contas['ativo_total'] = self.pegar_valor_conta(bpa_df, self.MAPA_CONTAS['ATIVO_TOTAL']) * fator_escala
            contas['passivo_circulante'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PASSIVO_CIRCULANTE']) * fator_escala
            contas['passivo_nao_circulante'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PASSIVO_NAO_CIRCULANTE']) * fator_escala
            contas['patrimonio_liquido'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PATRIMONIO_LIQUIDO']) * fator_escala
            contas['lucro_liquido'] = self.pegar_valor_conta(dre_df, self.MAPA_CONTAS['LUCRO_LIQUIDO']) * fator_escala
        except (ValueError, RuntimeError) as e:
            print(f"AVISO (Conta Faltante): Não foi possível extrair uma conta essencial para {cnpj}. {e}. Cálculo cancelado.")
            return None 
            
        # 5. Calcular os Indicadores
        indicadores = {}
        pc = contas['passivo_circulante']
        at = contas['ativo_total']
        pl = contas['patrimonio_liquido']
        
        if abs(pc) > 1e-9:
            indicadores['liq_corrente'] = contas['ativo_circulante'] / pc
        else:
            indicadores['liq_corrente'] = np.nan 

        divida_total = contas['passivo_circulante'] + contas['passivo_nao_circulante']
        
        if abs(at) > 1e-9:
            indicadores['endividamento_geral'] = divida_total / at
        else:
            indicadores['endividamento_geral'] = np.nan
        
        if abs(pl) > 1e-9:
            indicadores['divida_pl'] = divida_total / pl
            indicadores['roe'] = contas['lucro_liquido'] / pl
        else:
            indicadores['divida_pl'] = np.nan
            indicadores['roe'] = np.nan
        
        indicadores_limpos = {chave: float(valor) for chave, valor in indicadores.items()}
        
        return indicadores_limpos