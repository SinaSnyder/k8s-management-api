import axios from 'axios';

const api = axios.create({
  baseURL: 'http://api.rahimi.osdl.ir',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
