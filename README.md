Sistema Automatizado de Análise de Crédito Corporativo 🚀
Este projeto é um pipeline completo de análise de crédito em Python. Ele automatiza todo o fluxo de trabalho, desde a coleta de dados brutos da CVM até a geração de um relatório final com um rating de crédito e uma análise comparativa de pares do setor.

📊 Demo Interativa (Streamlit)
Você pode testar a aplicação web interativa neste link:

[https://app-credito.streamlit.app/]

(Este é o link que você obteve no "Deploy" - ex: https://meu-projeto-analise.streamlit.app/)

🎯 Principais Funcionalidades
O sistema é construído como um conjunto de "fábricas" modulares (na pasta /src/) que executam as seguintes tarefas:

Coleta Automatizada: Baixa e processa os demonstrativos financeiros (DFPs anuais) e dados cadastrais diretamente do Portal de Dados Abertos da CVM.

Análise de Pares Dinâmica: Permite ao usuário definir um Ticker-alvo (ex: PETR4) e uma lista de pares concorrentes (ex: PRIO3, RECV3, BRAV3), automatizando a análise comparativa.

Mapeamento Ticker ➔ CNPJ ➔ Setor: Utiliza um mapa mestre (mapa_ticker_cnpj.csv) para traduzir tickers (B3) em CNPJs (CVM) e um gestor de cadastro (gestor_cadastro.py) para encontrar os pares de forma robusta.

Cálculo Robusto de Indicadores: Implementa:

Lógica de Fallback: Tenta dados Consolidados (_con_) primeiro; se falhar, procura os dados Individuais (_ind_).

Otimização de Baixa Memória: Lê os arquivos ZIP da CVM "em pedaços" (chunks) para funcionar em ambientes com pouca RAM (como o Streamlit Cloud).

Robustez: Converte divisões por zero em nan (em vez de 0.0) para não distorcer as médias.

Modelo de Rating (Scoring): Gera um score quantitativo (0-100) e um rating (ex: "BB+") com base num barema e pesos personalizáveis (definidos no config.py).

Geração de Alertas: Gera "Red Flags" 🚩 e "Green Flags" 💚 ao comparar os indicadores da empresa-alvo com a média do setor.

Geração de Relatório PDF: Exporta a análise completa (Rating, Alertas, Tabelas) para um relatório PDF profissional, pronto para apresentação.

Interface Web: Um dashboard interativo (dashboard.py) construído com Streamlit para fácil utilização.

🛠️ Tecnologias Utilizadas
Python 3.11+

Streamlit: Para a interface web e o deploy.

Pandas: Para toda a manipulação e análise dos dados.

Requests: Para a coleta de dados (download dos arquivos .zip da CVM).

fpdf2: Para a geração do relatório final em .pdf.

📂 Estrutura do Projeto
O projeto é orquestrado pelo main.py (terminal) ou dashboard.py (web), que utilizam as "fábricas" modulares localizadas na pasta /src/.

AnaliseCredito/
│
├── .gitignore
├── dashboard.py         # <-- Ponto de entrada do App (Streamlit)
├── main.py              # <-- Ponto de entrada do Terminal (PDF)
├── requirements.txt     # <-- Dependências para o deploy
│
├── data/
│   ├── processed/
│   │   └── mapa_ticker_cnpj.csv # Nosso mapa Ticker -> CNPJ
│   └── raw/
│       ├── (Esta pasta é ignorada pelo .gitignore)
│       └── (Aqui ficam os .zip e .csv da CVM baixados)
│
├── output/
│   └── reports/
│       └── (Esta pasta é ignorada pelo .gitignore)
│
└── src/
    ├── config.py                # <-- CONFIGURAÇÃO CENTRAL (Pesos, Baremos, Caminhos)
    ├── coleta_dados.py          # (Fábrica 1) Baixa os dados da CVM
    ├── gestor_cadastro.py       # (Fábrica 2) Mapeia Ticker -> CNPJ -> Setor -> Pares
    ├── calculo_indicadores.py   # (Fábrica 3) Calcula os indicadores (Lógica de Fallback)
    ├── analise_setorial.py      # (Fábrica 4) Orquestra a análise dos pares
    ├── modelo_rating.py         # (Fábrica 5) Aplica o modelo de scoring (A+, B-, etc.)
    ├── alerta_flags.py          # (Fábrica 6) Gera os Red/Green Flags (vs. Média)
    └── gerador_relatorio.py     # (Fábrica 7) Monta o relatório final em PDF -> Geração do relatório desabilitada temporariamente por conta da implementação do dashboard online
    
