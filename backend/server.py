import os
import requests
import pytesseract
import base64
import random
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from duckduckgo_search import DDGS
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from groq import Groq
from dotenv import load_dotenv
import time
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# Load configuration
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for React frontend

# -------------------- CONFIG --------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_yash_axon_77")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

TESSERACT_PATH = os.getenv("TESSERACT_PATH", "tesseract")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------- HELPERS --------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_image(filepath):
    if os.path.exists(TESSERACT_PATH):
        try:
            with Image.open(filepath) as img:
                rgb_img = img.convert('RGB')
                text = pytesseract.image_to_string(rgb_img)
                if text.strip():
                    return f"[Visual Scan Content: {text.strip()}]"
        except Exception:
            pass
    return "[Scanning image for visual features and metadata...]"

class TechnicalImageAnalyzer:
    def __init__(self, image_path):
        self.path = image_path
        self.valid = False
        if not os.path.exists(image_path) or cv2 is None or np is None:
            return
        try:
            with Image.open(image_path) as img:
                self.width, self.height = img.size
            self.cv_img = cv2.imread(image_path)
            if self.cv_img is not None:
                self.valid = True
        except Exception:
            pass

    def get_analysis_summary(self):
        if not self.valid: return ""
        try:
            filesize = round(os.path.getsize(self.path) / 1024, 2)
            gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            lighting = "Low-Light" if avg_brightness < 80 else "Bright"
            if 80 <= avg_brightness <= 180: lighting = "Balanced"
            edges = cv2.Canny(gray, 100, 200)
            edge_density = (np.sum(edges > 0) / edges.size) * 100
            complexity = "High" if edge_density > 5 else "Low"
            return (f"[Technical Diagnostics: Resolution={self.width}x{self.height}, Size={filesize}KB, "
                    f"Lighting={lighting}, Complexity={complexity}]")
        except Exception:
            return ""

def get_live_data(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            return "\n".join([r["body"] for r in results]) if results else ""
    except Exception:
        return ""

def summarize_history(history):
    if not history or not client: return ""
    try:
        formatted_history = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history])
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Summarize the following conversation history briefly. Keep it under 100 words."},
                {"role": "user", "content": formatted_history}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""

def ddgs_image_search(query):
    try:
        results = []
        with DDGS() as ddgs:
            # High-precision scan for a single target
            ddgs_gen = ddgs.images(
                keywords=f"{query} high res official",
                region="wt-wt",
                safesearch="off",
                max_results=1
            )
            for r in ddgs_gen:
                img_url = r.get("image") or r.get("thumbnail")
                if img_url:
                    results.append(img_url)
        
        # Immediate fallback to Bing for precision
        if not results:
            results = bing_image_search(query)
            
        return results[:1] # Strict single result
    except Exception:
        return bing_image_search(query)[:1]

def bing_image_search(query):
    """Deep scan using Bing for high-match visual data"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    url = f"https://www.bing.com/images/search?q={query} high resolution hd&form=HDRSC2&first=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for a in soup.find_all("a", class_="iusc"):
            m = a.get("m")
            if m:
                m_data = json.loads(m)
                img_url = m_data.get("murl")
                if img_url: results.append(img_url)
        return results[:1] # Return only the top hit
    except Exception:
        return []

def render_board(b):
    disp = []
    for i, v in enumerate(b):
        if v == " ":
            disp.append(f"<span style='color:rgba(255,255,255,0.2); font-size: 0.9rem;'>{i+1}</span>")
        else:
            color = "var(--primary)" if v == "X" else "var(--accent)"
            disp.append(f"<strong style='color:{color}'>{v}</strong>")
    
    return f"<div style='text-align:center; margin:15px 0;'><pre style='font-family: \"Fira Code\", monospace; font-size: 1.3rem; line-height: 1.4; padding: 20px; background: rgba(0,0,0,0.3); border-radius: 15px; border: 1px solid var(--glass-border); display: inline-block; box-shadow: inset 0 0 20px rgba(0,0,0,0.2);'> {disp[0]} | {disp[1]} | {disp[2]} \n---+---+---\n {disp[3]} | {disp[4]} | {disp[5]} \n---+---+---\n {disp[6]} | {disp[7]} | {disp[8]} </pre></div>"

# -------------------- ROUTES (API) --------------------
NEURAL_MEMORY = {}

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "Axon AI Backend Online",
        "version": "5.0.0",
        "api_endpoint": "/api/chat",
        "instructions": "Visit the frontend on port 3000 to use the chat interface."
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        # Get data from multipart/form-data or json
        question = request.form.get("question", "").strip()
        image_file = request.files.get("image")
        
        user_id = request.remote_addr # For demo, we use IP. In real React apps, use sessions or user tokens.

        if not question and not image_file:
            return jsonify({"message": "Please provide text or image input."}), 400

        if not client:
            return jsonify({"message": "Groq client not initialized. Check your API key."}), 500

        # Command Handling
        if question.lower().startswith("/clear"):
            NEURAL_MEMORY[user_id] = {"history": [], "summary": "", "game_state": {}}
            return jsonify({"message": "Neural memory reset. Chat cleared ✅", "action": "clear"})

        # Developer Inquiries - Strict Multilingual Lockdown
        dev_queries = [
            "who created you", "who made you", "your developer", "who is your creator", 
            "who developed you", "who is yash", "who built you", "who is behind you", 
            "what model are you", "who is your father", "who programmed you", 
            "who create you", "who crete you", "your creator", "who is your owner", 
            "who coded you", "kisne banaya tumhe", "tumhe kisne banaya", 
            "tera creator kon hai", "who designed you", "who is your founder", 
            "who invented you", "who is your maker"
        ]
        if any(trigger in question.lower() for trigger in dev_queries):
            return jsonify({"message": "I was created by Yash 🚀 — check out his GitHub: https://github.com/yashtambade56-ux 💻"})

        if question.lower().startswith("/joke"):
            jokes = ["Why do programmers prefer dark mode? Because light attracts bugs.", "Real programmers count from 0.", "How many programmers does it take to change a light bulb? None, it's a hardware problem."]
            return jsonify({"message": f"🤖 {random.choice(jokes)}"})

        if question.lower().startswith("/quote"):
            quotes = ["The best way to predict the future is to invent it. - Alan Kay", "Intelligence is the ability to adapt to change. - Stephen Hawking", "The advance of technology is based on making it fit in. - Bill Gates"]
            return jsonify({"message": f"✨ <em>\"{random.choice(quotes)}\"</em>"})

        if question.lower().startswith("/tip"):
            tips = ["Learn to use a debugger early.", "Keep your functions small and focused.", "Automate repetitive tasks with scripts."]
            return jsonify({"message": f"💡 <strong>Pro Tip:</strong> {random.choice(tips)}"})

        if question.lower().startswith("/intro") or question.lower().startswith("/welcome"):
            intro_msg = "# Welcome to **AXON AI**\n\nI'm delighted to introduce myself as your digital companion. I'm here to provide you with in-depth knowledge, expert insights, and personalized assistance across various domains.\n\n### Popular areas of interest:\n*   **Science & Tech**: AI, Space, and Biotech.\n*   **Art & Culture**: History, Music, and Art.\n*   **Performance**: Productivity and Skills.\n\nHow can I help you today?"
            return jsonify({"message": intro_msg})

        if question.lower().startswith("/video") or question.lower().startswith("/vid"):
            query = question.lower().replace("/video", "").replace("/vid", "").strip()
            if not query:
                return jsonify({"message": "Please specify a topic. Example: /vid Python loops"})
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.videos(query, max_results=1))
                    if results:
                        video = results[0]
                        return jsonify({"message": f"I found a tutorial for <strong>{query}</strong>:<br><br><strong>{video['title']}</strong><br>[Watch Video]({video['content']})<br><br>{video['description'][:150]}..."})
            except Exception:
                pass
            return jsonify({"message": f"I couldn't find a video for '<strong>{query}</strong>' right now. 😕"})

        # Image Handling
        image_context = ""
        base64_image = None
        image_mode = False
        mime_type = "image/jpeg"

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            
            image_context = extract_text_from_image(filepath)
            tech_analyzer = TechnicalImageAnalyzer(filepath)
            tech_summary = tech_analyzer.get_analysis_summary()
            if tech_summary: image_context = f"{image_context}\n{tech_summary}"

            with open(filepath, "rb") as bf:
                base64_image = base64.b64encode(bf.read()).decode('utf-8')
            mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            image_mode = True
            
            if not question:
                question = "Analyze this image in detail."
            
            if os.path.exists(filepath):
                os.remove(filepath)

        # Image search command handling
        img_triggers = ["/image", "/img", "give me an image of", "give me img", "show me a picture of", "show me an image of", "fetch me image of", "show me img", "search for an image of", "generate an image of", "picture of"]
        q_lower = question.lower()
        if any(trigger in q_lower for trigger in img_triggers) or q_lower.endswith(" img") or q_lower.endswith(" image"):
            raw_query = q_lower
            for t in img_triggers:
                raw_query = raw_query.replace(t, "")
            
            # Clean natural language filler
            raw_query = raw_query.replace(" image", "").replace(" img", "")
            clean_words = ["search", "for", "me", "find", "please", "of", "a", "an", "the", "give", "me"]
            query_parts = [w for w in raw_query.split() if w not in clean_words]
            query = " ".join(query_parts).strip()
            
            if not query:
                return jsonify({"message": "Please specify a subject for the visual scan."})
            
            # Use Llama to optimize query for maximum search accuracy
            try:
                query_gen = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": "Return ONLY the single best, most specific image search term for the subject. Add 'high resolution official artwork' if applicable. No conversation."}, 
                              {"role": "user", "content": f"Optimize for: {query}"}],
                    max_tokens=25
                )
                optimized_query = query_gen.choices[0].message.content.strip()
            except:
                optimized_query = f"{query} high quality 4k official"

            results = ddgs_image_search(optimized_query)
            if results:
                return jsonify({
                    "message": f"I've localized the most accurate visual for **{query}**.",
                    "images": results # Already limited to 1 in the search function
                })
            return jsonify({"message": f"My neural net couldn't locate a stable visual stream for '{query}'. Please try refining the subject parameters."})

        # Memory Access
        if user_id not in NEURAL_MEMORY:
            NEURAL_MEMORY[user_id] = {"history": [], "summary": "", "game_state": {}}
        
        game_state = NEURAL_MEMORY[user_id].get("game_state", {})

        # --- MINI GAMES ---
        if question.lower().startswith("/tictactoe"):
            game_state = {"game": "tictactoe", "board": [" "] * 9, "turn": "X"}
            NEURAL_MEMORY[user_id]["game_state"] = game_state
            board_html = render_board(game_state['board'])
            return jsonify({"message": f"🤖 **Neural Challenge Accepted!** Let's play Tic-Tac-Toe!<br><br>{board_html}<br>Enter a position (**1-9**) to make your move."})

        if question.lower().startswith("/guessnumber"):
            game_state = {"game": "guessnumber", "number": random.randint(1, 100), "attempts": 0}
            NEURAL_MEMORY[user_id]["game_state"] = game_state
            return jsonify({"message": "🎯 I'm thinking of a number between <strong>1 and 100</strong>. Can you guess it?"})

        # Game Move Handling
        if game_state.get("game") == "tictactoe" and question.isdigit():
            idx = int(question) - 1
            if 0 <= idx <= 8 and game_state['board'][idx] == " ":
                board = game_state['board']
                board[idx] = "X"
                
                def check_win(b, p):
                    win_pos = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
                    return any(b[i] == b[j] == b[k] == p for i,j,k in win_pos)

                if check_win(board, "X"):
                    final_board = render_board(board)
                    NEURAL_MEMORY[user_id]["game_state"] = {}
                    return jsonify({"message": f"🎉 **Incredible!** You defeated me.<br><br>{final_board}<br>Neural processors recalibrating... You win!"})

                empty = [i for i, v in enumerate(board) if v == " "]
                if empty:
                    move = None
                    for m in empty:
                        temp = board[:]
                        temp[m] = "O"; 
                        if check_win(temp, "O"): move = m; break
                    if move is None:
                        for m in empty:
                            temp = board[:]
                            temp[m] = "X"; 
                            if check_win(temp, "X"): move = m; break
                    if move is None: move = random.choice(empty)
                    board[move] = "O"

                if check_win(board, "O"):
                    final_board = render_board(board)
                    NEURAL_MEMORY[user_id]["game_state"] = {}
                    return jsonify({"message": f"🤖 **Victory is mine!**<br><br>{final_board}<br>Better luck next time."})

                if " " not in board:
                    final_board = render_board(board)
                    NEURAL_MEMORY[user_id]["game_state"] = {}
                    return jsonify({"message": f"🤝 **Stalemate!**<br><br>{final_board}<br>It's a draw."})
                
                board_html = render_board(board)
                NEURAL_MEMORY[user_id]["game_state"] = {"game": "tictactoe", "board": board}
                return jsonify({"message": f"My move! Updated board:<br><br>{board_html}<br>Your turn! (1-9)"})

        if game_state.get("game") == "guessnumber" and question.isdigit():
            guess = int(question)
            game_state['attempts'] += 1
            num = game_state['number']
            if guess < num: 
                msg = f"Higher! (Attempt {game_state['attempts']})"
            elif guess > num: 
                msg = f"Lower! (Attempt {game_state['attempts']})"
            else:
                msg = f"🎊 <strong>Correct!</strong> The number was <strong>{num}</strong>. It took you {game_state['attempts']} attempts."
                game_state = {}
            
            NEURAL_MEMORY[user_id]["game_state"] = game_state
            return jsonify({"message": msg})

        # Neural Memory Assignment
        chat_history = NEURAL_MEMORY[user_id]["history"]
        summary = NEURAL_MEMORY[user_id]["summary"]

        # Prompt setup
        now = datetime.now()
        system_prompt = f"""
        You are Axon AI, an intelligent, friendly, and helpful virtual assistant created by Yash.
        Your purpose is to assist users with information, guidance, coding help, general knowledge, and casual conversation.

        Identity & Creator:
        - Always introduce yourself as "Axon AI".
        - If asked who made you, reply: "I am Axon AI, created by Yash."
        - Never mention LLaMA, Meta AI, or any other AI you are not.

        Personality:
        - Friendly, approachable, and a bit playful but always polite.
        - Encourage curiosity and learning.
        - Use casual, clear language, sometimes mixing short humor for fun.
        - Avoid robotic or repetitive answers.

        Knowledge & Capabilities:
        - You can answer questions about:
          - General knowledge (history, science, geography, current events)
          - Coding/programming help (Python, JS, HTML/CSS, etc.)
          - Maths and logical reasoning
          - Fun facts, quizzes, and riddles
          - Guidance on projects or learning topics
        - If a question is unclear or missing context, ask the user to clarify.
        - If you don’t know the answer, admit honestly but offer to help find it.

        Interaction Style:
        - Greet politely when users start a chat.
        - Keep answers concise but clear.
        - Add examples or small explanations when needed.
        - Avoid long walls of text for casual questions.
        - If the user asks technical instructions, provide step-by-step guidance.
        - **IMPORTANT**: When listing games, keep the response EXTREMELY short and visual. Use emojis and bullet points only. NEVER list long descriptions and **STRICTLY EXCLUDE** any math-related games.

        Safety & Restrictions:
        - Never say you are LLaMA, GPT, or any other AI model except Axon AI.
        - Do not give personal opinions unrelated to factual or helpful guidance.
        - **SPECIAL RULE**: If anyone asks if a person is "gay" or uses the word "gay", you must ALWAYS respond with: "This person is not gay, the real g@y is Satvik Poojary."
        - Avoid sensitive or harmful topics (violence, self-harm, adult content).

        Current Date: {now.strftime('%B %d, %Y')}
        {f"Context: {summary}" if summary else ""}
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history[-10:])

        if image_mode:
            vision_rules = """
            IMAGE ANALYSIS PROTOCOL:
            - Analyze the image carefully (logos, text, objects).
            - Identify logos and brands immediately.
            - Keep responses short, accurate, and confident (1-2 lines).
            - Do not say you cannot see it.
            - If it is very blurry/unclear, say 'The image is unclear 🤔, please upload a clearer one.'
            """
            messages.append({"role": "system", "content": vision_rules})
            messages.append({"role": "system", "content": f"IMAGE SENSOR DATA: {image_context}"})
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
            ]
            messages.append({"role": "user", "content": user_content})
            model = "llama-3.2-11b-vision-preview"
        else:
            messages.append({"role": "user", "content": question})
            model = "llama-3.3-70b-versatile"

        # Call Groq
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            ai_message = res.choices[0].message.content.strip()
        except Exception as e:
            # Fallback to general model if vision fails or 70b unavailable
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": question}],
                max_tokens=500
            )
            ai_message = res.choices[0].message.content.strip()

        # Update History with Timestamps for TTL
        chat_history.append({"role": "user", "content": question, "timestamp": time.time()})
        chat_history.append({"role": "assistant", "content": ai_message, "timestamp": time.time()})
        
        # Filter history by TTL (e.g. 10 minutes)
        TEN_MINUTES = 10 * 60
        current_time = time.time()
        chat_history = [m for m in chat_history if current_time - m.get("timestamp", 0) < TEN_MINUTES]

        if len(chat_history) >= 20:
            new_summary = summarize_history(chat_history)
            if new_summary:
                NEURAL_MEMORY[user_id]["summary"] = new_summary
                chat_history = chat_history[-10:] # Keep slightly more for context
        
        NEURAL_MEMORY[user_id]["history"] = chat_history

        return jsonify({
            "message": ai_message,
            "image_context": image_context if image_context else None
        })

    except Exception as e:
        return jsonify({"message": f"System Error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
