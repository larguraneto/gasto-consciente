import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Gasto Consciente", page_icon="💰", layout="centered")

# --- Conexão com Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Funções ---
def carregar_dados():
    try:
        # ttl=0 garante que ele não pegue dados "velhos" da memória (cache), sempre pega o atual
        df = conn.read(ttl=0)
        if df.empty or len(df.columns) < 4:
             return pd.DataFrame(columns=["Data", "Categoria", "Valor", "Descrição"])
        # Tratamento de dados para evitar erros de cálculo
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0.0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df
    except Exception:
         return pd.DataFrame(columns=["Data", "Categoria", "Valor", "Descrição"])

def salvar_no_google(df_novo):
    # Esta função sobrescreve a planilha inteira com os dados atualizados
    conn.update(data=df_novo)
    st.cache_data.clear() # Limpa o cache para garantir que a próxima leitura seja fresca

# --- Interface Principal ---
st.title("💰 Controle Financeiro")
st.write("Sistema integrado ao Google Sheets ☁️")

# Abas com os nomes novos
aba_registro, aba_analise = st.tabs(["Registro de Gastos", "Relatórios de Gastos"])

# --- ABA 1: REGISTRO ---
with aba_registro:
    st.header("Novo Registro")
    with st.form("form_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_gasto = st.date_input("Data", datetime.now())
        with col2:
            valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")

        opcoes_categorias = [
            "Alimentação", "Transporte", "Moradia", "Saúde/Farmácia", 
            "Lazer", "Educação", "Compras/Vestuário", 
            "Assinaturas/Serviços", "Investimentos", "Presentes", "Outros"
        ]
        categoria = st.selectbox("Categoria", opcoes_categorias)
        descricao = st.text_input("Descrição (Ex: Almoço)")
        
        if st.form_submit_button("💾 Salvar Gasto", use_container_width=True):
            df_atual = carregar_dados()
            novo_dado = pd.DataFrame([{
                "Data": str(data_gasto),
                "Categoria": categoria,
                "Valor": valor,
                "Descrição": descricao
            }])
            df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
            salvar_no_google(df_final)
            st.success("✅ Salvo no Google Sheets!")

# --- ABA 2: RELATÓRIOS E EDIÇÃO ---
with aba_analise:
    st.header("Panorama")
    
    # Botão de atualizar manual (útil quando a internet oscila)
    if st.button("🔄 Recarregar Dados"):
        st.rerun()

    df = carregar_dados()
    
    if not df.empty and 'Valor' in df.columns:
        total = df["Valor"].sum()
        
        # Métricas
        st.metric("Total Gasto", f"R$ {total:.2f}")
        
        st.divider()
        
        # Gráfico
        if total > 0:
            st.subheader("Distribuição")
            fig = px.pie(df, values="Valor", names="Categoria", hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # --- ÁREA DE EDIÇÃO ---
        st.subheader("📝 Editar ou Excluir")
        st.info("Altere valores direto na tabela ou marque a caixa para excluir.")
        
        # Prepara a tabela para edição
        df_edicao = df.copy()
        # Insere a coluna de excluir no começo (Check box)
        if "Excluir" not in df_edicao.columns:
            df_edicao.insert(0, "Excluir", False)
        
        # Mostra o editor
        df_editado = st.data_editor(
            df_edicao, 
            use_container_width=True, 
            hide_index=True,
            num_rows="dynamic" # Permite adicionar linhas se quiser
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        # Botão Vermelho (Ação de Excluir)
        with col_btn1:
            if st.button("🗑️ Excluir Marcados", type="primary"):
                # Filtra mantendo apenas o que NÃO foi marcado para excluir
                df_final = df_editado[df_editado["Excluir"] == False]
                # Remove a coluna auxiliar 'Excluir' antes de mandar pro Google
                df_final = df_final.drop(columns=["Excluir"])
                
                salvar_no_google(df_final)
                st.success("Itens excluídos da nuvem!")
                st.rerun()
        
        # Botão Normal (Ação de Salvar Edição de Texto/Valor)
        with col_btn2:
            if st.button("💾 Salvar Alterações"):
                # Apenas remove a coluna auxiliar e salva
                df_final = df_editado.drop(columns=["Excluir"])
                
                salvar_no_google(df_final)
                st.success("Alterações salvas na nuvem!")
                st.rerun()

    else:
        st.info("Nenhum dado encontrado.")