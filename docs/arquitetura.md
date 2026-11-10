# Arquitetura

![Diagrama da arquitetura](arquitetura.svg)

```mermaid
flowchart LR
    subgraph VM2["VM cliente1 (192.168.56.11)"]
        C1["cliente.py<br/>--nome Cliente1"]
    end
    subgraph VM3["VM cliente2 (192.168.56.12)"]
        C2["cliente.py<br/>--nome Cliente2"]
    end
    subgraph VM1["VM servidor (192.168.56.10)"]
        API["Flask API :5000<br/>(uma thread por requisição)"]
        DB[("SQLite<br/>tarefas.db")]
        API <-->|SQL| DB
    end
    C1 <-->|"HTTP + JSON<br/>X-Cliente: Cliente1"| API
    C2 <-->|"HTTP + JSON<br/>X-Cliente: Cliente2"| API
```

## Componentes

| Componente | Onde roda | Responsabilidade |
|------------|-----------|------------------|
| **Servidor** (`servidor/servidor.py`) | VM `servidor` | Abre o serviço HTTP na porta 5000, valida os pedidos, grava e lê as tarefas no SQLite e responde com JSON padronizado. É o único dono dos dados. |
| **Banco** (`tarefas.db`) | VM `servidor` | Tabela `tarefas` com id, título, descrição, estado, quem criou, quem alterou por último, horários e `versao`. |
| **Cliente 1 e Cliente 2** (`cliente/cliente.py`) | VMs `cliente1` e `cliente2` | Interface de terminal. Não guardam dados próprios: toda tela mostrada vem de uma resposta do servidor. |

## Comunicação

- Protocolo: HTTP/1.1 sobre TCP, com corpo em JSON (UTF-8).
- Cada cliente se identifica no cabeçalho `X-Cliente`, que o servidor grava em `criado_por` e `atualizado_por`.
- Formato de resposta: `{"sucesso": true|false, "mensagem": "...", "dados": ...}`.
- Códigos usados: `200` (ok), `201` (criado), `400` (dados inválidos), `404` (não encontrado), `409` (conflito de versão) e `500` (erro interno).

## Fluxo do exemplo do enunciado

```mermaid
sequenceDiagram
    participant C1 as Cliente 1
    participant S as Servidor
    participant C2 as Cliente 2
    C1->>S: POST /tarefas {"titulo": "Estudar introdução à programação"}
    S-->>C1: 201 {id: 1, estado: pendente, versao: 1}
    C2->>S: GET /tarefas
    S-->>C2: 200 [{id: 1, estado: pendente, versao: 1}]
    C2->>S: PATCH /tarefas/1/estado {"estado": "concluida", "versao": 1}
    S-->>C2: 200 {id: 1, estado: concluida, versao: 2}
    C1->>S: GET /tarefas
    S-->>C1: 200 [{id: 1, estado: concluida, atualizado_por: Cliente2}]
```

## Consistência e concorrência

- O servidor é multithread. Cada requisição usa sua própria conexão SQLite, e o SQLite serializa as escritas.
- A alteração de estado roda numa transação `BEGIN IMMEDIATE`, que lê a versão e atualiza a tarefa sem interferência de outro cliente.
- **Controle de concorrência otimista:** o cliente envia a `versao` que viu na última listagem. Se outro cliente alterou a tarefa nesse meio-tempo, o servidor responde `409` em vez de sobrescrever às cegas.
