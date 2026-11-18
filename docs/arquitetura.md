# Arquitetura

![Diagrama da arquitetura](arquitetura.svg)

```mermaid
flowchart LR
    subgraph VM2["VM cliente1 (192.168.56.11)"]
        C1["cliente.py Cliente1"]
    end
    subgraph VM3["VM cliente2 (192.168.56.12)"]
        C2["cliente.py Cliente2"]
    end
    subgraph VM1["VM servidor (192.168.56.10)"]
        API["Flask API :5000"]
        DB[("SQLite<br/>tarefas.db")]
        API <-->|SQL| DB
    end
    C1 <-->|"HTTP + JSON"| API
    C2 <-->|"HTTP + JSON"| API
```

## Componentes

| Componente | Onde roda | Responsabilidade |
|------------|-----------|------------------|
| **Servidor** (`servidor/servidor.py`) | VM `servidor` | Abre o serviço HTTP na porta 5000, recebe os pedidos, grava e lê as tarefas no SQLite e responde em JSON. É o único lugar onde os dados ficam guardados. |
| **Banco** (`tarefas.db`) | VM `servidor` | Tabela `tarefas` com `id`, `titulo` e `estado` (`pendente` ou `concluida`). |
| **Cliente 1 e Cliente 2** (`cliente/cliente.py`) | VMs `cliente1` e `cliente2` | Menu de terminal. Não guardam dados: tudo o que mostram vem do servidor. |

## Comunicação

- Protocolo: HTTP sobre TCP, com corpo em JSON.
- `GET /tarefas` lista, `POST /tarefas` cadastra e `PUT /tarefas/<id>` altera o estado.
- Sucesso: resposta com `mensagem`. Erro: resposta com `erro` e código 400 ou 404.
- Se o servidor não responder em 5 segundos, o cliente mostra "Servidor indisponível" e continua funcionando.

## Fluxo do exemplo do enunciado

```mermaid
sequenceDiagram
    participant C1 as Cliente 1
    participant S as Servidor
    participant C2 as Cliente 2
    C1->>S: POST /tarefas {"titulo": "Estudar introdução à programação"}
    S-->>C1: 201 Tarefa 1 cadastrada
    C2->>S: GET /tarefas
    S-->>C2: 200 [{id: 1, estado: pendente}]
    C2->>S: PUT /tarefas/1 {"estado": "concluida"}
    S-->>C2: 200 Tarefa 1 marcada como concluida
    C1->>S: GET /tarefas
    S-->>C1: 200 [{id: 1, estado: concluida}]
```
