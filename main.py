import sys
import os
from datetime import datetime # Importado para validar o ano

# --- Adicionar a pasta 'src' ao 'caminho' do Python ---
diretorio_src = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(diretorio_src)

# --- Importar as nossas "fábricas" ---
try:
    from analise_setorial import AnalisadorSetorial
    from gerador_relatorio import GeradorRelatorioPDF
    from alerta_flags import GeradorAlertas
    from modelo_rating import ModeloRating
    import config # Importamos o config para usar os caminhos no log
except ImportError as e:
    print(f"ERRO: Falha ao importar as classes das 'fábricas' da pasta /src/.")
    print(f"Detalhe: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Um erro inesperado ocorreu durante a importação: {e}")
    sys.exit(1)

# ====================================================================
# --- PAINEL DE CONTROLE (Defina os seus parâmetros aqui) ---
# ====================================================================

TICKER_ALVO = "CSMG3"
LISTA_PARES = ["SAPR11", "SBSP3"]
ANO_DE_ANALISE = 2024

# ====================================================================

def validar_inputs(ticker, pares, ano):
    """
    Valida os inputs do "Painel de Controlo" antes de executar.
    Levanta ValueError ou TypeError se algo estiver errado.
    """
    print("Validando inputs...")
    
    # 1. Validar Ano
    ano_atual = datetime.now().year
    if not isinstance(ano, int) or not (2010 <= ano <= ano_atual):
        raise ValueError(f"Ano '{ano}' é inválido. Deve ser um número inteiro entre 2010 e {ano_atual}.")
        
    # 2. Validar Ticker Alvo
    if not ticker or not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("TICKER_ALVO não pode ser vazio.")
        
    # 3. Validar Lista de Pares
    if not isinstance(pares, list):
        raise TypeError("LISTA_PARES deve ser uma lista (ex: ['PRIO3', 'RECV3']).")
        
    if len(pares) < 1:
        raise ValueError("LISTA_PARES deve conter pelo menos um concorrente.")
        
    print("Inputs validados com sucesso.")
    return True
# --- FIM DA NOVA FUNÇÃO ---


def rodar_analise_completa(ticker, pares, ano):
    """
    Orquestra a execução completa do sistema.
    """
    print(f"--- [MAIN] INICIANDO SISTEMA DE ANÁLISE DE CRÉDITO ---")
    print(f"--- [MAIN] Alvo: {ticker} | Ano: {ano} ---")
    
    try:
        # --- ETAPA 1: ANÁLISE SETORIAL (Calcular Indicadores) ---
        print("\n--- [MAIN] Iniciando Etapa 1: Análise Setorial (em memória) ---")
        analisador = AnalisadorSetorial()
        
        # 'analisar_pares' agora retorna os 3 resultados que precisamos
        # (df_completo_t, df_comparativo, dados_alvo_brutos)
        resultados_analise = analisador.analisar_pares(ticker, pares, ano)
        
        if resultados_analise[0] is None:
            print("--- [MAIN] ERRO na Etapa 1 (Análise Setorial). A análise foi cancelada. ---")
            return
            
        # Desempacotar os resultados
        df_completo_t, df_comparativo, dados_alvo_brutos = resultados_analise
            
        print("--- [MAIN] Etapa 1 concluída com sucesso (Dados em memória). ---")

        # --- ETAPA 2: ANÁLISE QUALITATIVA (Red Flags) ---
        print("\n--- [MAIN] Iniciando Etapa 2: Geração de Alertas ---")
        gerador_alertas = GeradorAlertas()
        # Passamos o DataFrame (em memória), não o nome do arquivo
        lista_alertas = gerador_alertas.gerar_alertas_setor(ticker, df_comparativo)

        # --- ETAPA 3: ANÁLISE QUANTITATIVA (Rating) ---
        print("\n--- [MAIN] Iniciando Etapa 3: Cálculo do Rating ---")
        modelo = ModeloRating()
        # Passamos os dados brutos do alvo (em memória)
        resultado_rating = modelo.calcular_rating_empresa(dados_alvo_brutos)

        # --- ETAPA 4: GERAÇÃO DO PDF (Consolidar tudo) ---
        print("\n--- [MAIN] Iniciando Etapa 4: Geração do Relatório PDF ---")
        gerador_pdf = GeradorRelatorioPDF()
        
        # Passamos TUDO (em memória) para o gerador
        gerador_pdf.gerar_relatorio(
            ticker_alvo = ticker,
            ano = ano,
            resultado_rating = resultado_rating,
            lista_alertas = lista_alertas,
            df_comparativo = df_comparativo,
            df_completo_t = df_completo_t
        )
        
        print("--- [MAIN] Etapa 4 concluída com sucesso (PDF gerado). ---")
        
    except Exception as e:
        print(f"--- [MAIN] UM ERRO CRÍTICO OCORREU: {e} ---")
        import traceback
        traceback.print_exc() # Imprime o erro detalhado

# --- Ponto de Entrada do Script (ATUALIZADO) ---
if __name__ == "__main__":
    
    try:
        # 1. Validar os inputs primeiro
        validar_inputs(TICKER_ALVO, LISTA_PARES, ANO_DE_ANALISE)
        
        # 2. Se a validação passar, executar o sistema
        rodar_analise_completa(TICKER_ALVO, LISTA_PARES, ANO_DE_ANALISE)
        
    except (ValueError, TypeError) as e:
        # Apanha erros de validação
        print(f"--- [MAIN] ERRO DE INPUT: {e} ---")
        print("Análise cancelada. Verifique os parâmetros no 'Painel de Controlo' do main.py.")

    print(f"\n--- [MAIN] Sistema de Análise de Crédito (Robustez Refatorada) concluído. ---")