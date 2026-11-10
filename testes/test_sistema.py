import logging
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

from servidor import criar_app
from cliente import ClienteTarefas, ErroServidor

logging.getLogger("werkzeug").setLevel(logging.WARNING)


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TesteApiServidor(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        app = criar_app(os.path.join(self.pasta.name, "teste.db"))
        self.http = app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def cadastrar(self, titulo="Tarefa", cliente="Cliente1"):
        return self.http.post("/tarefas", json={"titulo": titulo}, headers={"X-Cliente": cliente})

    def test_saude(self):
        r = self.http.get("/saude")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["sucesso"])

    def test_cadastro_comeca_pendente(self):
        r = self.cadastrar("Estudar redes")
        self.assertEqual(r.status_code, 201)
        tarefa = r.get_json()["dados"]
        self.assertEqual(tarefa["estado"], "pendente")
        self.assertEqual(tarefa["criado_por"], "Cliente1")
        self.assertEqual(tarefa["versao"], 1)

    def test_cadastro_sem_titulo_e_rejeitado(self):
        r = self.http.post("/tarefas", json={"titulo": "   "})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json()["sucesso"])

    def test_cadastro_sem_json_e_rejeitado(self):
        r = self.http.post("/tarefas", data="texto", content_type="text/plain")
        self.assertEqual(r.status_code, 400)

    def test_listagem_e_filtro(self):
        self.cadastrar("A")
        self.cadastrar("B")
        self.http.patch("/tarefas/1/estado", json={"estado": "concluida"})
        self.assertEqual(len(self.http.get("/tarefas").get_json()["dados"]), 2)
        pendentes = self.http.get("/tarefas?estado=pendente").get_json()["dados"]
        self.assertEqual([t["titulo"] for t in pendentes], ["B"])
        self.assertEqual(self.http.get("/tarefas?estado=xyz").status_code, 400)

    def test_atualizar_estado(self):
        self.cadastrar()
        r = self.http.patch("/tarefas/1/estado", json={"estado": "concluida"},
                            headers={"X-Cliente": "Cliente2"})
        self.assertEqual(r.status_code, 200)
        tarefa = r.get_json()["dados"]
        self.assertEqual(tarefa["estado"], "concluida")
        self.assertEqual(tarefa["atualizado_por"], "Cliente2")
        self.assertEqual(tarefa["versao"], 2)

    def test_estado_invalido(self):
        self.cadastrar()
        r = self.http.patch("/tarefas/1/estado", json={"estado": "feita"})
        self.assertEqual(r.status_code, 400)

    def test_tarefa_inexistente(self):
        self.assertEqual(self.http.get("/tarefas/99").status_code, 404)
        r = self.http.patch("/tarefas/99/estado", json={"estado": "concluida"})
        self.assertEqual(r.status_code, 404)

    def test_conflito_de_versao(self):
        self.cadastrar()
        self.http.patch("/tarefas/1/estado", json={"estado": "concluida", "versao": 1})
        r = self.http.patch("/tarefas/1/estado", json={"estado": "pendente", "versao": 1})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["dados"]["versao"], 2)

    def test_rota_inexistente(self):
        r = self.http.get("/nada")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.get_json()["sucesso"])


class TesteDoisClientes(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        app = criar_app(os.path.join(self.pasta.name, "teste.db"))
        self.porta = porta_livre()
        self.servidor = make_server("127.0.0.1", self.porta, app, threaded=True)
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()
        url = f"http://127.0.0.1:{self.porta}"
        self.cliente1 = ClienteTarefas(url, "Cliente1")
        self.cliente2 = ClienteTarefas(url, "Cliente2")

    def tearDown(self):
        self.servidor.shutdown()
        self.thread.join()
        self.pasta.cleanup()

    def test_cenario_do_enunciado(self):
        self.cliente1.cadastrar("Estudar introdução à programação")
        lista = self.cliente2.listar()["dados"]
        self.assertEqual(lista[0]["titulo"], "Estudar introdução à programação")
        self.assertEqual(lista[0]["criado_por"], "Cliente1")
        self.cliente2.alterar_estado(lista[0]["id"], "concluida")
        tarefa = self.cliente1.listar()["dados"][0]
        self.assertEqual(tarefa["estado"], "concluida")
        self.assertEqual(tarefa["atualizado_por"], "Cliente2")

    def test_conflito_entre_clientes(self):
        self.cliente1.cadastrar("Tarefa disputada")
        self.cliente1.listar()
        self.cliente2.listar()
        self.cliente2.alterar_estado(1, "concluida")
        with self.assertRaises(ErroServidor) as ctx:
            self.cliente1.alterar_estado(1, "pendente")
        self.assertEqual(ctx.exception.status, 409)
        self.cliente1.alterar_estado(1, "pendente")
        self.assertEqual(self.cliente2.listar()["dados"][0]["estado"], "pendente")

    def test_cadastros_simultaneos(self):
        def cadastrar_varias(cliente):
            for i in range(20):
                cliente.cadastrar(f"{cliente.nome} tarefa {i}")

        threads = [threading.Thread(target=cadastrar_varias, args=(c,))
                   for c in (self.cliente1, self.cliente2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        tarefas = self.cliente1.listar()["dados"]
        self.assertEqual(len(tarefas), 40)
        self.assertEqual(len({t["id"] for t in tarefas}), 40)


class TesteFalha(unittest.TestCase):

    def test_servidor_indisponivel(self):
        cliente = ClienteTarefas(f"http://127.0.0.1:{porta_livre()}", "Cliente1")
        with self.assertRaises(ErroServidor) as ctx:
            cliente.listar()
        self.assertIn("indisponível", str(ctx.exception))
        self.assertIsNone(ctx.exception.status)

    def test_dados_persistem_apos_reinicio(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = os.path.join(pasta, "teste.db")
            criar_app(banco).test_client().post("/tarefas", json={"titulo": "Persistente"})
            lista = criar_app(banco).test_client().get("/tarefas").get_json()["dados"]
            self.assertEqual([t["titulo"] for t in lista], ["Persistente"])


if __name__ == "__main__":
    unittest.main()
