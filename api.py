from flask import Flask, jsonify
import random

app = Flask(__name__)

@app.route("/")
def home():
	return jsonify({"message": "online"})

@app.route("kivy/<key>")
def kivy(key):
	return jsonify({f"{key}": {"temperature": random.randint(25, 40),
				   "brightness": random.randint(0, 100)})


#app.run(debug=True)

