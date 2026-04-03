import { useWorkspace } from './hooks/useWorkspace';
import Dashboard from './components/Dashboard';
import Navbar from './components/Navbar';
import SchemaExplorer from './components/SchemaExplorer';
import ChatPanel from './components/ChatPanel';
import NarrationOverlay from './components/NarrationOverlay';
import { useState } from 'react';

const MOCK_NARRATION_STEPS = [
  { target_id: 'chart_0', text: "Let's begin by looking at the first chart here. This gives us an overview of the primary metric.", duration: 4000 },
  { target_id: 'chart_1', text: "Moving closely to the next visualization, you can see how the trend changes dynamically.", duration: 4000 }
];

function AppContent() {
  const { workspaceId, workspace, loading, error, createWorkspace } = useWorkspace();
  const [dbUrl, setDbUrl] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isNarrating, setIsNarrating] = useState(false);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-white">Loading your workspace...</div>;
  }

  if (!workspaceId || !workspace) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-8 rounded-2xl w-full max-w-md shadow-2xl">
          <h1 className="text-3xl font-bold mb-6 text-center">Asklytics</h1>
          <p className="text-gray-300 mb-6 text-center">Connect your database to generate an instant dashboard.</p>
          {error && <div className="bg-red-500/20 text-red-200 p-3 rounded mb-4">{error}</div>}
          <form onSubmit={async (e) => {
            e.preventDefault();
            await createWorkspace(dbUrl);
          }}>
            <input 
              type="text" 
              placeholder="PostgreSQL or SQLite Connection URL" 
              className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 mb-4 text-white placeholder-gray-500 outline-none focus:border-blue-500 transition-colors"
              value={dbUrl}
              onChange={e => setDbUrl(e.target.value)}
              required
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-colors">
              Connect & Generate Dashboard
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden relative">
      <NarrationOverlay 
         steps={MOCK_NARRATION_STEPS} 
         isPlaying={isNarrating} 
         onClose={() => setIsNarrating(false)} 
      />
      <Navbar onChatToggle={() => setIsChatOpen(!isChatOpen)} onNarrate={() => setIsNarrating(true)} />
      <div className="flex flex-1 overflow-hidden relative">
        <SchemaExplorer />
        <main className="flex-1 overflow-y-auto p-6 relative">
          <Dashboard />
        </main>
        <ChatPanel isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
      </div>
    </div>
  );
}

export default function App() {
  return <AppContent />;
}
