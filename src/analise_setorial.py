import pandas as pd
import sys
import pprint
import os 
import numpy as np
import config 

try:
    # Ele ainda precisa das definições das classes
    from calculo_indicadores import CalculadoraIndicadores
    from gestor_cadastro import GestorCadastro
except ImportError:
    print("ERRO: Não foi possível encontrar as classes 'CalculadoraIndicadores' ou 'GestorCadastro'.")
    sys.exit(1)


class AnalisadorSetorial:
    
    # --- __INIT__ ATUALIZADO (Injeção de Dependência) ---
    def __init__(self, calculadora: CalculadoraIndicadores, gestor: GestorCadastro):
        """
        Construtor. Recebe as instâncias das "fábricas"
        de que precisa (injeção de dependência).
        """
        self.calculadora = calculadora # Recebe a calculadora
        self.gestor = gestor       # Recebe o gestor
        print(f"AnalisadorSetorial iniciado.")
    # --- FIM DA ATUALIZAÇÃO ---
        
    def _validar_indicadores(self, indicadores, ticker):
        """
        Verifica se os indicadores calculados são 'nan' (inválidos)
        ou se estão fora de um range aceitável (outliers).
        (Esta função está correta)
        """
        for nome, valor in indicadores.items():
            if np.isnan(valor):
                raise ValueError(f"Indicador '{nome}' é 'nan' (divisão por zero?).")
        if indicadores['liq_corrente'] < 0:
            raise ValueError(f"Indicador 'liq_corrente' é negativo ({indicadores['liq_corrente']:.2f}).")
        if abs(indicadores['roe']) > 5.0: 
            raise ValueError(f"Indicador 'roe' é extremo ({indicadores['roe']:.2%}).")
        if indicadores['endividamento_geral'] > 10.0:
            raise ValueError(f"Indicador 'endividamento_geral' é extremo ({indicadores['endividamento_geral']:.2%}).")
        return True
        
    def analisar_pares(self, ticker_alvo, lista_pares, ano):
        """
        Executa a análise de pares completa.
        (Esta função está correta e não muda)
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

        print(f"[Fase 3/4] Calculando e validando indicadores...")
        resultados_setor = [] 
        dados_alvo_brutos = None 
        
        for ticker, cnpj in empresas_para_analisar.items():
            indicadores = self.calculadora.calcular_indicadores_empresa(cnpj, ano)
            
            if indicadores is None:
                continue 
            
            try:
                self._validar_indicadores(indicadores, ticker)
                indicadores['empresa'] = ticker
                resultados_setor.append(indicadores)
                if ticker == ticker_alvo_upper:
                    dados_alvo_brutos = indicadores
            except ValueError as e:
                print(f"AVISO (Indicador Inválido): Empresa {ticker} ignorada. Motivo: {e}")

        if not resultados_setor:
            print(f"ERRO: Não foi possível calcular ou validar indicadores para nenhuma empresa.")
            return None, None, None
        if dados_alvo_brutos is None:
            print(f"ERRO: A empresa alvo ({ticker_alvo_upper}) foi filtrada ou falhou nos cálculos.")
            return None, None, None

        print(f"[Fase 4/4] Processando relatórios...")
        df_completo = pd.DataFrame(resultados_setor)
        df_completo = df_completo.set_index('empresa')

        dados_alvo_df = df_completo.loc[ticker_alvo_upper]
        media_setor = df_completo.mean(numeric_only=True)

        print("\n--- Análise de Pares Concluída ---")
        df_completo_t = df_completo.T
        
        df_comparativo = pd.DataFrame({
            f"Empresa Alvo ({ticker_alvo_upper})": dados_alvo_df, 
            "Média do Setor": media_setor
        })
        
        print("Análise setorial concluída. Retornando DataFrames para o main.py.")
        
        return df_completo_t, df_comparativo, dados_alvo_brutos