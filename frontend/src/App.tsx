import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

interface ChatSession { 
  id: string; 
  title: string; 
  uploaded_file?: string;
}

interface Message { 
  role: 'user' | 'ai'; 
  content: string; 
  sources?: string[]; 
}

export default function App() {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/chats')
      .then(res => res.json())
      .then(data => {
        setChats(data);
        if (data.length > 0) setCurrentChatId(data[0].id);
      })
      .catch(err => console.error("Failed to load chats:", err));
  }, []);

  useEffect(() => {
    if (currentChatId) {
      fetch(`http://127.0.0.1:8000/chats/${currentChatId}/messages`)
        .then(res => res.json())
        .then(data => setMessages(data))
        .catch(err => console.error("Failed to load messages:", err));
    } else {
      setMessages([]);
    }
  }, [currentChatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createNewChat = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/chats', { method: 'POST' });
      const newChat = await res.json();
      setChats([...chats, { id: newChat.chat_id, title: newChat.title }]);
      setCurrentChatId(newChat.chat_id);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !currentChatId) {
      alert("Please select or create a chat first!");
      return;
    }
    
    const file = e.target.files[0];
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`http://127.0.0.1:8000/upload/${currentChatId}`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) throw new Error("Upload failed");
      
      setChats(prevChats => prevChats.map(chat => 
        chat.id === currentChatId 
          ? { ...chat, title: file.name, uploaded_file: file.name } 
          : chat
      ));
      
      alert('File processed successfully!');
    } catch (error: any) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentChatId || isLoading) return;

    const userMessage = input;
    setInput('');
    setIsLoading(true);

    setMessages(prev => [
      ...prev, 
      { role: 'user', content: userMessage },
      { role: 'ai', content: '' }
    ]);

    try {
      const res = await fetch(`http://127.0.0.1:8000/chat/${currentChatId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!res.body) throw new Error("No readable stream available");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = "";
      let finalSources: string[] = [];
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        
        const chunkValue = decoder.decode(value, { stream: true });
        accumulatedText += chunkValue;

        const sourceSplit = accumulatedText.split('__SOURCES__');
        const textPart = sourceSplit[0];

        if (sourceSplit.length > 1) {
          try {
            finalSources = JSON.parse(sourceSplit[1]);
          } catch (e) {
            console.error("Waiting for full JSON...");
          }
        }

        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = { 
            role: 'ai', 
            content: textPart,
            sources: finalSources.length > 0 ? finalSources : undefined
          };
          return newMessages;
        });
      }
    } catch (error: any) {
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = { 
          role: 'ai', 
          content: `Error: ${error.message}` 
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const activeChat = chats.find(c => c.id === currentChatId);

  return (
    <div className="layout">
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
              onClick={() => setCurrentChatId(chat.id)}
            >
              {chat.title}
            </div>
          ))}
        </div>
      </aside>

      <main className="main-content">
        {!currentChatId ? (
          <div className="center-prompt">Select or create a chat to begin.</div>
        ) : (
          <>
            <header className="top-bar">
              {/* Left Side: File Indicator */}
              <div className="file-indicator-container">
                {activeChat?.uploaded_file && (
                  <div className="file-indicator">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    {activeChat.uploaded_file}
                  </div>
                )}
              </div>
              
              {/* Right Side: Upload Button */}
              <label className="upload-btn">
                {isUploading ? 'Processing...' : 'Upload PDF'}
                <input 
                  type="file" 
                  accept=".pdf" 
                  onChange={handleFileUpload} 
                  disabled={isUploading} 
                />
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
                    
                    {/* Show "Thinking..." if empty, otherwise show Markdown */}
                    {msg.role === 'ai' && msg.content === '' && isLoading ? (
                      <span className="loading">Thinking...</span>
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}

                    {msg.sources && msg.sources.length > 0 && (
                      <details className="sources">
                        <summary>View Sources</summary>
                        {msg.sources.map((s, j) => (
                          <p key={j} className="source-text">{s}</p>
                        ))}
                      </details>
                    )}
                  </div>
                </div>
              ))}
              
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