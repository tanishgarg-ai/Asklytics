import { X } from 'lucide-react';
import { useState } from 'react';
import { useWorkspace } from '../hooks/useWorkspace';

export default function SettingsModal({ onClose }) {
  const { updateSettings } = useWorkspace();
  const [dbUrl, setDbUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await updateSettings(dbUrl);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to update connection");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white"><X size={20}/></button>
        <h2 className="text-xl font-semibold mb-4 text-white">Workspace Settings</h2>
        
        {error && <div className="bg-red-500/20 text-red-200 p-2 rounded mb-4 text-sm">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-gray-400 mb-1">Update Database Connection</label>
          <input 
            type="text" 
            placeholder="New connection URL..." 
            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500 mb-4"
            value={dbUrl}
            onChange={e => setDbUrl(e.target.value)}
            required
          />
          <p className="text-xs text-yellow-500/80 mb-4">Warning: This will clear your current dashboard and regenerate it.</p>
          
          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-medium py-2 rounded-lg transition-colors"
          >
            {loading ? 'Reconnecting & Generating...' : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
}
