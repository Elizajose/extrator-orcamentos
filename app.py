import streamlit as st
import os
import tempfile
import json
import pandas as pd
import time
from fpdf import FPDF
from extrator import analisar_precos_direto_no_pdf 

# --- INICIALIZA A MEMÓRIA DA PÁGINA ---
if "tabela_vencedores" not in st.session_state:
    st.session_state.tabela_vencedores = None

# --- FUNÇÃO PARA DESENHAR O PDF ---
def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="Relatorio de Melhores Precos - ColetaE", ln=True, align='C')
    pdf.ln(10)

    for item in dados:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, txt=f"Produto: {item.get('produto_buscado', 'N/A')}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, txt=f"-> Fornecedor: {item.get('nome_empresa', 'N/A')} (CNPJ: {item.get('cnpj', 'N/A')})", ln=True)
        pdf.multi_cell(0, 8, txt=f"-> Descricao na Nota: {item.get('descricao_loja', 'N/A')}")
        preco = item.get('preco_unitario', 0.0)
        try:
            preco_formatado = f"R$ {float(preco):.2f}"
        except:
            preco_formatado = f"R$ {preco}"
        pdf.cell(0, 8, txt=f"-> Melhor Preco: {preco_formatado}", ln=True)
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Extrator de Orçamentos", layout="wide", page_icon="🧾")
st.title("🧾 Extrator de Orçamentos")
st.markdown("---")


col_up1, col_up2 = st.columns(2)

with col_up1:
    st.subheader("1. Lista de Compras (.txt)")
    arquivo_txt = st.file_uploader("Arquivo com os itens:", type=["txt"])

with col_up2:
    st.subheader("2. Orçamentos (.pdf)")
    st.caption("Selecione múltiplos PDFs simultaneamente.")
    arquivos_pdfs = st.file_uploader("Faça o upload dos PDFs", type=["pdf"], accept_multiple_files=True)

st.markdown("---")

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Processar Análise de Preços", type="primary", use_container_width=True):
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("⚠️ Por favor, suba a lista em TXT e pelo menos um PDF.")
    else:
        texto_lista = arquivo_txt.getvalue().decode("utf-8")
        
        with st.spinner('Analisando documentos via OCR... Por favor, aguarde.'):
            lista_geral_itens = []
            
            for arquivo_pdf in arquivos_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(arquivo_pdf.getvalue())
                    caminho_temporario = tmp.name
                
                try:
                    resultado_str = analisar_precos_direto_no_pdf(caminho_temporario, texto_lista)
                    
                    if "Erro" in resultado_str:
                        st.error(f"Aviso no arquivo {arquivo_pdf.name}: {resultado_str}")
                    else:
                        try:
                            dados_json = json.loads(resultado_str)
                            lista_geral_itens.extend(dados_json)
                        except json.JSONDecodeError:
                            st.error(f"Erro na conversão dos dados da loja: {arquivo_pdf.name}.")
                except Exception as e:
                    st.error(f"Falha ao analisar o arquivo {arquivo_pdf.name}: {e}")
                finally:
                   os.unlink(caminho_temporario)
                
                # remover quando for para versão paga
                time.sleep(6)
            
            # --- LÓGICA DE COMPARAÇÃO ---
            if lista_geral_itens:
                vencedores = {}
                for item in lista_geral_itens:
                    nome_produto = item.get("produto_buscado", "Desconhecido")
                    if nome_produto not in vencedores:
                        vencedores[nome_produto] = item
                    else:
                        if item.get("preco_unitario", float('inf')) < vencedores[nome_produto].get("preco_unitario", float('inf')):
                            vencedores[nome_produto] = item
                
                tabela_final = list(vencedores.values())
                
                # --- LIMPEZA DE DUPLICATAS ---
                # Remove itens exatos (mesma loja, mesmo preço, mesma descrição)
                df_limpo = pd.DataFrame(tabela_final)
                df_limpo = df_limpo.drop_duplicates(subset=['descricao_loja', 'nome_empresa', 'preco_unitario'])
                
                # Salva o resultado na memória do Streamlit
                st.session_state.tabela_vencedores = df_limpo.to_dict('records')
            else:
                st.warning("Nenhum dos itens foi encontrado.")
                st.session_state.tabela_vencedores = None

# --- EXIBIÇÃO E DOWNLOADS (Fora do bloco do botão) ---
# Isso garante que a tabela e os botões de download continuem na tela mesmo após recarregar
if st.session_state.tabela_vencedores is not None:
    st.success("✅ Análise Concluída com Sucesso!")
    
    st.dataframe(
        st.session_state.tabela_vencedores,
        column_config={
            "produto_buscado": "Produto Buscado",
            "descricao_loja": "Descrição Original",
            "preco_unitario": st.column_config.NumberColumn("Melhor Preço", format="R$ %.2f"),
            "nome_empresa": "Fornecedor Vencedor",
            "cnpj": "CNPJ"
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    st.subheader("📥 Exportar Relatórios")
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        pdf_bytes = gerar_pdf(st.session_state.tabela_vencedores)
        st.download_button(
            label="📄 Relatório Final (PDF)",
            data=pdf_bytes,
            file_name="relatorio_coletae.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
    with col_d2:
        df_export = pd.DataFrame(st.session_state.tabela_vencedores)
        df_export.columns = ["Produto Buscado", "Descrição Loja", "Melhor Preço", "Fornecedor", "CNPJ"]
        csv = df_export.to_csv(index=False, sep=";").encode('utf-8-sig')
        
        st.download_button(
            label="📊 Tabela Completa (CSV)",
            data=csv,
            file_name="planilha_coletae.csv",
            mime="text/csv",
            use_container_width=True
        )