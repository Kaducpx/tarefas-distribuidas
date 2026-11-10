import argparse
import logging
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request

ESTADOS_VALIDOS = ("pendente", "concluida")
TAMANHO_MAXIMO_TITULO = 200
TAMANHO_MAXIMO_DESCRICAO = 2000

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tarefas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo         TEXT    NOT NULL,
    descricao      TEXT    NOT NULL DEFAULT '',
    estado         TEXT    NOT NULL DEFAULT 'pendente'
                           CHECK (estado IN ('pendente', 'concluida')),
    criado_por     TEXT    NOT NULL,
    criado_em      TEXT    NOT NULL,
    atualizado_por TEXT    NOT NULL,
    atualizado_em  TEXT    NOT NULL,
    versao         INTEGER NOT NULL DEFAULT 1
);
"""


def agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resposta(sucesso, mensagem, dados=None, status=200):
    corpo = {"sucesso": sucesso, "mensagem": mensagem}
    if dados is not None:
        corpo["dados"] = dados
    return jsonify(corpo), status


def linha_para_dict(linha):
    return dict(linha) if linha is not None else None


def criar_app(caminho_banco):
    app = Flask(__name__)
    app.config["CAMINHO_BANCO"] = caminho_banco
    app.json.ensure_ascii = False
    log = logging.getLogger("servidor")

    def conexao():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["CAMINHO_BANCO"], timeout=10)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def fechar_conexao(_erro):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = conexao()
        db.executescript(ESQUEMA)
        db.commit()

    def nome_cliente():
        return request.headers.get("X-Cliente", "desconhecido").strip()[:50] or "desconhecido"

    @app.before_request
    def registrar_requisicao():
        log.info("%s %s  <- %s (%s)", request.method, request.path,
                 nome_cliente(), request.remote_addr)

    @app.get("/saude")
    def saude():
        return resposta(True, "Servidor em funcionamento.", {"horario": agora_iso()})

    @app.get("/tarefas")
    def listar_tarefas():
        estado = request.args.get("estado")
        if estado is not None and estado not in ESTADOS_VALIDOS:
            return resposta(False, f"Estado inválido. Use: {', '.join(ESTADOS_VALIDOS)}.", status=400)

        if estado:
            linhas = conexao().execute(
                "SELECT * FROM tarefas WHERE estado = ? ORDER BY id", (estado,)).fetchall()
        else:
            linhas = conexao().execute("SELECT * FROM tarefas ORDER BY id").fetchall()

        tarefas = [linha_para_dict(l) for l in linhas]
        return resposta(True, f"{len(tarefas)} tarefa(s) encontrada(s).", tarefas)

    @app.get("/tarefas/<int:id_tarefa>")
    def obter_tarefa(id_tarefa):
        linha = conexao().execute("SELECT * FROM tarefas WHERE id = ?", (id_tarefa,)).fetchone()
        if linha is None:
            return resposta(False, f"Tarefa {id_tarefa} não encontrada.", status=404)
        return resposta(True, "Tarefa encontrada.", linha_para_dict(linha))

    @app.post("/tarefas")
    def cadastrar_tarefa():
        corpo = request.get_json(silent=True)
        if not isinstance(corpo, dict):
            return resposta(False, "Corpo da requisição deve ser um JSON.", status=400)

        titulo = str(corpo.get("titulo", "")).strip()
        descricao = str(corpo.get("descricao", "") or "").strip()

        if not titulo:
            return resposta(False, "O título da tarefa é obrigatório.", status=400)
        if len(titulo) > TAMANHO_MAXIMO_TITULO:
            return resposta(False, f"O título deve ter até {TAMANHO_MAXIMO_TITULO} caracteres.", status=400)
        if len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
            return resposta(False, f"A descrição deve ter até {TAMANHO_MAXIMO_DESCRICAO} caracteres.", status=400)

        cliente = nome_cliente()
        momento = agora_iso()
        db = conexao()
        cursor = db.execute(
            """INSERT INTO tarefas (titulo, descricao, criado_por, criado_em,
                                    atualizado_por, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (titulo, descricao, cliente, momento, cliente, momento))
        db.commit()

        tarefa = linha_para_dict(db.execute(
            "SELECT * FROM tarefas WHERE id = ?", (cursor.lastrowid,)).fetchone())
        return resposta(True, f"Tarefa {tarefa['id']} cadastrada com sucesso.", tarefa, status=201)

    @app.patch("/tarefas/<int:id_tarefa>/estado")
    def atualizar_estado(id_tarefa):
        corpo = request.get_json(silent=True)
        if not isinstance(corpo, dict):
            return resposta(False, "Corpo da requisição deve ser um JSON.", status=400)

        novo_estado = corpo.get("estado")
        if novo_estado not in ESTADOS_VALIDOS:
            return resposta(False, f"Estado inválido. Use: {', '.join(ESTADOS_VALIDOS)}.", status=400)

        versao_esperada = corpo.get("versao")
        if versao_esperada is not None and not isinstance(versao_esperada, int):
            return resposta(False, "O campo 'versao' deve ser um número inteiro.", status=400)

        db = conexao()
        db.execute("BEGIN IMMEDIATE")
        try:
            atual = db.execute("SELECT * FROM tarefas WHERE id = ?", (id_tarefa,)).fetchone()
            if atual is None:
                db.rollback()
                return resposta(False, f"Tarefa {id_tarefa} não encontrada.", status=404)

            if versao_esperada is not None and versao_esperada != atual["versao"]:
                db.rollback()
                return resposta(
                    False,
                    f"Conflito: a tarefa {id_tarefa} foi alterada por "
                    f"'{atual['atualizado_por']}'. Atualize a lista e tente de novo.",
                    linha_para_dict(atual), status=409)

            if atual["estado"] == novo_estado:
                db.rollback()
                return resposta(True, f"A tarefa {id_tarefa} já estava '{novo_estado}'.",
                                linha_para_dict(atual))

            db.execute(
                """UPDATE tarefas
                   SET estado = ?, atualizado_por = ?, atualizado_em = ?, versao = versao + 1
                   WHERE id = ?""",
                (novo_estado, nome_cliente(), agora_iso(), id_tarefa))
            db.commit()
        except Exception:
            db.rollback()
            raise

        tarefa = linha_para_dict(db.execute(
            "SELECT * FROM tarefas WHERE id = ?", (id_tarefa,)).fetchone())
        return resposta(True, f"Tarefa {id_tarefa} marcada como '{novo_estado}'.", tarefa)

    @app.errorhandler(404)
    def rota_inexistente(_erro):
        return resposta(False, "Rota não encontrada.", status=404)

    @app.errorhandler(405)
    def metodo_invalido(_erro):
        return resposta(False, "Método não permitido para esta rota.", status=405)

    @app.errorhandler(500)
    def erro_interno(_erro):
        return resposta(False, "Erro interno no servidor.", status=500)

    return app


def main():
    pasta = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Servidor de tarefas")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--banco", default=os.environ.get(
        "TAREFAS_DB", os.path.join(pasta, "tarefas.db")))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app = criar_app(args.banco)
    logging.getLogger("servidor").info(
        "Servidor iniciado em %s:%d  (banco: %s)", args.host, args.porta, args.banco)
    app.run(host=args.host, port=args.porta, threaded=True)


if __name__ == "__main__":
    main()
