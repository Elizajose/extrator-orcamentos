import streamlit as st
import os
import re
from google import genai


API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

def analisar_precos_direto_no_pdf(caminho_pdf, lista_produtos_txt):
    prompt = f"""
    Sua tarefa é cruzar a lista de busca com os itens do PDF anexo.
    Lista de busca: {lista_produtos_txt}
    
    Regras de Extração CRÍTICAS:
    1. PRODUTOS (CORRESPONDÊNCIA DE SIGNIFICADO): Avalie a ESSÊNCIA do produto. Você DEVE aceitar abreviações fiscais comuns (ex: "Cad" para Caderno, "Refrig" para Refrigerante). O que você NÃO PODE aceitar são peças, acessórios ou itens de manutenção (ex: "Pé para Sofá" se a busca for "Sofá"). O produto vendido no PDF deve ser o equipamento principal solicitado.
    2. ANTI-FALSO POSITIVO: Se a descrição do PDF listar compatibilidade com vários itens (ex: "Pe Palito Rack Madeira Mesa Sofas"), isso é a prova de que é um ACESSÓRIO, não o móvel em si. Rejeite e ignore o item.
    3. FORNECEDOR: Identifique a Razão Social ("nome_empresa") e o "cnpj" do emissor. Se não achar, use "Não informado".
    4. PREÇO REAL (ATENÇÃO MÁXIMA): O "preco_unitario" deve refletir o CUSTO REAL FINAL do produto. 
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
        erro_str = str(e)
        if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
            return f"RATE_LIMIT_ERROR: {erro_str}"
        else:
            return f"Erro genérico na comunicação com a API: {erro_str}"
