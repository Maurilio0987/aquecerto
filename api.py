
from flask import Flask, jsonify, request
from datetime import datetime
import json
import os
import random

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "online"
    })


# ================================
# 📲 Rota para o app obter dados de temperatura e brilho
# ================================
@app.route("/app/<code>")
def app_get_data(code):
    caminho = f"{code}.json"

    if not os.path.exists(caminho):
        return jsonify({
            code: {
                "temperature": random.randint(25, 40),
                "brightness": random.randint(0, 100),
                "max": random.randint(25, 40),
                "min": random.randint(25, 40)
            }
        })
        
		#return jsonify({"status": "error",
		#				"message": "file not found"}), 404

    with open(caminho, "r") as file:
        data = json.load(file)
        return jsonify({
            "status": "ok",
            code: data
        })


# ================================
# 📤 Rota para o ESP32 enviar dados de temperatura e brilho
# ================================
@app.route("/esp32", methods=["POST"])
def esp32_post_data():
    dados = request.json

    code = str(dados.get("code"))
    temperature = str(dados.get("temperature"))
    brightness = str(dados.get("brightness"))

    with open(f"{code}.json", "w") as file:
        json.dump({
            "time": str(datetime.now()),
            "temperature": temperature,
            "brightness": brightness
        }, file)

    return jsonify({"status": "saved", "code": code})


# ================================
# 📥 Rota para obter configuração min/max/dias
# ================================
@app.route("esp32/config/<code>")
def get_config(code):
    caminho = f"config_{code}.json"

    if not os.path.exists(caminho):
        # Valores padrão
        config = {
            "min": 31,
            "max": 33,
            "dias": 0
        }
        return jsonify({"status": "default", code: config})

    with open(caminho, "r") as file:
        data = json.load(file)
        return jsonify({"status": "ok", code: data})


# ================================
# 📝 Rota para salvar nova configuração min/max/dias
# ================================
@app.route("app/config/<code>", methods=["POST"])
def set_config(code):
    data = request.json
    caminho = f"config_{code}.json"

    config = {
        "min": float(data.get("min", 31)),
        "max": float(data.get("max", 33)),
        "dias": int(data.get("dias", 0))
    }

    with open(caminho, "w") as file:
        json.dump(config, file)

    return jsonify({"status": "saved", code: config})


# ================================
# 🚀 Inicialização
# ================================
#if __name__ == "__main__":
#    app.run(debug=True, port=5000)

