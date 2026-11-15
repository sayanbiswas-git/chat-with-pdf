import { useState, useEffect, useRef } from 'react';
import './App.css';

interface ChatSession { id: string; title: string; }
interface Message { role: 'user' | 'ai'; content: string; sources?: string[]; }

export default function App() {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chats on start
  useEffect(() => {
    fetch('http://127.0.0.1:8000/chats')
      .then(res => res.json())
      .then(data => {
        setChats(data);
        if (data.length > 0) setCurrentChatId(data[0].id);
      });
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createNewChat = async () => {
    const res = await fetch('http://127.0.0.1:8000/chats', { method: 'POST' });
    const newChat = await res.json();
    setChats([...chats, { id: newChat.chat_id, title: newChat.title }]);
    setCurrentChatId(newChat.chat_id);
    setMessages([]);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !currentChatId) {
      alert("Please select or create a chat first!");
      return;
    }
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', e.target.files[0]);

    try {
      const res = await fetch(`http://127.0.0.1:8000/upload/${currentChatId}`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      alert('File processed successfully!');
    } catch (error: any) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentChatId) return;

    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(`http://127.0.0.1:8000/chat/${currentChatId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Error connecting to server.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="layout">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-header">Cowork</div>
        <button className="new-chat-btn" onClick={createNewChat}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
          New Chat
        </button>
        <div className="chat-list">
          {chats.map(chat => (
            <div 
              key={chat.id} 
              className={`chat-item ${chat.id === currentChatId ? 'active' : ''}`}
              onClick={() => { setCurrentChatId(chat.id); setMessages([]); }}
            >
              {chat.title}
            </div>
          ))}
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">
        {!currentChatId ? (
          <div className="center-prompt">Select or create a chat to begin.</div>
        ) : (
          <>
            <header className="top-bar">
              <label className="upload-btn">
                {isUploading ? 'Processing...' : 'Upload PDF'}
                <input type="file" accept=".pdf" onChange={handleFileUpload} disabled={isUploading} />
              </label>
            </header>

            <div className="chat-window">
              {messages.length === 0 && (
                <div className="center-prompt">
                  <h2>Tell me what you need.</h2>
                </div>
              )}
              
              {messages.map((msg, i) => (
                <div key={i} className={`message-row ${msg.role}`}>
                  <div className="message-content">
                    {msg.content}
                    {msg.sources && msg.sources.length > 0 && (
                      <details className="sources">
                        <summary>View Sources</summary>
                        {msg.sources.map((s, j) => <p key={j} className="source-text">{s}</p>)}
                      </details>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="message-row ai">
                  <div className="message-content loading">Thinking...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-container">
              <form onSubmit={sendMessage} className="input-box">
                <input
                  type="text"
                  placeholder="Ask anything..."
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  disabled={isLoading}
                />
                <button type="submit" disabled={!input.trim() || isLoading}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
              </form>
            </div>
          </>
        )}
      </main>
    </div>
  );
}