import pandas as pd
import sys
import pprint
import os 
import numpy as np # Importamos o numpy para verificar 'nan'
import config 

try:
    from calculo_indicadores import CalculadoraIndicadores
    from gestor_cadastro import GestorCadastro
except ImportError:
    print("ERRO: Não foi possível encontrar as classes 'CalculadoraIndicadores' ou 'GestorCadastro'.")
    sys.exit(1)

class AnalisadorSetorial:
    
    def __init__(self):
        self.calculadora = CalculadoraIndicadores()
        self.gestor = GestorCadastro()
        print(f"AnalisadorSetorial iniciado.")
    
    # --- NOVO MÉTODO DE VALIDAÇÃO ---
    def _validar_indicadores(self, indicadores, ticker):
        """
        Verifica se os indicadores calculados são 'nan' (inválidos)
        ou se estão fora de um range aceitável (outliers).
        Levanta um ValueError se a empresa for inválida para a análise.
        """
        
        # 1. Verificar se há 'nan' (dados inválidos)
        for nome, valor in indicadores.items():
            if np.isnan(valor):
                raise ValueError(f"Indicador '{nome}' é 'nan' (divisão por zero?).")
                
        # 2. Verificar outliers (lógica de sanidade)
        if indicadores['liq_corrente'] < 0:
            raise ValueError(f"Indicador 'liq_corrente' é negativo ({indicadores['liq_corrente']:.2f}).")
        
        if abs(indicadores['roe']) > 5.0: # ROE acima de 500%?
            raise ValueError(f"Indicador 'roe' é extremo ({indicadores['roe']:.2%}).")
            
        if indicadores['endividamento_geral'] > 10.0: # Dívida > 10x o Ativo?
            raise ValueError(f"Indicador 'endividamento_geral' é extremo ({indicadores['endividamento_geral']:.2%}).")
            
        return True
    # --- FIM DO NOVO MÉTODO ---
        
    def analisar_pares(self, ticker_alvo, lista_pares, ano):
        """
        Executa a análise de pares completa.
        """
        
        print(f"\n--- Iniciando Análise de Pares para Ticker: {ticker_alvo} | Ano: {ano} ---")
        
        print(f"[Fase 1/4] Identificando empresas...")
        ticker_alvo_upper = ticker_alvo.upper()
        lista_pares_upper = [p.upper() for p in lista_pares]
        tickers_para_analisar = sorted(list(set([ticker_alvo_upper] + lista_pares_upper))) 
        print(f"Empresa Alvo: {ticker_alvo_upper}")
        print(f"Pares Relevantes: {lista_pares_upper}")

        print(f"[Fase 2/4] Traduzindo Tickers para CNPJs...")
        empresas_para_analisar = {} 
        cnpj_alvo = None
        for ticker in tickers_para_analisar:
            cnpj = self.gestor.encontrar_cnpj_por_ticker(ticker)
            if not cnpj:
                print(f"AVISO: Ticker {ticker} não encontrado no 'mapa_ticker_cnpj.csv'. Será ignorado.")
                continue
            if ticker == ticker_alvo_upper:
                cnpj_alvo = cnpj
            empresas_para_analisar[ticker] = cnpj
        if not cnpj_alvo:
            print(f"ERRO: O CNPJ da empresa alvo ({ticker_alvo}) não foi encontrado.")
            return None, None, None
        print(f"Total de {len(empresas_para_analisar)} CNPJs encontrados para calcular.")

        # --- LÓGICA ATUALIZADA ---
        print(f"[Fase 3/4] Calculando e validando indicadores...")
        resultados_setor = [] 
        dados_alvo_brutos = None 
        
        for ticker, cnpj in empresas_para_analisar.items():
            # 1. Calcular
            indicadores = self.calculadora.calcular_indicadores_empresa(cnpj, ano)
            
            # 2. Verificar se o cálculo falhou (ex: conta faltante)
            if indicadores is None:
                # O 'calculo_indicadores' já imprimiu o AVISO
                continue 
            
            # 3. Validar a sanidade dos dados (ex: 'nan' ou outliers)
            try:
                self._validar_indicadores(indicadores, ticker)
                
                # Se passou, adicionar aos resultados
                indicadores['empresa'] = ticker
                resultados_setor.append(indicadores)
                
                if ticker == ticker_alvo_upper:
                    dados_alvo_brutos = indicadores # Captura os dados brutos do alvo
                    
            except ValueError as e:
                # Apanha o erro de validação (ex: ROE extremo ou 'nan')
                print(f"AVISO (Indicador Inválido): Empresa {ticker} ignorada. Motivo: {e}")

        if not resultados_setor:
            print(f"ERRO: Não foi possível calcular ou validar indicadores para nenhuma empresa.")
            return None, None, None
        # --- FIM DA ATUALIZAÇÃO ---

        print(f"[Fase 4/4] Processando relatórios...")
        df_completo = pd.DataFrame(resultados_setor)
        df_completo = df_completo.set_index('empresa')

        try:
            dados_alvo_df = df_completo.loc[ticker_alvo_upper]
        except KeyError:
            print(f"ERRO: A empresa alvo ({ticker_alvo_upper}) não tem dados calculados (foi filtrada ou falhou).")
            return None, None, None
            
        media_setor = df_completo.mean(numeric_only=True)

        print("\n--- Análise de Pares Concluída ---")
        df_completo_t = df_completo.T
        
        df_comparativo = pd.DataFrame({
            f"Empresa Alvo ({ticker_alvo_upper})": dados_alvo_df, 
            "Média do Setor": media_setor
        })
        
        print("Análise setorial concluída. Retornando DataFrames para o main.py.")
        
        return df_completo_t, df_comparativo, dados_alvo_brutos