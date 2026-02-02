import re

def validar_senha(senha):
    erros = []
    if not senha: 
        return ["Senha vazia"]
    
    if len(senha) < 8: 
        erros.append("A senha deve ter no mínimo 8 caracteres.")
    if not re.search(r"[A-Z]", senha): 
        erros.append("Pelo menos 1 letra maiúscula.")
    if len(re.findall(r"\d", senha)) < 2: 
        erros.append("Pelo menos 2 números.")
    if not re.search(r"[\W_]", senha): 
        erros.append("Pelo menos 1 caractere especial.")
    
    return erros