import pandas as pd
import os
import sys
import config
import numpy as np
import zipfile 
from coleta_dados import ColetorDadosCVM

class CalculadoraIndicadores:
    """
    OTIMIZAÇÃO FINAL (Deploy): 
    Lê dados de dentro do ZIP (para poupar espaço) e
    IGNORA MAIÚSCULAS/MINÚSCULAS nos nomes dos arquivos
    (para funcionar no Linux/Streamlit Cloud).
    """
    
    def __init__(self, coletor: ColetorDadosCVM):
        self.diretorio_dados_raw = config.CAMINHO_RAW_BALANCOS_CVM
        self.MAPA_CONTAS = config.MAPA_CONTAS_CVM
        self.coletor = coletor
        
        print(f"CalculadoraIndicadores iniciada (Modo Baixa Memória, Case-Insensitive).")
        
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

    # --- NOVO MÉTODO HELPER (PARA IGNORAR O CASE) ---
    def _encontrar_nome_arquivo_no_zip(self, zf, sufixo_arquivo_lower):
        """
        Encontra um arquivo no ZIP ignorando o "case" (maiúsculas/minúsculas).
        Ex: sufixo_arquivo_lower = 'dre_con_2024.csv'
        Encontra: 'dfp_cia_aberta_DRE_CON_2024.CSV'
        """
        nomes_no_zip = zf.namelist()
        
        for nome_real_no_zip in nomes_no_zip:
            # Compara ambos os nomes em minúsculas
            if nome_real_no_zip.lower().endswith(sufixo_arquivo_lower):
                return nome_real_no_zip # Encontrou! Retorna o nome com o case correto
        
        # Se não encontrou
        raise FileNotFoundError(f"Arquivo terminando em '{sufixo_arquivo_lower}' não encontrado no ZIP.")
    # --- FIM DO NOVO MÉTODO ---

    # --- MÉTODO _ler_dados_do_zip (ATUALIZADO) ---
    def _ler_dados_do_zip(self, ano, cnpj, tipo_doc="DFP"):
        """
        Lógica de leitura robusta:
        1. Garante que o ZIP do ano existe (baixa se necessário).
        2. Tenta ler os 3 arquivos CONSOLIDADOS (ignorando o case).
        3. Se falhar, tenta ler os 3 arquivos INDIVIDUAIS (ignorando o case).
        """
        
        if not self.coletor.baixar_demonstrativos(ano, tipo_doc):
            print(f"Falha ao baixar o ZIP do ano {ano}. Cálculo para {cnpj} cancelado.")
            return None, None, None, None 
            
        caminho_zip = self.coletor.caminho_saida_zip
        
        try:
            zf = zipfile.ZipFile(caminho_zip)
        except Exception as e:
            print(f"ERRO: Não foi possível abrir o arquivo ZIP: {e}")
            return None, None, None, None
            
        filtro_cnpj = lambda df, c: df['CNPJ_CIA'] == c
        filtro_exercicio = lambda df: df['ORDEM_EXERC'] == 'ÚLTIMO'

        dre_df, bpa_df, bpp_df = None, None, None
        tipo_dados_usados = None
        
        # Loop de Tentativa (primeiro CON, depois IND)
        for tipo_tentativa in ["CONSOLIDADO", "INDIVIDUAL"]:
            
            if tipo_tentativa == "INDIVIDUAL":
                print(f"INFO: Dados CONSOLIDADOS não encontrados para {cnpj} no ano {ano}. Tentando INDIVIDUAIS...")
                
            # Define os sufixos (em minúsculas) que queremos encontrar
            sufixos_arquivos = {
                'dre': f"dre_{'con' if tipo_tentativa == 'CONSOLIDADO' else 'ind'}_{ano}.csv",
                'bpa': f"bpa_{'con' if tipo_tentativa == 'CONSOLIDADO' else 'ind'}_{ano}.csv",
                'bpp': f"bpp_{'con' if tipo_tentativa == 'CONSOLIDADO' else 'ind'}_{ano}.csv"
            }
            
            try:
                # 1. Encontrar os nomes corretos (ignorando o case)
                nome_real_dre = self._encontrar_nome_arquivo_no_zip(zf, sufixos_arquivos['dre'])
                nome_real_bpa = self._encontrar_nome_arquivo_no_zip(zf, sufixos_arquivos['bpa'])
                nome_real_bpp = self._encontrar_nome_arquivo_no_zip(zf, sufixos_arquivos['bpp'])

                # 2. Ler os arquivos (sem "chunks", para manter a RAM baixa, mas não tão lento)
                df_dre = pd.read_csv(zf.open(nome_real_dre), sep=';', encoding='latin1', dtype={'CNPJ_CIA': str})
                df_bpa = pd.read_csv(zf.open(nome_real_bpa), sep=';', encoding='latin1', dtype={'CNPJ_CIA': str})
                df_bpp = pd.read_csv(zf.open(nome_real_bpp), sep=';', encoding='latin1', dtype={'CNPJ_CIA': str})

                # 3. Filtrar
                dre_df_filtrado = df_dre[filtro_cnpj(df_dre, cnpj) & filtro_exercicio(df_dre)].copy()
                bpa_df_filtrado = df_bpa[filtro_cnpj(df_bpa, cnpj) & filtro_exercicio(df_bpa)].copy()
                bpp_df_filtrado = df_bpp[filtro_cnpj(df_bpp, cnpj) & filtro_exercicio(df_bpp)].copy()
                
                if not dre_df_filtrado.empty and not bpa_df_filtrado.empty and not bpp_df_filtrado.empty:
                    dre_df, bpa_df, bpp_df = dre_df_filtrado, bpa_df_filtrado, bpp_df_filtrado
                    tipo_dados_usados = tipo_tentativa
                    break # Sucesso!
                        
            except Exception as e:
                # (Falha normal se o _con_ não existir, ou _ind_ não existir)
                # print(f"DEBUG: Falha ao tentar {tipo_tentativa}: {e}")
                pass 

        zf.close() 
        return dre_df, bpa_df, bpp_df, tipo_dados_usados
    # --- FIM DO MÉTODO ---

    def calcular_indicadores_empresa(self, cnpj, ano):
        """
        Método PRINCIPAL. Agora lê direto do ZIP (case-insensitive).
        """
        
        dre_df, bpa_df, bpp_df, tipo_dados_usados = self._ler_dados_do_zip(ano, cnpj)

        if tipo_dados_usados is None:
            print(f"AVISO (Dados Faltantes): CNPJ {cnpj} não possui dados 'ÚLTIMO' (CON ou IND) para o ano {ano}.")
            return None
        
        print(f"INFO: Usando dados {tipo_dados_usados} para {cnpj} (Ano {ano}).")
            
        try:
            escala_moeda_texto = bpa_df['ESCALA_MOEDA'].iloc[0]
            fator_escala = 1.0
            if escala_moeda_texto == 'MIL':
                fator_escala = 1000.0
            elif escala_moeda_texto == 'MILHAO':
                fator_escala = 1000000.0
        except Exception as e:
            fator_escala = 1.0
            
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