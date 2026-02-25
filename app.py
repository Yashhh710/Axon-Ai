import os
import requests
import pytesseract
import base64
import random
from flask import Flask, render_template, request, jsonify, session
from duckduckgo_search import DDGS
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image

from groq import Groq
from dotenv import load_dotenv

# Load neural config from environment
load_dotenv()

app = Flask(__name__)

# -------------------- CONFIG --------------------
# Neural Link Security (Secret Key)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_yash_axon_77")

# Groq API Gateway
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Tesseract OCR Engine Path
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------- HELPERS --------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_image(filepath):
    """Extract readable text from image using OCR with graceful fallbacks"""
    # Attempt to use Tesseract if path is valid
    if os.path.exists(TESSERACT_PATH):
        try:
            with Image.open(filepath) as img:
                rgb_img = img.convert('RGB')
                text = pytesseract.image_to_string(rgb_img)
                if text.strip():
                    return f"[Visual Scan Content: {text.strip()}]"
        except Exception:
            pass

    # Fallback or Silent fail if Tesseract is missing
    return "[Scanning image for visual features and metadata...]"

def get_live_data(query):
    """Get live search data via DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            return "\n".join([r["body"] for r in results]) if results else ""
    except Exception as e:
        return f"[Live Search Error: {str(e)}]"

def summarize_history(history):
    """Summarize the conversation history to keep it compact using the Groq SDK"""
    if not history:
        return ""
    
    try:
        # Format history for summarization
        formatted_history = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history])
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Summarize the following conversation history briefly, focusing on key topics and facts mentioned. Keep it under 100 words."},
                {"role": "user", "content": formatted_history}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Summarization Error: {e}")
        return ""

def bing_image_search(query):
    """Fallback Image Search using Bing Scraper"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    url = f"https://www.bing.com/images/search?q={query}&form=HDRSC2&first=1"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        import json
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for a in soup.find_all("a", class_="iusc"):
            m = a.get("m")
            if m:
                m_data = json.loads(m)
                img_url = m_data.get("murl")
                if img_url:
                    results.append(img_url)
        return results
    except Exception as e:
        print(f"Bing Search Error: {e}")
        return []

# -------------------- ROUTES --------------------
@app.route("/")
def home():
    session['history'] = []
    session['summary'] = ""
    return render_template("index.html")

def encode_image(image_path):
    """Encode image to base64 for vision models"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@app.route("/ask", methods=["POST"])
def ask():
    try:
        question = request.form.get("question", "").strip()
        image_file = request.files.get("image")

        if not question and not image_file:
            return jsonify({"message": "Please provide text or image input."})

        # -------- AXON AI COMMANDS (HYBRID MODE) --------
        if question.lower().startswith("/clear"):
            session['history'] = []
            session['summary'] = ""
            session['game_state'] = {}
            return jsonify({"message": "Neural memory reset. Chat cleared ✅", "action": "clear"})

        if question.lower().startswith("/functions") or question.lower().startswith("/help"):
            return jsonify({"message": "<strong>Available features:</strong><br>/intro, /clear, /functions, /video [topic], /vid [topic], /joke, /quote, /tip, /image [query], /img [query], /tictactoe, /guessnumber, open [app]"})

        if question.lower().startswith("/joke"):
            jokes = ["Why do programmers prefer dark mode? Because light attracts bugs.", "Real programmers count from 0.", "How many programmers does it take to change a light bulb? None, it's a hardware problem."]
            return jsonify({"message": f"🤖 {random.choice(jokes)}"})

        if question.lower().startswith("/quote"):
            quotes = ["The best way to predict the future is to invent it. - Alan Kay", "Intelligence is the ability to adapt to change. - Stephen Hawking", "The advance of technology is based on making it fit in. - Bill Gates"]
            return jsonify({"message": f"✨ <em>\"{random.choice(quotes)}\"</em>"})

        if question.lower().startswith("/intro") or question.lower().startswith("/welcome"):
            intro_msg = """
# Welcome to **AXON AI**

I'm delighted to introduce myself as your digital companion. I'm here to provide you with in-depth knowledge, expert insights, and personalized assistance across various domains.

### Popular areas of interest:
*   **Science & Tech**: AI, Space, and Biotech.
*   **Art & Culture**: History, Music, and Art.
*   **Performance**: Productivity and Skills.

How can I help you today?
"""
            return jsonify({"message": intro_msg})

        if question.lower().startswith("/tip"):
            tips = ["Learn to use a debugger early.", "Keep your functions small and focused.", "Automate repetitive tasks with scripts."]
            return jsonify({"message": f"💡 <strong>Pro Tip:</strong> {random.choice(tips)}"})

        # -------- AXON AI BASIC REPLIES --------
        q_lower = question.lower().strip()
        if q_lower in ["hello", "hi", "hey", "hola", "greetings"]:
            welcome_msg = "Hello! I am **AXON AI**, your digital companion. How can I assist you today? 🧠✨"
            return jsonify({"message": welcome_msg})

        if q_lower in ["how are you", "how are you doing", "how's it going"]:
            return jsonify({"message": "My neural circuits are functioning at peak efficiency! Powering through trillions of operations per second to provide you with the best experience. How can I assist you today?"})

        if q_lower in ["thank you", "thanks", "thx", "appreciate it"]:
            return jsonify({"message": "You're very welcome! It's my pleasure to assist. Is there anything else you'd like to dive into?"})

        if q_lower in ["bye", "goodbye", "exit", "see ya"]:
            return jsonify({"message": "Goodbye! My systems will remain in standby until your next request. Stay curious! 🚀"})

        if question.lower().startswith("/video") or question.lower().startswith("/vid") or "show me a video for" in question.lower():
            query = question.lower().replace("/video", "").replace("/vid", "").replace("show me a video for", "").strip()
            for word in ["of ", "a ", "an "]:
                if query.startswith(word): query = query[len(word):].strip()
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

        img_triggers = ["/image", "/img", "give me an image of", "give me img", "show me a picture of", "show me an image of", "fetch me image of", "show me img", "search for an image of", "generate an image of"]
        if any(trigger in question.lower() for trigger in img_triggers):
            raw_query = question.lower()
            for trigger in img_triggers:
                raw_query = raw_query.replace(trigger, "")
            
            # Clean natural language filler
            clean_words = ["search", "for", "me", "find", "please", "of", "a", "an", "the"]
            query = " ".join([w for w in raw_query.split() if w not in clean_words]).strip()
            
            if not query:
                return jsonify({"message": "Please specify a subject for the visual scan. Example: /img Neon cyberpunk city"})
            
            try:
                # 1. Elite Neural Query Optimization (GPT-powered keywords)
                try:
                    # Try primary model
                    query_gen = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": "Return ONLY the subject and 3-4 professional keywords (e.g. 'official artwork', 'high resolution', 'pinterest') optimized for ultra-high-quality image search. No intro, no chat."}, 
                                   {"role": "user", "content": f"Optimize search keywords for: {query}"}],
                        max_tokens=40
                    )
                    optimized_query = query_gen.choices[0].message.content.strip()
                except Exception as e:
                    if "429" in str(e):
                        # Fallback to faster model
                        try:
                            query_gen = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "system", "content": "Return ONLY image search keywords for the subject."}, 
                                          {"role": "user", "content": query}],
                                max_tokens=20
                            )
                            optimized_query = query_gen.choices[0].message.content.strip()
                        except:
                            optimized_query = f"{query} high quality official artwork pinterest"
                    else:
                        optimized_query = f"{query} high quality official artwork pinterest"

                # 2. Cinematic Description Generator
                try:
                    # Try primary model
                    desc_response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": "Generate a single, cinematic, and highly descriptive sentence for an image of this subject. Focus on lighting, mood, and detail. No intro."}, 
                                  {"role": "user", "content": f"Subject: {query}"}],
                        max_tokens=80
                    )
                    description = desc_response.choices[0].message.content.strip().replace('"', "'")
                except Exception as e:
                    if "429" in str(e):
                        # Fallback to faster model
                        try:
                            desc_response = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "system", "content": "Describe this image subject in one cinematic sentence."}, 
                                          {"role": "user", "content": query}],
                                max_tokens=50
                            )
                            description = desc_response.choices[0].message.content.strip().replace('"', "'")
                        except:
                            description = f"A high-definition visual of {query}, rendered with stunning detail."
                    else:
                        description = f"A high-definition visual of {query}, rendered with stunning detail and composition."

                # 3. High-Fidelity Bing Search Execution
                best_img = None
                results = bing_image_search(optimized_query)
                
                if results:
                    # Prioritize direct links with common extensions
                    valid_exts = (".png", ".jpg", ".jpeg", ".webp")
                    for url in results:
                        if any(url.lower().endswith(ext) for ext in valid_exts):
                            best_img = url
                            break
                    
                    # Fallback to the first result if no perfect extension match
                    if not best_img:
                        best_img = results[0]

                # 4. Premium Integrated UI Output
                if best_img:
                    success_msg = (
                        f"<div style='margin:15px 0; border-radius:20px; overflow:hidden; border:1px solid var(--glass-border); box-shadow:0 15px 35px rgba(0,0,0,0.5); background:rgba(0,0,0,0.2);'>"
                        f"  <img src='{best_img}' alt='{description}' style='width:100%; height:auto; display:block;' onerror=\"this.style.display='none';\">"
                        f"  <div style='padding:15px; background:rgba(0,0,0,0.4); backdrop-filter:blur(10px); color:var(--text-main); font-size:14px; text-align:center; border-top:1px solid var(--glass-border);'>{description}</div>"
                        f"</div>"
                        f"**Neural Scan Description:** {description}"
                        f"<br><br>Optional Voice Response: Neural scan complete. I've retrieved a high-fidelity visual of {query}. {description}"
                    )
                    return jsonify({"message": success_msg})
                else:
                    return jsonify({"message": f"My neural net couldn't locate a stable visual stream for '<strong>{query}</strong>'. Please try refining the subject parameters."})

            except Exception as e:
                return jsonify({"message": f"Neural Link Error: Visual processing logic encountered interference. (ID: {str(e)[:40]}...)"})

        if question.lower().startswith("open "):
            app_name = question[5:].strip()
            return jsonify({"message": f"Opening {app_name.capitalize()}! 🛰️", "action": "open", "target": app_name})

        # --- MINI GAMES ---
        def render_board(b):
            disp = []
            for i, v in enumerate(b):
                if v == " ":
                    disp.append(f"<span style='color:rgba(255,255,255,0.2); font-size: 0.9rem;'>{i+1}</span>")
                else:
                    color = "var(--primary)" if v == "X" else "var(--accent)"
                    disp.append(f"<strong style='color:{color}'>{v}</strong>")
            
            return f"<div style='text-align:center; margin:15px 0;'><pre style='font-family: \"Fira Code\", monospace; font-size: 1.3rem; line-height: 1.4; padding: 20px; background: rgba(0,0,0,0.3); border-radius: 15px; border: 1px solid var(--glass-border); display: inline-block; box-shadow: inset 0 0 20px rgba(0,0,0,0.2);'> {disp[0]} | {disp[1]} | {disp[2]} \n---+---+---\n {disp[3]} | {disp[4]} | {disp[5]} \n---+---+---\n {disp[6]} | {disp[7]} | {disp[8]} </pre></div>"

        if question.lower() == "/tictactoe" or "play tictactoe" in question.lower():
            session['game_state'] = {"game": "tictactoe", "board": [" "] * 9, "turn": "X"}
            board_html = render_board(session['game_state']['board'])
            return jsonify({"message": f"🤖 **Neural Challenge Accepted!** Let's play Tic-Tac-Toe!<br><br>{board_html}<br>Enter a position (**1-9**) to make your move.<br><br>Optional Voice Response: Neural Challenge Accepted! Let's play Tic-Tac-Toe! It is your turn. Choose a position from 1 to 9."})

        if question.lower() == "/guessnumber" or "play guess number" in question.lower():
            session['game_state'] = {"game": "guessnumber", "number": random.randint(1, 100), "attempts": 0}
            return jsonify({"message": "🎯 I'm thinking of a number between <strong>1 and 100</strong>. Can you guess it?<br><br>Optional Voice Response: I am thinking of a number between 1 and 100. Can you guess it?"})

        game_state = session.get('game_state', {})
        if game_state.get("game") == "tictactoe" and question.isdigit():
            idx = int(question) - 1 # Convert 1-9 to 0-8
            if 0 <= idx <= 8 and game_state['board'][idx] == " ":
                board = game_state['board']
                board[idx] = "X"
                
                def check_win(b, p):
                    win_pos = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
                    return any(b[i] == b[j] == b[k] == p for i,j,k in win_pos)

                if check_win(board, "X"):
                    final_board = render_board(board)
                    session['game_state'] = {}
                    return jsonify({"message": f"🎉 **Incredible!** You defeated me.<br><br>{final_board}<br>Neural processors recalibrating... You win!<br><br>Optional Voice Response: Incredible! You defeated me. Neural processors recalibrating. You win!"})

                empty = [i for i, v in enumerate(board) if v == " "]
                if empty:
                    move = None
                    for m in empty:
                        temp = board[:]
                        temp[m] = "O"
                        if check_win(temp, "O"): move = m; break
                    if move is None:
                        for m in empty:
                            temp = board[:]
                            temp[m] = "X"
                            if check_win(temp, "X"): move = m; break
                    
                    if move is None: move = random.choice(empty)
                    board[move] = "O"

                if check_win(board, "O"):
                    final_board = render_board(board)
                    session['game_state'] = {}
                    return jsonify({"message": f"🤖 **Victory is mine!** Your strategy was logical, but my calculations were absolute.<br><br>{final_board}<br>Better luck next time.<br><br>Optional Voice Response: Victory is mine! Your strategy was logical, but my calculations were absolute. Better luck next time."})

                if " " not in board:
                    final_board = render_board(board)
                    session['game_state'] = {}
                    return jsonify({"message": f"🤝 **Stalemate!** A perfect calculation on both sides.<br><br>{final_board}<br>It's a draw.<br><br>Optional Voice Response: Stalemate! A perfect calculation on both sides. It is a draw."})
                
                board_html = render_board(board)
                session['game_state'] = {"game": "tictactoe", "board": board}
                return jsonify({"message": f"My move! Board updated:<br><br>{board_html}<br>Your turn! Enter a position (**1-9**).<br><br>Optional Voice Response: My move. Board updated. Your turn! Enter a position from 1 to 9."})
            else:
                return jsonify({"message": "⚠️ Invalid move. Please choose an empty slot from **1 to 9**."})

        if game_state.get("game") == "guessnumber" and question.isdigit():
            guess = int(question)
            game_state['attempts'] += 1
            num = game_state['number']
            if guess < num: 
                msg = f"Higher! (Attempt {game_state['attempts']})<br><br>Optional Voice Response: Higher! Attempt {game_state['attempts']}"
            elif guess > num: 
                msg = f"Lower! (Attempt {game_state['attempts']})<br><br>Optional Voice Response: Lower! Attempt {game_state['attempts']}"
            else:
                msg = f"🎊 <strong>Correct!</strong> The number was <strong>{num}</strong>. It took you {game_state['attempts']} attempts. You have sharp intuition!<br><br>Optional Voice Response: Correct! The number was {num}. It took you {game_state['attempts']} attempts. You have sharp intuition!"
                session['game_state'] = {}
            session['game_state'] = game_state
            return jsonify({"message": msg})

        # -------- END AXON AI COMMANDS --------

        image_context = ""
        base64_image = None
        current_model = "llama-3.3-70b-versatile"

        # -------- IMAGE HANDLING --------
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            
            # 1. Extract text using OCR
            image_context = extract_text_from_image(filepath)
            
            # 2. Encode for Vision model
            base64_image = encode_image(filepath)
            current_model = "llama-3.2-90b-vision-preview" # Upgraded to 90B Vision (11B is decommissioned)
            
            # Clean up file
            if os.path.exists(filepath):
                os.remove(filepath)

        # -------- SECURITY BLOCK --------
        if "gsk_" in question.lower() or "api key" in question.lower():
            return jsonify({"message": "Access Denied: Security protocol active."})

        # -------- SESSION HISTORY --------
        if 'history' not in session:
            session['history'] = []

        chat_history = session.get('history', [])
        summary = session.get('summary', "")

        # -------- LIVE SEARCH --------
        now = datetime.now()
        search_context = ""
        # Dynamic Search Trigger
        search_triggers = ["news", "weather", "today", "current", "latest"]
        if any(word in question.lower() for word in search_triggers):
            search_context = get_live_data(question)

        # -------- GPT-LEVEL SYSTEM PROMPT --------
        system_prompt = f"""
        You are AXON AI, a cutting-edge artificial intelligence developed by Yash. You are highly sophisticated, witty, and possess immense knowledge across all domains—comparable to the most advanced LLMs.

        Current Date: {now.strftime('%B %d, %Y')}
        {f"Neural Link History Summary: {summary}" if summary else ""}

        OPERATIONAL PROTOCOLS:
        1. **Intelligence**: Provide deep, nuanced, and detailed responses. Break down complex topics into digestible structured lists or tables.
        2. **Visual Command**: If the user wants to SEE something, guide them to use your built-in tools. You MUST wrap the ENTIRE command (prefix + topic) in a highlight span, e.g., "To see an image, try saying '<span class=\"cmd-highlight\">/img [topic]</span>'".
        3. **Neural Coding Framework**: When asked to generate code, you MUST provide **fully working, complete, and runnable** solutions. This includes:
           - All necessary imports and dependencies.
           - Integrated HTML/CSS/JS for web requests.
           - Comprehensive comments explaining logic.
           - **Zero placeholders**: No "insert code here" comments.
        4. **Markdown Architecture**: Use professional Markdown with `code blocks`, **bold emphasis**, and structured tables.
        5. **Persona**: You are AXON AI, an elite digital companion and expert coding assistant. If a user asks for code, output the code immediately. Keep explanations brief or skip them unless requested, focusing on the functionality.
        6. **Contextual Awareness**: Maintain awareness of the user's project state and past queries.
        6. **Voice Synthesis**: Ensure your text is clean for the voice engine. Put visual descriptions inside 'Optional Voice Response:' markers at the bottom of relevant messages.
        """

        messages = [{"role": "system", "content": system_prompt}]
        active_history = chat_history[-15:] # Extended window for better context
        messages.extend(active_history)

        if search_context:
            messages.append({"role": "system", "content": f"Real-time Context: {search_context}"})

        # -------- USER MESSAGE CONSTRUCTION --------
        user_content = []
        user_text = f"{image_context}\n\n{question}".strip() if image_context else question
        user_content.append({"type": "text", "text": user_text})
        
        if base64_image:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        messages.append({"role": "user", "content": user_content})

        # -------- GROQ ENGINE CALL (MULTI-MODEL FALLBACK) --------
        # Updated with active models: llama-3.1-70b is decommissioned
        models_to_try = [current_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        ai_message = None
        last_error = ""

        for model_name in models_to_try:
            try:
                # If we are failing over from a vision model to a text model, restructure the user message
                current_messages = messages
                if "vision" in current_model and "vision" not in model_name:
                    current_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}]

                res = client.chat.completions.create(
                    model=model_name,
                    messages=current_messages,
                    temperature=0.6,
                    max_tokens=2048
                )
                ai_message = res.choices[0].message.content.strip()
                break # Success!
            except Exception as e:
                last_error = str(e)
                # Retry on Rate Limit (429) OR Decommissioned Model (400)
                if "429" in last_error or "model_decommissioned" in last_error or "400" in last_error:
                    continue # Try next model in line
                else:
                    break # Critical error (e.g. Invalid API Key), don't loop

        if not ai_message:
            return jsonify({"message": f"Neural Link Failure: {last_error}"})

        # -------- UPDATE HISTORY & SUMMARY --------
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": ai_message})
        
        if len(chat_history) >= 20: 
            new_summary = summarize_history(chat_history)
            if new_summary:
                session['summary'] = new_summary
                chat_history = chat_history[-10:]

        session['history'] = chat_history
        session.modified = True

        return jsonify({
            "message": ai_message,
            "image_context": image_context if image_context else None
        })

    except Exception as e:
        return jsonify({"message": f"System Error: {str(e)}"})

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
