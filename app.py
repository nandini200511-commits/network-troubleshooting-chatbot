from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "secret123"

bcrypt = Bcrypt(app)

# ---------------- MONGODB CONNECTION ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["chatbotDB"]

users = db["users"]
dataset = db["troubleshooting_data"]
chat_history = db["chat_history"]

# ---------------- STOPWORDS ----------------
stopwords = [
"is","the","a","an","my","to","of","and","in","on","for",
"i","am","are","was","were","be","been","being","it","this"
]

# ---------------- COMMAND SUGGESTIONS ----------------
commands = {
    "Physical": "Check cables and hardware connections.",
    "Data Link": "Try resetting network adapter.",
    "Network": "Try command: ping google.com",
    "Transport": "Check open ports using netstat.",
    "Session": "Try reconnecting the session or VPN.",
    "Presentation": "Check SSL/TLS certificates.",
    "Application": "Use nslookup to check DNS resolution."
}

# ---------------- LOGIN PAGE ----------------
@app.route("/")
def login():
    return render_template("login.html")

# ---------------- REGISTER PAGE ----------------
@app.route("/register")
def register():
    return render_template("register.html")

# ---------------- REGISTER USER ----------------
@app.route("/register_user", methods=["POST"])
def register_user():

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    users.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password
    })

    return redirect(url_for("login"))

# ---------------- LOGIN USER ----------------
@app.route("/login_user", methods=["POST"])
def login_user():

    email = request.form["email"]
    password = request.form["password"]

    user = users.find_one({"email": email})

    if user and bcrypt.check_password_hash(user["password"], password):
        session["user"] = user["username"]
        return redirect(url_for("chatbot"))

    return "Invalid login credentials"

# ---------------- CHATBOT PAGE ----------------
@app.route("/chatbot")
def chatbot():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("chatbot.html")

# ---------------- CHATBOT LOGIC ----------------
def get_response(user_input):

    words = user_input.lower().split()
    words = [word for word in words if word not in stopwords]

    problems = dataset.find()

    best_match = None
    best_score = 0

    for problem in problems:

        keywords = problem["keywords"]

        score = 0

        for word in words:
            if word in keywords:
                score += 1

        if score > best_score:
            best_score = score
            best_match = problem

    if best_match:

        layer = best_match.get("layer", "Unknown")
        solution = best_match.get("solution", "No solution available")
        command = commands.get(layer, "")

        return {
            "solution": solution,
            "layer": layer,
            "command": command
        }

    return {
        "solution": "Sorry, I could not understand your network problem.",
        "layer": "Unknown",
        "command": ""
    }

# ---------------- CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():

    user_message = request.json["message"]

    result = get_response(user_message)

    # Save chat history
    chat_history.insert_one({
        "user": session.get("user"),
        "query": user_message,
        "layer": result["layer"],
        "response": result["solution"]
    })

    return jsonify(result)

# ---------------- HISTORY PAGE ----------------
@app.route("/history")
def history():

    if "user" not in session:
        return redirect(url_for("login"))

    history_data = chat_history.find({"user": session["user"]})

    return render_template("history.html", history=history_data)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)