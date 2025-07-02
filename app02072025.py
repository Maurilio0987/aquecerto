import flet as ft
import json
import os
import requests
import threading
import time
from typing import Dict

# --- Constantes ---
CAMINHO_ARQUIVO = "campanulas.json"
SUPABASE_URL = "https://rktybanymktqkjyopcrd.supabase.co/rest/v1/campanulas"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJrdHliYW55bWt0cWtqeW9wY3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzNzIxMjcsImV4cCI6MjA2Njk0ODEyN30.8bUcaM1MdjcuWoMsbqaDFoBM4YDY8p5nXfkMRNgjEz0"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json"
}
# Paleta de cores para os cards
CORES_CARD = [
    ft.Colors.BLUE_GREY_800,
    ft.Colors.TEAL_800,
    ft.Colors.BROWN_600,
    ft.Colors.INDIGO_700,
    ft.Colors.DEEP_ORANGE_800,
    ft.Colors.PURPLE_800,
]


def main(page: ft.Page):
    page.title = "Campânulas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Evento para controlar a thread ativa
    active_thread_stop_event = threading.Event()

    def carregar_dados():
        if os.path.exists(CAMINHO_ARQUIVO):
            try:
                with open(CAMINHO_ARQUIVO, "r", encoding='utf-8') as arq:
                    return json.load(arq)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def salvar_dados(dados):
        with open(CAMINHO_ARQUIVO, "w", encoding='utf-8') as arq:
            json.dump(dados, arq, indent=4, ensure_ascii=False)

    def mostrar_tela(tela_factory):
        active_thread_stop_event.set()
        active_thread_stop_event.clear()

        nova_tela = tela_factory()
        page.controls.clear()
        page.floating_action_button = getattr(nova_tela, 'fab', None)
        page.add(nova_tela)
        page.update()

    def tela_principal():
        campanulas = carregar_dados()
        card_refs: Dict[str, Dict[str, ft.Ref]] = {}
        row_cards_ref = ft.Ref[ft.Row]()

        def criar_card_campanula(campanula: dict, cor: str):
            codigo = campanula.get("codigo")
            ref_temp = ft.Ref[ft.Text]()
            ref_luz = ft.Ref[ft.Text]()
            ref_umidade = ft.Ref[ft.Text]()

            card_refs[codigo] = {"temp": ref_temp, "luz": ref_luz, "umidade": ref_umidade}

            card_visual = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(campanula.get("nome", "Sem Nome"), size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Cód: {codigo}", size=12, color=ft.Colors.WHITE70),
                        ft.Divider(height=10, color="transparent"),
                        ft.Row(
                            controls=[
                                ft.Text(ref=ref_temp, value="--°C", size=14),
                                ft.Text(ref=ref_luz, value="--%", size=14),
                                ft.Text(ref=ref_umidade, value="--%", size=14),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND
                        )
                    ], spacing=5),
                    width=200,
                    padding=15,
                    bgcolor=cor,
                    border_radius=ft.border_radius.all(10),
                ),
                elevation=4
            )

            return ft.Container(
                content=card_visual,
                on_click=lambda e, c=campanula: mostrar_tela(lambda: tela_detalhes(c)),
                border_radius=ft.border_radius.all(10)
            )

        def scroll_cards(delta: int):
            if row_cards_ref.current:
                row_cards_ref.current.scroll_to(offset=row_cards_ref.current.scroll_offset + delta, duration=300)

        def atualizar_todos_os_cards():
            while not active_thread_stop_event.is_set():
                for i, camp in enumerate(campanulas):
                    if active_thread_stop_event.is_set(): break
                    codigo = camp.get("codigo")
                    try:
                        r = requests.get(f"{SUPABASE_URL}?id=eq.{codigo}", headers=SUPABASE_HEADERS, timeout=5)
                        if r.status_code == 200 and r.json():
                            dados = r.json()[0]
                            refs = card_refs.get(codigo)
                            if refs and page:
                                refs["temp"].current.value = f"{dados.get('temp_atual', '--')}°C"
                                refs["luz"].current.value = f"L: {dados.get('intensidade', '--')}%"
                                refs["umidade"].current.value = f"U: {dados.get('umidade', '--')}%"
                                page.update()
                        time.sleep(2)
                    except requests.RequestException:
                        time.sleep(5)
                time.sleep(10)

        if not campanulas:
            view = ft.Column([
                ft.Text("Nenhuma Campânula", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Clique no botão + para adicionar a sua primeira!", color=ft.Colors.WHITE70),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
        else:
            cards = [criar_card_campanula(c, CORES_CARD[i % len(CORES_CARD)]) for i, c in enumerate(campanulas)]
            row_view = ft.Row(ref=row_cards_ref, controls=cards, scroll=ft.ScrollMode.HIDDEN, expand=True)

            view = ft.Column(
                [
                    ft.Text("Suas Campânulas", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Row(
                        [
                            ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW, on_click=lambda e: row_view.scroll_to(delta=-220, duration=200), icon_color=ft.Colors.WHITE54),
                            row_view,
                            ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, on_click=lambda e: row_view.scroll_to(delta=220, duration=200), icon_color=ft.Colors.WHITE54),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
                spacing=20,
            )
            threading.Thread(target=atualizar_todos_os_cards, daemon=True).start()

        view.fab = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda _: mostrar_tela(tela_adicionar))
        return view

    def tela_detalhes(campanula: dict):
        codigo = campanula.get("codigo")
        nome_label = ft.Text(campanula.get("nome", "Sem nome"), size=24, weight=ft.FontWeight.BOLD)
        codigo_label = ft.Text(f"Código: {codigo}", color=ft.Colors.WHITE70)
        temp_label = ft.Text("Temperatura Atual: -- °C")
        luz_label = ft.Text("Intensidade da luz: -- %")
        umidade_label = ft.Text("Umidade: -- %")
        tempmax_label = ft.Text("Temp. Máxima: -- °C")
        tempmin_label = ft.Text("Temp. Mínima: -- °C")
        dias_label = ft.Text("Dia: --")
        input_min = ft.TextField(label="Definir Temp. Mínima", border_color=ft.Colors.WHITE54, width=200)
        input_max = ft.TextField(label="Definir Temp. Máxima", border_color=ft.Colors.WHITE54, width=200)
        input_dia = ft.TextField(label="Definir Dia", border_color=ft.Colors.WHITE54, width=200)
        erro_label = ft.Text("", color=ft.Colors.RED_ACCENT)

        def limpar_erro_apos_segundos(segundos=3):
            def limpar():
                erro_label.value = ""
                page.update()
            threading.Timer(segundos, limpar).start()

        def atualizar_detalhes():
            while not active_thread_stop_event.is_set():
                try:
                    r = requests.get(f"{SUPABASE_URL}?id=eq.{codigo}", headers=SUPABASE_HEADERS, timeout=5)
                    if r.status_code == 200 and r.json():
                        dados = r.json()[0]
                        if not page:
                            break
                        temp_label.value = f"Temperatura Atual: {dados.get('temp_atual', '--')} °C"
                        luz_label.value = f"Intensidade da luz: {dados.get('intensidade', '--')} %"
                        umidade_label.value = f"Umidade: {dados.get('umidade', '--')} %"
                        tempmax_label.value = f"Temp. Máxima: {dados.get('temp_max', '--')} °C"
                        tempmin_label.value = f"Temp. Mínima: {dados.get('temp_min', '--')} °C"
                        dias_label.value = f"Dia: {dados.get('dia', '--')}"
                        page.update()
                except requests.RequestException:
                    pass
                time.sleep(5)

        threading.Thread(target=atualizar_detalhes, daemon=True).start()

        def definir_temp_min(_):
            try:
                valor = float(input_min.value.strip().replace(",", "."))
            except ValueError:
                erro_label.value = "Valor mínimo inválido"
                erro_label.color = ft.Colors.RED
                page.update()
                limpar_erro_apos_segundos()
                return

            try:
                r = requests.get(f"{SUPABASE_URL}?id=eq.{codigo}", headers=SUPABASE_HEADERS, timeout=5)
                if r.status_code != 200 or not r.json():
                    raise Exception()
                temp_max = r.json()[0].get("temp_max", None)
                if temp_max is not None and isinstance(temp_max, (int, float)) and valor > temp_max:
                    erro_label.value = "Mínima não pode ser maior que a máxima"
                    erro_label.color = ft.Colors.RED
                    page.update()
                    limpar_erro_apos_segundos()
                    return
            except:
                erro_label.value = "Erro ao validar com o servidor"
                erro_label.color = ft.Colors.RED
                page.update()
                limpar_erro_apos_segundos()
                return

            r = requests.patch(
                f"{SUPABASE_URL}?id=eq.{codigo}",
                headers=SUPABASE_HEADERS,
                json={"temp_min": valor}
            )
            erro_label.value = "Temperatura mínima atualizada!" if r.status_code in (200, 204) else "Erro ao atualizar"
            erro_label.color = ft.Colors.GREEN if r.status_code in (200, 204) else ft.Colors.RED
            page.update()
            limpar_erro_apos_segundos()

        def definir_temp_max(_):
            try:
                valor = float(input_max.value.strip().replace(",", "."))
            except ValueError:
                erro_label.value = "Valor máximo inválido"
                erro_label.color = ft.Colors.RED
                page.update()
                limpar_erro_apos_segundos()
                return

            try:
                r = requests.get(f"{SUPABASE_URL}?id=eq.{codigo}", headers=SUPABASE_HEADERS, timeout=5)
                if r.status_code != 200 or not r.json():
                    raise Exception()
                temp_min = r.json()[0].get("temp_min", None)
                if temp_min is not None and isinstance(temp_min, (int, float)) and valor < temp_min:
                    erro_label.value = "Máxima não pode ser menor que a mínima"
                    erro_label.color = ft.Colors.RED
                    page.update()
                    limpar_erro_apos_segundos()
                    return
            except:
                erro_label.value = "Erro ao validar com o servidor"
                erro_label.color = ft.Colors.RED
                page.update()
                limpar_erro_apos_segundos()
                return

            r = requests.patch(
                f"{SUPABASE_URL}?id=eq.{codigo}",
                headers=SUPABASE_HEADERS,
                json={"temp_max": valor}
            )
            erro_label.value = "Temperatura máxima atualizada!" if r.status_code in (200, 204) else "Erro ao atualizar"
            erro_label.color = ft.Colors.GREEN if r.status_code in (200, 204) else ft.Colors.RED
            page.update()
            limpar_erro_apos_segundos()

        def definir_dia(_):
            try:
                valor = int(input_dia.value.strip())
                if valor < 0:
                    raise ValueError()
            except:
                erro_label.value = "Dia inválido (não pode ser negativo)"
                erro_label.color = ft.Colors.RED
                page.update()
                limpar_erro_apos_segundos()
                return

            r = requests.patch(
                f"{SUPABASE_URL}?id=eq.{codigo}",
                headers=SUPABASE_HEADERS,
                json={"dia": valor}
            )
            erro_label.value = "Dia atualizado!" if r.status_code in (200, 204) else "Erro ao atualizar"
            erro_label.color = ft.Colors.GREEN if r.status_code in (200, 204) else ft.Colors.RED
            page.update()
            limpar_erro_apos_segundos()

        def remover_campanula(_):
            dados = carregar_dados()
            dados_filtrados = [c for c in dados if c.get("codigo") != codigo]
            salvar_dados(dados_filtrados)
            mostrar_tela(tela_principal)

        return ft.Column([
            ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_tela(tela_principal),
                                  tooltip="Voltar")], alignment=ft.MainAxisAlignment.START),
            nome_label, codigo_label, ft.Divider(),
            temp_label, luz_label, umidade_label, tempmax_label, tempmin_label, dias_label,
            ft.Divider(),

            ft.Row(
                [
                    ft.Column(
                        [input_max, input_min, input_dia],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Column(
                        [
                            ft.ElevatedButton("Definir Máxima", on_click=definir_temp_max),
                            ft.ElevatedButton("Definir Mínima", on_click=definir_temp_min),
                            ft.ElevatedButton("Definir Dia", on_click=definir_dia),
                        ],
                        spacing=20,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),

            erro_label,
            ft.Divider(height=20, color="transparent"),
            ft.ElevatedButton("Remover Campânula", icon=ft.Icons.DELETE_FOREVER, on_click=remover_campanula,
                              color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700),
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def tela_adicionar():
        nome_field = ft.TextField(label="Nome da Campânula", border_color=ft.Colors.WHITE54)
        codigo_field = ft.TextField(label="Código da Campânula", border_color=ft.Colors.WHITE54)

        def adicionar_nova(_):
            nome = nome_field.value.strip()
            codigo = codigo_field.value.strip()
            if nome and codigo:
                dados = carregar_dados()
                if any(c['codigo'] == codigo for c in dados):
                    codigo_field.error_text = "Este código já está em uso!"
                    codigo_field.update()
                    return
                dados.append({"nome": nome, "codigo": codigo})
                salvar_dados(dados)
                mostrar_tela(tela_principal)

        return ft.Column([
            ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_tela(tela_principal),
                                  tooltip="Voltar")], alignment=ft.MainAxisAlignment.START),
            ft.Text("Adicionar Nova Campânula", size=24, weight=ft.FontWeight.BOLD),
            nome_field,
            codigo_field,
            ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=adicionar_nova)
        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
            alignment=ft.MainAxisAlignment.CENTER)

    # Inicia a aplicação
    mostrar_tela(tela_principal)


if __name__ == "__main__":
    ft.app(target=main)
