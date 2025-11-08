# dashboard.py (Versão Final com Injeção de Dependência)
import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

# --- Configuração de Caminho ---
diretorio_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(diretorio_src)

# --- Importar as "fábricas" ---
try:
    from coleta_dados import ColetorDadosCVM 
    from gestor_cadastro import GestorCadastro
    from calculo_indicadores import CalculadoraIndicadores
    from analise_setorial import AnalisadorSetorial
    from modelo_rating import ModeloRating
    from alerta_flags import GeradorAlertas
    import config
    
except ImportError as e:
    st.error(f"ERRO CRÍTICO: Não foi possível importar as 'fábricas' da pasta /src/.")
    st.error(f"Detalhe: {e}")
    st.stop()
# --- Fim da Configuração ---


# --- OTIMIZAÇÃO DE CACHE (COM INJEÇÃO DE DEPENDÊNCIA) ---

@st.cache_resource
def carregar_coletor_dados():
    print("Iniciando ColetorDadosCVM (cache)...")
    return ColetorDadosCVM()

@st.cache_resource
def carregar_gestor_cadastro():
    print("Iniciando GestorCadastro (cache)...")
    return GestorCadastro()

@st.cache_resource
# Esta calculadora agora PRECISA de um coletor
def carregar_calculadora_indicadores():
    print("Iniciando CalculadoraIndicadores (cache)...")
    coletor = carregar_coletor_dados() # Pega a instância do coletor
    return CalculadoraIndicadores(coletor) # Injeta o coletor

@st.cache_resource
# Este analisador agora PRECISA da calculadora e do gestor
def carregar_analisador_setorial():
    print("Iniciando dependências (Calculadora, Gestor)...")
    calculadora = carregar_calculadora_indicadores()
    gestor = carregar_gestor_cadastro()
    
    print("Iniciando AnalisadorSetorial (cache)...")
    return AnalisadorSetorial(calculadora, gestor) # Injeta as dependências

@st.cache_resource
def carregar_gerador_alertas():
    print("Iniciando GeradorAlertas (cache)...")
    return GeradorAlertas()

@st.cache_resource
def carregar_modelo_rating():
    print("Iniciando ModeloRating (cache)...")
    return ModeloRating()
# --- FIM DO CACHE ---


# --- Funções "Helper" de Formatação (Sem alteração) ---
def formatar_para_percentagem(valor):
    if pd.isna(valor): return "N/A"
    return f"{valor * 100:.2f}%"

def formatar_para_decimal(valor):
    if pd.isna(valor): return "N/A"
    return f"{valor:.2f}"


# --- FUNÇÃO PRINCIPAL (ATUALIZADA) ---
def rodar_analise_dashboard(ticker_alvo, lista_pares, ano):
    """
    Função principal que executa todo o backend e
    exibe os resultados na interface do Streamlit.
    """
    # 1. Carregar as "fábricas" (a partir do cache)
    try:
        # A Etapa 1 (Coleta) foi removida daqui,
        # pois agora ela é chamada DE DENTRO do analisador.
        analisador = carregar_analisador_setorial()
        modelo = carregar_modelo_rating()
        alertas = carregar_gerador_alertas()
    except Exception as e:
        st.error(f"Erro ao iniciar as 'fábricas': {e}")
        return

    # --- ETAPA 1 (Antiga 2): ANÁLISE SETORIAL ---
    df_completo_t, df_comparativo, dados_alvo_brutos = None, None, None
    with st.spinner(f"[Etapa 1/3] Verificando dados CVM e calculando indicadores..."):
        # Esta função agora faz TUDO (Coleta, Cache, Cálculo, Fallback)
        resultados = analisador.analisar_pares(ticker_alvo, lista_pares, ano)
        
        if resultados[0] is None:
            st.error(f"Falha na Etapa 1 (Análise Setorial). Verifique o terminal para mais detalhes (ex: dados faltantes da CVM).")
            st.stop()
            
        df_completo_t, df_comparativo, dados_alvo_brutos = resultados
        st.success("Etapa 1 concluída!")

    # --- ETAPA 2 (Antiga 3): ANÁLISE QUALITATIVA (Red Flags) ---
    lista_alertas_resultado = None
    with st.spinner("[Etapa 2/3] Gerando Alertas (vs. Média do Setor)..."):
        lista_alertas_resultado = alertas.gerar_alertas_setor(ticker_alvo, df_comparativo)
        if lista_alertas_resultado is None:
            st.error("Falha na Etapa 2 (Geração de Alertas).")
            st.stop()
        st.success("Etapa 2 concluída!")

    # --- ETAPA 3 (Antiga 4): ANÁLISE QUANTITATIVA (Rating) ---
    resultado_rating = None
    with st.spinner("[Etapa 3/4] Calculando Rating de Crédito Absoluto..."):
        resultado_rating = modelo.calcular_rating_empresa(dados_alvo_brutos)
        if resultado_rating is None:
            st.error("Falha na Etapa 3 (Cálculo do Rating).")
            st.stop()
        st.success("Etapa 3 concluída!")
    
    # --- Exibir Resultados (Sem alteração aqui) ---
    
    st.header(f"Rating de Crédito (Absoluto) para {ticker_alvo.upper()}")
    col1, col2 = st.columns(2) 
    col1.metric("Rating Final", resultado_rating['rating'])
    col2.metric("Score Final (0-100)", f"{resultado_rating['score_final']:.2f}")
    st.subheader("Pontuação por Categoria (0-100)")
    detalhes = resultado_rating['detalhes_scores']
    col1, col2, col3 = st.columns(3)
    col1.metric("Liquidez", f"{detalhes['score_liquidez']:.0f}")
    col2.metric("Endividamento", f"{detalhes['score_endividamento']:.0f}")
    col3.metric("Rentabilidade", f"{detalhes['score_rentabilidade']:.0f}")

    st.header("Análise Qualitativa (vs. Média do Setor)")
    st.subheader("Conclusões e Sinais de Alerta")
    for alerta in lista_alertas_resultado:
        if "[RED FLAG]" in alerta:
            st.error(alerta)
        elif "[GREEN FLAG]" in alerta:
            st.success(alerta)
            
    st.header("Análise Quantitativa Detalhada")
    
    TRADUCAO = config.TRADUCAO_INDICADORES
    PERC_TRADUZIDOS = [TRADUCAO.get(p) for p in config.INDICADORES_PERCENTUAIS]

    df_comp_renomeado = df_comparativo.rename(index=TRADUCAO)
    df_comp_formatado = df_comp_renomeado.copy()
    for idx in df_comp_renomeado.index:
        if idx in PERC_TRADUZIDOS:
            df_comp_formatado.loc[idx] = df_comp_renomeado.loc[idx].apply(formatar_para_percentagem)
        else:
            df_comp_formatado.loc[idx] = df_comp_renomeado.loc[idx].apply(formatar_para_decimal)
    st.subheader(f"Comparativo: {ticker_alvo.upper()} vs. Média do Setor")
    st.dataframe(df_comp_formatado) 

    df_completo_t_renomeado = df_completo_t.rename(index=TRADUCAO)
    df_completo_t_formatado = df_completo_t_renomeado.copy()
    for idx in df_completo_t_renomeado.index:
        if idx in PERC_TRADUZIDOS:
            df_completo_t_formatado.loc[idx] = df_completo_t_renomeado.loc[idx].apply(formatar_para_percentagem)
        else:
            df_completo_t_formatado.loc[idx] = df_completo_t_renomeado.loc[idx].apply(formatar_para_decimal)
    with st.expander("Ver Indicadores Detalhados (Todos os Pares)"):
        st.dataframe(df_completo_t_formatado)


# ====================================================================
# --- INTERFACE DO USUÁRIO (O "Painel") ---
# ====================================================================

st.set_page_config(layout="wide")
st.title("Sistema Automatizado de Análise de Crédito Corporativo")

st.sidebar.header("Parâmetros da Análise")

# --- LÓGICA DA BARRA LATERAL (Simplificada) ---
try:
    gestor_global = carregar_gestor_cadastro()
    if not gestor_global._carregar_mapa_ticker():
        raise Exception("Falha ao carregar o arquivo 'mapa_ticker_cnpj.csv'")
    
    lista_tickers = gestor_global.df_mapa_ticker['TICKER'].unique()
    lista_tickers.sort()
    
    try:
        default_index = list(lista_tickers).index("PETR4")
    except ValueError:
        default_index = 0 
    
    ticker_alvo = st.sidebar.selectbox(
        "Ticker Alvo",
        options=lista_tickers,
        index=default_index
    )
    
    pares_input = st.sidebar.text_area(
        "Pares Concorrentes (separados por vírgula)", 
        value="PRIO3, RECV3, BRAV3" 
    )

except Exception as e:
    st.sidebar.error(f"Erro ao carregar mapa de tickers: {e}")
    ticker_alvo = st.sidebar.text_input("Ticker Alvo", value="PETR4")
    pares_input = st.sidebar.text_area("Pares Concorrentes (separados por vírgula)", value="PRIO3, RECV3, BRAV3")

ano_atual = datetime.now().year
ano_input = st.sidebar.number_input("Ano de Análise", min_value=2010, max_value=ano_atual, value=ano_atual - 1)


# --- Botão de Execução ---
if st.sidebar.button("Gerar Análise", type="primary"):
    
    lista_pares = [ticker.strip().upper() for ticker in pares_input.split(',') if ticker.strip()]
    
    if not ticker_alvo.strip():
        st.error("Por favor, insira um Ticker Alvo.")
    elif not lista_pares:
        st.error("Por favor, insira pelo menos um Ticker na caixa 'Pares Concorrentes'.")
    else:
        rodar_analise_dashboard(ticker_alvo, lista_pares, ano_input)

else:
    st.info("Por favor, preencha os parâmetros na barra lateral e clique em 'Gerar Análise'.")