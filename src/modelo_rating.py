import pandas as pd
import sys
import config # <-- IMPORTA A NOSSA CONFIGURAÇÃO

class ModeloRating:
    
    def __init__(self):
        # Usa as constantes do config.py
        self.PESOS_INDICADORES = config.PESOS_RATING
        self.BAREMA_LC = config.BAREMA_LIQUIDEZ_CORRENTE
        self.BAREMA_EG = config.BAREMA_ENDIVIDAMENTO_GERAL
        self.BAREMA_DPL = config.BAREMA_DIVIDA_PL
        self.BAREMA_ROE = config.BAREMA_ROE
        self.FAIXAS_RATING = config.FAIXAS_RATING
        
        print("ModeloRating iniciado com sucesso.")

    def _pontuar_indicador(self, valor, barema, menor_melhor=False):
        """
        Método INTERNO genérico para aplicar o "Barema".
        """
        if menor_melhor: # Para endividamento (menor é melhor)
            for limite, pontos in barema:
                if valor < limite:
                    return pontos
        else: # Para liquidez e ROE (maior é melhor)
            for limite, pontos in barema:
                if valor > limite:
                    return pontos
        return 0 # Default

    def _converter_score_para_rating(self, score):
        for limite, rating in self.FAIXAS_RATING:
            if score > limite:
                return rating
        return "D" # Default (o último da lista)

    def calcular_rating_empresa(self, indicadores_empresa):
        """
        Método PÚBLICO. Orquestra o cálculo de Rating.
        """
        
        try:
            # 4a. Pontuar indicadores individuais
            pontos_lc = self._pontuar_indicador(indicadores_empresa['liq_corrente'], self.BAREMA_LC)
            
            pontos_eg = self._pontuar_indicador(indicadores_empresa['endividamento_geral'], self.BAREMA_EG, menor_melhor=True)
            pontos_dpl = self._pontuar_indicador(indicadores_empresa['divida_pl'], self.BAREMA_DPL, menor_melhor=True)
            
            pontos_roe = self._pontuar_indicador(indicadores_empresa['roe'], self.BAREMA_ROE)

            # 4b. Calcular a média de cada grupo
            score_liquidez = pontos_lc
            score_rentabilidade = pontos_roe
            score_endividamento = (pontos_eg + pontos_dpl) / 2
            
            # 4c. Aplicar os PESOS (Média Ponderada)
            score_final = (
                (score_liquidez * self.PESOS_INDICADORES['LIQUIDEZ']) +
                (score_endividamento * self.PESOS_INDICADORES['ENDIVIDAMENTO']) +
                (score_rentabilidade * self.PESOS_INDICADORES['RENTABILIDADE'])
            )
            
            # 4d. Converter para Rating
            rating_final = self._converter_score_para_rating(score_final)

            # 5. Retornar os resultados
            resultado = {
                'score_final': round(score_final, 2),
                'rating': rating_final,
                'detalhes_scores': {
                    'score_liquidez': score_liquidez,
                    'score_endividamento': score_endividamento,
                    'score_rentabilidade': score_rentabilidade
                }
            }
            return resultado
            
        except KeyError as e:
            print(f"ERRO no ModeloRating: Indicador-chave {e} não encontrado nos dados.")
            return None
        except Exception as e:
            print(f"ERRO no ModeloRating: {e}")
            return None