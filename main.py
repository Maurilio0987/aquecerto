import flet as ft
import json
import os
import requests
import threading
import time

CAMINHO_ARQUIVO = "campanulas.json"
BASE_URL = "https://aquecerto.onrender.com/app/"

def main(page: ft.Page):
    page.title = "Aquecerto"
    page.theme_mode = ft.ThemeMode.LIGHT

    ## ------------------------------
    ## Carregamento e salvamento JSON
    ## ------------------------------
    def carregar_dados():
        if os.path.exists(CAMINHO_ARQUIVO):
            try:
                with open(CAMINHO_ARQUIVO, "r") as arq:
                    return json.load(arq)
            except:
                return []
        return []

    def salvar_dados(dados):
        with open(CAMINHO_ARQUIVO, "w") as arq:
            json.dump(dados, arq, indent=4)

    ## -------------------------
    ## Telas (Containers)
    ## -------------------------

    conteudo = ft.Container(alignment=ft.alignment.center, expand=True)

    ## Tela Inicial
    def tela_inicial():
        return ft.Column([
            ft.Text("Menu Principal", size=30, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Suas Campânulas", on_click=lambda _: mostrar_tela(tela_campanulas())),
            ft.ElevatedButton("Adicionar Campânula", on_click=lambda _: mostrar_tela(tela_adicionar())),
            ft.ElevatedButton("Remover Campânula", on_click=lambda _: mostrar_tela(tela_remover())),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)

    ## Tela Campânulas
    stop_atualizacao = False
    thread_atualizacao = None

    def tela_campanulas():
        campanulas = carregar_dados()
        indice_atual = {"valor": 0}

        nome_label = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        codigo_label = ft.Text("")
        temp_label = ft.Text("Temperatura: --- °C")
        brilho_label = ft.Text("Intensidade da luz: --- %")

        input_min = ft.TextField(label="Temperatura Mínima", keyboard_type="number", width=150)
        input_max = ft.TextField(label="Temperatura Máxima", keyboard_type="number", width=150)

        def atualizar_labels():
            if not campanulas:
                nome_label.value = "Nenhuma campânula"
                codigo_label.value = ""
                temp_label.value = ""
                brilho_label.value = ""
                input_min.value = ""
                input_max.value = ""
                return

            camp = campanulas[indice_atual["valor"]]
            nome_label.value = camp['nome']
            codigo_label.value = f"Código: {camp['codigo']}"
            temp_label.value = ""
            brilho_label.value = ""
            input_min.value = ""
            input_max.value = ""
            page.update()

        def iniciar_atualizacao():
            nonlocal thread_atualizacao
            parar_atualizacao()
            def atualizar():
                while not stop_atualizacao:
                    try:
                        camp = campanulas[indice_atual["valor"]]
                        r = requests.get(BASE_URL + camp["codigo"], timeout=5)
                        if r.status_code == 200:
                            dados_api = r.json()[camp["codigo"]]
                            temperatura = dados_api["temperature"]
                            brilho = dados_api["brightness"]
                        else:
                            temperatura = "---"
                            brilho = "---"
                    except:
                        temperatura = "---"
                        brilho = "---"

                    temp_label.value = f"Temperatura: {temperatura} °C"
                    brilho_label.value = f"Intensidade da luz: {brilho} %"
                    page.update()
                    time.sleep(5)

            thread_atualizacao = threading.Thread(target=atualizar, daemon=True)
            thread_atualizacao.start()

        def parar_atualizacao():
            nonlocal stop_atualizacao
            stop_atualizacao = True
            time.sleep(0.1)
            stop_atualizacao = False

        def proximo(_):
            if not campanulas:
                return
            indice_atual["valor"] = (indice_atual["valor"] + 1) % len(campanulas)
            atualizar_labels()
            iniciar_atualizacao()

        def anterior(_):
            if not campanulas:
                return
            indice_atual["valor"] = (indice_atual["valor"] - 1) % len(campanulas)
            atualizar_labels()
            iniciar_atualizacao()

        def definir(_):
            if not campanulas:
                return
            camp = campanulas[indice_atual["valor"]]
            codigo = camp["codigo"]
            try:
                valor_min = float(input_min.value.strip())
                valor_max = float(input_max.value.strip())
            except:
                print("Erro: entradas inválidas")
                return

            payload = {
                codigo: {
                    "min": valor_min,
                    "max": valor_max
                }
            }

            try:
                r = requests.post(BASE_URL + "/config/" + codigo, json=payload, timeout=5)
                if r.status_code == 200:
                    print("Dados enviados com sucesso")
                else:
                    print("Erro ao enviar dados:", r.status_code)
            except Exception as e:
                print("Erro ao conectar:", e)

        atualizar_labels()
        iniciar_atualizacao()

        return ft.Column([
            ft.Text("Suas Campânulas", size=25, weight=ft.FontWeight.BOLD),

            ft.Container(
                content=ft.Column([
                    nome_label,
                    codigo_label,
                    temp_label,
                    brilho_label,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10
            ),

            # NOVO BLOCO: Inputs e botão
            ft.Row([
                ft.Column([input_max, input_min]),
                ft.ElevatedButton("Definir", on_click=definir),
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.Row([
                ft.ElevatedButton("◀️", on_click=anterior),
                ft.ElevatedButton("▶️", on_click=proximo)
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.ElevatedButton("Voltar", on_click=lambda _: encerrar_voltar())
        ],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER)


    def encerrar_voltar():
        global stop_atualizacao
        stop_atualizacao = True
        time.sleep(0.1)
        stop_atualizacao = False
        mostrar_tela(tela_inicial())

    ## Tela Adicionar
    def tela_adicionar():
        nome = ft.TextField(label="Nome da Campânula")
        codigo = ft.TextField(label="Código da Campânula")

        def adicionar(_):
            if nome.value.strip() and codigo.value.strip():
                dados = carregar_dados()
                dados.append({"nome": nome.value.strip(), "codigo": codigo.value.strip()})
                salvar_dados(dados)
                mostrar_tela(tela_inicial())

        return ft.Column([
            ft.Text("Adicionar Nova Campânula", size=25, weight=ft.FontWeight.BOLD),
            nome,
            codigo,
            ft.ElevatedButton("Adicionar", on_click=adicionar),
            ft.ElevatedButton("Voltar", on_click=lambda _: mostrar_tela(tela_inicial()))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    ## Tela Remover
    def tela_remover():
        lista = ft.Column(scroll=ft.ScrollMode.ALWAYS)
        campanulas = carregar_dados()

        def atualizar_lista():
            campanulas.clear()
            campanulas.extend(carregar_dados())  # Recarrega do arquivo

            lista.controls.clear()
            if campanulas:
                for camp in campanulas:
                    linha = ft.Row([
                        ft.Text(f"{camp['nome']} ({camp['codigo']})", expand=True),
                        ft.ElevatedButton("Remover", on_click=lambda e, c=camp: remover(c))
                    ])
                    lista.controls.append(linha)
            else:
                lista.controls.append(ft.Text("Nenhuma campânula cadastrada."))
            page.update()

        def remover(campanula):
            dados = carregar_dados()
            dados = [c for c in dados if c != campanula]
            salvar_dados(dados)
            atualizar_lista()  # Atualiza a lista na tela

        atualizar_lista()

        return ft.Column([
            ft.Text("Remover Campânula", size=25, weight=ft.FontWeight.BOLD),
            lista,
            ft.ElevatedButton("Voltar", on_click=lambda _: mostrar_tela(tela_inicial()))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    ## --------------------------
    ## Função de troca de tela
    ## --------------------------
    def mostrar_tela(tela):
        conteudo.content = tela
        page.update()

    ## Inicializa na tela inicial
    mostrar_tela(tela_inicial())

    page.add(conteudo)

ft.app(target=main)
