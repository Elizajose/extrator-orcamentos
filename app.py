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
    pdf.cell(0, 10, txt="Relatorio de Melhores Precos - Extrator de Orcamentos", ln=True, align='C')
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

# --- CUSTOM CSS (O SEGREDO DO VISUAL NOVO) ---
st.markdown("""
    <style>
    /* Oculta os labels padrão do file_uploader para usarmos os nossos em HTML */
    [data-testid="stFileUploader"] label {
        display: none;
    }
    
    /* Deixa os Cards (Containers) com cara de SaaS, bordas arredondadas e sombra leve */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        padding: 1rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }

    /* Estiliza a área de arrastar o arquivo (Dropzone) */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #cbd5e1 !important;
        border-radius: 12px !important;
        background-color: #f8fafc !important;
    }

    /* O Botão Principal Azul */
    div.stButton > button {
        background-color: #3b82f6 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: #2563eb !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }
    
    /* Esconde o menu superior do Streamlit para ficar mais limpo */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO CUSTOMIZADO EM HTML ---
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 30px; margin-top: 10px;">
    <div style="background-color: #e0e7ff; padding: 20px; border-radius: 16px; margin-right: 20px;">
        <span style="font-size: 40px;">🧾</span>
    </div>
    <div>
        <h1 style="margin: 0; padding: 0; color: #0f172a; font-family: sans-serif;">Extrator de Orçamentos</h1>
        <p style="margin: 5px 0 0 0; color: #64748b; font-size: 16px;">✨ Automatize a análise das suas cotações e encontre o <strong style="color: #3b82f6;">menor preço</strong> em segundos.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- ÁREA DE UPLOADS (CARDS INDEPENDENTES) ---
col_up1, col_up2 = st.columns(2)

with col_up1:
    with st.container(border=True):
        st.markdown("""
        <div style="margin-bottom: 15px;">
            <h3 style="margin: 0; color: #1e293b; font-size: 20px;">📄 1. Lista de Compras (.txt)</h3>
            <p style="margin: 0; color: #64748b; font-size: 14px;">Suba o arquivo com os itens (um por linha):</p>
        </div>
        """, unsafe_allow_html=True)
        arquivo_txt = st.file_uploader("txt_hidden", type=["txt"])

with col_up2:
    with st.container(border=True):
        st.markdown("""
        <div style="margin-bottom: 15px;">
            <h3 style="margin: 0; color: #1e293b; font-size: 20px;">📗 2. Orçamentos (.pdf)</h3>
            <p style="margin: 0; color: #64748b; font-size: 14px;">Faça o upload dos arquivos (Máximo de 10 PDFs):</p>
        </div>
        """, unsafe_allow_html=True)
        arquivos_pdfs = st.file_uploader("pdf_hidden", type=["pdf"], accept_multiple_files=True)

# --- REGRAS DE SEGURANÇA E LIMITES ---
pode_processar = True 
if arquivos_pdfs and len(arquivos_pdfs) > 10:
    st.error(f"⚠️ **Limite excedido!** Você anexou {len(arquivos_pdfs)} PDFs. O limite máximo do sistema é de 10 arquivos por vez.")
    pode_processar = False

st.write("") # Espaço em branco

# --- BANNER INFERIOR COM O BOTÃO (Igual a referência) ---
with st.container(border=True):
    col_texto, col_botao = st.columns([2, 1])
    
    with col_texto:
        st.markdown("""
        <div style="display: flex; align-items: center; height: 100%; margin-top: 5px;">
            <div style="margin-right: 15px; font-size: 30px;">🔍</div>
            <div>
                <h4 style="margin:0; color: #0f172a; font-size: 18px;">Pronto para analisar!</h4>
                <p style="margin:0; color: #64748b; font-size: 14px;">Clique no botão ao lado e deixe o sistema encontrar as melhores oportunidades para você.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_botao:
        st.write("") # Ajuste de alinhamento vertical
        if st.button("🚀 Processar Análise", use_container_width=True, disabled=not pode_processar):
            iniciar_processamento = True
        else:
            iniciar_processamento = False

# --- MOTOR DE PROCESSAMENTO ---
if iniciar_processamento:
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("⚠️ Por favor, suba a lista em TXT e pelo menos um PDF antes de processar.")
    else:
        st.session_state.tabela_vencedores = None
        texto_lista = arquivo_txt.getvalue().decode("utf-8")
        
        with st.spinner('Analisando documentos via IA... Por favor, aguarde.'):
            lista_geral_itens = []
            
            for arquivo_pdf in arquivos_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(arquivo_pdf.getvalue())
                    caminho_temporario = tmp.name
                
                try:
                    resultado_str = analisar_precos_direto_no_pdf(caminho_temporario, texto_lista)
                    
                    if resultado_str.startswith("RATE_LIMIT_ERROR"):
                        st.error(f"❌ O arquivo '{arquivo_pdf.name}' excedeu o limite gratuito da IA.")
                        st.info("⏳ Pausando por 60 segundos para resetar o limite. Aguarde...")
                        time.sleep(60)
                        os.unlink(caminho_temporario)
                        continue 
                        
                    elif "Erro" in resultado_str:
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
                    if os.path.exists(caminho_temporario):
                        os.unlink(caminho_temporario)
                
                time.sleep(6)
            
            if lista_geral_itens:
                vencedores = {}
                for item in lista_geral_itens:
                    nome_produto = item.get("produto_buscado", "Desconhecido")
                    if nome_produto not in vencedores:
                        vencedores[nome_produto] = item
                    else:
                        try:
                            preco_novo = float(item.get("preco_unitario", 999999))
                            preco_vencedor = float(vencedores[nome_produto].get("preco_unitario", 999999))
                            if preco_novo < preco_vencedor:
                                vencedores[nome_produto] = item
                        except:
                            pass
                
                tabela_final = list(vencedores.values())
                st.session_state.tabela_vencedores = tabela_final
            else:
                st.warning("Nenhum dos itens foi encontrado nos orçamentos válidos.")

# --- EXIBIÇÃO E DOWNLOADS ---
if st.session_state.tabela_vencedores is not None:
    st.markdown("<br><h3 style='color: #0f172a;'>✅ Análise Concluída! Veja os melhores preços:</h3>", unsafe_allow_html=True)
    
    st.dataframe(
        st.session_state.tabela_vencedores,
        column_config={
            "produto_buscado": "Produto Solicitado",
            "descricao_loja": "Descrição na Nota",
            "preco_unitario": st.column_config.NumberColumn("Melhor Preço Un.", format="R$ %.2f"),
            "nome_empresa": "Fornecedor Vencedor",
            "cnpj": "CNPJ"
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        pdf_bytes = gerar_pdf(st.session_state.tabela_vencedores)
        st.download_button(
            label="📄 Baixar Relatório (PDF)",
            data=pdf_bytes,
            file_name="relatorio_orcamentos_vencedores.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_d2:
        df_export = pd.DataFrame(st.session_state.tabela_vencedores)
        if not df_export.empty:
            df_export = df_export[["produto_buscado", "descricao_loja", "preco_unitario", "nome_empresa", "cnpj"]]
            df_export.columns = ["Produto Solicitado", "Descrição Nota", "Melhor Preço Un.", "Fornecedor", "CNPJ"]
            csv = df_export.to_csv(index=False, sep=";").encode('utf-8-sig')
            
            st.download_button(
                label="📊 Baixar Planilha (CSV)",
                data=csv,
                file_name="planilha_orcamentos_vencedores.csv",
                mime="text/csv",
                use_container_width=True
            )
