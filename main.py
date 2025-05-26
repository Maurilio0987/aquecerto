from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock

import requests


BASE_URL = "https://aquecerto.onrender.com/kivy/"


gui = Builder.load_file("gui.kv")


class MyApp(App):
	def build(self):
		return gui


	def on_start(self):
		Clock.schedule_interval(lambda dt: self.api(dt=dt, key="abc123"), 5)


	def api(self, dt, key):
		response = requests.get(BASE_URL + key).json()
		data = response[key]
		self.root.ids["temperature"].text = "Temperatura: " + str(data["temperature"]) + " °C"
		self.root.ids["brightness"].text = "Intensidade da luz: " + str(data["brightness"]) + " %"


MyApp().run()