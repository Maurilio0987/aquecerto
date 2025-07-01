import flet as ft
import json
import os
import requests
import threading
import time

CAMINHO_ARQUIVO = "campanulas.json"

SUPABASE_URL = "https://rktybanymktqkjyopcrd.supabase.co/rest/v1/campanulas"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJrdHliYW55bWt0cWtqeW9wY3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzNzIxMjcsImV4cCI6MjA2Njk0ODEyN30.8bUcaM1MdjcuWoMsbqaDFoBM4YDY8p5nXfkMRNgjEz0"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json"
}

def main(page: ft.Page):
    page.title = "Campânulas"
    page.theme_mode = ft.ThemeMode.LIGHT
    conteudo = ft.Container(alignment=ft.alignment.center, expand=True)

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

    def mostrar_tela(tela):
        conteudo.content = tela
        page.update()

    def tela_inicial():
        return ft.Column([
            ft.Text("Menu Principal", size=30, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Suas Campânulas", on_click=lambda _: mostrar_tela(tela_campanulas())),
            ft.ElevatedButton("Adicionar Campânula", on_click=lambda _: mostrar_tela(tela_adicionar())),
            ft.ElevatedButton("Remover Campânula", on_click=lambda _: mostrar_tela(tela_remover())),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    stop_atualizacao = False
    thread_atualizacao = None

    def tela_campanulas():
        campanulas = carregar_dados()
        indice_atual = {"valor": 0}

        nome_label = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        codigo_label = ft.Text("Código: ---")
        temp_label = ft.Text("Temperatura Atual: --- °C")
        brilho_label = ft.Text("Intensidade da luz: --- %")
        tempmax_label = ft.Text("Temperatura Máxima: --- °C")
        tempmin_label = ft.Text("Temperatura Mínima: --- °C")
        dias_label = ft.Text("Dia: ---")

        input_min = ft.TextField(label="Definir Temperatura Mínima", keyboard_type="number", width=150)
        input_max = ft.TextField(label="Definir Temperatura Máxima", keyboard_type="number", width=150)
        input_dia = ft.TextField(label="Definir Dia", keyboard_type="number", width=150)

        erro_label = ft.Text("", color=ft.Colors.RED)

        def atualizar_labels():
            if not campanulas:
                nome_label.value = "Nenhuma campânula"
                return
            camp = campanulas[indice_atual["valor"]]
            nome_label.value = camp['nome']
            codigo_label.value = f"Código: {camp['codigo']}"
            page.update()

        def iniciar_atualizacao():
            nonlocal thread_atualizacao
            parar_atualizacao()

            def atualizar():
                while not stop_atualizacao:
                    try:
                        camp = campanulas[indice_atual["valor"]]
                        codigo = camp["codigo"]
                        r = requests.get(
                            f"{SUPABASE_URL}?id=eq.{codigo}",
                            headers=SUPABASE_HEADERS,
                            timeout=5
                        )
                        if r.status_code == 200 and r.json():
                            dados = r.json()[0]
                            temp_label.value = f"Temperatura: {dados.get('temp_atual', '---')} °C"
                            brilho_label.value = f"Intensidade da luz: {dados.get('intensidade', '---')} %"
                            tempmax_label.value = f"Temperatura Máxima: {dados.get('temp_max', '---')} °C"
                            tempmin_label.value = f"Temperatura Mínima: {dados.get('temp_min', '---')} °C"
                            dias_label.value = f"Dia: {dados.get('dia', '---')}"
                        else:
                            temp_label.value = brilho_label.value = tempmax_label.value = tempmin_label.value = dias_label.value = "---"
                    except:
                        temp_label.value = brilho_label.value = tempmax_label.value = tempmin_label.value = dias_label.value = "---"
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
            if not campanulas: return
            indice_atual["valor"] = (indice_atual["valor"] + 1) % len(campanulas)
            atualizar_labels()
            iniciar_atualizacao()

        def anterior(_):
            if not campanulas: return
            indice_atual["valor"] = (indice_atual["valor"] - 1) % len(campanulas)
            atualizar_labels()
            iniciar_atualizacao()

        def definir_temp_min(_):
            try:
                valor = float(input_min.value.strip().replace(',', '.'))
            except ValueError:
                erro_label.value = "Valor mínimo inválido"
                page.update()
                return

            camp = campanulas[indice_atual["valor"]]
            codigo = camp["codigo"]

            payload = {"temp_min": valor}
            try:
                r = requests.patch(
                    f"{SUPABASE_URL}?id=eq.{codigo}",
                    headers=SUPABASE_HEADERS,
                    json=payload,
                    timeout=5
                )
                erro_label.value = "Temp. mín. atualizada!" if r.status_code in (200, 204) else f"Erro: {r.status_code}"
            except Exception as e:
                erro_label.value = f"Erro: {e}"
            page.update()

        def definir_temp_max(_):
            try:
                valor = float(input_max.value.strip().replace(',', '.'))
            except ValueError:
                erro_label.value = "Valor máximo inválido"
                page.update()
                return

            camp = campanulas[indice_atual["valor"]]
            codigo = camp["codigo"]

            payload = {"temp_max": valor}
            try:
                r = requests.patch(
                    f"{SUPABASE_URL}?id=eq.{codigo}",
                    headers=SUPABASE_HEADERS,
                    json=payload,
                    timeout=5
                )
                erro_label.value = "Temp. máx. atualizada!" if r.status_code in (200, 204) else f"Erro: {r.status_code}"
            except Exception as e:
                erro_label.value = f"Erro: {e}"
            page.update()

        def definir_dia(_):
            try:
                valor = int(input_dia.value.strip())
            except ValueError:
                erro_label.value = "Dia inválido"
                page.update()
                return

            camp = campanulas[indice_atual["valor"]]
            codigo = camp["codigo"]

            payload = {"dia": valor}
            try:
                r = requests.patch(
                    f"{SUPABASE_URL}?id=eq.{codigo}",
                    headers=SUPABASE_HEADERS,
                    json=payload,
                    timeout=5
                )
                erro_label.value = "Dia atualizado!" if r.status_code in (200, 204) else f"Erro: {r.status_code}"
            except Exception as e:
                erro_label.value = f"Erro: {e}"
            page.update()

        atualizar_labels()
        iniciar_atualizacao()

        return ft.Column([
            ft.Text("Suas Campânulas", size=25, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    nome_label, codigo_label, temp_label,
                    brilho_label, tempmax_label, tempmin_label, dias_label
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10
            ),
            erro_label,
            ft.Row(
                [
                    ft.Column(  # Coluna dos inputs
                        [input_min, input_max, input_dia],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    ft.Column(  # Coluna dos botões
                        [
                            ft.ElevatedButton("Definir Mín.", on_click=definir_temp_min),
                            ft.ElevatedButton("Definir Máx.", on_click=definir_temp_max),
                            ft.ElevatedButton("Definir Dia", on_click=definir_dia)
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=30  # Espaço entre as colunas
            ),


            ft.Row([
                ft.ElevatedButton("◀️", on_click=anterior),
                ft.ElevatedButton("▶️", on_click=proximo)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.ElevatedButton("Voltar", on_click=lambda _: encerrar_voltar())
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def encerrar_voltar():
        nonlocal stop_atualizacao
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
            nome, codigo,
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

    mostrar_tela(tela_inicial())
    page.add(conteudo)

ft.app(target=main)
