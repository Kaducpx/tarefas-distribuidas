# Relatório Técnico: Sistema Distribuído de Gerenciamento de Tarefas

**Equipe:** _(preencher)_
**Disciplina:** _(preencher)_
**Data:** _(preencher)_

## 1. Objetivo

Desenvolver uma aplicação cliente-servidor em que dois clientes independentes, em
máquinas virtuais distintas, cadastram, consultam e atualizam tarefas mantidas por
um servidor central, também em máquina virtual.

## 2. Tecnologias

| Item | Escolha | Motivo |
|------|---------|--------|
| Linguagem | Python 3 | Sugerida no enunciado; disponível nas VMs Ubuntu. |
| Servidor | Flask 3 | API HTTP simples; o servidor de desenvolvimento já atende cada requisição em uma thread. |
| Armazenamento | SQLite | Persiste em arquivo (os dados sobrevivem a reinícios) e trata escritas concorrentes. |
| Cliente | Python, biblioteca padrão (`urllib`) | Não exige instalar nada nas VMs clientes. |
| Virtualização | VirtualBox + Vagrant | Cria as três VMs e a rede privada de forma reproduzível. |

## 3. Implementação

### 3.1 Servidor (`servidor/servidor.py`)

- Inicializa o banco (cria a tabela `tarefas` se não existir) e abre o serviço HTTP em `0.0.0.0:5000`.
- Rotas: `GET /saude`, `GET /tarefas` (com filtro por estado), `GET /tarefas/<id>`,
  `POST /tarefas` e `PATCH /tarefas/<id>/estado`.
- Valida as entradas: título obrigatório, limite de tamanho, estado restrito a `pendente` ou `concluida` e corpo em JSON.
- Responde sempre com `{"sucesso", "mensagem", "dados"}` e com o código HTTP adequado (200, 201, 400, 404, 409, 500).
- Registra no log cada pedido, com o nome e o IP do cliente.
- Guarda quem criou e quem alterou cada tarefa por último (cabeçalho `X-Cliente`).

### 3.2 Clientes (`cliente/cliente.py`)

- O mesmo programa atende o Cliente 1 e o Cliente 2. O parâmetro `--nome` diferencia os dois.
- O menu permite listar todas, listar pendentes ou concluídas, cadastrar, concluir, reabrir e testar a conexão.
- Depois de cada operação, o cliente busca a lista de novo no servidor, então a tela sempre mostra o estado atual dos dados compartilhados.
- Erros de rede (servidor desligado, tempo esgotado) e erros do servidor (400, 404, 409) aparecem como mensagens, sem encerrar o programa.

### 3.3 Concorrência

- Cada requisição abre sua própria conexão com o SQLite.
- A alteração de estado usa a transação `BEGIN IMMEDIATE`, e cada tarefa tem um campo `versao`.
  O cliente envia a versão que viu, e se outro cliente alterou a tarefa nesse meio-tempo o servidor
  recusa com **409 Conflito**, em vez de sobrescrever a alteração alheia.

## 4. Testes realizados

Testes automatizados em `testes/test_sistema.py` (`python -m unittest discover -s testes -v`). **Resultado: 15 testes, todos aprovados.**

| # | Teste | Resultado esperado | Resultado |
|---|-------|--------------------|-----------|
| 1 | Verificação de saúde (`/saude`) | 200, `sucesso: true` | OK |
| 2 | Cadastro de tarefa | 201, estado `pendente`, versão 1 | OK |
| 3 | Cadastro sem título | 400 com mensagem de erro | OK |
| 4 | Cadastro com corpo que não é JSON | 400 | OK |
| 5 | Listagem e filtro por estado | filtra corretamente; estado inválido gera 400 | OK |
| 6 | Alteração de estado | estado `concluida`, versão 2, autor registrado | OK |
| 7 | Estado inválido | 400 | OK |
| 8 | Tarefa inexistente | 404 | OK |
| 9 | Conflito de versão | 409 com a versão atual | OK |
| 10 | Rota inexistente | 404 em JSON | OK |
| 11 | Cenário do enunciado com dois clientes por HTTP real | Cliente 1 vê a alteração feita pelo Cliente 2 | OK |
| 12 | Conflito entre dois clientes | o segundo cliente recebe 409 e depois consegue alterar | OK |
| 13 | 40 cadastros simultâneos (2 clientes × 20) | 40 tarefas com IDs únicos | OK |
| 14 | **Falha:** servidor indisponível | cliente recebe "Servidor indisponível" sem travar | OK |
| 15 | **Falha:** reinício do servidor | dados persistem no SQLite | OK |

**Testes manuais nas VMs:** _(preencher com os prints da demonstração: cenário do
enunciado, `systemctl stop tarefas` durante o uso e conflito de atualização)_

## 5. Problemas encontrados e soluções

| Problema | Solução |
|----------|---------|
| Dois clientes alterando a mesma tarefa ao mesmo tempo: a última escrita apagaria a anterior sem aviso. | Campo `versao` com controle de concorrência otimista e resposta 409. |
| Uma conexão SQLite não pode ser usada por várias threads. | Uma conexão por requisição (`flask.g`), fechada ao final. |
| O cliente travava ou encerrava quando o servidor caía. | Tempo limite de 5 s e tratamento de erros de rede com mensagem amigável. |
| A VM cliente não alcançava o servidor. | Servidor escutando em `0.0.0.0` (não só em `127.0.0.1`) e porta 5000 liberada no firewall. |
| Acentos apareciam como `ç` no JSON. | `app.json.ensure_ascii = False` e saída UTF-8 no cliente. |

_(acrescentar os problemas que a equipe encontrar ao montar as VMs)_

## 6. Conclusão

O sistema atende às funcionalidades pedidas para o servidor e para os clientes. Os dois
clientes operam ao mesmo tempo e sempre enxergam o mesmo conjunto de dados, mantido pelo
servidor central. O tratamento de indisponibilidade e o controle de versão mostram, na
prática, dois desafios típicos de sistemas distribuídos: falhas parciais e acesso
concorrente a dados compartilhados.
