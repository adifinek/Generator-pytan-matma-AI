from flask import Flask, jsonify
from vercel import VercelMiddleware

app = Flask(__name__)
app.wsgi_app = VercelMiddleware(app.wsgi_app)  # Integracja z Vercel

@app.route('/')
def home():
    return jsonify({"message": "Działa poprawnie na Vercel!"})