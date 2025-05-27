from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.carousel import Carousel
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.button import Button
import json
import os
import requests


CAMINHO_ARQUIVO = "campanulas.json"
BASE_URL = "https://aquecerto.onrender.com/kivy/"


class TelaInicial(Screen):
    pass


class TelaCampanulas(Screen):
    evento_atualizacao = None  # Controle do Clock

    def on_pre_enter(self):
        self.ids.carousel.clear_widgets()
        self.campanulas = self.carregar_dados()
        self.caixas = []

        if self.campanulas:
            for campanula in self.campanulas:
                box = BoxLayout(orientation="vertical", padding=20, spacing=10)

                label_nome = Label(text=f"Nome: {campanula['nome']}", font_size='24sp')
                label_codigo = Label(text=f"Código: {campanula['codigo']}", font_size='24sp')
                label_temperatura = Label(text="Temperatura: --- °C", font_size='24sp')
                label_brilho = Label(text="Intensidade da luz: --- %", font_size='24sp')

                box.add_widget(label_nome)
                box.add_widget(label_codigo)
                box.add_widget(label_temperatura)
                box.add_widget(label_brilho)

                self.ids.carousel.add_widget(box)
                self.caixas.append({
                    "codigo": campanula["codigo"],
                    "label_temperatura": label_temperatura,
                    "label_brilho": label_brilho
                })

            self.evento_atualizacao = Clock.schedule_interval(self.atualizar_dados, 5)
        else:
            box = BoxLayout(orientation="vertical", padding=20, spacing=10)
            box.add_widget(Label(text="Nenhuma campânula cadastrada.", font_size='24sp'))
            self.ids.carousel.add_widget(box)

    def on_leave(self):
        if self.evento_atualizacao:
            self.evento_atualizacao.cancel()
            self.evento_atualizacao = None

    def atualizar_dados(self, dt):
        for campanula in self.caixas:
            codigo = campanula["codigo"]
            try:
                resposta = requests.get(BASE_URL + codigo, timeout=5)
                if resposta.status_code == 200:
                    dados_api = resposta.json()[codigo]
                    temperatura = dados_api["temperature"]
                    brilho = dados_api["brightness"]
                else:
                    temperatura = '---'
                    brilho = '---'
            except:
                temperatura = '---'
                brilho = '---'

            campanula["label_temperatura"].text = f"Temperatura: {temperatura} °C"
            campanula["label_brilho"].text = f"Intensidade da luz: {brilho} %"

    def carregar_dados(self):
        if os.path.exists(CAMINHO_ARQUIVO):
            with open(CAMINHO_ARQUIVO, "r") as arquivo:
                try:
                    return json.load(arquivo)
                except:
                    return []
        return []


class TelaAdicionarCampanula(Screen):
    def adicionar_campanula(self):
        nome = self.ids.input_nome.text.strip()
        codigo = self.ids.input_codigo.text.strip()

        if nome and codigo:
            dados = self.carregar_dados()

            dados.append({"nome": nome, "codigo": codigo})
            self.salvar_dados(dados)

            self.ids.input_nome.text = ""
            self.ids.input_codigo.text = ""

            self.manager.current = "tela_inicial"

    def carregar_dados(self):
        if os.path.exists(CAMINHO_ARQUIVO):
            with open(CAMINHO_ARQUIVO, "r") as arquivo:
                try:
                    return json.load(arquivo)
                except:
                    return []
        return []

    def salvar_dados(self, dados):
        with open(CAMINHO_ARQUIVO, "w") as arquivo:
            json.dump(dados, arquivo, indent=4)


class TelaRemoverCampanula(Screen):
    def on_pre_enter(self):
        self.atualizar_lista()

    def atualizar_lista(self):
        self.ids.box_lista.clear_widgets()
        campanulas = self.carregar_dados()

        if campanulas:
            for campanula in campanulas:
                linha = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

                label = Label(
                    text=f"{campanula['nome']} ({campanula['codigo']})",
                    size_hint_x=0.7,
                    halign="left",
                    valign="middle"
                )
                label.bind(size=label.setter('text_size'))

                botao = Button(
                    text="Remover",
                    size_hint_x=0.3,
                    on_press=lambda instance, c=campanula: self.remover(c)
                )

                linha.add_widget(label)
                linha.add_widget(botao)

                self.ids.box_lista.add_widget(linha)
        else:
            self.ids.box_lista.add_widget(Label(text="\n\nNenhuma campânula cadastrada."))

    def remover(self, campanula):
        dados = self.carregar_dados()
        dados = [c for c in dados if c != campanula]
        self.salvar_dados(dados)
        self.atualizar_lista()

    def carregar_dados(self):
        if os.path.exists(CAMINHO_ARQUIVO):
            with open(CAMINHO_ARQUIVO, "r") as arquivo:
                try:
                    return json.load(arquivo)
                except:
                    return []
        return []

    def salvar_dados(self, dados):
        with open(CAMINHO_ARQUIVO, "w") as arquivo:
            json.dump(dados, arquivo, indent=4)


class GerenciadorTelas(ScreenManager):
    pass


class MeuApp(App):
    def build(self):
        gui = Builder.load_file("gui.kv")
        gui.transition = NoTransition()
        return gui


MeuApp().run()
