# Servidor 
#
# Este programa roda na máquina virtual "servidor" e é o único lugar onde as
# tarefas ficam guardadas. Os dois clientes não guardam nada: eles mandam
# pedidos pela rede (HTTP) e o servidor responde com os dados em JSON.
#
# O que o servidor faz:
#   GET  /tarefas        -> devolve a litagem de todas as tarefas
#   POST /tarefas        -> faz o cadastro de uma tarefa nova
#   PUT  /tarefas/<id>   -> muda o estado de uma tarefa que pode ser pendente ou concluida
#
# As tarefas ficam salvas num banco SQLite, então elas não se perdem
# quando o servidor é desligado e ligado de novo.

import os
import sqlite3

from flask import Flask, jsonify, request

# Caminho do arquivo do banco de dados. Se a variável de ambiente TAREFAS_DB
# existir, usa o caminho dela, se não, cria o "tarefas.db" na mesma pasta desse arquivo também que consiga rodar o servidor em qualquer pasta, sem precisar criar o banco manualmente.
PASTA = os.path.dirname(os.path.abspath(__file__))
BANCO = os.environ.get("TAREFAS_DB", os.path.join(PASTA, "tarefas.db"))

# unicos estados que uma tarefa pode ter
ESTADOS = ("pendente", "concluida")

# cria a aplicação Flask. A segunda linha faz com que  os acentos apareçam
# normalmente no JSON, pra que não vire codigos como o ç
app = Flask(__name__)
app.json.ensure_ascii = False


#funções de acesso ao banco
# Abre uma conexão com o banco, o row_factory faz cada linha poder ser
# lida pelo nome da coluna (linha["titulo"]) e convertida em dicionario.
def conectar():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


# Executa um SELECT e devolve o resultado como uma lista de dicionarios,
# que é o jeito facil de transformar em JSON.
def consultar(sql, parametros=()):
    conexao = conectar()
    linhas = [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]
    conexao.close()
    return linhas


# roda um comando que altera o banco, CREATE, INSERT ou UPDATE,
# salva a alteração com commit e devolve o cursor, que informa
# o id criado "lastrowid" e quantas linhas foram alteradas "rowcount".
def alterar(sql, parametros=()):
    conexao = conectar()
    cursor = conexao.execute(sql, parametros)
    conexao.commit()
    conexao.close()
    return cursor


# cria a tabela de tarefas na primeira vez que o servidor roda
# cada tarefa tem um número que é auto incrementado, um título e um estado,
# que sempre começa como "pendente"
def criar_tabela():
    alterar(
        "CREATE TABLE IF NOT EXISTS tarefas ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "titulo TEXT NOT NULL, "
        "estado TEXT NOT NULL DEFAULT 'pendente')"
    )



# Rotas, cada função abaixo responde a um tipo de pedido dos clientes

# Listar tarefas fas todas as busca no banco, em ordem de número, e devolve
# junto com uma mensagem dizendo quantas encontrou
@app.get("/tarefas")
def listar_tarefas():
    tarefas = consultar("SELECT * FROM tarefas ORDER BY id")
    return jsonify({"mensagem": f"{len(tarefas)} tarefa(s) encontrada(s).", "tarefas": tarefas})


# cadastrar tarefas, faz a leitura do título enviado pelo cliente, se tive vazio,
# responde com erro 400 de pedido invalido, see tive certo, grava no
# banco e responde 201 criado,  com o número da tarefa nova.
@app.post("/tarefas")
def cadastrar_tarefa():
    dados = request.get_json(silent=True) or {}
    titulo = str(dados.get("titulo", "")).strip()
    if not titulo:
        return jsonify({"erro": "O título da tarefa é obrigatório."}), 400

    cursor = alterar("INSERT INTO tarefas (titulo) VALUES (?)", (titulo,))
    return jsonify({"mensagem": f"Tarefa {cursor.lastrowid} cadastrada com sucesso."}), 201


# alterar estado, faz a leitura do novo estado enviado pelo cliente e confere se é
# pendente ou concluida, se não da erro 400. Depois atualiza a tarefa.
# Se nenhuma linha for alterada, é porque não tem a tarefa.
@app.put("/tarefas/<int:id_tarefa>")
def alterar_estado(id_tarefa):
    dados = request.get_json(silent=True) or {}
    estado = dados.get("estado")
    if estado not in ESTADOS:
        return jsonify({"erro": "Estado inválido. Use 'pendente' ou 'concluida'."}), 400

    cursor = alterar("UPDATE tarefas SET estado = ? WHERE id = ?", (estado, id_tarefa))
    if cursor.rowcount == 0:
        return jsonify({"erro": f"Tarefa {id_tarefa} não encontrada."}), 404
    return jsonify({"mensagem": f"Tarefa {id_tarefa} marcada como {estado}."})


#Inicio do programa

# Garante que a tabela existe e ai liga o servidor.
# o host=0.0.0.0 faz o servidor com que o servidor aceite conexões vindas de outras máquinas
# as VMsdos clientes, e não só da própria máquina.
# threaded= True faz com que consiga atender os dois clientes ao mesmo tempo
if __name__ == "__main__":
    criar_tabela()
    app.run(host="0.0.0.0", port=5000, threaded=True)
