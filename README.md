# Sistema Distribuído de Gerenciamento de Tarefas

Dois clientes independentes acessam um servidor central para cadastrar, consultar
e atualizar tarefas. O servidor guarda os dados em SQLite e responde por HTTP/JSON.

```
TarefasDistribuidas/
├── servidor/
│   ├── servidor.py        # API Flask + SQLite
│   └── requirements.txt
├── cliente/
│   └── cliente.py         # cliente de terminal (usado pelo Cliente 1 e pelo Cliente 2)
├── testes/
│   └── test_sistema.py    # 15 testes automatizados (API, dois clientes, falhas)
├── docs/
│   ├── arquitetura.md     # diagrama e descrição da arquitetura
│   ├── arquitetura.svg    # diagrama em imagem
│   └── relatorio.md       # relatório técnico
└── Vagrantfile            # cria as 3 máquinas virtuais
```

## API do servidor

| Método | Rota                     | Descrição                                        |
|--------|--------------------------|--------------------------------------------------|
| GET    | `/saude`                 | Verifica se o servidor está no ar                |
| GET    | `/tarefas[?estado=...]`  | Lista tarefas (filtro opcional `pendente`/`concluida`) |
| GET    | `/tarefas/<id>`          | Consulta uma tarefa                              |
| POST   | `/tarefas`               | Cadastra `{"titulo": "...", "descricao": "..."}` |
| PATCH  | `/tarefas/<id>/estado`   | Altera `{"estado": "concluida", "versao": 1}`    |

Toda resposta segue o formato `{"sucesso": bool, "mensagem": str, "dados": ...}`.
O cliente se identifica pelo cabeçalho `X-Cliente`.

---

## Instruções de execução

### Baixar o projeto

```bash
git clone https://github.com/Kaducpx/tarefas-distribuidas.git
cd tarefas-distribuidas
```

### Opção A: máquinas virtuais (Vagrant + VirtualBox)

Pré-requisitos: [VirtualBox](https://www.virtualbox.org/) e [Vagrant](https://www.vagrantup.com/) instalados.

**Ubuntu:**

```bash
sudo apt update
sudo apt install -y virtualbox
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update
sudo apt install -y vagrant
```

**Windows:**

```bash
winget install Oracle.VirtualBox Hashicorp.Vagrant
```

No Windows, se o Hyper-V ou a Integridade de Memória estiverem ativos, o VirtualBox fica bem mais lento e o boot das VMs pode estourar o tempo. Nesse caso, ligue uma VM por vez (`vagrant up servidor`, depois `cliente1`, depois `cliente2`).

| VM        | IP              | Papel                          |
|-----------|-----------------|--------------------------------|
| servidor  | 192.168.56.10   | API na porta 5000 (systemd)    |
| cliente1  | 192.168.56.11   | Cliente1                       |
| cliente2  | 192.168.56.12   | Cliente2                       |

1. Na pasta do projeto, crie e configure as três VMs:

   ```bash
   vagrant up
   ```

   O servidor já sobe como serviço (`tarefas.service`) ao final da criação.

2. Em um terminal, abra o Cliente 1:

   ```bash
   vagrant ssh cliente1 -c "python3 /opt/tarefas/cliente.py --nome Cliente1 --servidor http://192.168.56.10:5000"
   ```

3. Em outro terminal, abra o Cliente 2:

   ```bash
   vagrant ssh cliente2 -c "python3 /opt/tarefas/cliente.py --nome Cliente2 --servidor http://192.168.56.10:5000"
   ```

   Dentro das VMs clientes também existe o atalho `tarefas`, já configurado com o nome e o endereço do servidor.

4. Para acompanhar os pedidos chegando no servidor:

   ```bash
   vagrant ssh servidor -c "journalctl -u tarefas -f"
   ```

5. Para desligar tudo:

   ```bash
   vagrant halt
   ```

### Opção B: VMs criadas manualmente

Crie três VMs (por exemplo, Ubuntu 22.04) na mesma rede (host-only ou rede interna) e copie as pastas.

No **servidor**:

```bash
sudo apt install -y python3-venv
python3 -m venv venv
venv/bin/pip install -r servidor/requirements.txt
venv/bin/python servidor/servidor.py --porta 5000
```

Libere a porta 5000 no firewall, se ele estiver ativo (`sudo ufw allow 5000/tcp`).

Em cada **cliente** (só precisa do Python 3, sem bibliotecas extras):

```bash
python3 cliente/cliente.py --nome Cliente1 --servidor http://IP_DO_SERVIDOR:5000
```

### Opção C: tudo na mesma máquina (para testar rápido)

No Ubuntu:

```bash
sudo apt install -y python3-venv
python3 -m venv .venv
.venv/bin/pip install -r servidor/requirements.txt
.venv/bin/python servidor/servidor.py
```

No Windows, troque `python3` por `python` e `.venv/bin/` por `.venv\Scripts\`.

Depois, em dois outros terminais:

```bash
python3 cliente/cliente.py --nome Cliente1
```

```bash
python3 cliente/cliente.py --nome Cliente2
```

### Modo comando do cliente

Além do menu, o cliente aceita comandos diretos, úteis em roteiros de demonstração:

```bash
python cliente/cliente.py --nome Cliente1 cadastrar "Estudar introdução à programação"
python cliente/cliente.py --nome Cliente2 listar
python cliente/cliente.py --nome Cliente2 concluir 1
python cliente/cliente.py --nome Cliente1 listar --estado concluida
```

### Testes automatizados

```bash
python -m unittest discover -s testes -v
```

---

## Roteiro de demonstração

1. **Cliente 1** → opção 4 → cadastra "Estudar introdução à programação".
2. **Cliente 2** → opção 1 → a tarefa do Cliente 1 aparece na lista.
3. **Cliente 2** → opção 5 → conclui a tarefa 1.
4. **Cliente 1** → opção 1 → a tarefa aparece como `[x] concluida`, alterada por Cliente2.

**Teste de falha 1: servidor fora do ar**
1. No servidor: `sudo systemctl stop tarefas` (ou `Ctrl+C` no terminal do servidor).
2. Em qualquer cliente, tente listar → aparece `ERRO: Servidor indisponível...` e o cliente continua aberto.
3. No servidor: `sudo systemctl start tarefas`.
4. No cliente, liste de novo → os dados continuam lá, porque estão gravados em SQLite.

**Teste de falha 2: conflito de atualização**
1. Os dois clientes listam as tarefas.
2. O Cliente 2 conclui a tarefa 1.
3. Sem listar de novo, o Cliente 1 tenta marcar a tarefa 1 como pendente → o servidor
   recusa com `Conflito: a tarefa 1 foi alterada por 'Cliente2'`.
4. O cliente exibe a lista atualizada, e uma nova tentativa funciona.
