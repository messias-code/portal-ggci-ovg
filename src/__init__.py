"""
=============================================================================
ARQUIVO: __init__.py
CONTEXTO: Definição de Pacote Python
=============================================================================

EXPLICAÇÃO TÉCNICA PARA O TIME:

1. PROPÓSITO:
   A presença deste arquivo (mesmo que vazio) instrui o interpretador Python
   a tratar este diretório como um PACOTE (Python Package) importável.

2. POR QUE ELE EXISTE?
   Sem este arquivo, o Python pode não reconhecer a pasta 'src' como um módulo.
   É graças a ele que conseguimos fazer no arquivo principal (app.py):
   
   >>> from src.database import ...
   >>> from src.layouts import ...

3. POSSO DELETAR?
   NÃO. Jamais apague este arquivo, mesmo que ele pareça inútil.
   Embora o Python 3.3+ suporte "Namespace Packages" (pastas sem __init__),
   manter este arquivo é uma boa prática de Engenharia de Software para:
   - Garantir compatibilidade total.
   - Evitar ambiguidades de importação.
   - Sinalizar explicitamente que esta pasta contém código-fonte do projeto.

4. USO AVANÇADO (CURIOSIDADE):
   Se quiséssemos, poderíamos usar este arquivo para expor variáveis globais
   do pacote ou simplificar imports, por exemplo:
   __version__ = "1.0.0"

STATUS:
Mantido vazio intencionalmente (padrão de projeto).
"""