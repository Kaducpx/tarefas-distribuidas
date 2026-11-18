# Sistema Distribuído de Gerenciamento de Tarefas

Dois clientes independentes acessam um servidor central para cadastrar, consultar
e atualizar tarefas. O servidor guarda os dados em SQLite e responde por HTTP/JSON.

```
tarefas-distribuidas/
├── servidor/
│   ├── servidor.py        # API Flask + SQLite
│   └── requirements.txt
├── cliente/
│   └── cliente.py         # cliente de terminal (Cliente 1 e Cliente 2)
├── testes/
│   └── test_sistema.py    # testes automatizados
├── docs/
│   ├── arquitetura.md     # diagrama e descrição da arquitetura
│   ├── arquitetura.svg    # diagrama em imagem
│   └── relatorio.md       # relatório técnico
└── Vagrantfile            # cria as 3 máquinas virtuais
```

## API do servidor

| Método | Rota             | Corpo                       | Descrição                 |
|--------|------------------|-----------------------------|---------------------------|
| GET    | `/tarefas`       |                             | Lista todas as tarefas    |
| POST   | `/tarefas`       | `{"titulo": "..."}`         | Cadastra uma tarefa       |
| PUT    | `/tarefas/<id>`  | `{"estado": "concluida"}`   | Altera o estado da tarefa |

Respostas de sucesso trazem `mensagem`. Respostas de erro trazem `erro` e o código
HTTP adequado (400 para dados inválidos, 404 para tarefa inexistente).

---

## Instruções de execução

### Baixar o projeto

```bash
git clone https://github.com/Kaducpx/tarefas-distribuidas.git
cd tarefas-distribuidas
```

### Opção A: máquinas virtuais (Vagrant + VirtualBox)

| VM        | IP              | Papel                          |
|-----------|-----------------|--------------------------------|
| servidor  | 192.168.56.10   | API na porta 5000 (systemd)    |
| cliente1  | 192.168.56.11   | Cliente1                       |
| cliente2  | 192.168.56.12   | Cliente2                       |

**Instalar no Ubuntu:**

```bash
sudo apt update
sudo apt install -y virtualbox
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update
sudo apt install -y vagrant
```

**Instalar no Windows:**

```bash
winget install Oracle.VirtualBox Hashicorp.Vagrant
```

No Windows, se o Hyper-V estiver ativo, o VirtualBox fica bem mais lento. Nesse caso,
ligue uma VM por vez: `vagrant up servidor`, depois `cliente1`, depois `cliente2`.

1. Na pasta do projeto, crie as três VMs:

   ```bash
   vagrant up
   ```

   O servidor já sobe como serviço (`tarefas.service`).

2. Em um terminal, abra o Cliente 1:

   ```bash
   vagrant ssh cliente1 -c "python3 /opt/tarefas/cliente.py Cliente1 http://192.168.56.10:5000"
   ```

3. Em outro terminal, abra o Cliente 2:

   ```bash
   vagrant ssh cliente2 -c "python3 /opt/tarefas/cliente.py Cliente2 http://192.168.56.10:5000"
   ```

   Dentro das VMs clientes também existe o atalho `tarefas`, que já abre o cliente com o nome e o endereço certos.

4. Para acompanhar os pedidos chegando ao servidor:

   ```bash
   vagrant ssh servidor -c "journalctl -u tarefas -f"
   ```

5. Para desligar tudo:

   ```bash
   vagrant halt
   ```

### Opção B: VMs criadas manualmente

Crie três VMs Ubuntu na mesma rede e copie o projeto para elas.

No **servidor**:

```bash
sudo apt install -y python3-venv
python3 -m venv venv
venv/bin/pip install -r servidor/requirements.txt
venv/bin/python servidor/servidor.py
```

Se o firewall estiver ativo, libere a porta: `sudo ufw allow 5000/tcp`.

Em cada **cliente** (só precisa do Python 3):

```bash
python3 cliente/cliente.py Cliente1 http://IP_DO_SERVIDOR:5000
```

### Opção C: tudo na mesma máquina (para testar rápido)

```bash
sudo apt install -y python3-venv
python3 -m venv .venv
.venv/bin/pip install -r servidor/requirements.txt
.venv/bin/python servidor/servidor.py
```

Depois, em dois outros terminais:

```bash
python3 cliente/cliente.py Cliente1
```

```bash
python3 cliente/cliente.py Cliente2
```

No Windows, troque `python3` por `python` e `.venv/bin/` por `.venv\Scripts\`.

### Testes automatizados

```bash
.venv/bin/python -m unittest discover -s testes -v
```

---

## Roteiro de demonstração

1. **Cliente 1**: opção 2, cadastrar "Estudar introdução à programação".
2. **Cliente 2**: opção 1, a tarefa do Cliente 1 aparece na lista.
3. **Cliente 2**: opção 3, número 1, a tarefa fica concluída.
4. **Cliente 1**: opção 1, a tarefa aparece como `[x]`.

**Teste de falha: servidor fora do ar**

1. Desligue o servidor:

   ```bash
   vagrant ssh servidor -c "sudo systemctl stop tarefas"
   ```

2. Em qualquer cliente, escolha a opção 1. Aparece `ERRO: Servidor indisponível...` e o cliente continua aberto.
3. Religue o servidor:

   ```bash
   vagrant ssh servidor -c "sudo systemctl start tarefas"
   ```

4. No cliente, liste de novo. As tarefas continuam lá, porque estão gravadas no SQLite.
