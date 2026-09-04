import api from './axios';

export const getClusters = () => api.get('/cluster');
export const createCluster = (data) => api.post('/cluster', data);

export const getNamespaces = (clusterId) => api.get(`/namespace?cluster_id=${clusterId}`);
export const createNamespace = (data) => api.post('/namespace', data);
export const deleteNamespace = (id) => api.delete(`/namespace/${id}`);

export const getApps = (namespaceId) => api.get(`/app?namespace_id=${namespaceId}`);
export const createApp = (data) => api.post('/app', data);
export const updateApp = (id, data) => api.put(`/app/${id}`, data);
export const deleteApp = (id) => api.delete(`/app/${id}`);
