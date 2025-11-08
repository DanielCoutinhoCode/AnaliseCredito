import pandas as pd
import os
import sys
from datetime import datetime
import config 

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    from fpdf.fonts import FontFace
except ImportError:
    print("ERRO: Biblioteca 'fpdf2' não encontrada.")
    sys.exit(1)

try:
    from alerta_flags import GeradorAlertas
    from modelo_rating import ModeloRating
except ImportError:
    print("ERRO: Falha ao importar AlertaFlags ou ModeloRating.")
    sys.exit(1)


class GeradorRelatorioPDF:
    
    def __init__(self):
        self.diretorio_relatorios_pdf = config.CAMINHO_OUTPUT_REPORTS
        self.TRADUCAO_INDICADORES = config.TRADUCAO_INDICADORES
        self.INDICADORES_PERCENTUAIS = config.INDICADORES_PERCENTUAIS
        self.perc_traduzidos = [self.TRADUCAO_INDICADORES.get(p) for p in self.INDICADORES_PERCENTUAIS]
        
        os.makedirs(self.diretorio_relatorios_pdf, exist_ok=True)
        print(f"GeradorRelatorioPDF iniciado. Pasta de saída: {self.diretorio_relatorios_pdf}")

    def _ler_dados_relatorio(self, ticker_alvo, ano):
        # (Este método está correto e otimizado)
        ticker_alvo_upper = ticker_alvo.upper()
        nome_completo = f"relatorio_pares_{ticker_alvo_upper}_{ano}_completo.csv"
        nome_comparativo = f"relatorio_pares_{ticker_alvo_upper}_{ano}_comparativo.csv"
        
        caminho_completo = os.path.join(config.CAMINHO_DADOS_PROCESSADOS, nome_completo)
        caminho_comparativo = os.path.join(config.CAMINHO_DADOS_PROCESSADOS, nome_comparativo)
        
        try:
            df_completo = pd.read_csv(
                caminho_completo, sep=';', index_col=0, decimal='.', encoding='utf-8-sig'
            )
            df_comparativo = pd.read_csv(
                caminho_comparativo, sep=';', index_col=0, decimal='.', encoding='utf-8-sig'
            )
            dados_alvo_brutos = df_completo[ticker_alvo_upper].to_dict()
            return df_completo, df_comparativo, dados_alvo_brutos
        except Exception as e:
            print(f"ERRO ao ler arquivos CSV (verifique 'analise_setorial.py'): {e}")
            return None, None, None

    def _escrever_tabela_pdf(self, pdf, df_dados, col_widths, text_align):
        pdf.set_font("Helvetica", size=10)
        estilo_cabecalho_tabela = FontFace(emphasis="BOLD")
        
        with pdf.table(
            col_widths=col_widths,
            text_align=text_align,
            first_row_as_headings=True,
            headings_style=estilo_cabecalho_tabela,
            line_height=1.5
        ) as tabela:
            # Add header row
            row = tabela.row()
            for cell in df_dados[0]:
                row.cell(cell, align="CENTER")
            
            # Add data rows
            for linha in df_dados[1:]:
                row = tabela.row()
                for cell in linha:
                    row.cell(str(cell), align="CENTER", middle=True)

    def gerar_relatorio(self, ticker_alvo, ano, resultado_rating, lista_alertas, df_comparativo, df_completo_t):
        """
        Método PRINCIPAL. Orquestra a criação do PDF.
        """
        
        print(f"Iniciando geração de PDF para {ticker_alvo} ({ano})...")
        
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # --- Secções 2, 3, 4, 5 (Títulos, Rating, Alertas) ---
        # (Estas secções estão corretas e não mudam)
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Relatório de Análise de Crédito", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 10, f"Empresa Alvo: {ticker_alvo.upper()} | Ano: {ano}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        pdf.set_font("Helvetica", '', 8)
        data_geracao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        pdf.cell(0, 10, f"Gerado em: {data_geracao}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 7, "Rating de Crédito (Absoluto):", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(2)
        pdf.set_font("Helvetica", 'B', 24)
        pdf.cell(0, 10, resultado_rating['rating'], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 7, f"Score Final (0-100): {resultado_rating['score_final']:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        detalhes = resultado_rating['detalhes_scores']
        pdf.set_font("Helvetica", '', 8)
        pdf.cell(0, 5, f"Detalhes: Liquidez ({detalhes['score_liquidez']:.0f}) | Endividamento ({detalhes['score_endividamento']:.0f}) | Rentabilidade ({detalhes['score_rentabilidade']:.0f})",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 7, "Conclusões e Sinais de Alerta (vs. Média do Setor):", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(2)
        pdf.set_font("Helvetica", '', 10)
        largura_texto = pdf.w - pdf.l_margin - pdf.r_margin
        for alerta in lista_alertas:
            if "[RED FLAG]" in alerta:
                pdf.set_text_color(194, 24, 7)
            elif "[GREEN FLAG]" in alerta:
                pdf.set_text_color(0, 128, 0)
            pdf.multi_cell(largura_texto, 5, f"- {alerta}", new_x=XPos.LMARGIN)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(10)
        
        # --- Seção 8 (Tabela Comparativa) ---
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 7, "Análise Comparativa (Empresa vs. Média do Setor):", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(2)
        df_comp_renomeado = df_comparativo.rename(index=self.TRADUCAO_INDICADORES)
        dados_tabela_comp = [ [df_comp_renomeado.index.name or 'Indicador'] + list(df_comp_renomeado.columns) ]
        for idx, row in df_comp_renomeado.iterrows():
            linha_formatada = [idx]
            for val in row:
                if idx in self.perc_traduzidos:
                    linha_formatada.append(f"{val*100:.2f}%")
                else:
                    linha_formatada.append(f"{val:.2f}")
            dados_tabela_comp.append(linha_formatada)
        self._escrever_tabela_pdf(pdf, dados_tabela_comp, 
                                 col_widths=(60, 65, 65), 
                                 text_align=("LEFT", "CENTER", "CENTER"))
        pdf.ln(10)

        # --- Seção 9 (Tabela Completa) - CORRIGIDA ---
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 7, "Indicadores Detalhados (Todos os Pares):", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(2)
        
        df_completo_t_renomeado = df_completo_t.rename(columns=self.TRADUCAO_INDICADORES)
        dados_tabela_completa = [ [df_completo_t_renomeado.index.name or 'Empresa'] + list(df_completo_t_renomeado.columns) ]
        for idx, row in df_completo_t_renomeado.iterrows():
            linha_formatada = [idx]
            for nome_coluna, val in row.items():
                if nome_coluna in self.perc_traduzidos:
                    linha_formatada.append(f"{val*100:.2f}%")
                else:
                    linha_formatada.append(f"{val:.2f}")
            dados_tabela_completa.append(linha_formatada)
        
        # --- LÓGICA DE LARGURA DINÂMICA ---
        # 1. Contar o número total de colunas
        num_colunas = len(dados_tabela_completa[0]) # (ex: 1 + 8 = 9 colunas)
        
        # 2. Definir a largura da primeira coluna (Nomes)
        largura_primeira_coluna = 50 # 50mm para o nome
        
        # 3. Calcular a largura restante para as colunas de dados
        largura_pagina_util = 190 # (210mm - 20mm de margens)
        largura_restante = largura_pagina_util - largura_primeira_coluna
        num_colunas_dados = num_colunas - 1
        
        # 4. Calcular a largura de cada coluna de dados
        # (Se for 0, definir um padrão para evitar divisão por zero)
        if num_colunas_dados > 0:
            largura_coluna_dados = largura_restante / num_colunas_dados
        else:
            largura_coluna_dados = largura_restante
            
        # 5. Criar as listas de 'col_widths' e 'text_align' dinamicamente
        col_widths = [largura_primeira_coluna] + [largura_coluna_dados] * num_colunas_dados
        text_align = ["LEFT"] + ["CENTER"] * num_colunas_dados
        
        # (Se houver muitas colunas, o texto do cabeçalho pode quebrar, 
        # mas o PDF não vai mais "crashar")
        
        self._escrever_tabela_pdf(pdf, dados_tabela_completa,
                                  col_widths=tuple(col_widths), # Converte lista para tuplo
                                  text_align=tuple(text_align)) # Converte lista para tuplo
        
        # 10. Guardar o Arquivo PDF
        nome_pdf = f"Relatorio_Analise_{ticker_alvo.upper()}_{ano}.pdf"
        caminho_pdf = os.path.join(self.diretorio_relatorios_pdf, nome_pdf)
        
        try:
            pdf.output(caminho_pdf)
            print(f"\n--- SUCESSO! ---")
            print(f"Relatório PDF gerado em: {caminho_pdf}")
        except Exception as e:
            print(f"\n--- ERRO AO SALVAR PDF ---")
            print(f"Erro: {e}")