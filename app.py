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

# --- CUSTOM CSS (BANHO DE LOJA) ---
# Aqui a gente injeta código visual (cores, botões arredondados, efeitos de hover)
st.markdown("""
    <style>
    /* Estilo do botão principal */
    div.stButton > button:first-child {
        background-color: #2e66ff; /* Azul corporativo moderno */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    /* Efeito ao passar o mouse no botão */
    div.stButton > button:first-child:hover {
        background-color: #1a4fdb;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(46, 102, 255, 0.3);
    }
    /* Melhorando os subtítulos */
    h3 {
        color: #e0e0e0;
        font-weight: 400 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.title("🧾 Extrator de Orçamentos")
st.markdown("Automatize a análise das suas cotações e encontre o :blue[**menor preço**] em segundos.")
st.markdown("---")

# --- ÁREA DE UPLOADS (AGORA ALINHADA) ---
col_up1, col_up2 = st.columns(2)

with col_up1:
    st.subheader("📝 1. Lista de Compras (.txt)")
    # O Streamlit já bloqueia múltiplos arquivos TXT por padrão quando não usamos "accept_multiple_files=True"
    arquivo_txt = st.file_uploader("Suba o arquivo com os itens (um por linha):", type=["txt"])

with col_up2:
    st.subheader("📑 2. Orçamentos (.pdf)")
    # Legenda removida para as caixas ficarem 100% niveladas!
    arquivos_pdfs = st.file_uploader("Faça o upload dos arquivos (Máximo de 10 PDFs):", type=["pdf"], accept_multiple_files=True)

st.markdown("---")

# --- REGRAS DE SEGURANÇA E LIMITES ---
# Variável para bloquear o botão caso o usuário quebre as regras
pode_processar = True 

# Validação: Limite de 10 PDFs
if arquivos_pdfs and len(arquivos_pdfs) > 10:
    st.error(f"⚠️ **Limite excedido!** Você anexou {len(arquivos_pdfs)} PDFs. O limite máximo do sistema é de 10 arquivos por vez.")
    st.info("💡 Dica: Remova alguns arquivos clicando no 'X' na caixa de upload acima para liberar o botão de processamento.")
    pode_processar = False

# --- BOTÃO PRINCIPAL ---
# O botão só fica clicável se 'pode_processar' for True
if st.button("🚀 Processar Análise e Encontrar Mais Barato", use_container_width=True, disabled=not pode_processar):
    if not arquivo_txt or not arquivos_pdfs:
        st.warning("⚠️ Por favor, suba a lista em TXT e pelo menos um PDF.")
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
                        st.info("⏳ Pausando obrigatoriamente por 60 segundos para resetar o limite. Aguarde...")
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
                    st.error(f"Falha crítica ao analisar o arquivo {arquivo_pdf.name}: {e}")
                finally:
                    if os.path.exists(caminho_temporario):
                        os.unlink(caminho_temporario)
                
                time.sleep(6)
            
            # --- LÓGICA DE COMPARAÇÃO FINAL ---
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
                if st.session_state.tabela_vencedores is None:
                    st.warning("Nenhum dos itens foi encontrado nos orçamentos válidos.")

# --- EXIBIÇÃO E DOWNLOADS ---
if st.session_state.tabela_vencedores is not None:
    st.success("✅ Análise Concluída! Veja os melhores preços abaixo:")
    
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
    st.subheader("📥 Exportar Relatórios")
    
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
