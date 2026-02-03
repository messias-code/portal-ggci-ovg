## 🌐 Como Liberar Acesso na Rede (WSL/Windows)

Se você estiver rodando o projeto dentro do **WSL (Linux no Windows)** e precisar que outros computadores na rede da OVG acessem, siga estes passos:

### Passo 1: Redirecionar Porta (Port Forwarding)

Como o WSL tem um IP diferente do Windows, precisamos criar uma "ponte".
Abra o **PowerShell como Administrador** e rode:

```powershell
# Substitua o IP 'connectaddress' pelo IP interno do seu WSL (descubra com 'ip a s' no terminal Linux)
netsh interface portproxy add v4tov4 listenport=8050 listenaddress=0.0.0.0 connectport=8050 connectaddress=172.23.89.131

```

### Passo 2: Liberar Firewall

Para permitir que outros computadores cheguem até o seu PC na porta 8050:

```powershell
New-NetFirewallRule -DisplayName "Portal GGCI Dash" -Direction Inbound -LocalPort 8050 -Protocol TCP -Action Allow

```

### Passo 3: Acessar

Os colegas devem acessar pelo **IP do seu Windows** (descubra com `ipconfig` no PowerShell):
`http://192.168.0.XX:8050`

---

## 🎨 Identidade Visual (OVG)

O projeto utiliza o tema **Dark** com a paleta de cores oficial da OVG:

* **Rosa:** `#FF6B8B`
* **Roxo:** `#8E44AD`
* **Amarelo:** `#FFCE54`
* **Verde:** `#A0D468`
* **Azul:** `#4FC1E9`

---

**Desenvolvido por:** Ihan Messias N. dos Santos
**Departamento:** GGCI