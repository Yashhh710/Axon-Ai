import os
import base64
import random
import time
import platform
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import uvicorn
import requests
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.utils import secure_filename

# Try to import CV2 and NumPy for technical analysis
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

# -------------------- INITIALIZATION --------------------
# Load environment variables
load_dotenv()

# Setup paths (Relative to project root)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "uploads"

# Create required directories
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# App Configuration
app = FastAPI(title="Axon AI")

# CORS Middleware (Required for web deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production safe when using specific domains, '*' for initial global access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware (For game state)
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_yash_axon_77")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static and Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# External API Clients
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Tesseract Configuration
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "tesseract")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Global Neural Memory (In-memory storage)
NEURAL_MEMORY: Dict[str, Dict[str, Any]] = {}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# -------------------- HELPERS --------------------
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def extract_text_from_image(filepath: Path) -> str:
    """Extract readable text from image using OCR with graceful fallbacks"""
    try:
        # Check if tesseract is available in path or at configured path
        with Image.open(filepath) as img:
            rgb_img = img.convert('RGB')
            # Run in a thread to not block event loop
            text = await asyncio.to_thread(pytesseract.image_to_string, rgb_img)
            if text.strip():
                return f"[Visual Scan Content: {text.strip()}]"
    except Exception as e:
        print(f"OCR Error: {e}")
    
    return "[Scanning image for visual features and metadata...]"

class TechnicalImageAnalyzer:
    """Analyzes physical and technical properties of the image using CV2 and NumPy"""
    def __init__(self, image_path: Path):
        self.path = image_path
        self.valid = False
        if not self.path.exists() or cv2 is None or np is None:
            return
        
        try:
            with Image.open(image_path) as img:
                self.width, self.height = img.size
            
            self.cv_img = cv2.imread(str(image_path))
            if self.cv_img is not None:
                self.valid = True
        except Exception as e:
            print(f"Technical Analysis Init Error: {e}")

    def get_analysis_summary(self):
        if not self.valid:
            return ""
        
        try:
            # Basic Metadata
            filesize = round(os.path.getsize(self.path) / 1024, 2)
            
            # Brightness & Lighting
            gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            lighting = "Low-Light/Dark" if avg_brightness < 80 else "Bright/Well-Lit"
            if 80 <= avg_brightness <= 180: lighting = "Balanced"
            
            # Visual Complexity (Edge Density)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = (np.sum(edges > 0) / edges.size) * 100
            complexity = "High (Highly Detailed/Textured)" if edge_density > 5 else "Low (Simple/Minimalist)"
            
            return (f"[Technical Diagnostics: Resolution={self.width}x{self.height}, Size={filesize}KB, "
                    f"Lighting={lighting} (Score: {round(avg_brightness,1)}), "
                    f"Complexity={complexity} (EdgeDensity: {round(edge_density,2)}%)]")
        except Exception as e:
            print(f"Technical Analysis execution Error: {e}")
            return ""

def get_live_data(query: str) -> str:
    """Get live search data via DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            return "\n".join([r["body"] for r in results]) if results else ""
    except Exception as e:
        return f"[Live Search Error: {str(e)}]"

async def summarize_history(history: List[Dict[str, str]]) -> str:
    """Summarize the conversation history to keep it compact"""
    if not history:
        return ""
    
    try:
        formatted_history = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history])
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
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

def ddgs_image_search(query: str) -> List[str]:
    """Integrated Image Search via DuckDuckGo Neural Gateway"""
    try:
        results = []
        with DDGS() as ddgs:
            # We convert the generator to a list to avoid issues with closing the context
            ddgs_gen = list(ddgs.images(
                keywords=query,
                region="wt-wt",
                safesearch="off",
                max_results=10
            ))
            for r in ddgs_gen:
                img_url = r.get("image") or r.get("thumbnail")
                if img_url:
                    results.append(img_url)
        return results
    except Exception as e:
        print(f"DDGS Image Search Error: {e}")
        return []

def bing_image_search(query: str) -> List[str]:
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

def encode_image(image_path: Path) -> str:
    """Encode image to base64 for vision models"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def is_creator_query(text: str) -> bool:
    """Detect if the query is about the creator or developer with comprehensive keyword matching"""
    text_lower = text.lower().strip()
    
    # 1. Direct triggers
    direct_triggers = [
        "@dev", "/dev", "yash tambade", "yashhh", "about axon ai", 
        "axon ai creator", "axon ai developer", "who is yash", "about yash"
    ]
    if any(t in text_lower for t in direct_triggers):
        return True
    
    # 2. Key phrases
    key_phrases = [
        "who made you", "who created you", "who built you", "who is your developer",
        "who is behind this", "who owns this", "who developed this", "who coded you",
        "your creator", "your developer", "your owner", "tell me about developer",
        "tell me about creator", "info about developer", "info about creator",
        "developer info", "creator info", "dev info", "creator details",
        "developer details", "about developer", "about creator", "about you"
    ]
    if any(p in text_lower for p in key_phrases):
        return True
        
    # 3. Keyword combinations (Heuristic)
    creators = ["creator", "developer", "owner", "builder", "coded", "developed", "built", "made"]
    targets = ["you", "axon", "this app", "this ai", "assistant", "ai"]
    
    has_creator = any(word in text_lower for word in creators)
    has_target = any(word in text_lower for word in targets)
    
    # Check for "dev" as a standalone word or in common contexts
    if " dev " in f" {text_lower} " or text_lower == "dev":
        return True
        
    return has_creator and has_target

def get_creator_info_html() -> str:
    """Returns a clean, Markdown-formatted profile of the creator"""
    return """
# 🧠 Yash Tambade
> "Building small things that feel big"

### 🚀 About Creator
Yash Tambade is a young tech enthusiast from Navi Mumbai, currently pursuing a B.Tech in Computer Science (2025–2029). He focuses on frontend development, UI design, AI experiments, and interactive web projects.

### 📌 Key Details
- **🎂 Age:** 17
- **📍 Location:** Navi Mumbai, Maharashtra, India
- **🎓 Education:** B.Tech in Computer Science

### ⚡ Skills
- HTML, CSS, JavaScript
- Python Programming
- UI/UX Design
- Game Logic & Interactive Projects

### 🛠️ Projects
- **Axon AI:** AI chatbot with real-time neural search integration.
- **GameBox:** Collection of immersive Scratch mini-games.
- **Mini Games & Apps:** Various interactive web-based projects.
- **Portfolio Website:** Professional digital showcase.

### 🌐 Connect with Developer
- **GitHub (Prod):** [github.com/yashtambade56-ux](https://github.com/yashtambade56-ux)
- **GitHub (Lab):** [github.com/Yashhh710](https://github.com/Yashhh710)
- **LinkedIn:** [linkedin.com/in/yash-tambade-173508379](https://linkedin.com/in/yash-tambade-173508379)
- **Portfolio:** [Portfolio v1](https://yashhh710.github.io/Portfolio_v1/)
- **📧 Email:** [yashtambade56@gmail.com](mailto:yashtambade56@gmail.com)
"""

# -------------------- ROUTES --------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        user_id = request.client.host
        NEURAL_MEMORY[user_id] = {"history": [], "summary": ""}
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        print(f"Home Error: {e}")
        return HTMLResponse(content="<h1>Critical Neural Link Failure</h1><p>Check logs.</p>", status_code=500)

@app.post("/ask")
async def ask(
    request: Request,
    question: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    try:
        if not question and not image:
            return JSONResponse(content={"message": "Please provide text or image input."})

        question = question.strip() if question else ""
        user_id = request.client.host

        # -------- AXON AI COMMANDS (HYBRID MODE) --------
        if question.lower().startswith("/clear"):
            NEURAL_MEMORY[user_id] = {"history": [], "summary": ""}
            request.session['game_state'] = {}
            return JSONResponse(content={"message": "Neural memory reset. Chat cleared ✅", "action": "clear"})

        if question.lower().startswith("/functions") or question.lower().startswith("/help"):
            return JSONResponse(content={"message": "<strong>Available features:</strong><br>/intro, /clear, /functions, /video [topic], /vid [topic], /joke, /quote, /tip, /image [query], /img [query], /tictactoe, /guessnumber, open [app]"})

        if question.lower().startswith("/joke"):
            jokes = ["Why do programmers prefer dark mode? Because light attracts bugs.", "Real programmers count from 0.", "How many programmers does it take to change a light bulb? None, it's a hardware problem."]
            return JSONResponse(content={"message": f"🤖 {random.choice(jokes)}"})

        if question.lower().startswith("/quote"):
            quotes = ["The best way to predict the future is to invent it. - Alan Kay", "Intelligence is the ability to adapt to change. - Stephen Hawking", "The advance of technology is based on making it fit in. - Bill Gates"]
            return JSONResponse(content={"message": f"✨ <em>\"{random.choice(quotes)}\"</em>"})

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
            return JSONResponse(content={"message": intro_msg})

        if question.lower().startswith("/tip"):
            tips = ["Learn to use a debugger early.", "Keep your functions small and focused.", "Automate repetitive tasks with scripts."]
            return JSONResponse(content={"message": f"💡 <strong>Pro Tip:</strong> {random.choice(tips)}"})

        # -------- AXON AI BASIC REPLIES --------
        q_lower = question.lower().strip()
        if q_lower in ["hello", "hi", "hey", "hola", "greetings"]:
            welcome_msg = "Hello! I am **AXON AI**, your digital companion. How can I assist you today? 🧠✨"
            return JSONResponse(content={"message": welcome_msg})

        if q_lower in ["how are you", "how are you doing", "how's it going"]:
            return JSONResponse(content={"message": "My neural circuits are functioning at peak efficiency! Powering through trillions of operations per second to provide you with the best experience. How can I assist you today?"})

        if q_lower in ["thank you", "thanks", "thx", "appreciate it"]:
            return JSONResponse(content={"message": "You're very welcome! It's my pleasure to assist. Is there anything else you'd like to dive into?"})

        if q_lower in ["bye", "goodbye", "exit", "see ya"]:
            return JSONResponse(content={"message": "Goodbye! My systems will remain in standby until your next request. Stay curious! 🚀"})

        if is_creator_query(question):
            return JSONResponse(content={"message": get_creator_info_html()})

        if question.lower().startswith("/video") or question.lower().startswith("/vid") or "show me a video for" in question.lower():
            query = question.lower().replace("/video", "").replace("/vid", "").replace("show me a video for", "").strip()
            for word in ["of ", "a ", "an "]:
                if query.startswith(word): query = query[len(word):].strip()
            if not query:
                return JSONResponse(content={"message": "Please specify a topic. Example: /vid Python loops"})
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.videos(query, max_results=1))
                    if results:
                        video = results[0]
                        return JSONResponse(content={"message": f"I found a tutorial for <strong>{query}</strong>:<br><br><strong>{video['title']}</strong><br>[Watch Video]({video['content']})<br><br>{video['description'][:150]}..."})
            except Exception:
                pass
            return JSONResponse(content={"message": f"I couldn't find a video for '<strong>{query}</strong>' right now. 😕"})

        img_triggers = ["/image", "/img", "give me an image of", "give me img", "show me a picture of", "show me an image of", "fetch me image of", "show me img", "search for an image of", "generate an image of"]
        if any(trigger in question.lower() for trigger in img_triggers):
            raw_query = question.lower()
            for trigger in img_triggers:
                raw_query = raw_query.replace(trigger, "")
            
            clean_words = ["search", "for", "me", "find", "please", "of", "a", "an", "the"]
            query = " ".join([w for w in raw_query.split() if w not in clean_words]).strip()
            
            if not query:
                return JSONResponse(content={"message": "Please specify a subject for the visual scan. Example: /img Neon cyberpunk city"})
            
            try:
                # Optimized Query Generation
                try:
                    query_gen = await asyncio.to_thread(
                        client.chat.completions.create,
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "system", "content": "Return ONLY image search keywords for the subject."}, 
                                  {"role": "user", "content": query}],
                        max_tokens=20
                    )
                    optimized_query = query_gen.choices[0].message.content.strip()
                except:
                    optimized_query = f"{query} high quality official artwork pinterest"

                # Cinematic Description
                try:
                    desc_response = await asyncio.to_thread(
                        client.chat.completions.create,
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "system", "content": "Describe this image subject in one cinematic sentence."}, 
                                  {"role": "user", "content": query}],
                        max_tokens=50
                    )
                    description = desc_response.choices[0].message.content.strip().replace('"', "'")
                except:
                    description = f"A high-definition visual of {query}, rendered with stunning detail."

                # Hybrid Search
                best_img = None
                results = await asyncio.to_thread(ddgs_image_search, optimized_query)
                if not results:
                    results = await asyncio.to_thread(bing_image_search, optimized_query)
                
                if results:
                    valid_exts = (".png", ".jpg", ".jpeg", ".webp")
                    for url in results:
                        if any(url.lower().endswith(ext) for ext in valid_exts):
                            best_img = url
                            break
                    if not best_img:
                        best_img = results[0]

                if best_img:
                    success_msg = (
                        f"<div style='margin:15px 0; border-radius:20px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); box-shadow:0 15px 35px rgba(0,0,0,0.5); background:rgba(0,0,0,0.2);'>"
                        f"  <img src='{best_img}' alt='{description}' style='width:100%; height:auto; display:block;' onerror=\"this.style.display='none';\">"
                        f"  <div style='padding:15px; background:rgba(0,0,0,0.4); backdrop-filter:blur(10px); color:white; font-size:14px; text-align:center; border-top:1px solid rgba(255,255,255,0.1);'>{description}</div>"
                        f"</div>"
                        f"**Neural Scan Description:** {description}"
                    )
                    return JSONResponse(content={"message": success_msg})
                else:
                    return JSONResponse(content={"message": f"My neural net couldn't locate a stable visual stream for '<strong>{query}</strong>'."})

            except Exception as e:
                return JSONResponse(content={"message": f"Neural Link Error: {str(e)[:40]}..."})

        if question.lower().startswith("open "):
            app_name = question[5:].strip()
            return JSONResponse(content={"message": f"Opening {app_name.capitalize()}! 🛰️", "action": "open", "target": app_name})

        # --- MINI GAMES ---
        def render_board(b):
            disp = []
            for i, v in enumerate(b):
                if v == " ":
                    disp.append(f"<span style='color:rgba(255,255,255,0.2); font-size: 0.9rem;'>{i+1}</span>")
                else:
                    color = "#6366f1" if v == "X" else "#10b981"
                    disp.append(f"<strong style='color:{color}'>{v}</strong>")
            
            return f"<div style='text-align:center; margin:15px 0;'><pre style='font-family: monospace; font-size: 1.3rem; line-height: 1.4; padding: 20px; background: rgba(0,0,0,0.3); border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); display: inline-block;'> {disp[0]} | {disp[1]} | {disp[2]} \n---+---+---\n {disp[3]} | {disp[4]} | {disp[5]} \n---+---+---\n {disp[6]} | {disp[7]} | {disp[8]} </pre></div>"

        if question.lower() == "/tictactoe" or "play tictactoe" in question.lower():
            request.session['game_state'] = {"game": "tictactoe", "board": [" "] * 9, "turn": "X"}
            board_html = render_board(request.session['game_state']['board'])
            return JSONResponse(content={"message": f"🤖 **Neural Challenge Accepted!** Let's play Tic-Tac-Toe!<br><br>{board_html}<br>Enter a position (**1-9**) to make your move."})

        if question.lower() == "/guessnumber" or "play guess number" in question.lower():
            request.session['game_state'] = {"game": "guessnumber", "number": random.randint(1, 100), "attempts": 0}
            return JSONResponse(content={"message": "🎯 I'm thinking of a number between <strong>1 and 100</strong>. Can you guess it?"})

        game_state = request.session.get('game_state', {})
        if game_state.get("game") == "tictactoe" and question.isdigit():
            idx = int(question) - 1
            if 0 <= idx <= 8 and game_state['board'][idx] == " ":
                board = game_state['board']
                board[idx] = "X"
                
                def check_win(b, p):
                    win_pos = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
                    return any(b[i] == b[j] == b[k] == p for i,j,k in win_pos)

                if check_win(board, "X"):
                    request.session['game_state'] = {}
                    return JSONResponse(content={"message": f"🎉 **Incredible!** You defeated me.<br><br>{render_board(board)}<br>Neural processors recalibrating... You win!"})

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
                    request.session['game_state'] = {}
                    return JSONResponse(content={"message": f"🤖 **Victory is mine!** Your strategy was logical.<br><br>{final_board}<br>Better luck next time."})

                if " " not in board:
                    final_board = render_board(board)
                    request.session['game_state'] = {}
                    return JSONResponse(content={"message": f"🤝 **Stalemate!** A perfect calculation.<br><br>{final_board}<br>It's a draw."})
                
                request.session['game_state'] = {"game": "tictactoe", "board": board}
                return JSONResponse(content={"message": f"My move! Board updated:<br><br>{render_board(board)}<br>Your turn! Enter a position (**1-9**)."})

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
                request.session['game_state'] = {}
            request.session['game_state'] = game_state
            return JSONResponse(content={"message": msg})

        # -------- IMAGE HANDLING --------
        image_context = ""
        base64_image = None
        current_model = "llama-3.3-70b-versatile"
        image_mode = False

        if image:
            filename = secure_filename(image.filename)
            if allowed_file(filename):
                filepath = UPLOAD_DIR / filename
                with open(filepath, "wb") as buffer:
                    buffer.write(await image.read())
                
                # 1. OCR
                image_context = await extract_text_from_image(filepath)
                
                # 2. Technical Analysis
                tech_analyzer = TechnicalImageAnalyzer(filepath)
                tech_summary = tech_analyzer.get_analysis_summary()
                if tech_summary:
                    image_context = f"{image_context}\n{tech_summary}"

                # 3. Vision Encoding
                base64_image = encode_image(filepath)
                mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
                current_model = "llama-3.2-11b-vision-preview" 
                image_mode = True

                if not question:
                    question = "Perform a comprehensive neural analysis of this visual data."
                
                # Cleanup
                if filepath.exists():
                    os.remove(filepath)

        # -------- SECURITY & NEURAL MEMORY --------
        if "gsk_" in question.lower() or "api key" in question.lower():
            return JSONResponse(content={"message": "Access Denied: Security protocol active."})

        if user_id not in NEURAL_MEMORY:
            NEURAL_MEMORY[user_id] = {"history": [], "summary": ""}
            
        chat_history = list(NEURAL_MEMORY[user_id].get("history", []))
        summary = str(NEURAL_MEMORY[user_id].get("summary", ""))

        # -------- LIVE SEARCH --------
        now = datetime.now()
        search_context = ""
        search_triggers = ["news", "weather", "today", "current", "latest"]
        if any(word in question.lower() for word in search_triggers):
            search_context = get_live_data(question)

        # -------- SYSTEM PROMPT --------
        system_prompt = f"""
You are AXON AI, an advanced intelligent AI assistant. 
Be helpful, intelligent, and accurate. Provide concise answers by default.
User Location: {user_id}
Current Date: {now.strftime('%B %d, %Y')}
{f"Neural Link History Summary: {summary}" if summary else ""}
        """

        messages = [{"role": "system", "content": system_prompt}]
        active_history = chat_history[-10:]
        messages.extend(active_history)

        if search_context:
            messages.append({"role": "system", "content": f"Real-time Context: {search_context}"})

        # User Content
        user_content = []
        if image_mode:
            if image_context:
                messages.append({"role": "system", "content": f"NEURAL IMAGE SENSOR DATA:\n{image_context}"})
            user_content.append({"type": "text", "text": question})
            user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}})
        else:
            user_content.append({"type": "text", "text": question})

        messages.append({"role": "user", "content": user_content})

        # -------- GROQ CALL --------
        models_to_try = [current_model, "llama-3.1-8b-instant"]
        ai_message = None
        last_error = ""

        for model_name in models_to_try:
            try:
                # Handle non-vision models if we have an image
                curr_msgs = messages
                if image_mode and "vision" not in model_name:
                    cleaned_history = [h for h in chat_history[-5:] if isinstance(h.get("content"), str)]
                    fallback_text = f"TECHNICAL IMAGE CONTEXT:\n{image_context}\n\nUSER QUESTION: {question}"
                    curr_msgs = [{"role": "system", "content": system_prompt}]
                    curr_msgs.extend(cleaned_history)
                    curr_msgs.append({"role": "user", "content": fallback_text})

                res = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model_name,
                    messages=curr_msgs,
                    temperature=0.2,
                    max_tokens=2048
                )
                ai_message = res.choices[0].message.content.strip()
                break
            except Exception as e:
                last_error = str(e)
                if "429" in last_error:
                    await asyncio.sleep(1)
                    continue
                break

        if not ai_message:
            return JSONResponse(content={"message": f"Neural Link Failure: {last_error}"})

        # Update History
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": ai_message})
        
        if len(chat_history) >= 20: 
            new_summary = await summarize_history(chat_history)
            if new_summary:
                NEURAL_MEMORY[user_id]["summary"] = new_summary
                chat_history = chat_history[-6:]

        NEURAL_MEMORY[user_id]["history"] = chat_history

        return JSONResponse(content={"message": ai_message})

    except Exception as e:
        return JSONResponse(content={"message": f"System Error: {str(e)}"})

# -------------------- STARTUP --------------------
# PORT Handling for Deployment (Render/Railway/Heroku)
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    import uvicorn
    # In production, we use 0.0.0.0 to bind to all interfaces
    # The 'main:app' string format enables auto-reload only during local dev if needed
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")