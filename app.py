from flask import Flask, render_template, request, jsonify
import random
# from core_logic import AnkiGenerator # Assuming this is your main class/function

app = Flask(__name__,
            template_folder="app/templates",
            static_folder="app/static")


# Home page, includes profiles, settings, and navigation to other sections 
@app.route('/')
def index():
    return render_template('login.html') 

# For HTML generation testing, to be removed later
random_words = [
    "Ephemeral", "Komorebi", "Fernweh", "Taciturno", "Bibliothèque",
    "Sempiternal", "Saudade", "Schadenfreude", "Murciélago", "Tsundoku",
    "Labyrinth", "Petrichor", "Ziggurat", "Querencia", "Hiraeth",
    "Oubliette", "Waldeinsamkeit", "Mellifluous", "Ikigai", "Gula",
    "Vellichor", "Inmarcesible", "Chiaroscuro", "Kintsugi", "L’appel du vide",
    "Serendipity", "Doppelgänger", "Sobremesa", "Ukiyo", "Ethereal",
    "Flâneur", "Wanderlust", "Ataraxia", "Pamplemousse", "Nadir",
    "Cachivache", "Kenshō", "Bruma", "Sonder", "Torschlusspanik",
    "Susurrus", "Mono no aware", "Dépaysement", "Heimat", "Ojala",
    "Ineffable", "Yūgen", "Cafuné", "Gezellig", "Glück"
]

# Review page, where you view cards and mark them as known/unknown
@app.route('/card', methods=['GET'])
def generate_cards():
    selected_words = random.choice(random_words) # Simulate card generation with random words
    selected_words2 = random.choice(random_words) # Simulate card generation with random words
    # This will be the main interface for reviewing cards
    return render_template('card.html', main_text_placeholder=selected_words, back_text_placeholder=selected_words2) 

@app.route('/handle_card_response', methods=['POST'])
def handle_card_response():
    data = request.get_json()
    response = data.get('action')
    # Here you would process the user's response and update your spaced repetition algorithm
    print(f"User marked the card as: {response}")
    return jsonify({"status": "success"})

# Stats page, where you can see your progress and performance over time
@app.route('/stats', methods=['GET'])
def stats():
    return render_template('stats.html')

# Simple API endpoints
@app.route('/api/health')
def api_health():
    return jsonify({"status": "ok"})


@app.route('/api/review/next')
def api_review_next():
    return jsonify({
        "card_id": 1,
        "spanish": "hola",
        "english": "hello"
    })


@app.route('/api/review/<int:card_id>', methods=['POST'])
def api_review_grade(card_id):
    data = request.get_json()
    rating = data.get("rating", 2)

    return jsonify({
        "card_id": card_id,
        "rating": rating,
        "message": "Review saved (demo stub)",
        "next_due_days": 3
    })

if __name__ == '__main__':
    app.run(debug=True)