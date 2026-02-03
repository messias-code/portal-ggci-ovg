"""
=============================================================================
MÓDULO DE UTILITÁRIOS
=============================================================================
Funções auxiliares para validações e tratamentos genéricos.
"""
import re

def validar_requisitos_senha(senha: str) -> list:
    """
    Verifica se uma senha atende aos requisitos de segurança da OVG.
    
    Regras:
    1. Mínimo 8 caracteres.
    2. Pelo menos 1 letra maiúscula [A-Z].
    3. Pelo menos 2 números [0-9].
    4. Pelo menos 1 caractere especial (símbolo).

    Args:
        senha (str): A senha em texto plano.

    Returns:
        list: Uma lista de strings com os erros encontrados. 
              Se a lista estiver vazia, a senha é válida.
    """
    erros = []
    
    if not senha: 
        return ["A senha não pode estar vazia."]
    
    # 1. Tamanho
    if len(senha) < 8: 
        erros.append("A senha deve ter no mínimo 8 caracteres.")
    
    # 2. Maiúscula
    if not re.search(r"[A-Z]", senha): 
        erros.append("Pelo menos 1 letra maiúscula.")
    
    # 3. Números (contagem)
    if len(re.findall(r"\d", senha)) < 2: 
        erros.append("Pelo menos 2 números.")
    
    # 4. Símbolos (não alfanuméricos)
    if not re.search(r"[\W_]", senha): 
        erros.append("Pelo menos 1 caractere especial (ex: @, #, $).")
    
    return erros