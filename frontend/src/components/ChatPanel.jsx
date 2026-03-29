import { X, Send, Bot, User } from 'lucide-react';
import { useWorkspace } from '../hooks/useWorkspace';
import { useState, useRef, useEffect } from 'react';
import api from '../api/client';

export default function ChatPanel({ isOpen, onClose }) {
  const { workspaceId, workspace, role, addChart, addChatMessage } = useWorkspace();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [workspace?.chat_history, isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || role === 'view') return;
    
    const userMsg = input.trim();
    setInput('');
    addChatMessage({ role: 'user', content: userMsg });
    setLoading(true);

    try {
      const res = await api.post(`/workspaces/${workspaceId}/chat`, { query: userMsg });
      addChart(res.data.plotly_payload);
      addChatMessage({ 
          role: 'assistant', 
          content: `I've added the chart to your dashboard.\n\n\`\`\`sql\n${res.data.sql_used}\n\`\`\`` 
      });
    } catch (err) {
      addChatMessage({ 
          role: 'assistant', 
          content: `Error: ${err.response?.data?.detail || err.message}` 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className={`absolute top-0 right-0 h-full w-96 bg-zinc-900 border-l border-white/10 shadow-2xl transition-transform duration-300 z-20 flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
      <div className="p-4 border-b border-white/10 flex items-center justify-between bg-black/20">
        <h2 className="font-semibold text-gray-200 flex items-center gap-2"><Bot size={18}/> Asklytics Agent</h2>
        <button onClick={onClose} className="p-1 hover:bg-white/10 rounded text-gray-400"><X size={18} /></button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar flex flex-col">
        {workspace?.chat_history?.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-blue-600' : 'bg-purple-600'}`}>
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className={`px-4 py-2 rounded-2xl max-w-[80%] text-sm ${msg.role === 'user' ? 'bg-blue-600/20 border border-blue-500/30 text-blue-100' : 'bg-white/10 border border-white/10 text-gray-200'}`}>
              <div className="whitespace-pre-wrap font-sans">{msg.content}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-purple-600">
              <Bot size={14} />
            </div>
            <div className="px-4 py-2 rounded-2xl bg-white/10 border border-white/10 text-gray-200 flex items-center gap-1 text-sm">
              <span className="animate-bounce">●</span><span className="animate-bounce" style={{animationDelay: '0.2s'}}>●</span><span className="animate-bounce" style={{animationDelay: '0.4s'}}>●</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-black/20 border-t border-white/10">
        <form onSubmit={handleSubmit} className="flex gap-2 relative">
          <input 
            type="text" 
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={role === 'view' || loading}
            placeholder={role === 'view' ? "Upgrade to edit access to interact." : "Ask for a new chart..."}
            className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm text-white focus:border-blue-500 outline-none disabled:opacity-50 disabled:cursor-not-allowed pr-10"
          />
          <button 
            type="submit" 
            disabled={role === 'view' || loading || !input.trim()}
            className="absolute right-1 top-1 p-1.5 bg-blue-600 hover:bg-blue-500 rounded-full text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </aside>
  );
}
