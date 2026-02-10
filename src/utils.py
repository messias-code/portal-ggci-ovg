"""
=============================================================================
ARQUIVO: utils.py (MÓDULO DE UTILITÁRIOS)
DESCRIÇÃO:
    Este arquivo contém funções auxiliares puras (que não dependem de banco
    de dados ou framework visual).
    
    CONCEITO CHAVE (HELPER FUNCTIONS):
    Funções utilitárias devem ser "stateless" (sem estado). Elas recebem um 
    dado (input), processam e devolvem um resultado (output), sem alterar 
    variáveis globais. Isso facilita testes e reutilização.
=============================================================================
"""
import re  # Biblioteca padrão do Python para Expressões Regulares (Regex)

def validar_requisitos_senha(senha_plana: str) -> list:
    """
    Valida a complexidade de uma senha baseada nas políticas de segurança da organização.

    CONCEITO DE REGEX (Expressões Regulares):
    Usamos padrões de texto para verificar se a senha contém certos tipos de caracteres.
    - [A-Z]: Procura qualquer letra maiúscula.
    - \d: Procura qualquer dígito (0-9).
    - \W: Procura qualquer coisa que NÃO seja letra ou número (símbolos).

    Args:
        senha_plana (str): A senha em texto puro que o usuário digitou.

    Returns:
        list: Uma lista contendo as mensagens de erro. 
              Se a lista retornar vazia ([]), significa que a senha é válida.
    """
    # Lista acumuladora: Vamos adicionar erros aqui conforme os encontramos.
    # Isso permite informar ao usuário TUDO o que ele precisa corrigir de uma vez.
    lista_erros = []
    
    # Validação 0: Existência
    if not senha_plana: 
        return ["A senha não pode estar vazia."]
    
    # Validação 1: Tamanho Mínimo
    # len() é a função mais rápida para checar comprimento.
    if len(senha_plana) < 8: 
        lista_erros.append("A senha deve ter no mínimo 8 caracteres.")
    
    # Validação 2: Letra Maiúscula
    # re.search retorna True se encontrar o padrão em QUALQUER lugar da string.
    # Padrão r"[A-Z]": Busca uma letra entre A e Z.
    if not re.search(r"[A-Z]", senha_plana): 
        lista_erros.append("Pelo menos 1 letra maiúscula.")
    
    # Validação 3: Quantidade de Números
    # Aqui usamos re.findall porque precisamos CONTAR as ocorrências.
    # Padrão r"\d": Representa 'digit' (0, 1, 2... 9).
    numeros_encontrados = re.findall(r"\d", senha_plana)
    if len(numeros_encontrados) < 2: 
        lista_erros.append("Pelo menos 2 números.")
    
    # Validação 4: Caracteres Especiais (Símbolos)
    # Padrão r"[\W_]":
    # \W -> Significa "Non-Word Character" (qualquer coisa que não seja letra ou número).
    # _  -> O underline as vezes é considerado letra em programação, então forçamos a busca dele aqui.
    if not re.search(r"[\W_]", senha_plana): 
        lista_erros.append("Pelo menos 1 caractere especial (ex: @, #, $).")
    
    return lista_erros