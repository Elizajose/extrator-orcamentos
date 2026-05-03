import streamlit as st
import os
import re
from google import genai
from google.genai.types import exceptions


API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

def analisar_precos_direto_no_pdf(caminho_pdf, lista_produtos_txt):
    prompt = f"""
    Sua tarefa é cruzar a lista de busca com os itens do PDF anexo.
    Lista de busca: {lista_produtos_txt}
    
    Regras de Extração CRÍTICAS:
    1. PRODUTOS: Encontre a correspondência no PDF para os itens buscados.
    2. FORNECEDOR: Identifique a Razão Social ("nome_empresa") e o "cnpj" do emissor. Se não achar, use "Não informado".
    3. PREÇO REAL (ATENÇÃO MÁXIMA): O "preco_unitario" deve refletir o CUSTO REAL FINAL do produto. 
       - Se o documento destacar impostos adicionais por item (como IPI ou ST - Substituição Tributária), SOME esses valores ao preço unitário.
       - Se o documento apresentar descontos aplicados ao item, SUBTRAIA do valor unitário.
       - Retorne apenas o número float com ponto (ex: 2399.90).
    
    Retorne ESTRITAMENTE UMA LISTA JSON de objetos com as chaves exatas: "produto_buscado", "descricao_loja", "preco_unitario", "nome_empresa", "cnpj".
    """
    
    try:
        arquivo_gemini = client.files.upload(file=caminho_pdf)
        resposta = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[arquivo_gemini, prompt]
        )
        
        texto = resposta.text
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if match:
            return match.group(0)
        else:
            return f"Erro na IA: Nenhum formato JSON válido foi encontrado."
            
    except Exception as e:
        return f"Erro na comunicação com a API: {str(e)}"
