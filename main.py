# =======================================================================================
# CÓDIGO FINAL DO SIMULADOR DE CARTEIRA - VERSÃO STREAMLIT COM TODOS OS INCREMENTOS
# =======================================================================================

# Passo 1: Importação das bibliotecas necessárias
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
from datetime import datetime
from bcb import sgs

# Ignorar avisos para uma saída mais limpa
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

# =======================================================================================
# PASSO 2: FUNÇÃO PRINCIPAL DA SIMULAÇÃO (O CÁLCULO NÃO MUDA)
# =======================================================================================
def simular_carteira_com_aportes(dados_completos, pct_cdi, tickers, valor_aporte_inicial, valor_aporte_periodico, numero_aportes):
    """
    Calcula a evolução de uma carteira com aportes periódicos.
    """
    dados = dados_completos.copy()
    
    # Define as datas em que os aportes periódicos ocorrerão
    if numero_aportes > 0:
        intervalo_aportes = len(dados) // numero_aportes if numero_aportes > 0 else len(dados) + 1
        indices_aportes = [i * intervalo_aportes for i in range(numero_aportes)]
        datas_aportes = dados.index[indices_aportes].tolist()
    else:
        datas_aportes = []

    # --- Inicialização das carteiras com o Aporte Inicial ---
    capital_em_cdi = valor_aporte_inicial * pct_cdi
    aporte_inicial_acoes = valor_aporte_inicial * (1.0 - pct_cdi)
    acoes_carteira = {ticker: 0.0 for ticker in tickers}
    if tickers and valor_aporte_inicial > 0:
        aporte_inicial_por_acao = aporte_inicial_acoes / len(tickers)
        preco_inicial_dia = dados.iloc[0]
        for ticker in tickers:
            preco = float(preco_inicial_dia[ticker])
            if preco > 0:
                acoes_carteira[ticker] = aporte_inicial_por_acao / preco

    capital_bench_cdi = valor_aporte_inicial
    capital_bench_ipca = valor_aporte_inicial
    
    patrimonio_diario = []
    patrimonio_bench_cdi_diario = []
    patrimonio_bench_ipca_diario = []
    
    mes_anterior = None

    for data_atual, linha in dados.iterrows():
        # 1. Verifica se hoje é dia de aporte periódico
        if data_atual in datas_aportes:
            capital_em_cdi += valor_aporte_periodico * pct_cdi
            aporte_em_acoes = valor_aporte_periodico * (1.0 - pct_cdi)
            
            if tickers:
                aporte_por_acao = aporte_em_acoes / len(tickers)
                for ticker in tickers:
                    preco_do_dia = float(linha[ticker])
                    if preco_do_dia > 0:
                        acoes_carteira[ticker] += aporte_por_acao / preco_do_dia
            
            capital_bench_cdi += valor_aporte_periodico
            capital_bench_ipca += valor_aporte_periodico

        # 2. Rendimento diário do capital alocado
        capital_em_cdi *= linha['fator_cdi_diario']
        capital_bench_cdi *= linha['fator_cdi_diario']
        
        mes_atual = data_atual.month
        if mes_anterior is not None and mes_atual != mes_anterior:
            capital_bench_ipca *= linha['fator_ipca_mensal']
        mes_anterior = mes_atual

        # 3. Cálculo do patrimônio diário
        valor_acoes_hoje = sum(acoes_carteira[ticker] * float(linha[ticker]) for ticker in tickers)
        
        patrimonio_total_carteira = valor_acoes_hoje + capital_em_cdi
        patrimonio_diario.append(patrimonio_total_carteira)
        patrimonio_bench_cdi_diario.append(capital_bench_cdi)
        patrimonio_bench_ipca_diario.append(capital_bench_ipca)

    dados['Patrimonio_Carteira'] = patrimonio_diario
    dados['Patrimonio_Benchmark_CDI'] = patrimonio_bench_cdi_diario
    dados['Patrimonio_Benchmark_IPCA'] = patrimonio_bench_ipca_diario
    
    return dados

# =======================================================================================
# PASSO 3: CONFIGURAÇÃO DA INTERFACE COM STREAMLIT
# =======================================================================================

# Configura o título da página e o layout
st.set_page_config(layout="wide", page_title="Simulador de Carteira")

# Título principal da aplicação
st.title("📊 Simulador de Carteira de Investimentos com Aportes")
st.markdown("Use os controles na barra lateral para configurar e rodar a simulação (No celular clique em '>>').")

# --- Barra Lateral (Sidebar) para os controles ---
st.sidebar.header("Parâmetros da Simulação")

# --- Widgets na Sidebar ---
data_inicial = st.sidebar.date_input("Data Inicial", datetime(2021, 1, 1))
data_final = st.sidebar.date_input("Data Final", datetime.now())

aporte_inicial = st.sidebar.number_input("Aporte Inicial (R$)", min_value=0.0, value=10000.0, step=1000.0)
valor_aporte = st.sidebar.number_input("Valor por Aporte Periódico (R$)", min_value=0.0, value=1000.0, step=100.0)
numero_aportes = st.sidebar.number_input("Nº de Aportes Periódicos", min_value=0, value=24, step=1)

pct_cdi_int = st.sidebar.slider("% Alocado em CDI", min_value=0, max_value=100, value=80, step=5, format="%d%%")
pct_cdi = pct_cdi_int / 100.0

reinvestir_dividendos = st.sidebar.checkbox("Reinvestir Dividendos?", value=True)

num_ativos = st.sidebar.number_input("Nº de Ativos na Carteira", min_value=0, max_value=10, value=3, step=1)

# --- Criação dinâmica dos campos de ticker ---
tickers_inputs = []
exemplos = ['PETR4', 'BBAS3', 'CMIG4', 'ITUB4', 'VALE3', 'ELET3', 'WEGE3', 'SUZB3', 'B3SA3', 'ABEV3']
for i in range(num_ativos):
    tickers_inputs.append(
        st.sidebar.text_input(f"Ativo {i+1}", value=exemplos[i] if i < len(exemplos) else "").upper()
    )

# Botão para executar a simulação
if st.sidebar.button("Simular Carteira", type="primary"):

    # --- Lógica de execução que antes estava no notebook ---
    tickers_raw = [ticker for ticker in tickers_inputs if ticker]
    tickers = [t + '.SA' for t in tickers_raw if not t.endswith('.SA')]

    if not tickers and pct_cdi < 1.0:
        st.error("Por favor, insira os tickers dos ativos ou defina a alocação em CDI para 100%.")
    else:
        try:
            with st.spinner(f"Buscando dados para: {', '.join(tickers_raw) if tickers else 'CDI'}, CDI e IPCA..."):
                coluna_preco = 'Adj Close' if reinvestir_dividendos else 'Close'

                if tickers:
                    dados_ativos = yf.download(tickers, start=data_inicial, end=data_final, progress=False, auto_adjust=False)[coluna_preco]
                    if isinstance(dados_ativos, pd.Series):
                        dados_ativos = dados_ativos.to_frame(name=tickers[0])
                else: 
                    dados_ativos = pd.DataFrame(index=pd.date_range(start=data_inicial, end=data_final, name='Date'))

                # ***** CORREÇÃO APLICADA AQUI *****
                dados_cdi = sgs.get({'cdi': 12}, start=data_inicial, end=data_final)
                dados_ipca_mensal = sgs.get({'ipca': 433}, start=data_inicial, end=data_final)
                # ***** FIM DA CORREÇÃO *****

                dados_completos = dados_ativos.copy()
                dados_completos['fator_cdi_diario'] = 1 + (dados_cdi['cdi'] / 100)
                
                dados_ipca_mensal['fator_ipca_mensal'] = 1 + (dados_ipca_mensal['ipca'] / 100)
                dados_ipca_mensal.index = dados_ipca_mensal.index.to_period('M')
                dados_completos['mes'] = dados_completos.index.to_period('M')
                
                dados_completos = pd.merge(dados_completos, dados_ipca_mensal[['fator_ipca_mensal']],
                                           left_on='mes', right_index=True, how='left')
                
                dados_completos.fillna(method='ffill', inplace=True)
                dados_completos.dropna(inplace=True)

            st.success("Dados carregados com sucesso!")

            with st.spinner("Calculando a evolução da carteira com aportes..."):
                dados_resultado = simular_carteira_com_aportes(
                    dados_completos, pct_cdi, tickers,
                    aporte_inicial, valor_aporte, numero_aportes
                )

            if dados_resultado is None or dados_resultado.empty:
                st.error("Análise não pôde ser concluída (sem dados comuns para o período).")
            else:
                # =======================================================================
                # SEÇÃO DE RESULTADOS COM TODOS OS INCREMENTOS APLICADOS
                # =======================================================================
                st.subheader("Resultados Consolidados")

                # Extrai os resultados finais e calcula o total aportado
                resultado_carteira = float(dados_resultado['Patrimonio_Carteira'].iloc[-1])
                resultado_cdi = float(dados_resultado['Patrimonio_Benchmark_CDI'].iloc[-1])
                resultado_ipca = float(dados_resultado['Patrimonio_Benchmark_IPCA'].iloc[-1])
                total_aportado = aporte_inicial + (valor_aporte * numero_aportes)

                # 1. Calculos de rendimento
                rendimento_pct_carteira = ((resultado_carteira / total_aportado) - 1) if total_aportado > 0 else 0
                rendimento_pct_cdi = ((resultado_cdi / total_aportado) - 1) if total_aportado > 0 else 0
                rendimento_pct_ipca = ((resultado_ipca / total_aportado) - 1) if total_aportado > 0 else 0
                
                # 2. Exibição dos resultados em colunas
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        label="Patrimônio Final da Carteira",
                        value=f"R$ {resultado_carteira:,.2f}",
                        delta=f"{rendimento_pct_carteira:.2%} de rendimento"
                    )
                    
                    # Lógica para estilizar o % do CDI com cor dinâmica
                    if rendimento_pct_cdi > 0:
                        percentual_do_cdi = (rendimento_pct_carteira / rendimento_pct_cdi) * 100
                        
                        # --- LÓGICA DA COR ---
                        # Se for maior ou igual a 100% do CDI, fica azul. Senão, vermelho.
                        if percentual_do_cdi >= 100:
                            cor_do_texto = "#2176ff" # Azul
                        else:
                            cor_do_texto = "#ff4b4b" # Vermelho
                        # --- FIM DA LÓGICA DA COR ---

                        st.markdown(
                            f"""
                            <p style='font-size: 1rem; color: {cor_do_texto}; margin-top: -10px;'>
                                <b>{percentual_do_cdi:.2f}% do CDI</b>
                            </p>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # Caso não seja aplicável, exibe em cinza
                        st.markdown(
                            f"""
                            <p style='font-size: 1rem; color: gray; margin-top: -10px;'>
                                <b>N/A</b>
                            </p>
                            """,
                            unsafe_allow_html=True
                        )

                with col2:
                    st.metric(
                        label="Patrimônio em 100% CDI",
                        value=f"R$ {resultado_cdi:,.2f}",
                        delta=f"{rendimento_pct_cdi:.2%} de rendimento"
                    )

                with col3:
                    st.metric(
                        label="Patrimônio em 100% IPCA",
                        value=f"R$ {resultado_ipca:,.2f}",
                        delta=f"{rendimento_pct_ipca:.2%} de rendimento"
                    )
                
                # =======================================================================
                # FIM DA SEÇÃO DE RESULTADOS
                # =======================================================================

                st.subheader("Evolução do Patrimônio")
                
                # Gráfico de Evolução do Patrimônio
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(dados_resultado.index, dados_resultado['Patrimonio_Carteira'], label='Evolução da Carteira', color='navy', linewidth=2.5)
                ax.plot(dados_resultado.index, dados_resultado['Patrimonio_Benchmark_CDI'], label='Benchmark: 100% CDI', color='purple', linestyle=':')
                ax.plot(dados_resultado.index, dados_resultado['Patrimonio_Benchmark_IPCA'], label='Benchmark: 100% IPCA', color='green', linestyle='-.')
                ax.set_title('Evolução da Carteira vs. Benchmarks', fontsize=16)
                ax.set_ylabel('Patrimônio (R$)')
                ax.grid(True, which='both', linestyle='--', linewidth=0.5)
                ax.legend()
                plt.tight_layout()
                st.pyplot(fig)

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
            st.error("Verifique os tickers dos ativos ou o período selecionado. Alguns ativos podem não ter dados para todo o intervalo.")

# --- Créditos no final da barra lateral ---
st.sidebar.markdown("---")
st.sidebar.markdown("Elaborado por Tales Rabelo Freitas")
st.sidebar.markdown("[LinkedIn](https://www.linkedin.com/in/tales-rabelo-freitas-1a1466187/)")
