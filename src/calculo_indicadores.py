import pandas as pd
import os
import sys
import config
import numpy as np
import zipfile # <-- Importante
from coleta_dados import ColetorDadosCVM

class CalculadoraIndicadores:
    """
    OTIMIZAÇÃO 3 (Nuvem): Esta classe não usa mais cache de DataFrame
    (para poupar RAM). Em vez disso, lê os dados de CADA empresa
    diretamente de dentro dos arquivos ZIP.
    """
    
    # --- __INIT__ ATUALIZADO ---
    def __init__(self, coletor: ColetorDadosCVM):
        self.diretorio_dados_raw = config.CAMINHO_RAW_BALANCOS_CVM
        self.MAPA_CONTAS = config.MAPA_CONTAS_CVM
        self.coletor = coletor
        
        print(f"CalculadoraIndicadores iniciada.")
        
        # --- O CACHE DE DATAFRAME FOI REMOVIDO ---
    # --- FIM DA ATUALIZAÇÃO ---

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

    # --- MÉTODO _ler_dados_do_zip (NOVO MÉTODO AUXILIAR) ---
    def _ler_dados_do_zip(self, ano, cnpj, tipo_doc="DFP"):
        """
        Lógica de leitura robusta:
        1. Garante que o ZIP do ano existe (baixa se necessário).
        2. Tenta ler os 3 arquivos CONSOLIDADOS de dentro do ZIP.
        3. Se falhar, tenta ler os 3 arquivos INDIVIDUAIS de dentro do ZIP.
        """
        
        # 1. Garantir que o ZIP existe
        sucesso_coleta = self.coletor.baixar_demonstrativos(ano, tipo_doc)
        if not sucesso_coleta:
            print(f"Falha ao baixar o ZIP do ano {ano}. Cálculo para {cnpj} cancelado.")
            return None, None, None, None # Retorna 4 Nones
            
        caminho_zip = self.coletor.caminho_saida_zip
        
        # 2. Abrir o arquivo ZIP
        try:
            zf = zipfile.ZipFile(caminho_zip)
        except Exception as e:
            print(f"ERRO: Não foi possível abrir o arquivo ZIP: {e}")
            return None, None, None, None
            
        # 3. Definir filtros
        filtro_cnpj = lambda df, c: df['CNPJ_CIA'] == c
        filtro_exercicio = lambda df: df['ORDEM_EXERC'] == 'ÚLTIMO'

        dre_df, bpa_df, bpp_df = None, None, None
        tipo_dados_usados = None

        # Nomes dos arquivos dentro do ZIP
        nomes_con = {
            'dre': f"{tipo_doc.lower()}_cia_aberta_dre_con_{ano}.csv",
            'bpa': f"{tipo_doc.lower()}_cia_aberta_bpa_con_{ano}.csv",
            'bpp': f"{tipo_doc.lower()}_cia_aberta_bpp_con_{ano}.csv"
        }
        nomes_ind = {
            'dre': f"{tipo_doc.lower()}_cia_aberta_dre_ind_{ano}.csv",
            'bpa': f"{tipo_doc.lower()}_cia_aberta_bpa_ind_{ano}.csv",
            'bpp': f"{tipo_doc.lower()}_cia_aberta_bpp_ind_{ano}.csv"
        }
        
        # --- TENTATIVA 1: DADOS CONSOLIDADOS (Lendo do ZIP) ---
        try:
            # Esta é a parte "mágica": pd.read_csv(zf.open(...))
            df_dre_con = pd.read_csv(zf.open(nomes_con['dre']), sep=';', encoding='latin1')
            df_bpa_con = pd.read_csv(zf.open(nomes_con['bpa']), sep=';', encoding='latin1')
            df_bpp_con = pd.read_csv(zf.open(nomes_con['bpp']), sep=';', encoding='latin1')
            
            # Aplicar filtros
            dre_df_con_filtrado = df_dre_con[filtro_cnpj(df_dre_con, cnpj) & filtro_exercicio(df_dre_con)].copy()
            bpa_df_con_filtrado = df_bpa_con[filtro_cnpj(df_bpa_con, cnpj) & filtro_exercicio(df_bpa_con)].copy()
            bpp_df_con_filtrado = df_bpp_con[filtro_cnpj(df_bpp_con, cnpj) & filtro_exercicio(df_bpp_con)].copy()

            if not dre_df_con_filtrado.empty and not bpa_df_con_filtrado.empty and not bpp_df_con_filtrado.empty:
                dre_df, bpa_df, bpp_df = dre_df_con_filtrado, bpa_df_con_filtrado, bpp_df_con_filtrado
                tipo_dados_usados = "CONSOLIDADO"
        except Exception as e:
            # (É normal falhar aqui se o arquivo não existir no ZIP)
            pass 
        
        # --- TENTATIVA 2: DADOS INDIVIDUAIS (Fallback) ---
        if tipo_dados_usados is None: 
            try:
                print(f"INFO: Dados CONSOLIDADOS não encontrados para {cnpj} no ano {ano}. Tentando INDIVIDUAIS...")
                df_dre_ind = pd.read_csv(zf.open(nomes_ind['dre']), sep=';', encoding='latin1')
                df_bpa_ind = pd.read_csv(zf.open(nomes_ind['bpa']), sep=';', encoding='latin1')
                df_bpp_ind = pd.read_csv(zf.open(nomes_ind['bpp']), sep=';', encoding='latin1')
                
                dre_df_ind_filtrado = df_dre_ind[filtro_cnpj(df_dre_ind, cnpj) & filtro_exercicio(df_dre_ind)].copy()
                bpa_df_ind_filtrado = df_bpa_ind[filtro_cnpj(df_bpa_ind, cnpj) & filtro_exercicio(df_bpa_ind)].copy()
                bpp_df_ind_filtrado = df_bpp_ind[filtro_cnpj(df_bpp_ind, cnpj) & filtro_exercicio(df_bpp_ind)].copy()
                
                if not dre_df_ind_filtrado.empty and not bpa_df_ind_filtrado.empty and not bpp_df_ind_filtrado.empty:
                    dre_df, bpa_df, bpp_df = dre_df_ind_filtrado, bpa_df_ind_filtrado, bpp_df_ind_filtrado
                    tipo_dados_usados = "INDIVIDUAL"
            except Exception as e:
                # (Falha normal se o _ind_ também não existir)
                pass 

        zf.close() # Fechar o arquivo ZIP
        return dre_df, bpa_df, bpp_df, tipo_dados_usados
    # --- FIM DO NOVO MÉTODO ---


    # --- MÉTODO PÚBLICO ATUALIZADO ---
    def calcular_indicadores_empresa(self, cnpj, ano):
        """
        Método PRINCIPAL. Agora lê direto do ZIP.
        """
        
        # 1. Chamar o nosso novo leitor de ZIP
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