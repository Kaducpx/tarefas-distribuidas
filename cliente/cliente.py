import json
import sys
import urllib.error
import urllib.request


def requisitar(servidor, metodo, caminho, dados=None):
    corpo = json.dumps(dados).encode("utf-8") if dados is not None else None
    pedido = urllib.request.Request(servidor + caminho, data=corpo, method=metodo,
                                    headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=5) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        try:
            return json.loads(erro.read().decode("utf-8"))
        except ValueError:
            return {"erro": f"Erro HTTP {erro.code}."}
    except (urllib.error.URLError, OSError):
        return {"erro": f"Servidor indisponível em {servidor}."}


def listar(servidor):
    return requisitar(servidor, "GET", "/tarefas")


def cadastrar(servidor, titulo):
    return requisitar(servidor, "POST", "/tarefas", {"titulo": titulo})


def alterar_estado(servidor, id_tarefa, estado):
    return requisitar(servidor, "PUT", f"/tarefas/{id_tarefa}", {"estado": estado})


def mostrar_resultado(resposta):
    if "erro" in resposta:
        print("ERRO:", resposta["erro"])
    else:
        print("OK:", resposta["mensagem"])


def mostrar_tarefas(resposta):
    if "erro" in resposta:
        print("ERRO:", resposta["erro"])
        return
    print(resposta["mensagem"])
    for tarefa in resposta["tarefas"]:
        marca = "x" if tarefa["estado"] == "concluida" else " "
        print(f"  {tarefa['id']:>3}  [{marca}] {tarefa['titulo']}")


def menu(nome, servidor):
    while True:
        print(f"\n===== {nome} ({servidor}) =====")
        print("1. Listar tarefas")
        print("2. Cadastrar tarefa")
        print("3. Marcar tarefa como concluída")
        print("4. Marcar tarefa como pendente")
        print("0. Sair")
        opcao = input("Opção: ").strip()

        if opcao == "0":
            return
        elif opcao == "1":
            mostrar_tarefas(listar(servidor))
        elif opcao == "2":
            titulo = input("Título: ").strip()
            mostrar_resultado(cadastrar(servidor, titulo))
            mostrar_tarefas(listar(servidor))
        elif opcao in ("3", "4"):
            id_tarefa = input("Número da tarefa: ").strip()
            if id_tarefa.isdigit():
                estado = "concluida" if opcao == "3" else "pendente"
                mostrar_resultado(alterar_estado(servidor, int(id_tarefa), estado))
                mostrar_tarefas(listar(servidor))
            else:
                print("ERRO: informe um número válido.")
        else:
            print("ERRO: opção inválida.")


if __name__ == "__main__":
    nome = sys.argv[1] if len(sys.argv) > 1 else "Cliente"
    servidor = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5000"
    menu(nome, servidor)
