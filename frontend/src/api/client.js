import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1'
});

api.interceptors.request.use(config => {
  const wsId = localStorage.getItem('workspace_id');
  if (wsId) {
    config.headers['X-Workspace-ID'] = wsId;
  }
  return config;
});

export default api;
