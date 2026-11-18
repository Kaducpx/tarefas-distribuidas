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

---

## Como testar

Antes de começar, deixe o **Cliente 1** e o **Cliente 2** abertos, cada um no seu terminal,
um do lado do outro. Tire um print depois de cada teste para colocar no relatório.

### Teste 1: os dois clientes veem as mesmas tarefas

1. No **Cliente 1**, digite `2` e cadastre a tarefa `Estudar introdução à programação`.
2. No **Cliente 2**, digite `1`. A tarefa cadastrada pelo Cliente 1 aparece na lista.
3. No **Cliente 2**, digite `3` e depois `1`. A tarefa fica marcada com `[x]`.
4. No **Cliente 1**, digite `1`. A tarefa aparece com `[x]`, ou seja, o Cliente 1 viu o que o Cliente 2 fez.

### Teste 2: reabrir uma tarefa

1. No **Cliente 1**, digite `4` e depois `1`.
2. No **Cliente 2**, digite `1`. A tarefa voltou a aparecer com `[ ]`.

### Teste 3: erros de digitação

Em qualquer cliente:

| O que fazer | O que deve aparecer |
|---|---|
| Digitar `2` e apertar Enter sem escrever o título | `ERRO: O título da tarefa é obrigatório.` |
| Digitar `3` e depois `99` | `ERRO: Tarefa 99 não encontrada.` |
| Digitar `3` e depois uma letra | `ERRO: informe um número válido.` |
| Digitar `7` no menu | `ERRO: opção inválida.` |

### Teste 4: o servidor cai (teste de falha)

1. Abra um terceiro terminal e desligue o servidor:

   ```bash
   vagrant ssh servidor -c "sudo systemctl stop tarefas"
   ```

2. Em qualquer cliente, digite `1`. Deve aparecer `ERRO: Servidor indisponível...`, e o cliente continua aberto.
3. Ligue o servidor de novo:

   ```bash
   vagrant ssh servidor -c "sudo systemctl start tarefas"
   ```

4. No cliente, digite `1`. As tarefas continuam lá, nada foi perdido.

### Teste 5: um cliente sai e o outro continua

1. No **Cliente 1**, digite `0` para sair.
2. No **Cliente 2**, cadastre uma tarefa nova e liste. Tudo funciona normalmente.
3. Abra o Cliente 1 de novo e liste. A tarefa nova feita pelo Cliente 2 aparece.
