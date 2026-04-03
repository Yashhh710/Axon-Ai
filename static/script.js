const chatBox = document.getElementById("chat-box");
let isVoiceEnabled = true;
let selectedFile = null;
let recognition = null;
let wakeWordRecognition = null;
let isSystemActive = false;
let isSidebarOpen = true;
let isImgMode = false;

// --- Sidebar Toggle ---
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    isSidebarOpen = !isSidebarOpen;
    if (isSidebarOpen) {
        sidebar.style.transform = "translateX(0)";
        document.body.classList.remove("sidebar-closed");
    } else {
        sidebar.style.transform = "translateX(-100%)";
        document.body.classList.add("sidebar-closed");
    }
}

// Audio Elements
const sndActivate = document.getElementById("sound-activate");
const sndSuccess = document.getElementById("sound-success");

function playSound(audio) {
    if (audio) {
        audio.currentTime = 0;
        audio.play().catch(e => console.warn("Audio play blocked", e));
    }
}

// --- ROBUST CLAP DETECTION ---
function initClapDetection() {
    window.AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!window.AudioContext) return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        const microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        let lastClapTime = 0;
        let avgVolume = 0;

        function checkLevel() {
            analyser.getByteFrequencyData(dataArray);
            let instantVolume = 0;
            for (let i = 0; i < dataArray.length; i++) instantVolume += dataArray[i];
            instantVolume /= dataArray.length;

            // Sudden peak detection: instant volume is significantly higher than rolling average
            // AND above a minimum threshold to avoid sensitive triggers
            if (instantVolume > avgVolume * 2.5 && instantVolume > 40 && Date.now() - lastClapTime > 1500) {
                lastClapTime = Date.now();
                if (!isSystemActive) {
                    console.log("Clap trigger activated!");
                    activateJarvis("Neural trigger detected: Initializing Axon interface.");
                }
            }

            // Fast rolling average for background noise
            avgVolume = avgVolume * 0.9 + instantVolume * 0.1;

            requestAnimationFrame(checkLevel);
        }
        checkLevel();
    }).catch(err => console.error("Mic Error for Clap:", err));
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById("img-preview").src = e.target.result;
            document.getElementById("preview-container").classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }
}

function clearImage() {
    selectedFile = null;
    document.getElementById("preview-container").classList.add("hidden");
    document.getElementById("image-input").value = "";
}

function addMessage(text, sender, imageFile = null) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${sender}-row`;

    // Remove voice marker from display
    let displayText = text;
    const voiceMarker = "Optional Voice Response:";
    if (displayText.includes(voiceMarker)) {
        displayText = displayText.split(voiceMarker)[0].trim();
    }

    const inner = document.createElement("div");
    inner.className = "message-inner";
    wrapper.dataset.rawText = text;

    if (sender === "ai") {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = "🧠";
        avatar.title = "Speak / Stop";
        avatar.onclick = () => {
            if (avatar.classList.contains("avatar-speaking")) {
                stopVoice();
            } else {
                speak(wrapper.dataset.rawText, true, null, avatar);
            }
        };
        inner.appendChild(avatar);

        const contentArea = document.createElement("div");
        contentArea.className = "content-area";
        contentArea.innerHTML = formatAIResponse(displayText);
        inner.appendChild(contentArea);
    } else {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        const userImg = document.createElement("img");
        userImg.src = "https://avatars.githubusercontent.com/u/233944797?v=4";
        userImg.style.width = "100%";
        userImg.style.height = "100%";
        userImg.style.borderRadius = "inherit";
        userImg.style.objectFit = "cover";
        avatar.appendChild(userImg);
        inner.appendChild(avatar);

        const bubble = document.createElement("div");
        bubble.className = "content-bubble";

        if (imageFile) {
            const img = document.createElement("img");
            img.src = URL.createObjectURL(imageFile);
            img.style.maxWidth = "100%";
            img.style.borderRadius = "8px";
            img.style.marginBottom = "8px";
            bubble.appendChild(img);
        }

        const txt = document.createElement("div");
        txt.textContent = displayText;
        bubble.appendChild(txt);
        inner.appendChild(bubble);
    }

    wrapper.appendChild(inner);
    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Auto-close on mobile
    if (window.innerWidth <= 768 && isSidebarOpen) toggleSidebar();

    return wrapper;
}

function formatAIResponse(text) {
    if (!text) return "";
    
    const renderer = new marked.Renderer();
    
    // Updated for compatibility with newer marked versions
    renderer.code = function(code, language, escaped) {
        // Handle both older and newer marked arguments
        const codeText = typeof code === 'object' ? code.text : code;
        const lang = (typeof code === 'object' ? code.lang : language) || 'plaintext';
        
        try {
            const highlighted = hljs.highlightAuto(codeText).value;
            return `<pre><div class="code-header"><span>${lang}</span><button class="copy-btn" onclick="copyToClipboard(this)">Copy</button></div><code>${highlighted}</code></pre>`;
        } catch (e) {
            console.warn("Highlight.js failed, falling back to plaintext:", e);
            return `<pre><div class="code-header"><span>${lang}</span><button class="copy-btn" onclick="copyToClipboard(this)">Copy</button></div><code>${codeText}</code></pre>`;
        }
    };

    // Force ALL links (Markdown format) to open in a new tab
    renderer.link = function(href, title, text) {
        let linkHref = typeof href === 'object' ? href.href : href;
        let linkTitle = (typeof href === 'object' ? href.title : title) || '';
        let linkText = (typeof href === 'object' ? href.text : text) || '';
        return `<a href="${linkHref}" title="${linkTitle}" target="_blank" rel="noopener noreferrer">${linkText}</a>`;
    };

    marked.setOptions({
        renderer: renderer,
        breaks: true,
        gfm: true
    });
    
    try {
        let htmlContent = marked.parse(text);
        
        // Post-processing to ensure even raw HTML links from server open in a new tab
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = htmlContent;
        tempDiv.querySelectorAll("a").forEach(a => {
            a.setAttribute("target", "_blank");
            a.setAttribute("rel", "noopener noreferrer");
        });
        
        return tempDiv.innerHTML;
    } catch (e) {
        console.error("Marked parsing error:", e);
        return text;
    }
}

function copyToClipboard(btn) {
    const pre = btn.closest('pre');
    const code = pre.querySelector('code').innerText;
    
    navigator.clipboard.writeText(code).then(() => {
        const originalText = btn.textContent;
        btn.innerHTML = '<span style="color:#10b981">✓</span> Copied';
        btn.classList.add('copied');
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

function handleEnter(e) { if (e.key === "Enter") askAI(); }
function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    document.getElementById("voice-icon").textContent = isVoiceEnabled ? "🔊" : "🔈";
}
function stopVoice() {
    window.speechSynthesis.cancel();
    // Stop all audio elements to ensure full silence
    document.querySelectorAll("audio").forEach(audio => {
        audio.pause();
        audio.currentTime = 0;
    });
    // Remove speaking animation from all avatars
    document.querySelectorAll(".ai-row .avatar").forEach(el => el.classList.remove("avatar-speaking"));
}

function speak(text, force = false, onEndCallback = null, targetAvatar = null) {
    window.speechSynthesis.cancel();
    // Remove animation from any other potentially pulsing brains
    document.querySelectorAll(".ai-row .avatar").forEach(el => el.classList.remove("avatar-speaking"));

    if (!isVoiceEnabled && !force) {
        if (onEndCallback) onEndCallback();
        return;
    }

    let speechText = text;
    const voiceMarker = "Optional Voice Response:";
    if (text.includes(voiceMarker)) speechText = text.split(voiceMarker)[1].trim();

    speechText = speechText.replace(/<[^>]*>?/gm, '').replace(/[*#=~_`]/g, '').replace(/-{2,}/g, ' ');

    const ut = new SpeechSynthesisUtterance(speechText);

    // Identify which brain to animate
    let avatarToAnimate = targetAvatar;
    if (!avatarToAnimate) {
        const avatars = document.querySelectorAll(".ai-row .avatar");
        avatarToAnimate = avatars[avatars.length - 1];
    }

    if (avatarToAnimate) avatarToAnimate.classList.add("avatar-speaking");

    ut.onend = () => {
        if (avatarToAnimate) avatarToAnimate.classList.remove("avatar-speaking");
        if (onEndCallback) onEndCallback();
    };
    ut.onerror = () => {
        if (avatarToAnimate) avatarToAnimate.classList.remove("avatar-speaking");
        if (onEndCallback) onEndCallback();
    };
    window.speechSynthesis.speak(ut);
}

function activateJarvis(customMessage = null) {
    if (isSystemActive) return;
    isSystemActive = true;
    if (wakeWordRecognition) try { wakeWordRecognition.stop(); } catch (e) { }

    playSound(sndActivate);
    document.getElementById("status-light").style.background = "#6366f1"; // Pulsing Purple
    document.getElementById("voice-overlay").classList.remove("hidden");

    let reply = customMessage || "Axon system online. Awaiting instruction.";
    speak(reply, true, () => startListening());
}

function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return alert("System incompatibility: Speech recognition not supported.");

    recognition = new SpeechRecognition();
    const transcriptDisp = document.getElementById("voice-transcript");
    recognition.onstart = () => {
        document.getElementById("status-light").style.boxShadow = "0 0 15px #6366f1";
        document.getElementById("voice-overlay").classList.remove("hidden");
        transcriptDisp.textContent = "Awaiting neural synchronization...";
    };

    recognition.onresult = (e) => {
        const t = e.results[0][0].transcript;
        transcriptDisp.textContent = t;
        if (e.results[0].isFinal) {
            document.getElementById("question").value = t;
            setTimeout(() => { stopListening(); askAI(true); }, 800);
        }
    };

    recognition.onend = () => stopListening();
    recognition.start();
}

function stopListening() {
    if (recognition) try { recognition.stop(); } catch (e) { }
    document.getElementById("voice-overlay").classList.add("hidden");
    document.getElementById("status-light").style.background = "#10b981"; // Back to Green
    document.getElementById("status-light").style.boxShadow = "none";
    isSystemActive = false;
}

async function askAI(fromVoice = false) {
    const input = document.getElementById("question");
    const q = input.value.trim();

    // Intercept clear command to provide clean UI reset
    if (q.toLowerCase() === "/clear") {
        newThread();
        return;
    }

    if (!q && !selectedFile) return;

    let finalQuestion = q;
    if (isImgMode && !q.startsWith("/img") && !q.startsWith("/image")) {
        finalQuestion = "/img " + q;
    }

    addMessage(q, "user", selectedFile);
    input.value = "";

    const formData = new FormData();
    formData.append("question", finalQuestion);
    if (selectedFile) formData.append("image", selectedFile);

    const statusText = selectedFile ? "Initializing Neural Vision Scan..." : "Processing command...";
    clearImage();

    const aiMsg = addMessage(statusText, "ai");
    aiMsg.classList.add("processing");

    try {
        const res = await fetch("/ask", { method: "POST", body: formData });
        
        if (!res.ok) {
            throw new Error(`Server responded with ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        aiMsg.dataset.rawText = data.message;
        const contentArea = aiMsg.querySelector(".content-area");
        contentArea.innerHTML = formatAIResponse(data.message);
        hljs.highlightAll();
        speak(data.message, fromVoice);
    } catch (e) {
        console.error("Neural link error:", e);
        aiMsg.querySelector(".content-area").innerHTML = `Neural Interruption: ${e.message}. Check system console for diagnostics.`;
        aiMsg.classList.remove("processing");
    }
}

async function newThread() {
    // Stop any active speech and listening mode
    stopVoice();
    stopListening();

    // Clear the chat box UI
    chatBox.innerHTML = "";

    // Add the initialization message
    addMessage("Axon system initialized. Neural link established. How can I assist you in your workspace today?", "ai");

    // Clear any pending input or images
    document.getElementById("question").value = "";
    clearImage();

    // Notify server to reset session history
    const formData = new FormData();
    formData.append("question", "/clear");

    try {
        await fetch("/ask", { method: "POST", body: formData });
    } catch (e) {
        console.error("Failed to notify server of thread reset:", e);
    }

    // Ensure scroll position is at top
    chatBox.scrollTop = 0;

    // Auto-close sidebar on mobile
    if (window.innerWidth <= 768 && isSidebarOpen) toggleSidebar();
}

document.addEventListener("DOMContentLoaded", () => {
    // --- AXON LOADING SEQUENCE ---
    const loader = document.getElementById('loader-wrapper');
    const progressFill = document.getElementById('progress-fill');
    const statusText = document.getElementById('loader-status');
    const statuses = [
        "Synchronizing Neural Pathways...",
        "Calibrating Logic Core...",
        "Establishing Secure Link...",
        "Optimizing Workspace...",
        "Axon System Online"
    ];

    let progress = 0;
    let statusIndex = 0;

    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;

        progressFill.style.width = `${progress}%`;

        // Update status text based on progress
        const targetStatusIndex = Math.floor((progress / 101) * statuses.length);
        if (targetStatusIndex > statusIndex && targetStatusIndex < statuses.length) {
            statusIndex = targetStatusIndex;
            statusText.style.opacity = '0';
            setTimeout(() => {
                statusText.textContent = statuses[statusIndex];
                statusText.style.opacity = '1';
            }, 200);
        }

        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                loader.classList.add('fade-out');
                // Voice initialization after loader
                if (!isVoiceEnabled) return;
                // Optional: Play a "system online" sound or greeting
            }, 500);
        }
    }, 200);

    addMessage("Axon system initialized. Neural link established. How can I assist you in your workspace today?", "ai");
    document.body.addEventListener('click', () => {
        if (!wakeWordRecognition) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRecognition) {
                wakeWordRecognition = new SpeechRecognition();
                wakeWordRecognition.continuous = true;
                wakeWordRecognition.interimResults = true; // Use interim for faster response

                wakeWordRecognition.onresult = (e) => {
                    if (isSystemActive) return;

                    const results = e.results[e.results.length - 1];
                    const t = results[0].transcript.toLowerCase();

                    // Fuzzy wake word detection
                    const triggers = ["hey axon", "axon", "exxon", "acton", "hey acton", "ax on", "hey action"];
                    if (triggers.some(trigger => t.includes(trigger))) {
                        console.log("Wake word trigger detected:", t);
                        // Only trigger if it's the final result OR a very confident interim
                        if (results.isFinal || results[0].confidence > 0.8) {
                            activateJarvis();
                        }
                    }
                };

                wakeWordRecognition.onend = () => {
                    if (!isSystemActive) {
                        try { wakeWordRecognition.start(); } catch (err) { }
                    }
                };

                wakeWordRecognition.start();
                initClapDetection();
            }
        }
    }, { once: true });
});

function switchMode(mode) {
    if (mode === 'chat') {
        newThread();
    }
    const navItems = document.querySelectorAll('.nav-item');
    const sections = {
        'chat': document.getElementById('pathway-section'),
        'games': document.getElementById('games-section'),
        'images': document.getElementById('images-section')
    };

    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.mode === mode) {
            item.classList.add('active');
        }
    });

    Object.keys(sections).forEach(key => {
        if (key === mode) {
            sections[key].classList.remove('hidden');
        } else {
            sections[key].classList.add('hidden');
        }
    });

    // Neural Stats Animation
    if (mode === 'games') {
        const stats = document.querySelectorAll('.stat-value');
        stats.forEach(stat => {
            stat.style.opacity = "0";
            setTimeout(() => {
                stat.style.transition = "opacity 0.5s, transform 0.5s";
                stat.style.opacity = "1";
                stat.style.transform = "translateY(0)";
            }, 100);
        });

        if (chatBox.innerHTML === "") {
            addMessage("Neural Gaming Module activated. Which simulation would you like to initiate?", "ai");
        }
    }

    if (mode === 'images') {
        if (chatBox.innerHTML === "") {
            addMessage("Neural Image Search active. Provide a subject for visual synthesis.", "ai");
        }
        toggleImgMode(true);
    } else {
        toggleImgMode(false);
    }
}

function toggleImgMode(force) {
    if (force !== undefined) {
        isImgMode = force;
    } else {
        isImgMode = !isImgMode;
    }

    const imgTag = document.getElementById('img-tag');
    const questionInput = document.getElementById('question');
    const imgBtn = document.getElementById('img-mode-btn');

    if (isImgMode) {
        imgTag.classList.remove('hidden');
        questionInput.placeholder = "Search images for...";
        imgBtn.style.color = "var(--primary)";
    } else {
        imgTag.classList.add('hidden');
        questionInput.placeholder = "Enter command or query...";
        imgBtn.style.color = "";
    }
}

function searchImagesFromSidebar() {
    const input = document.getElementById('image-search-input');
    const query = input.value.trim();
    if (query) {
        const chatInput = document.getElementById('question');
        chatInput.value = query;
        toggleImgMode(true);
        askAI();
        input.value = "";
    }
}

function quickImageSearch(query) {
    const chatInput = document.getElementById('question');
    chatInput.value = query;
    toggleImgMode(true);
    askAI();
}

function startGame(gameName) {
    // Clear previous selections
    document.querySelectorAll('.game-card').forEach(c => c.classList.remove('selected'));

    // Find and highlight current selection
    const cards = document.querySelectorAll('.game-card');
    cards.forEach(card => {
        if (card.querySelector('.game-name').innerText === gameName) {
            card.classList.add('selected');
        }
    });

    const input = document.getElementById("question");
    input.value = `Play ${gameName}`;
    askAI();

    // Close sidebar on mobile after selection
    if (window.innerWidth <= 768 && isSidebarOpen) toggleSidebar();
}

function filterGames() {
    const query = document.getElementById('game-search').value.toLowerCase();
    const cards = document.querySelectorAll('.game-card');

    cards.forEach(card => {
        const name = card.querySelector('.game-name').innerText.toLowerCase();
        if (name.includes(query)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

function filterCategory(cat) {
    // Update button states
    document.querySelectorAll('.cat-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    const cards = document.querySelectorAll('.game-card');
    cards.forEach(card => {
        const category = card.dataset.category;
        if (cat === 'all' || category === cat) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}
// --- GLOBAL CLEANUP ---
// Ensures all neural audio streams stop when the page is refreshed or closed
window.addEventListener('beforeunload', () => {
    stopVoice();
    stopListening();
});
