import os
import sqlite3

from flask import Flask, jsonify, request

PASTA = os.path.dirname(os.path.abspath(__file__))
BANCO = os.environ.get("TAREFAS_DB", os.path.join(PASTA, "tarefas.db"))
ESTADOS = ("pendente", "concluida")

app = Flask(__name__)
app.json.ensure_ascii = False


def conectar():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def consultar(sql, parametros=()):
    conexao = conectar()
    linhas = [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]
    conexao.close()
    return linhas


def alterar(sql, parametros=()):
    conexao = conectar()
    cursor = conexao.execute(sql, parametros)
    conexao.commit()
    conexao.close()
    return cursor


def criar_tabela():
    alterar(
        "CREATE TABLE IF NOT EXISTS tarefas ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "titulo TEXT NOT NULL, "
        "estado TEXT NOT NULL DEFAULT 'pendente')"
    )


@app.get("/tarefas")
def listar_tarefas():
    tarefas = consultar("SELECT * FROM tarefas ORDER BY id")
    return jsonify({"mensagem": f"{len(tarefas)} tarefa(s) encontrada(s).", "tarefas": tarefas})


@app.post("/tarefas")
def cadastrar_tarefa():
    dados = request.get_json(silent=True) or {}
    titulo = str(dados.get("titulo", "")).strip()
    if not titulo:
        return jsonify({"erro": "O título da tarefa é obrigatório."}), 400

    cursor = alterar("INSERT INTO tarefas (titulo) VALUES (?)", (titulo,))
    return jsonify({"mensagem": f"Tarefa {cursor.lastrowid} cadastrada com sucesso."}), 201


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


if __name__ == "__main__":
    criar_tabela()
    app.run(host="0.0.0.0", port=5000, threaded=True)
