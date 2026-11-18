import os
import socket
import sys
import tempfile
import threading
import unittest

from werkzeug.serving import make_server

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "servidor"))
sys.path.insert(0, os.path.join(RAIZ, "cliente"))

import servidor
import cliente


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TesteServidor(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        servidor.BANCO = os.path.join(self.pasta.name, "teste.db")
        servidor.criar_tabela()
        self.http = servidor.app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def test_cadastrar_e_listar(self):
        r = self.http.post("/tarefas", json={"titulo": "Estudar redes"})
        self.assertEqual(r.status_code, 201)
        tarefas = self.http.get("/tarefas").get_json()["tarefas"]
        self.assertEqual(tarefas, [{"id": 1, "titulo": "Estudar redes", "estado": "pendente"}])

    def test_cadastro_sem_titulo(self):
        r = self.http.post("/tarefas", json={"titulo": "  "})
        self.assertEqual(r.status_code, 400)

    def test_alterar_estado(self):
        self.http.post("/tarefas", json={"titulo": "A"})
        r = self.http.put("/tarefas/1", json={"estado": "concluida"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.http.get("/tarefas").get_json()["tarefas"][0]["estado"], "concluida")

    def test_estado_invalido(self):
        self.http.post("/tarefas", json={"titulo": "A"})
        r = self.http.put("/tarefas/1", json={"estado": "feita"})
        self.assertEqual(r.status_code, 400)

    def test_tarefa_inexistente(self):
        r = self.http.put("/tarefas/99", json={"estado": "concluida"})
        self.assertEqual(r.status_code, 404)


class TesteDoisClientes(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        servidor.BANCO = os.path.join(self.pasta.name, "teste.db")
        servidor.criar_tabela()
        porta = porta_livre()
        self.servidor_http = make_server("127.0.0.1", porta, servidor.app, threaded=True)
        self.thread = threading.Thread(target=self.servidor_http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{porta}"

    def tearDown(self):
        self.servidor_http.shutdown()
        self.thread.join()
        self.pasta.cleanup()

    def test_cenario_do_enunciado(self):
        cliente.cadastrar(self.url, "Estudar introdução à programação")
        tarefas = cliente.listar(self.url)["tarefas"]
        self.assertEqual(tarefas[0]["titulo"], "Estudar introdução à programação")
        cliente.alterar_estado(self.url, tarefas[0]["id"], "concluida")
        self.assertEqual(cliente.listar(self.url)["tarefas"][0]["estado"], "concluida")

    def test_servidor_indisponivel(self):
        resposta = cliente.listar(f"http://127.0.0.1:{porta_livre()}")
        self.assertIn("indisponível", resposta["erro"])


if __name__ == "__main__":
    unittest.main()
