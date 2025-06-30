import flet as ft
import json
import os
import requests
import threading
import time

CAMINHO_ARQUIVO = "campanulas.json"
BASE_URL = "https://aquecerto.onrender.com/app/"
CONFIG_URL = "https://aquecerto.onrender.com/esp32/config/"

def main(page: ft.Page):
    page.title = "Aquecerto"
    page.theme_mode = ft.ThemeMode.LIGHT

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

    conteudo = ft.Container(alignment=ft.alignment.center, expand=True)

    def tela_inicial():
        return ft.Column([
            ft.Text("Menu Principal", size=30, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Suas Campânulas", on_click=lambda _: mostrar_tela(tela_campanulas())),
            ft.ElevatedButton("Adicionar Campânula", on_click=lambda _: mostrar_tela(tela_adicionar())),
            ft.ElevatedButton("Remover Campânula", on_click=lambda _: mostrar_tela(tela_remover())),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)

    stop_atualizacao = False
    thread_atualizacao = None

    def tela_campanulas():
        campanulas = carregar_dados()
        indice_atual = {"valor": 0}

        nome_label = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        codigo_label = ft.Text("")
        temp_label = ft.Text("Temperatura Atual: --- °C")
        brilho_label = ft.Text("Intensidade da luz: --- %")
        tempmax_label = ft.Text("Temperatura Máxima: --- °C")
        tempmin_label = ft.Text("Temperatura Mínima: --- °C")
        dias_label = ft.Text("Dia: ---")

        input_min = ft.TextField(label="Temperatura Mínima", keyboard_type="number", width=150)
        input_max = ft.TextField(label="Temperatura Máxima", keyboard_type="number", width=150)

        erro_label = ft.Text("", color=ft.Colors.RED)

        def atualizar_labels():
            if not campanulas:
                nome_label.value = "Nenhuma campânula"
                codigo_label.value = ""
                temp_label.value = ""
                brilho_label.value = ""
                tempmax_label.value = ""
                tempmin_label.value = ""
                dias_label.value = ""
                input_min.value = ""
                input_max.value = ""
                return

            camp = campanulas[indice_atual["valor"]]
            nome_label.value = camp['nome']
            codigo_label.value = f"Código: {camp['codigo']}"
            temp_label.value = ""
            brilho_label.value = ""
            tempmax_label.value = ""
            tempmin_label.value = ""
            dias_label.value = ""
            input_min.value = ""
            input_max.value = ""
            erro_label.value = ""
            page.update()

        def iniciar_atualizacao():
            nonlocal thread_atualizacao
            parar_atualizacao()

            def atualizar():
                while not stop_atualizacao:
                    try:
                        camp = campanulas[indice_atual["valor"]]
                        codigo = camp["codigo"]

                        r = requests.get(BASE_URL + codigo, timeout=5)
                        if r.status_code == 200:
                            dados_api = r.json()[codigo]
                            temperatura = dados_api["temperature"]
                            brilho = dados_api["brightness"]
                            max = dados_api["max"]
                            min = dados_api["min"]
                        else:
                            temperatura = brilho = max = min = "---"

                        # Buscar dias
                        try:
                            r_config = requests.get(CONFIG_URL + codigo, timeout=5)
                            if r_config.status_code == 200:
                                dados_config = r_config.json()[codigo]
                                dias = dados_config.get("dias", "---")
                            else:
                                dias = "---"
                        except:
                            dias = "---"

                    except:
                        temperatura = brilho = max = min = dias = "---"

                    temp_label.value = f"Temperatura: {temperatura} °C"
                    brilho_label.value = f"Intensidade da luz: {brilho} %"
                    tempmax_label.value = f"Temperatura Máxima: {max} °C"
                    tempmin_label.value = f"Temperatura Mínima: {min} °C"
                    dias_label.value = f"Dia: {dias}"
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
                valor_min = float(input_min.value.strip().replace(',', '.'))
                valor_max = float(input_max.value.strip().replace(',', '.'))

                if valor_min > valor_max:
                    erro_label.value = "Erro: Temperatura mínima não pode ser maior que a máxima."
                    page.update()
                    return
            except ValueError:
                erro_label.value = "Erro: entradas inválidas."
                page.update()
                return

            payload = {
                codigo: {
                    "min": valor_min,
                    "max": valor_max,
                    "dias": 0
                }
            }

            try:
                r = requests.post(BASE_URL + "/config/" + codigo, json=payload, timeout=5)
                if r.status_code == 200:
                    erro_label.value = "Dados enviados com sucesso! Aguarde"
                else:
                    erro_label.value = f"Erro ao enviar dados: {r.status_code}"
            except Exception as e:
                erro_label.value = f"Erro ao conectar: {e}"

            page.update()

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
                    tempmax_label,
                    tempmin_label,
                    dias_label,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10
            ),

            erro_label,

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

    def tela_remover():
        lista = ft.Column(scroll=ft.ScrollMode.ALWAYS)
        campanulas = carregar_dados()

        def atualizar_lista():
            campanulas.clear()
            campanulas.extend(carregar_dados())
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
            atualizar_lista()

        atualizar_lista()

        return ft.Column([
            ft.Text("Remover Campânula", size=25, weight=ft.FontWeight.BOLD),
            lista,
            ft.ElevatedButton("Voltar", on_click=lambda _: mostrar_tela(tela_inicial()))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def mostrar_tela(tela):
        conteudo.content = tela
        page.update()

    mostrar_tela(tela_inicial())
    page.add(conteudo)

ft.app(target=main)
