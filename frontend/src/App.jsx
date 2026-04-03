import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Send, 
  Mic, 
  Image as ImageIcon, 
  X, 
  Plus, 
  MessageSquare, 
  Gamepad2, 
  Palette, 
  Volume2, 
  VolumeX,
  RefreshCw,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  BrainCircuit,
  History,
  Target,
  Trophy,
  Puzzle,
  Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// -------------------- UI COMPONENTS --------------------

// 1. Sidebar Component
const Sidebar = ({ currentMode, setMode, onNewThread, onShowGames, onPlayGame, messages }) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside className={`transition-all duration-300 ${isOpen ? 'w-64' : 'w-16'} bg-[#17191e] border-r border-white/5 flex flex-col z-50`}>
      <div className="p-4 flex items-center justify-between overflow-hidden">
        {isOpen && <h1 className="font-bold text-lg flex items-center gap-2"><span className="text-indigo-500">🧠</span> AXON AI</h1>}
        <button onClick={() => setIsOpen(!isOpen)} className="p-1 hover:bg-white/5 rounded text-axon-muted">
          {isOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      <div className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        <button 
          onClick={onNewThread}
          className="w-full flex items-center gap-3 p-3 rounded-xl bg-[#1e2229] border border-white/10 text-white hover:bg-indigo-600 hover:border-indigo-500/50 hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] transition-all duration-300 group mb-6 hover:scale-[1.02]"
        >
          <div className="p-1 px-1.5 rounded-lg bg-white/5 group-hover:bg-white/20 transition-all">
            <Plus size={18} />
          </div>
          {isOpen && <span className="text-sm font-bold tracking-tight">Reset Neural Core</span>}
        </button>

        <NavItem 
          active={currentMode === 'nexus'} 
          icon={<BrainCircuit size={18} />} 
          label="Neural Nexus 3-in-1" 
          isOpen={isOpen} 
          onClick={() => setMode('nexus')} 
        />

        <NavItem 
          active={currentMode === 'games'} 
          icon={<Gamepad2 size={18} />} 
          label="Game Engine" 
          isOpen={isOpen} 
          onClick={() => setMode('games')} 
        />

        {currentMode === 'games' && isOpen && (
          <div className="mt-8 px-1">
            <h3 className="text-[10px] uppercase tracking-widest text-[#6366f1] font-bold mb-4 flex items-center gap-2">
              <Trophy size={12} /> Neural Arcade
            </h3>
            <div className="space-y-1 max-h-[350px] overflow-y-auto pr-1 scrollbar-history">
              <GameButton icon={<Target size={14} />} label="Tic-Tac-Toe" onClick={() => onPlayGame("/tictactoe")} />
              <GameButton icon={<Sparkles size={14} />} label="Guess Number" onClick={() => onPlayGame("/guessnumber")} />
              <GameButton icon={<MessageSquare size={14} />} label="20 Questions" onClick={() => onPlayGame("Play 20 Questions")} />
              <GameButton icon={<X size={14} />} label="Hangman" onClick={() => onPlayGame("Play Hangman")} />
              <GameButton icon={<Palette size={14} />} label="Word Chain" onClick={() => onPlayGame("Play Word Chain")} />
              <GameButton icon={<MoreVertical size={14} />} label="Would You Rather" onClick={() => onPlayGame("Play Would You Rather")} />
              <GameButton icon={<Puzzle size={14} />} label="Trivia Quiz" onClick={() => onPlayGame("Play Trivia")} />
              <GameButton icon={<BrainCircuit size={14} />} label="Brain Teaser" onClick={() => onPlayGame("Play Brain Teaser")} />
              <GameButton icon={<Gamepad2 size={14} />} label="Emoji Mystery" onClick={() => onPlayGame("Play Emoji Mystery")} />
            </div>
          </div>
        )}

        {isOpen && messages.length > 2 && (
          <div className="mt-8 px-1">
            <h3 className="text-[10px] uppercase tracking-widest text-white/30 font-bold mb-4">Recent Neural Links</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-2 scrollbar-history">
              {messages.filter(m => m.role === 'user').slice(-8).reverse().map((m, i) => (
                <button 
                  key={i} 
                  className="w-full text-left p-2.5 rounded-xl transition-all duration-300 group border border-transparent hover:bg-indigo-600 hover:shadow-[0_x_10px_rgba(99,102,241,0.2)] hover:scale-[1.01] active:scale-95"
                  onClick={() => {/* Navigate history */}}
                >
                  <div className="text-[11px] text-axon-muted group-hover:text-white truncate font-semibold flex items-center gap-2 transition-all">
                    <History size={12} className="text-white/20 group-hover:text-white" />
                    {m.content}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-3">
          <img 
            src="https://avatars.githubusercontent.com/u/233944797?v=4" 
            alt="Profile" 
            className="w-8 h-8 rounded-full border border-white/10 object-cover"
          />
          {isOpen && (
            <div className="flex-1 overflow-hidden">
              <div className="text-xs font-semibold truncate">Yash Tambade</div>
              <div className="text-[10px] text-axon-muted truncate italic">Neural Core v1.0</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

const NavItem = ({ active, icon, label, isOpen, onClick }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-300 transform ${active ? 'bg-indigo-600 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)] scale-[1.02] hover:brightness-110' : 'text-axon-muted hover:bg-white/5 hover:text-white'}`}
  >
    {icon}
    {isOpen && <span className="text-sm font-semibold">{label}</span>}
  </button>
);

const GameButton = ({ icon, label, onClick }) => (
  <button 
    onClick={onClick}
    className="w-full flex items-center gap-3 p-2.5 rounded-xl text-axon-muted hover:bg-white/5 hover:text-white border border-transparent transition-all duration-300 group active:scale-95 hover:translate-x-1"
  >
    <div className="p-1.5 rounded-lg bg-white/5 group-hover:bg-white/10 transition-all">
      {icon}
    </div>
    <span className="text-[11px] font-bold tracking-wide uppercase transition-all">{label}</span>
  </button>
);

// 2. Message Bubble Component
const Message = ({ msg, voiceEnabled }) => {
  const isAI = msg.role === 'assistant';
  const displayContent = msg.content.split('Optional Voice Response:')[0].trim();

  // Highlight.js initialization inside marked
  useEffect(() => {
    hljs.highlightAll();
  }, [msg.content]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full mb-8 flex ${isAI ? 'justify-start' : 'justify-end'}`}
    >
      <div className={`max-w-[85%] flex gap-4 ${isAI ? 'flex-row' : 'flex-row-reverse'}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full overflow-hidden flex items-center justify-center text-sm ${isAI ? 'bg-indigo-500 text-white cursor-pointer' : 'border border-white/10'}`}>
          {isAI ? (
            <BrainCircuit size={18} />
          ) : (
            <img 
              src="https://avatars.githubusercontent.com/u/233944797?v=4" 
              alt="User" 
              className="w-full h-full object-cover"
            />
          )}
        </div>
        
        <div className={`px-4 py-3 rounded-2xl ${isAI ? 'bg-transparent text-axon-text' : 'bg-[#1e2229] border border-white/5 shadow-xl'}`}>
          {msg.imageUrl && (
            <img src={msg.imageUrl} alt="upload" className="max-w-[200px] rounded-lg mb-2 border border-white/10" />
          )}
          
          <div 
            className="markdown-content text-[15px]" 
            dangerouslySetInnerHTML={{ __html: isAI ? marked.parse(displayContent) : displayContent }} 
          />

          {msg.images && (
            <div className="flex gap-2 flex-wrap mt-4">
              {msg.images.map((url, i) => (
                <img key={i} src={url} alt="search" className="w-48 h-48 object-cover rounded-xl border border-white/10 hover:scale-105 transition-transform cursor-pointer" />
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// -------------------- MAIN APP COMPONENT --------------------

const App = () => {
  const [isBooting, setIsBooting] = useState(true);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Axon system initialized. Neural link established. How can I assist you in your workspace today?', timestamp: Date.now() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('nexus');
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => {
    // 5.5s Boot Sequence from loading.html
    const bootTimer = setTimeout(() => {
      setIsBooting(false);
    }, 5500);

    // Stop all speech on unmount or refresh
    const handleBeforeUnload = () => window.speechSynthesis.cancel();
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      clearTimeout(bootTimer);
      window.speechSynthesis.cancel();
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
    const timer = setInterval(() => {
      const TEN_MINS = 10 * 60 * 1000;
      setMessages(prev => prev.filter(m => Date.now() - m.timestamp < TEN_MINS));
    }, 30000); // Check every 30s
    return () => clearInterval(timer);
  }, [messages, loading]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleNewThread = async () => {
    setMessages([{ role: 'assistant', content: 'Axon system reset. Starting fresh neural link...' }]);
    setMode('chat');
    window.speechSynthesis.cancel();
    try {
      await axios.post('/api/chat', { question: '/clear' });
    } catch (err) {
      console.warn("Server reset fail", err);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Voice input is not supported in this browser.");
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
        // Auto-submit after voice input
        setTimeout(() => {
          handleSubmit(null, transcript);
        }, 100);
      };
      recognition.onerror = (event) => {
        console.error("Speech Recognition Error", event.error);
        setIsListening(false);
      };
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
      recognition.start();
    }
  };

  const stopSpeech = () => {
    window.speechSynthesis.cancel();
  };

  const handleSubmit = async (e, voiceTranscript = null) => {
    if (e) e.preventDefault();
    let currentInput = (voiceTranscript || input).trim();
    if (!currentInput && !selectedImage) return;

    // Auto-command detection for 3-in-1 Nexus Mode
    if (!currentInput.startsWith('/')) {
      const lower = currentInput.toLowerCase();
      if (lower.includes('tic') || (lower.includes('toe') && lower.includes('play'))) currentInput = '/tictactoe';
      else if (lower.includes('guess') && lower.includes('number')) currentInput = '/guessnumber';
    }

    const userMsg = { role: 'user', content: voiceTranscript || input, imageUrl: previewUrl, timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    
    setInput('');
    const currentImage = selectedImage;
    setSelectedImage(null);
    setPreviewUrl('');
    setLoading(true);

    const formData = new FormData();
    formData.append('question', currentInput);
    if (currentImage) formData.append('image', currentImage);

    try {
      const response = await axios.post('/api/chat', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const aiMsg = { 
        role: 'assistant', 
        content: response.data.message,
        images: response.data.images || null,
        timestamp: Date.now()
      };
      
      setMessages(prev => [...prev, aiMsg]);

      // Simple Text-to-Speech
      if (voiceEnabled) {
        let speechText = response.data.message.split('Optional Voice Response:')[1] || response.data.message;
        speechText = speechText.replace(/<[^>]*>?/gm, ''); // Clean HTML
        const utterance = new SpeechSynthesisUtterance(speechText);
        window.speechSynthesis.speak(utterance);
      }

    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Neural Link Error: System experienced interference. Please retry.' }]);
    } finally {
      setLoading(false);
    }
  };

  if (isBooting) {
    return (
      <div className="fixed inset-0 bg-[#050505] flex flex-col items-center justify-center z-[9999] overflow-hidden">
        {/* Cyberpunk Grid */}
        <div className="absolute inset-0 opacity-20 pointer-events-none" 
             style={{ 
               backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(18, 16, 16, 0.4) 1px, transparent 1px)',
               backgroundSize: '50px 50px' 
             }}></div>
        
        <div className="flex flex-col items-center z-10">
          <div className="flex items-end gap-3 mb-10 h-24">
            {[20, 40, 60, 100, 60, 40, 20].map((h, i) => (
              <motion.div 
                key={i} 
                initial={{ height: 0 }}
                animate={{ height: [`${h * 0.4}%`, `${h}%`, `${h * 0.4}%`] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.1 }}
                className="w-1.5 bg-indigo-500 rounded-full shadow-[0_0_20px_rgba(99,102,241,0.6)]"
              />
            ))}
          </div>

          <motion.h1 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-4xl font-black tracking-[12px] text-white uppercase mb-4 relative"
          >
            Axon AI
            <div className="absolute top-0 left-0 w-full h-full text-indigo-500 blur-[2px] opacity-50 mix-blend-screen animate-pulse">Axon AI</div>
          </motion.h1>

          <div className="text-center">
            <p className="text-indigo-400 font-mono text-[10px] tracking-[4px] uppercase mb-1">Establishing Neural Link...</p>
            <p className="text-gray-600 font-mono text-[9px] italic tracking-widest">Core decrypted | Creator: Yash Tambade | Memory initialized</p>
          </div>

          <div className="w-64 h-[1px] bg-white/5 mt-8 relative overflow-hidden">
             <motion.div 
               initial={{ left: '-100%' }}
               animate={{ left: '100%' }}
               transition={{ duration: 5.5, ease: "linear" }}
               className="absolute top-0 w-full h-full bg-indigo-500 shadow-[0_0_10px_#6366f1]"
             />
          </div>
        </div>
      </div>
    );
  }

  const handleShowGames = () => {
    setMode('chat');
    handleSubmit(null, "List all the interactive games you can play with me!");
  };

  const handlePlayGame = (gameCommand) => {
    setMode('chat');
    handleSubmit(null, gameCommand);
  };

  return (
    <div className="flex h-screen w-screen bg-[#0f1115] text-axon-text font-sans">
      <Sidebar 
        currentMode={mode} 
        setMode={setMode} 
        onNewThread={handleNewThread} 
        onShowGames={handleShowGames}
        onPlayGame={handlePlayGame}
        messages={messages} 
      />

      <main className="flex-1 flex flex-col relative h-screen">
        {/* Top bar */}
        <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-[#0f1115]/50 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-2 text-sm text-axon-muted">
             <BrainCircuit size={16} className="text-indigo-500" />
             <span>Neural Channel • {mode.toUpperCase()}</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={stopSpeech}
              className="p-2 rounded-lg text-axon-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Stop Voice Output"
            >
              <VolumeX size={20} />
            </button>
            <button 
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              className={`p-2 rounded-lg transition-colors ${voiceEnabled ? 'text-indigo-400 bg-indigo-500/10' : 'text-axon-muted'}`}
            >
              {voiceEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </button>
            <button className="text-axon-muted hover:text-white"><MoreVertical size={20} /></button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-3xl mx-auto">
            {messages.map((m, i) => (
              <Message key={i} msg={m} voiceEnabled={voiceEnabled} />
            ))}
            {loading && (
              <div className="flex gap-4 mb-8">
                <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-500 flex items-center justify-center animate-pulse">
                  🧠
                </div>
                <div className="flex items-center gap-2 text-indigo-400 text-sm font-medium">
                  <RefreshCw size={14} className="animate-spin text-indigo-500" />
                  Neural Processing...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input Dock */}
        <div className="w-full max-w-4xl mx-auto px-6 pb-10">
          <div className="relative group">
            <AnimatePresence>
              {previewUrl && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="absolute bottom-full mb-4 left-0 p-2 bg-[#1e2229] border border-white/10 rounded-2xl shadow-2xl"
                >
                  <div className="relative w-32 h-32">
                    <img src={previewUrl} alt="preview" className="w-full h-full object-cover rounded-xl" />
                    <button 
                      onClick={() => { setSelectedImage(null); setPreviewUrl(''); }}
                      className="absolute -top-2 -right-2 bg-red-500 text-white p-1 rounded-full shadow-lg"
                    >
                      <X size={12} />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <form 
              onSubmit={handleSubmit}
              className="bg-[#1e2229] border border-white/10 rounded-2xl p-2 flex items-end gap-2 focus-within:border-indigo-500/50 hover:border-indigo-500/30 transition-all duration-300 shadow-2xl focus-within:shadow-[0_0_20px_rgba(99,102,241,0.1)]"
            >
              <input 
                type="file" 
                id="image-file" 
                accept="image/*" 
                className="hidden" 
                onChange={handleFileChange}
              />
              <button 
                type="button"
                onClick={() => document.getElementById('image-file').click()}
                className="p-3 text-axon-muted hover:text-white hover:bg-white/5 rounded-xl transition-colors"
              >
                <ImageIcon size={22} />
              </button>

              <textarea 
                rows="1"
                placeholder="Ask anything or search anything"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                className="flex-1 bg-transparent border-none outline-none resize-none py-3 px-2 text-[16px] max-h-48 scrollbar-hide"
              />

              <button 
                type="button"
                onClick={toggleListening}
                className={`p-3 rounded-xl transition-colors hidden sm:block ${isListening ? 'text-red-500 animate-pulse bg-red-500/10' : 'text-axon-muted hover:text-white hover:bg-white/5'}`}
              >
                <Mic size={22} />
              </button>

              <button 
                type="submit"
                disabled={loading || (!input.trim() && !selectedImage)}
                className={`p-3 rounded-xl transition-all ${loading || (!input.trim() && !selectedImage) ? 'text-white/20' : 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 hover:scale-105'}`}
              >
                <Send size={22} />
              </button>
            </form>
            <p className="text-[10px] text-center text-axon-muted mt-3 font-medium opacity-50">
             ⚠️ - Axon may make mistakes, so please verify important information.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
