from flask import Flask, jsonify

app = Flask(__name__)

list1 = [
    {"name": "ravi"},
    {"name": "shankar"},
]

@app.route("/")
def home():
    return "Welcome"

@app.route("/api/data")
def data():
    return jsonify(list1)

if __name__ == "__main__":
    app.run()