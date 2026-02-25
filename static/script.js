const chatBox = document.getElementById("chat-box");
let isVoiceEnabled = true;
let selectedFile = null;
let recognition = null; // Global for control

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById("img-preview").src = e.target.result;
            document.getElementById("preview-container").classList.remove("hidden");
            document.getElementById("question").placeholder = "Add a caption...";
        };
        reader.readAsDataURL(file);
    }
}

function clearImage() {
    selectedFile = null;
    document.getElementById("preview-container").classList.add("hidden");
    document.getElementById("image-input").value = "";
    document.getElementById("question").placeholder = "Ask anything...";
}

async function askAI() {
    const input = document.getElementById("question");
    const originalQuestion = input.value.trim();
    if (!originalQuestion && !selectedFile) return;

    let displayQuestion = originalQuestion;
    const imgTriggers = ["/image", "/img", "give me an image of", "give me img", "show me a picture of", "show me an image of", "fetch me image of", "show me img", "search for an image of", "generate an image of"];

    for (const trigger of imgTriggers) {
        if (originalQuestion.toLowerCase().startsWith(trigger)) {
            const topic = originalQuestion.substring(trigger.length).trim();
            displayQuestion = `<span class="cmd-highlight">/img ${topic}</span>`;
            break;
        }
    }

    const userBubble = addMessage(displayQuestion, "user", selectedFile);
    userBubble.dataset.fullText = originalQuestion;

    const formData = new FormData();
    formData.append("question", originalQuestion);
    if (selectedFile) formData.append("image", selectedFile);

    const aiBubble = addMessage("Analyzing neural patterns...", "ai");
    aiBubble.classList.add("thinking");
    input.value = "";
    clearImage();

    try {
        const res = await fetch("/ask", { method: "POST", body: formData });
        const data = await res.json();
        aiBubble.classList.remove("thinking");

        if (data.action === "clear") {
            chatBox.innerHTML = "";
            window.speechSynthesis.cancel();
            addMessage(data.message, "ai");
            speak(data.message);
        } else if (data.action === "open") {
            handleOpenAction(data.target, aiBubble);
            speak(data.message);
        } else {
            typeEffect(aiBubble, data.message);
            speak(data.message);
        }
    } catch (e) {
        aiBubble.classList.remove("thinking");
        aiBubble.textContent = "⚠️ Neural link severed.";
        speak("Neural link severed.");
    }
}

function handleOpenAction(target, aiBubble) {
    const content = aiBubble.querySelector('.msg-content') || aiBubble;
    const confirmMsg = `Axon AI needs permission to open: **${target}**. Grant permission?`;
    content.innerHTML = formatAIResponse(confirmMsg);
    aiBubble.dataset.fullText = `Axon AI needs permission to open: ${target}. Grant permission?`;

    const btnContainer = document.createElement("div");
    btnContainer.className = "permission-btns";
    btnContainer.style.marginTop = "10px";

    const yesBtn = document.createElement("button");
    yesBtn.textContent = "Allow";
    yesBtn.className = "perm-btn allow";
    yesBtn.onclick = () => {
        content.innerHTML = formatAIResponse(`${target.charAt(0).toUpperCase() + target.slice(1)} opened! 🏰♟️`);
        aiBubble.dataset.fullText = `${target} opened!`;
        if (target.toLowerCase() === "chess") window.open("https://www.chess.com", "_blank");
        else if (target.toLowerCase() === "calculator") window.open("https://www.google.com/search?q=calculator", "_blank");
        else window.open(`https://www.google.com/search?q=${target}`, "_blank");
    };

    const noBtn = document.createElement("button");
    noBtn.textContent = "Deny";
    noBtn.className = "perm-btn deny";
    noBtn.onclick = () => {
        content.innerHTML = formatAIResponse(`Permission denied. I cannot open ${target}.`);
        aiBubble.dataset.fullText = `Permission denied. I cannot open ${target}.`;
    };

    btnContainer.appendChild(yesBtn);
    btnContainer.appendChild(noBtn);
    content.appendChild(btnContainer);
}

function addMessage(text, sender, imageFile = null) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.dataset.fullText = text;

    const content = document.createElement("div");
    content.className = "msg-content";

    if (imageFile) {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(imageFile);
        img.className = "img-msg";
        content.appendChild(img);
    }

    if (sender === "ai") {
        content.innerHTML = formatAIResponse(text);
    } else if (text) {
        const textDiv = document.createElement("div");
        if (text.includes('class="cmd-highlight"')) {
            textDiv.innerHTML = text;
        } else {
            textDiv.textContent = text;
        }
        content.appendChild(textDiv);
    }
    msg.appendChild(content);

    const actions = document.createElement("div");
    actions.className = "msg-actions";

    const speakBtn = document.createElement("button");
    speakBtn.className = "msg-action-btn";
    speakBtn.innerHTML = "🔊";
    speakBtn.title = "Listen to message";
    speakBtn.onclick = () => {
        if (msg.classList.contains("thinking")) return;
        const textToSpeak = msg.dataset.fullText || (sender === "ai" ? text : content.textContent);
        speak(textToSpeak, true);
    };

    actions.appendChild(speakBtn);
    msg.appendChild(actions);

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
}

function formatAIResponse(text) {
    if (!text) return "";

    // Configure marked to use highlight.js
    marked.setOptions({
        highlight: function (code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        breaks: true,
        gfm: true
    });

    // Remove voice marker from visual display
    let displayText = text;
    const voiceMarker = "Optional Voice Response:";
    if (displayText.includes(voiceMarker)) {
        displayText = displayText.split(voiceMarker)[0].trim();
    }

    return marked.parse(displayText);
}

function typeEffect(element, text) {
    const content = element.querySelector('.msg-content') || element;
    element.dataset.fullText = text;

    let displayText = text;
    const voiceMarker = "Optional Voice Response:";
    if (displayText.includes(voiceMarker)) {
        displayText = displayText.split(voiceMarker)[0].trim();
    }

    if (displayText.length < 50 || displayText.includes("<") || displayText.includes("```") || displayText.includes("|")) {
        content.innerHTML = formatAIResponse(displayText);
        hljs.highlightAll();
        addCopyButtons();
        chatBox.scrollTop = chatBox.scrollHeight;
        return;
    }

    let i = 0;
    content.innerHTML = "";

    function type() {
        if (i < displayText.length) {
            let currentText = displayText.substring(0, i + 1);
            content.innerHTML = formatAIResponse(currentText);
            i++;
            chatBox.scrollTop = chatBox.scrollHeight;
            setTimeout(type, 5);
        } else {
            hljs.highlightAll();
            addCopyButtons();
        }
    }
    type();
}

function addCopyButtons() {
    document.querySelectorAll('.ai pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;
        const btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.innerHTML = 'Copy';
        btn.onclick = () => {
            const code = pre.querySelector('code').innerText;
            navigator.clipboard.writeText(code);
            btn.innerHTML = 'Copied!';
            setTimeout(() => btn.innerHTML = 'Copy', 2000);
        };
        pre.appendChild(btn);
    });
}

function handleEnter(e) { if (e.key === "Enter") askAI(); }
function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    document.getElementById("voice-icon").textContent = isVoiceEnabled ? "🔊" : "🔈";
    if (!isVoiceEnabled) window.speechSynthesis.cancel();
}
function speak(text, force = false) {
    window.speechSynthesis.cancel();
    const overlay = document.getElementById("speech-overlay");
    const speechTextDisp = document.getElementById("speech-text");

    if (!isVoiceEnabled && !force) {
        overlay.classList.add("hidden");
        return;
    }

    let speechText = text.replace(/<[^>]*>?/gm, ''); // Remove HTML tags
    const voiceMarker = "Optional Voice Response:";
    if (text.includes(voiceMarker)) {
        speechText = text.split(voiceMarker)[1].trim();
    }

    // Update UI
    speechTextDisp.textContent = speechText;
    overlay.classList.remove("hidden");

    const ut = new SpeechSynthesisUtterance(speechText);
    ut.onend = () => {
        setTimeout(() => {
            if (!window.speechSynthesis.speaking) {
                overlay.classList.add("hidden");
            }
        }, 1000);
    };
    window.speechSynthesis.speak(ut);
}
function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return alert("Browser not supported");

    recognition = new SpeechRecognition();
    const overlay = document.getElementById("voice-overlay");
    const transcriptDisp = document.getElementById("voice-transcript");
    const input = document.getElementById("question");

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        overlay.classList.remove("hidden");
        transcriptDisp.textContent = "Listening for neural sigals...";
    };

    recognition.onresult = (e) => {
        const transcript = Array.from(e.results)
            .map(result => result[0])
            .map(result => result.transcript)
            .join('');

        transcriptDisp.textContent = transcript;
        input.value = transcript;

        if (e.results[0].isFinal) {
            setTimeout(() => {
                stopListening();
                askAI();
            }, 800);
        }
    };

    recognition.onerror = (e) => {
        console.error("Neural Voice Error:", e.error);
        if (e.error === 'not-allowed') {
            transcriptDisp.textContent = "⚠️ Link Denied: Microphone access required.";
        } else {
            transcriptDisp.textContent = "⚠️ Signal interference detected.";
        }
        setTimeout(stopListening, 2000);
    };

    recognition.onend = () => {
        // Only hide if we aren't waiting for the final result timeout
        if (!input.value) overlay.classList.add("hidden");
    };

    recognition.start();
}

function stopListening() {
    if (recognition) {
        recognition.stop();
        document.getElementById("voice-overlay").classList.add("hidden");
    }
}

// Initial Greeting
document.addEventListener("DOMContentLoaded", () => {
    const welcomeMsg = `Hi there! I am **AXON AI**. How can I assist you today? Try saying "Hello" to see what I can do!`;
    addMessage(welcomeMsg, "ai");
});

