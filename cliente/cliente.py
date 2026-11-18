# Cliente
#
# Este programa roda nas Vms cliente1 e cliente2. É o mesmo
# arquivo nas duas, o que muda é o nome passado na hora de abrir
#
#   python3 cliente.py Cliente1 http://192.168.56.10:5000
#   python3 cliente.py Cliente2 http://192.168.56.10:5000
#
# o cliente mostra um menu no terminal e, a cada opção escolhida, manda um
# pedido pela rede http pro servidor e mostra a resposta. Ele não guarda nenhuma
# tarefa , tudo que aparece ali na tela vem do servidor, por isso que os dois
# clientes sempre veem os mesmos dados
#
# só usa libs que ja vem com o python por isso nao precisa instalar nada.

import json
import sys
import urllib.error
import urllib.request


#funções de comunicação com o servidor
# é a função principal do cliente, todas as outras tem que passar por ela. Monta o pedido
# http, envia pro servidor e já devolve a resposta convertida de JSON pra
# dicionario. O metodo é GET, POST ou PUT e o caminho é a rota, tipo /tarefas.
#
# Se der problema, devolve um dicionario com a chave "erro" em vez de fechar o
# programa, existe dois casos, primeiro: o servidor respondeu mas com erro, ai cai no 
# HTTPError, segundo: servidor nem respondeu porque está desligado ou sem rede,
# ai cai no URLError. O timeout=5 faz o cliente desistir depois de 5 segundos
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


# as três funções abaixo são as operações do sistema, cada uma só chama a
# requisitar com a rota certa

# pede pro servidor a listagem de todas as tarefas
def listar(servidor):
    return requisitar(servidor, "GET", "/tarefas")


# manda o título de uma tarefa nova pro servidor cadastrar
def cadastrar(servidor, titulo):
    return requisitar(servidor, "POST", "/tarefas", {"titulo": titulo})


# pede pro servidor mudar o estado de uma tarefa, que pode ser pendente
# ou concluida
def alterar_estado(servidor, id_tarefa, estado):
    return requisitar(servidor, "PUT", f"/tarefas/{id_tarefa}", {"estado": estado})



# pra exibir na tela, essad duas funções só mostra a resposta do servidor

# mostra o resultado de um cadastro ou de uma alteração, "OK" com a mensagem
# que o servidor mandou, ou "ERRO" com o motivo.
def mostrar_resultado(resposta):
    if "erro" in resposta:
        print("ERRO:", resposta["erro"])
    else:
        print("OK:", resposta["mensagem"])


# mostra a listagem de tarefas, uma por linha, com o número, uma caixinha
# [x] pra concluída ou [ ] pra pendente, e o título.
# se não vier lista, mostra o erro.
def mostrar_tarefas(resposta):
    if "erro" in resposta:
        print("ERRO:", resposta["erro"])
        return
    print(resposta["mensagem"])
    for tarefa in resposta["tarefas"]:
        marca = "x" if tarefa["estado"] == "concluida" else " "
        print(f"  {tarefa['id']:>3}  [{marca}] {tarefa['titulo']}")



#Menu

#vai mostrando o menu até o usuário escolher pra sair.
# depois que cadatra ou altera uma tarefa, o cliente busca a lista de novo no
# servidor, pra tela mostrar sempre o mais recente, inclusive o que o outro
# cliente tiver mudado.
def menu(nome, servidor):
    while True:
        print(f"\n===== {nome} ({servidor}) =====")
        print("1. Listar tarefas")
        print("2. Cadastrar tarefa")
        print("3. Marcar tarefa como concluída")
        print("4. Marcar tarefa como pendente")
        print("0. Sair")
        opcao = input("Opção: ").strip()

        # opção 0, finaliza o cliente
        if opcao == "0":
            return
        # opção 1, faz a listagem das tarefaz
        elif opcao == "1":
            mostrar_tarefas(listar(servidor))
        # opção 2, pede o titulo cadastra a tarefa e mostra a lista de novo
        elif opcao == "2":
            titulo = input("Título: ").strip()
            mostrar_resultado(cadastrar(servidor, titulo))
            mostrar_tarefas(listar(servidor))
        # opções 3 e 4, pede o numero da tarefa e mudam o estado dela
        # o isdigit() confere se foi digitado um numero antes de enviar
        elif opcao in ("3", "4"):
            id_tarefa = input("Número da tarefa: ").strip()
            if id_tarefa.isdigit():
                estado = "concluida" if opcao == "3" else "pendente"
                mostrar_resultado(alterar_estado(servidor, int(id_tarefa), estado))
                mostrar_tarefas(listar(servidor))
            else:
                print("ERRO: informe um número válido.")
        # qualquer outra coisa digitada no menu
        else:
            print("ERRO: opção inválida.")



#Inicio do programa

# faz a leitura do nome do cliente e do endereço do servidor que foram passados
# na hora de abrir o programa. Se não chegar nada, usa "Cliente" e o servidor na
# própria máquina, que é o 127.0.0.1 ai depois abre o menu.
if __name__ == "__main__":
    nome = sys.argv[1] if len(sys.argv) > 1 else "Cliente"
    servidor = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5000"
    menu(nome, servidor)
