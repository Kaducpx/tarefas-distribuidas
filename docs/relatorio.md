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
| Linguagem | Python 3 | Sugerida no enunciado e já disponível no Ubuntu. |
| Servidor | Flask | Cria uma API HTTP com poucas linhas e atende vários clientes ao mesmo tempo. |
| Armazenamento | SQLite | Grava os dados em arquivo, então eles sobrevivem a reinícios do servidor. |
| Cliente | Python, biblioteca padrão (`urllib`) | Não exige instalar nada nas VMs clientes. |
| Virtualização | VirtualBox + Vagrant | Cria as três VMs e a rede entre elas com um único comando. |

## 3. Implementação

### 3.1 Servidor (`servidor/servidor.py`)

- Cria a tabela `tarefas` (`id`, `titulo`, `estado`) se ela ainda não existir e abre o serviço em `0.0.0.0:5000`.
- `GET /tarefas` lista as tarefas, `POST /tarefas` cadastra e `PUT /tarefas/<id>` altera o estado.
- Recusa título vazio e estado diferente de `pendente`/`concluida` (erro 400). Responde 404 para tarefa inexistente.
- Todos os clientes acessam o mesmo banco, por isso enxergam os mesmos dados.

### 3.2 Clientes (`cliente/cliente.py`)

- O mesmo programa é usado pelo Cliente 1 e pelo Cliente 2. O nome e o endereço do servidor são passados na linha de comando.
- O menu permite listar, cadastrar, marcar como concluída e marcar como pendente.
- Depois de cada alteração, o cliente busca a lista de novo no servidor e mostra o estado atual.
- Se o servidor estiver fora do ar, mostra "Servidor indisponível" e continua aberto.

## 4. Testes realizados

Os testes foram feitos à mão, nas três máquinas virtuais, seguindo o passo a passo do `README.md`.

| # | Teste | Resultado esperado | Resultado obtido |
|---|-------|--------------------|------------------|
| 1 | Cliente 1 cadastra, Cliente 2 lista e conclui, Cliente 1 lista de novo | os dois clientes veem a mesma tarefa e a mudança feita pelo outro | _(preencher)_ |
| 2 | Reabrir uma tarefa concluída | a tarefa volta para pendente nos dois clientes | _(preencher)_ |
| 3 | Título vazio, tarefa inexistente, número inválido e opção inválida | mensagem de erro, sem fechar o programa | _(preencher)_ |
| 4 | **Falha:** desligar o servidor e depois religar | cliente mostra "Servidor indisponível"; ao religar, as tarefas continuam lá | _(preencher)_ |
| 5 | Um cliente sai e o outro continua usando | o outro cliente funciona normalmente | _(preencher)_ |

_(colocar os prints de cada teste)_

## 5. Problemas encontrados e soluções

| Problema | Solução |
|----------|---------|
| As VMs clientes não alcançavam o servidor. | Servidor escutando em `0.0.0.0` (e não só em `127.0.0.1`) e porta 5000 liberada. |
| O cliente travava quando o servidor caía. | Tempo limite de 5 segundos e mensagem de erro no lugar da falha. |
| Acentos apareciam como `ç` no JSON. | `app.json.ensure_ascii = False` no servidor. |
| No Windows com Hyper-V ativo, as VMs demoravam a ligar. | Ligar uma VM por vez e aumentar o tempo de espera no `Vagrantfile`. |

_(acrescentar os problemas que a equipe encontrar)_

## 6. Conclusão

O sistema atende às funcionalidades pedidas para o servidor e para os clientes. Os dois
clientes funcionam ao mesmo tempo e sempre enxergam os mesmos dados, mantidos pelo
servidor central. O teste com o servidor desligado mostra como o cliente lida com a
falha de um componente do sistema distribuído sem perder os dados.
