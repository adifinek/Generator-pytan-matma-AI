from flask import Flask, request, jsonify, session
import openai
import re
import sympy as sp
import random

app = Flask(__name__)
app.secret_key = 'tajny_klucz'

# Ustaw swój klucz OpenAI – najlepiej przez zmienną środowiskową
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4"


# ----------------- FUNKCJE POMOCNICZE -----------------

def simplify_expression(expr):
    """
    Upraszcza wyrażenie i zwraca wynik w formacie ułamka "licznik/mianownik".
    Jeśli wynik to nieskończoność, zwraca "oo" lub "-oo".
    """
    simplified = sp.nsimplify(expr)
    if simplified == sp.oo:
        return "oo"
    elif simplified == -sp.oo:
        return "-oo"
    elif simplified.is_Rational:
        return f"{simplified.p}/{simplified.q}"
    else:
        return str(simplified)

def parse_and_compute_limit(question: str) -> str:
    """
    Oblicza granicę funkcji na podstawie pytania, stosując faktoryzację i regułę de l’Hôpitala.
    """
    # Szukaj punktu granicznego
    match_limit_point = re.search(r"x\s*(?:dąży\s*do|->)\s*(-?\d+(?:[.,]\d+)?)", question)
    if not match_limit_point:
        return "Nie istnieje"
    limit_point = float(match_limit_point.group(1).replace(',', '.'))

    # Szukaj definicji f(x)
    match_expr = re.search(r"f\(x\)\s*=\s*(.+?)(?:\s+gdy\s+x\s*(?:dąży\s+do|->)|$)", question, re.IGNORECASE)
    expr_str = match_expr.group(1).strip() if match_expr else None

    if not expr_str:
        return "Nie istnieje"

    # Poprawki wyrażenia
    expr_str = expr_str.replace('^', '**')
    expr_str = re.sub(r'(\d)([a-zA-Z(])', r'\1*\2', expr_str)

    # Sympyfikacja
    x = sp.Symbol('x', real=True)
    try:
        f_expr = sp.sympify(expr_str, {"x": x, "sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log})
    except Exception:
        return "Nie istnieje"

    def compute_limit_with_fixes(expr):
        try:
            L = sp.limit(expr, x, limit_point)
        except:
            L = None

        if L is None or L is sp.nan:
            try:
                expr_fact = sp.factor(expr)
                L = sp.limit(expr_fact, x, limit_point)
            except:
                pass

        if (L is None or L is sp.nan) and expr.is_rational_function(x):
            num, den = sp.fraction(expr)
            try:
                if sp.limit(num, x, limit_point) == 0 and sp.limit(den, x, limit_point) == 0:
                    new_expr = sp.diff(num, x) / sp.diff(den, x)
                    L = sp.limit(new_expr, x, limit_point)
            except:
                pass
        return L

    limit_value = compute_limit_with_fixes(f_expr)

    if limit_value is None or limit_value is sp.nan:
        return "Nie istnieje"
    else:
        return simplify_expression(limit_value)

def generuj_pytanie_gpt() -> str:
    """
    Generuje pytanie o granicę funkcji za pomocą GPT.
    """
    system_msg = {
        "role": "system",
        "content": (
            "Jesteś asystentem matematycznym specjalizującym się wyłącznie w granicach funkcji. "
            "Wygeneruj jedno pytanie dotyczące granicy funkcji, "
            "w formacie: 'Oblicz granicę funkcji f(x) = <wyrażenie> gdy x dąży do <punkt>.'"
        )
    }
    user_msg = {"role": "user", "content": "Wygeneruj jedno pytanie dotyczące granicy funkcji."}
    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[system_msg, user_msg],
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "Oblicz granicę funkcji f(x) = (x**2 - 1)/(x - 1) gdy x dąży do 1."

def losuj_pytanie(pytania_uzyte) -> dict:
    max_attempts = 10
    for _ in range(max_attempts):
        txt = generuj_pytanie_gpt()
        if txt not in pytania_uzyte:
            ans = parse_and_compute_limit(txt)
            return {"question": txt, "answer": ans}
    return {"question": "Oblicz granicę funkcji f(x) = (x**2 - 1)/(x - 1) gdy x dąży do 1.", "answer": parse_and_compute_limit("(x**2 - 1)/(x - 1)")}

# ----------------- FLASK ROUTES -----------------

@app.route('/')
def home():
    session['score'] = 0
    session['pytania_uzyte'] = []
    return '''
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Perfekcyjny kalkulator granic funkcji</title>
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                background: url('static/bg.jpg') no-repeat center center fixed;
                background-size: cover;
                margin: 0;
                padding: 0;
                color: white;
            }
            header {
                background-color: rgba(0, 0, 0, 0.85);
                width: 100%;
                padding: 15px 0;
                position: fixed;
                top: 0;
                left: 0;
                z-index: 100;
                text-align: center;
            }
            .container {
                max-width: 1000px;
                background: rgba(0, 0, 0, 0.8);
                padding: 40px 30px;
                margin: 120px auto 80px auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.7);
                border-radius: 8px;
                text-align: center;
            }
            h2 {
                font-size: 2rem;
                margin-bottom: 25px;
            }
            input[type="text"] {
                width: calc(100% - 40px);
                padding: 12px;
                margin: 15px auto;
                border: 1px solid #ccc;
                border-radius: 4px;
                color: black;
                font-size: 1.1rem;
                display: block;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 1.1rem;
                transition: background-color 0.3s;
                margin: 15px auto;
                display: block;
            }
            button:hover {
                background-color: #45a049;
            }
            h3 {
                font-size: 1.2rem;
                margin: 15px 0;
            }
            .result {
                padding: 15px;
                margin-top: 20px;
                font-size: 1.2rem;
                border-radius: 6px;
                background-color: rgba(255,255,255,0.1);
            }
            footer {
                text-align: center;
                padding: 15px;
                background-color: rgba(0,0,0,0.85);
                width: 100%;
                position: fixed;
                bottom: 0;
                left: 0;
                color: white;
            }
        </style>
        <script>
            async function getQuestion() {
                let response = await fetch("/get_question", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({})
                });
                let data = await response.json();
                document.getElementById("question").innerText = data.question;
                document.getElementById("correct_answer").value = data.answer;
                document.getElementById("answer").value = "";
                document.getElementById("result").innerText = "";
            }

            async function checkAnswer() {
                let userAnswer = document.getElementById("answer").value;
                let correctAnswer = document.getElementById("correct_answer").value.trim();
                let response = await fetch("/check_answer", {
                  method: "POST",
                  headers: {"Content-Type": "application/json"},
                  body: JSON.stringify({"user_answer": userAnswer, "correct_answer": correctAnswer})
                });
                let data = await response.json();
                let resultElement = document.getElementById("result");
                if (data.correct) {
                  resultElement.innerText = "Poprawna odpowiedź!";
                  document.getElementById("score").innerText = "Punkty: " + data.score;
                } else {
                  resultElement.innerText = "Błędna odpowiedź. Poprawna odpowiedź: " + data.correct_answer;
                }
            }
        </script>
    </head>
    <body>
      <header>
          <h1>Generator zadań z granic funkcji AI</h1>
      </header>
      <div class="container">
        <h2>Granice funkcji</h2>
        <button onclick="getQuestion()">Generuj pytanie</button>
        <h3 id="question">Tutaj pojawi się pytanie</h3>
        <input type="text" id="answer" placeholder="Twoja odpowiedź">
        <p style="font-size: 0.9rem; color: lightgray; margin-top: -10px;">
            Wpisz odpowiedź w formacie ułamka, np. <b>1/2</b>, lub jeśli granica to nieskończoność, użyj <b>oo</b> (nieskończoność) lub <b>-oo</b> (minus nieskończoność).
        </p>
        <input type="hidden" id="correct_answer">
        <button onclick="checkAnswer()">Sprawdź odpowiedź</button>
        <h3 id="result"></h3>
        <h3 id="score">Punkty: 0</h3>
      </div>
      <footer>
          <p>&copy; 2025 Adam Dobek || Generator zadań z granic funkcji AI</p>
      </footer>
    </body>
    </html>
    '''

@app.route('/get_question', methods=['POST'])
def get_question():
    pytania_uzyte = session.get('pytania_uzyte', [])
    pytanie = losuj_pytanie(pytania_uzyte)
    pytania_uzyte.append(pytanie["question"])
    session['pytania_uzyte'] = pytania_uzyte
    return jsonify({"question": pytanie["question"], "answer": pytanie["answer"]})

@app.route('/check_answer', methods=['POST'])
def check():
    data = request.get_json()
    user_answer = data["user_answer"]
    correct_answer = data["correct_answer"]

    # Porównanie odpowiedzi (uwzględnia ułamki i nieskończoności)
    def compare(user, correct):
        try:
            if user.lower() == correct.lower():
                return True
            user_expr = sp.nsimplify(user)
            correct_expr = sp.nsimplify(correct)
            return sp.simplify(user_expr - correct_expr) == 0
        except:
            return False

    correct = compare(user_answer, correct_answer)
    score = session.get('score', 0)
    if correct:
        score += 1
    session['score'] = score
    return jsonify({"correct": correct, "correct_answer": correct_answer, "score": score})

if __name__ == '__main__':
    app.run(debug=True)
