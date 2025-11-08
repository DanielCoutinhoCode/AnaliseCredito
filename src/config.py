# src/config.py
"""
Arquivo de Configuração Central.

Contém todas as constantes, caminhos, URLs, e regras de negócio
(mapas de indicadores, pesos de rating) para o sistema.
"""

# --- 1. CAMINHOS E ARQUIVOS ---
# (Relativos à pasta raiz 'AnaliseCredito', onde o main.py é executado)
CAMINHO_DADOS_RAW = "data/raw/"
CAMINHO_DADOS_PROCESSADOS = "data/processed/"
CAMINHO_OUTPUT_REPORTS = "output/reports/"

CAMINHO_RAW_BALANCOS_CVM = f"{CAMINHO_DADOS_RAW}balancos_cvm/"
CAMINHO_RAW_CADASTRO_CVM = f"{CAMINHO_DADOS_RAW}cadastro_cvm/"

# --- 2. URLs EXTERNAS ---
URL_CADASTRO_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
URL_BASE_DFP_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/"

# --- 3. NOMES DE ARQUIVOS ---
ARQUIVO_MAPA_TICKER_CNPJ = f"{CAMINHO_DADOS_PROCESSADOS}mapa_ticker_cnpj.csv"
ARQUIVO_CADASTRO_CVM = f"{CAMINHO_RAW_CADASTRO_CVM}cad_cia_aberta.csv"

# --- 4. MAPEAMENTO DE INDICADORES ---
# 4a. Mapeamento de Contas CVM (para calculo_indicadores.py)
MAPA_CONTAS_CVM = {
    'ATIVO_TOTAL': '1',
    'ATIVO_CIRCULANTE': '1.01',
    'PASSIVO_CIRCULANTE': '2.01',
    'PASSIVO_NAO_CIRCULANTE': '2.02',
    'PATRIMONIO_LIQUIDO': '2.03',
    'LUCRO_LIQUIDO': '3.11'
}

# 4b. "Tradução" de Nomes (para gerador_relatorio.py)
TRADUCAO_INDICADORES = {
    'liq_corrente': 'Liquidez Corrente',
    'endividamento_geral': 'Endividamento Geral (%)',
    'divida_pl': 'Dívida/PL',
    'roe': 'ROE (%)'
}

# 4c. Lista de Indicadores que são Percentuais
INDICADORES_PERCENTUAIS = ['endividamento_geral', 'roe']

# --- 5. MODELO DE RATING (para modelo_rating.py) ---
# 5a. Pesos dos Grupos de Indicadores
PESOS_RATING = {
    'LIQUIDEZ': 0.30,       # 30%
    'ENDIVIDAMENTO': 0.40,  # 40%
    'RENTABILIDADE': 0.30   # 30%
}

# 5b. O Barema de Pontuação (0-100)
# (Manter isto aqui centraliza as regras de negócio)
BAREMA_LIQUIDEZ_CORRENTE = [
    (2.0, 100), # > 2.0 = 100 pontos
    (1.5, 80),  # > 1.5 = 80 pontos
    (1.0, 60),  # > 1.0 = 60 pontos
    (0.8, 40),  # > 0.8 = 40 pontos
    (0.0, 20)   # <= 0.8 = 20 pontos
]

BAREMA_ENDIVIDAMENTO_GERAL = [
    (0.4, 100), # < 0.4 = 100 pontos
    (0.6, 80),
    (0.8, 50),
    (float('inf'), 20) # Acima de 0.8 = 20 pontos
]

BAREMA_DIVIDA_PL = [
    (1.0, 100), # < 1.0 = 100 pontos
    (2.0, 80),
    (3.5, 50),
    (float('inf'), 20)
]

BAREMA_ROE = [
    (0.20, 100), # > 20% = 100 pontos
    (0.15, 90),
    (0.10, 70),
    (0.05, 50),
    (0.00, 30),  # > 0% = 30 pontos
    (float('-inf'), 10) # Negativo = 10 pontos
]

# 5c. Faixas de Conversão Score -> Rating
FAIXAS_RATING = [
    (95, "AAA"),
    (90, "AA+"),
    (85, "AA"),
    (80, "AA-"),
    (75, "A+"),
    (70, "A"),
    (65, "A-"),
    (60, "BBB+"),
    (55, "BBB"),
    (50, "BBB-"),
    (45, "BB+"),
    (40, "BB"),
    (35, "BB-"),
    (30, "B+"),
    (25, "B"),
    (20, "B-"),
    (15, "CCC"),
    (10, "CC"),
    (0, "D")
]