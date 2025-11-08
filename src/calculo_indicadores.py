import pandas as pd
import os
import sys
import config
import numpy as np # Importamos numpy para usar o 'nan' de forma explícita

class CalculadoraIndicadores:
    """
    Classe responsável por ler os arquivos CSV brutos (baixados pelo ColetorDadosCVM)
    e calcular os indicadores financeiros para uma empresa específica.
    
    DIA 10 (Robustez):
    - 'pegar_valor_conta' agora levanta 'ValueError' em vez de retornar 0.0 (Ponto 1)
    - Indicadores com divisão por zero retornam 'nan' em vez de 0.0 (Ponto 5)
    - Cache de dados agora valida a integridade (Ponto 3)
    """
    
    def __init__(self):
        self.diretorio_dados_raw = config.CAMINHO_RAW_BALANCOS_CVM
        self.MAPA_CONTAS = config.MAPA_CONTAS_CVM
        print(f"CalculadoraIndicadores iniciada. Lendo dados de: {self.diretorio_dados_raw}")
        
        self.ano_em_cache = None
        self.df_dre_con = None
        self.df_bpa_con = None
        self.df_bpp_con = None
        self.df_dre_ind = None
        self.df_bpa_ind = None
        self.df_bpp_ind = None

    # --- FUNÇÃO DE CACHE ATUALIZADA ---
    def _carregar_dados_do_ano(self, ano, tipo_doc="DFP"):
        """
        Método INTERNO inteligente.
        Lê os 6 CSVs (CON e IND) de um ano do disco e
        os guarda na memória (cache).
        """
        
        # 1. Verificar se os dados já estão em cache E se são válidos
        if self.ano_em_cache == ano:
            # Ponto 3: Validação da integridade do cache
            if self.df_dre_con is not None or self.df_dre_ind is not None:
                # print(f"DEBUG: Usando dados em cache para o ano {ano}.")
                return True
            else:
                print(f"AVISO: Cache de {ano} estava corrompido (None). Recarregando...")
                self.ano_em_cache = None # Força o recarregamento
            
        print(f"Cache de {self.ano_em_cache} inválido. Carregando novos dados do ano {ano} do disco...")
        
        arquivos = {
            'dre_con': f"{tipo_doc.lower()}_cia_aberta_dre_con_{ano}.csv",
            'bpa_con': f"{tipo_doc.lower()}_cia_aberta_bpa_con_{ano}.csv",
            'bpp_con': f"{tipo_doc.lower()}_cia_aberta_bpp_con_{ano}.csv",
            'dre_ind': f"{tipo_doc.lower()}_cia_aberta_dre_ind_{ano}.csv",
            'bpa_ind': f"{tipo_doc.lower()}_cia_aberta_bpa_ind_{ano}.csv",
            'bpp_ind': f"{tipo_doc.lower()}_cia_aberta_bpp_ind_{ano}.csv"
        }
        
        self.ano_em_cache = None
        dfs_carregados = {}
        pelo_menos_um_carregado = False

        for chave, nome_arquivo in arquivos.items():
            caminho_arquivo = os.path.join(self.diretorio_dados_raw, nome_arquivo)
            try:
                df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')
                dfs_carregados[chave] = df
                pelo_menos_um_carregado = True
            except FileNotFoundError:
                dfs_carregados[chave] = None
            except Exception as e:
                print(f"ERRO inesperado ao carregar o arquivo {nome_arquivo}: {e}")
                dfs_carregados[chave] = None

        if not pelo_menos_um_carregado:
            print(f"ERRO CRÍTICO: Nenhum arquivo de dados (CON ou IND) encontrado para o ano {ano}.")
            return False

        self.df_dre_con = dfs_carregados['dre_con']
        self.df_bpa_con = dfs_carregados['bpa_con']
        self.df_bpp_con = dfs_carregados['bpp_con']
        self.df_dre_ind = dfs_carregados['dre_ind']
        self.df_bpa_ind = dfs_carregados['bpa_ind']
        self.df_bpp_ind = dfs_carregados['bpp_ind']
        
        self.ano_em_cache = ano
        print(f"Dados do ano {ano} (CON e IND) carregados para o cache.")
        return True

    # --- FUNÇÃO DE PEGAR CONTA ATUALIZADA ---
    def pegar_valor_conta(self, df_filtrado, cd_conta):
        """
        Método auxiliar para buscar um valor de conta em um DataFrame.
        CORREÇÃO: Levanta um erro se a conta não for encontrada.
        """
        try:
            valor = df_filtrado.loc[df_filtrado['CD_CONTA'] == cd_conta, 'VL_CONTA'].iloc[0]
            return valor
        except IndexError:
            # Não retorna 0.0. Levanta um erro.
            raise ValueError(f"Conta essencial {cd_conta} não encontrada")
        except Exception as e:
            # Outros erros (ex: df_filtrado é None) também devem falhar
            raise RuntimeError(f"Erro inesperado ao buscar conta {cd_conta}: {e}")
    # --- FIM DA ATUALIZAÇÃO ---

    def calcular_indicadores_empresa(self, cnpj, ano):
        """
        Método PRINCIPAL. Calcula todos os indicadores para um CNPJ/Ano.
        """
        
        if not self._carregar_dados_do_ano(ano):
            return None
            
        filtro_cnpj = lambda df, c: df['CNPJ_CIA'] == c
        filtro_exercicio = lambda df: df['ORDEM_EXERC'] == 'ÚLTIMO'

        dre_df, bpa_df, bpp_df = None, None, None
        tipo_dados_usados = None
        
        # --- TENTATIVA 1: CONSOLIDADO ---
        try:
            if self.df_dre_con is not None and self.df_bpa_con is not None and self.df_bpp_con is not None:
                dre_df_con = self.df_dre_con[filtro_cnpj(self.df_dre_con, cnpj) & filtro_exercicio(self.df_dre_con)].copy()
                bpa_df_con = self.df_bpa_con[filtro_cnpj(self.df_bpa_con, cnpj) & filtro_exercicio(self.df_bpa_con)].copy()
                bpp_df_con = self.df_bpp_con[filtro_cnpj(self.df_bpp_con, cnpj) & filtro_exercicio(self.df_bpp_con)].copy()

                if not dre_df_con.empty and not bpa_df_con.empty and not bpp_df_con.empty:
                    dre_df, bpa_df, bpp_df = dre_df_con, bpa_df_con, bpp_df_con
                    tipo_dados_usados = "CONSOLIDADO"
        except Exception:
            pass # Ignora falhas de filtragem aqui
        
        # --- TENTATIVA 2: INDIVIDUAL (Fallback) ---
        if tipo_dados_usados is None: 
            try:
                if self.df_dre_ind is not None and self.df_bpa_ind is not None and self.df_bpp_ind is not None:
                    print(f"INFO: Dados CONSOLIDADOS não encontrados para {cnpj} no ano {ano}. Tentando INDIVIDUAIS...")
                    dre_df_ind = self.df_dre_ind[filtro_cnpj(self.df_dre_ind, cnpj) & filtro_exercicio(self.df_dre_ind)].copy()
                    bpa_df_ind = self.df_bpa_ind[filtro_cnpj(self.df_bpa_ind, cnpj) & filtro_exercicio(self.df_bpa_ind)].copy()
                    bpp_df_ind = self.df_bpp_ind[filtro_cnpj(self.df_bpp_ind, cnpj) & filtro_exercicio(self.df_bpp_ind)].copy()
                    
                    if not dre_df_ind.empty and not bpa_df_ind.empty and not bpp_df_ind.empty:
                        dre_df, bpa_df, bpp_df = dre_df_ind, bpa_df_ind, bpp_df_ind
                        tipo_dados_usados = "INDIVIDUAL"
            except Exception:
                pass # Ignora falhas de filtragem aqui

        if tipo_dados_usados is None:
            print(f"AVISO (Dados Faltantes): CNPJ {cnpj} não possui dados 'ÚLTIMO' (CON ou IND) para o ano {ano}.")
            return None
        
        print(f"INFO: Usando dados {tipo_dados_usados} para {cnpj} (Ano {ano}).")
            
        try:
            # 4. Extrair os valores
            # Esta seção agora pode falhar (com ValueError) se uma conta não for encontrada
            escala_moeda_texto = bpa_df['ESCALA_MOEDA'].iloc[0]
            fator_escala = 1.0
            if escala_moeda_texto == 'MIL':
                fator_escala = 1000.0
            elif escala_moeda_texto == 'MILHAO':
                fator_escala = 1000000.0
            
            contas = {}
            contas['ativo_circulante'] = self.pegar_valor_conta(bpa_df, self.MAPA_CONTAS['ATIVO_CIRCULANTE']) * fator_escala
            contas['ativo_total'] = self.pegar_valor_conta(bpa_df, self.MAPA_CONTAS['ATIVO_TOTAL']) * fator_escala
            contas['passivo_circulante'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PASSIVO_CIRCULANTE']) * fator_escala
            contas['passivo_nao_circulante'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PASSIVO_NAO_CIRCULANTE']) * fator_escala
            contas['patrimonio_liquido'] = self.pegar_valor_conta(bpp_df, self.MAPA_CONTAS['PATRIMONIO_LIQUIDO']) * fator_escala
            contas['lucro_liquido'] = self.pegar_valor_conta(dre_df, self.MAPA_CONTAS['LUCRO_LIQUIDO']) * fator_escala

        except (ValueError, RuntimeError) as e:
            # --- Apanha o erro de conta faltante
            print(f"AVISO (Conta Faltante): Não foi possível extrair uma conta essencial para {cnpj}. {e}. Cálculo cancelado.")
            return None # Retorna None se uma conta crítica não for encontrada
            
        # 5. Calcular os Indicadores 
        indicadores = {}
        
        pc = contas['passivo_circulante']
        at = contas['ativo_total']
        pl = contas['patrimonio_liquido']
        
        # --- ATUALIZAÇÃO DE CÁLCULO ---
        # Usar np.nan (ou float('nan')) em vez de 0.0 para divisões inválidas
        # Usar abs(x) > 1e-9 (próximo de zero) em vez de x > 0
        
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
        
        # Otimização anterior: converter para float nativo
        # (np.nan é um float, por isso esta conversão é segura)
        indicadores_limpos = {chave: float(valor) for chave, valor in indicadores.items()}
        
        return indicadores_limpos