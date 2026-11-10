import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

TEMPO_LIMITE = 5


class ErroServidor(Exception):
    def __init__(self, mensagem, status=None, dados=None):
        super().__init__(mensagem)
        self.status = status
        self.dados = dados


class ClienteTarefas:
    def __init__(self, url_servidor, nome):
        self.url = url_servidor.rstrip("/")
        self.nome = nome
        self.versoes = {}

    def _requisitar(self, metodo, caminho, corpo=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(
            self.url + caminho, data=dados, method=metodo,
            headers={"Content-Type": "application/json", "X-Cliente": self.nome})
        try:
            with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                conteudo = json.loads(erro.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                conteudo = {}
            raise ErroServidor(conteudo.get("mensagem", f"Erro HTTP {erro.code}."),
                               erro.code, conteudo.get("dados")) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as erro:
            motivo = getattr(erro, "reason", erro)
            raise ErroServidor(f"Servidor indisponível em {self.url} ({motivo}).") from None

    def saude(self):
        return self._requisitar("GET", "/saude")

    def listar(self, estado=None):
        caminho = "/tarefas" + (f"?estado={estado}" if estado else "")
        resposta = self._requisitar("GET", caminho)
        for tarefa in resposta.get("dados", []):
            self.versoes[tarefa["id"]] = tarefa["versao"]
        return resposta

    def cadastrar(self, titulo, descricao=""):
        resposta = self._requisitar("POST", "/tarefas", {"titulo": titulo, "descricao": descricao})
        tarefa = resposta["dados"]
        self.versoes[tarefa["id"]] = tarefa["versao"]
        return resposta

    def alterar_estado(self, id_tarefa, estado):
        corpo = {"estado": estado}
        if id_tarefa in self.versoes:
            corpo["versao"] = self.versoes[id_tarefa]
        try:
            resposta = self._requisitar("PATCH", f"/tarefas/{id_tarefa}/estado", corpo)
        except ErroServidor as erro:
            if erro.status == 409 and erro.dados:
                self.versoes[id_tarefa] = erro.dados["versao"]
            raise
        self.versoes[id_tarefa] = resposta["dados"]["versao"]
        return resposta


def imprimir_tarefas(tarefas):
    if not tarefas:
        print("  (nenhuma tarefa)")
        return
    print(f"  {'ID':>3}  {'ESTADO':<13}  {'TÍTULO':<40}  ÚLTIMA ALTERAÇÃO")
    print("  " + "-" * 90)
    for t in tarefas:
        marca = "[x]" if t["estado"] == "concluida" else "[ ]"
        estado = f"{marca} {t['estado']}"
        titulo = t["titulo"] if len(t["titulo"]) <= 40 else t["titulo"][:37] + "..."
        alteracao = f"{t['atualizado_por']} em {horario_local(t['atualizado_em'])}"
        print(f"  {t['id']:>3}  {estado:<13}  {titulo:<40}  {alteracao}")


def horario_local(iso_utc):
    try:
        return datetime.fromisoformat(iso_utc).astimezone().strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return iso_utc


def sucesso(msg):
    print(f"\n  OK: {msg}")


def erro(msg):
    print(f"\n  ERRO: {msg}")


def mostrar_lista(cliente, estado=None):
    try:
        resposta = cliente.listar(estado)
    except ErroServidor as e:
        erro(str(e))
        return
    print(f"\n  {resposta['mensagem']}")
    imprimir_tarefas(resposta["dados"])


def ler_id(texto):
    valor = input(texto).strip()
    if not valor.isdigit():
        erro("Informe um número de tarefa válido.")
        return None
    return int(valor)


def menu(cliente):
    opcoes = """
  ============ {nome} -> {url} ============
  1. Listar todas as tarefas
  2. Listar tarefas pendentes
  3. Listar tarefas concluídas
  4. Cadastrar nova tarefa
  5. Marcar tarefa como concluída
  6. Marcar tarefa como pendente
  7. Testar conexão com o servidor
  0. Sair"""
    try:
        cliente.saude()
        sucesso(f"Conectado ao servidor {cliente.url}.")
    except ErroServidor as e:
        erro(f"{e} O menu continua disponível; tente novamente depois.")

    while True:
        print(opcoes.format(nome=cliente.nome, url=cliente.url))
        escolha = input("  Opção: ").strip()

        if escolha == "0":
            print("  Até logo!")
            return
        elif escolha == "1":
            mostrar_lista(cliente)
        elif escolha == "2":
            mostrar_lista(cliente, "pendente")
        elif escolha == "3":
            mostrar_lista(cliente, "concluida")
        elif escolha == "4":
            titulo = input("  Título: ").strip()
            descricao = input("  Descrição (opcional): ").strip()
            try:
                sucesso(cliente.cadastrar(titulo, descricao)["mensagem"])
            except ErroServidor as e:
                erro(str(e))
            mostrar_lista(cliente)
        elif escolha in ("5", "6"):
            id_tarefa = ler_id("  Número da tarefa: ")
            if id_tarefa is not None:
                estado = "concluida" if escolha == "5" else "pendente"
                try:
                    sucesso(cliente.alterar_estado(id_tarefa, estado)["mensagem"])
                except ErroServidor as e:
                    erro(str(e))
                mostrar_lista(cliente)
        elif escolha == "7":
            try:
                sucesso(cliente.saude()["mensagem"])
            except ErroServidor as e:
                erro(str(e))
        else:
            erro("Opção inválida.")


def executar_comando(cliente, args):
    try:
        if args.comando == "listar":
            resposta = cliente.listar(args.estado)
            print(resposta["mensagem"])
            imprimir_tarefas(resposta["dados"])
            return 0
        if args.comando == "cadastrar":
            print("OK:", cliente.cadastrar(args.titulo, args.descricao)["mensagem"])
        else:
            estado = "concluida" if args.comando == "concluir" else "pendente"
            print("OK:", cliente.alterar_estado(args.id, estado)["mensagem"])
        return 0
    except ErroServidor as e:
        print("ERRO:", e)
        return 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Cliente do gerenciador de tarefas")
    parser.add_argument("--nome", default=os.environ.get("CLIENTE_NOME", "Cliente"),
                        help="identificação deste cliente (ex.: Cliente1)")
    parser.add_argument("--servidor", default=os.environ.get("SERVIDOR_URL", "http://127.0.0.1:5000"),
                        help="endereço do servidor (ex.: http://192.168.56.10:5000)")
    sub = parser.add_subparsers(dest="comando")

    p_listar = sub.add_parser("listar", help="lista as tarefas")
    p_listar.add_argument("--estado", choices=("pendente", "concluida"))
    p_cad = sub.add_parser("cadastrar", help="cadastra uma tarefa")
    p_cad.add_argument("titulo")
    p_cad.add_argument("descricao", nargs="?", default="")
    for nome in ("concluir", "reabrir"):
        p = sub.add_parser(nome, help=f"{nome} uma tarefa")
        p.add_argument("id", type=int)

    args = parser.parse_args()
    cliente = ClienteTarefas(args.servidor, args.nome)

    if args.comando is None:
        try:
            menu(cliente)
        except (KeyboardInterrupt, EOFError):
            print("\n  Encerrado.")
        return 0
    return executar_comando(cliente, args)


if __name__ == "__main__":
    sys.exit(main())
