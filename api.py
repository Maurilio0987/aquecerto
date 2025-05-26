from flask import Flask, jsonify, request
from datetime import datetime
import json
import os
import random


app = Flask(__name__)


@app.route("/")
def home():
	return jsonify({"status": "ok",
					"message": "online"})


@app.route("/kivy/<code>")
def kivy(code):
	if not os.path.exists(f"{code}.json"):
		return jsonify({"status": "error",
						"message": "file not found"}), 404

	with open(f"{code}.json", "r") as file:
		data = json.load(file)
		return jsonify({"status": "ok", 
					   f"{code}": data})


	#return jsonify({f"{code}": {"temperature": random.randint(25, 40),
	#					        "brightness": random.randint(0, 100)}})


@app.route("/esp32", methods=["POST"])
def esp32():
	data = request.json
	
	code = str(dados.get("code"))
	temperature = str(dados.get("temperature"))
	brightness = str(dados.get("brightness"))

	with open(f"{code}.json", "w") as file:
		json.dump({
			"time": str(datetime.now()),
			"temperature": temperature,
			"brightness": brightness
			}, file)





app.run(debug=True, port="13999")

