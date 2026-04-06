import { useState, useEffect, createContext, useContext } from 'react';
import { jwtDecode } from 'jwt-decode';
import api from '../api/client';

const WorkspaceContext = createContext();

export const WorkspaceProvider = ({ children }) => {
  const [workspace, setWorkspace] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    let wsId = null;
    let wsRole = 'owner';

    if (token) {
      try {
        const decoded = jwtDecode(token);
        wsId = decoded.workspace_id;
        wsRole = decoded.role;
        // The token needs to be passed in requests via ?token=... or header.
        // We'll attach it to a custom header if needed, but endpoint expects ?token= or X-Workspace-ID.
        // For shared view, if we use X-Workspace-ID the backend returns Not Authorized unless we pass the token string.
        // The simplest way is to inject token as query param, or update interceptor.
        // Let's store token in state and interceptor.
        localStorage.setItem('share_token', token);
      } catch (e) {
        console.error("Invalid token", e);
      }
    } else {
      wsId = localStorage.getItem('workspace_id');
      localStorage.removeItem('share_token');
    }

    if (wsId) {
      setWorkspaceId(wsId);
      setRole(wsRole);
      loadWorkspace(wsId, token);
    } else {
      setLoading(false);
    }
  }, []);

  const loadWorkspace = async (id, token = null) => {
    try {
      setLoading(true);
      const url = token ? `/workspaces/${id}?token=${token}` : `/workspaces/${id}`;
      const res = await api.get(url);
      setWorkspace(res.data);
      if (!token && res.data.role === 'owner') {
         localStorage.setItem('workspace_id', id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      if (err.response?.status === 404) {
          localStorage.removeItem('workspace_id');
          setWorkspaceId(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const createWorkspace = async (db_url) => {
    setLoading(true);
    try {
      const res = await api.post('/workspaces', { db_url });
      setWorkspace(res.data);
      setWorkspaceId(res.data.workspace_id);
      setRole('owner');
      localStorage.setItem('workspace_id', res.data.workspace_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  const updateSettings = async (db_url) => {
     setLoading(true);
     setError(null);
     try {
       const res = await api.put(`/workspaces/${workspaceId}/settings`, { db_url });
       setWorkspace(res.data.workspace);
     } catch (err) {
       setError(err.response?.data?.detail || err.message);
       throw err;
     } finally {
       setLoading(false);
     }
  }

  const updateDashboard = async (newDashboard) => {
    setWorkspace(prev => ({ ...prev, dashboard: newDashboard }));
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const url = token ? `/workspaces/${workspaceId}/dashboard?token=${token}` : `/workspaces/${workspaceId}/dashboard`;
      await api.put(url, { dashboard: newDashboard });
    } catch (err) {
      console.error("Failed to update dashboard", err);
    }
  };

  const refreshDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const url = token ? `/workspaces/${workspaceId}/refresh?token=${token}` : `/workspaces/${workspaceId}/refresh`;
      const res = await api.post(url);
      setWorkspace(prev => ({ 
        ...prev, 
        dashboard: res.data.dashboard,
        schema: res.data.schema || prev.schema 
      }));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const addChart = (chart) => {
      setWorkspace(prev => ({
          ...prev,
          dashboard: [...prev.dashboard, chart]
      }));
  };

  const addChatMessage = (msg) => {
      setWorkspace(prev => ({
          ...prev,
          chat_history: [...(prev.chat_history || []), msg]
      }));
  }

  return (
    <WorkspaceContext.Provider value={{ 
        workspace, workspaceId, role, loading, error, 
        createWorkspace, loadWorkspace, updateSettings, addChart, addChatMessage, updateDashboard, refreshDashboard 
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => useContext(WorkspaceContext);
