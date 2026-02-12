"""
=============================================================================
ARQUIVO: utils.py (MÓDULO DE UTILITÁRIOS)
DESCRIÇÃO:
    Este arquivo contém funções auxiliares puras (que não dependem de banco
    de dados ou framework visual).
=============================================================================
"""
import re

def validar_requisitos_senha(senha_plana: str) -> list:
    r"""
    Valida a complexidade de uma senha baseada nas políticas de segurança.
    """
    lista_erros = []
    
    # Validação 0: Existência
    if not senha_plana: 
        return ["A senha é obrigatória."]
    
    # Validação 1: Tamanho Mínimo
    if len(senha_plana) < 8: 
        lista_erros.append("Mínimo de 8 caracteres.")
    
    # Validação 2: Letra Maiúscula
    if not re.search(r"[A-Z]", senha_plana): 
        lista_erros.append("Mínimo de 1 letra maiúscula.")
    
    # Validação 3: Quantidade de Números
    numeros_encontrados = re.findall(r"\d", senha_plana)
    if len(numeros_encontrados) < 2: 
        lista_erros.append("Mínimo de 2 números.")
    
    # Validação 4: Caracteres Especiais
    if not re.search(r"[\W_]", senha_plana): 
        lista_erros.append("Mínimo de 1 caractere especial (@, #, $, etc).")
    
    return lista_erros