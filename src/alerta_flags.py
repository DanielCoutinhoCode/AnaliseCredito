import pandas as pd
import os
import sys
import config # <-- IMPORTA A NOSSA CONFIGURAÇÃO

class GeradorAlertas:
    
    def __init__(self):
        print("GeradorAlertas iniciado.")

    # --- MÉTODO ATUALIZADO ---
    def gerar_alertas_setor(self, ticker_alvo, df_comparativo):
        """
        Lê um DataFrame comparativo (em memória) e gera alertas.
        Não lê mais arquivos CSV.
        
        Args:
            ticker_alvo (str): O ticker da empresa alvo (ex: "PETR4").
            df_comparativo (pd.DataFrame): O DF com as colunas "Empresa Alvo" e "Média do Setor".
        """
        
        print(f"\n--- Gerando Alertas para Ticker: {ticker_alvo} ---")
        
        # 2. Ler o DataFrame (já está na memória)
        try:
            coluna_alvo = f"Empresa Alvo ({ticker_alvo.upper()})"
            coluna_media = "Média do Setor" 
            
            empresa_alvo = df_comparativo[coluna_alvo]
            media_setor = df_comparativo[coluna_media]
        except KeyError as e:
            print(f"ERRO: O DataFrame comparativo não contém a coluna esperada: {e}.")
            return None
            
        # 3. Aplicar as Regras de Negócio
        print("Analisando regras...")
        alertas = [] 

        # Usamos os nomes de índice do DataFrame (que vêm do calculo_indicadores.py)
        if empresa_alvo['liq_corrente'] < 1.0:
            alertas.append(f"[RED FLAG] Liquidez Corrente ({empresa_alvo['liq_corrente']:.2f}) está abaixo de 1.0. Indica potencial risco de curto prazo.")
        else:
            alertas.append(f"[GREEN FLAG] Liquidez Corrente ({empresa_alvo['liq_corrente']:.2f}) está acima de 1.0. Boa posição de curto prazo.")

        if empresa_alvo['liq_corrente'] < media_setor['liq_corrente']:
            alertas.append(f"[RED FLAG] Liquidez Corrente está abaixo da média do setor ({media_setor['liq_corrente']:.2f}).")
        
        if empresa_alvo['endividamento_geral'] > media_setor['endividamento_geral']:
            alertas.append(f"[RED FLAG] Endividamento Geral ({empresa_alvo['endividamento_geral']:.2%}) está ACIMA da média do setor ({media_setor['endividamento_geral']:.2%}).")
        else:
            alertas.append(f"[GREEN FLAG] Endividamento Geral ({empresa_alvo['endividamento_geral']:.2%}) está abaixo da média do setor.")

        if empresa_alvo['divida_pl'] > media_setor['divida_pl']:
            alertas.append(f"[RED FLAG] Alavancagem Dívida/PL ({empresa_alvo['divida_pl']:.2f}) está ACIMA da média do setor ({media_setor['divida_pl']:.2f}).")
            
        if empresa_alvo['roe'] < 0:
            alertas.append(f"[RED FLAG] Rentabilidade (ROE) está negativa ({empresa_alvo['roe']:.2%}). A empresa está a dar prejuízo.")
        
        if empresa_alvo['roe'] < media_setor['roe']:
            alertas.append(f"[RED FLAG] Rentabilidade (ROE) ({empresa_alvo['roe']:.2%}) está abaixo da média do setor ({media_setor['roe']:.2%}).")
        else:
            alertas.append(f"[GREEN FLAG] Rentabilidade (ROE) ({empresa_alvo['roe']:.2%}) está acima da média do setor ({media_setor['roe']:.2%}).")

        # 4. Imprimir os alertas
        print("\n--- Conclusões da Análise (Sinais de Alerta) ---")
        if not alertas:
            print("Nenhum alerta gerado.")
        else:
            for alerta in alertas:
                print(f"- {alerta}")
                
        return alertas