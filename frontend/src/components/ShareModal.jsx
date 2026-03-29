import { X, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { useWorkspace } from '../hooks/useWorkspace';
import api from '../api/client';

export default function ShareModal({ onClose }) {
  const { workspaceId } = useWorkspace();
  const [role, setRole] = useState('view');
  const [expiry, setExpiry] = useState(24);
  const [link, setLink] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/workspaces/${workspaceId}/share`, {
        role,
        expires_in_hours: expiry
      });
      setLink(res.data.share_url);
      setCopied(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate link");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white"><X size={20}/></button>
        <h2 className="text-xl font-semibold mb-4 text-white">Share Workspace</h2>
        
        {error && <div className="bg-red-500/20 text-red-200 p-2 rounded mb-4 text-sm">{error}</div>}
        
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Access Role</label>
            <select 
              value={role} 
              onChange={e => setRole(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
            >
              <option value="view">View Only</option>
              <option value="edit">Edit (Can chat & alter dashboard)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Expires In</label>
            <select 
              value={expiry} 
              onChange={e => setExpiry(Number(e.target.value))}
              className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
            >
              <option value={24}>24 Hours</option>
              <option value={168}>7 Days</option>
              <option value={720}>30 Days</option>
            </select>
          </div>
        </div>
        
        {!link ? (
          <button 
            onClick={handleGenerate} 
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-medium py-2 rounded-lg transition-colors"
          >
            {loading ? 'Generating...' : 'Generate Share Link'}
          </button>
        ) : (
          <div className="mt-4">
            <label className="block text-sm font-medium text-green-400 mb-1">Link Generated!</label>
            <div className="flex gap-2">
              <input 
                type="text" 
                readOnly 
                value={link} 
                className="flex-1 bg-black/50 border border-green-500/30 rounded-lg px-3 py-2 text-sm text-gray-300"
              />
              <button 
                onClick={handleCopy}
                className="px-3 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors"
              >
                {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
