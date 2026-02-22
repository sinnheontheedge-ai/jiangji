import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ✅ 修复: 创建独立的axios实例用于非/api/v1的接口
const symbolsApi = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// symbols API也需要拦截器
symbolsApi.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('Symbols API Error:', error);
    return Promise.reject(error);
  }
);

// 策略相关API
export const strategyAPI = {
  list: () => api.get('/strategies'),
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/strategies/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (id) => api.delete(`/strategies/${id}`),
  get: (id) => api.get(`/strategies/${id}`),
};

// 账户相关API
export const accountAPI = {
  list: () => api.get('/accounts'),
  create: (data) => api.post('/accounts', data),
  update: (id, data) => api.put(`/accounts/${id}`, data),
  delete: (id) => api.delete(`/accounts/${id}`),
  get: (id) => api.get(`/accounts/${id}`),
};

// 实例相关API
export const instanceAPI = {
  list: () => api.get('/instances'),
  create: (data) => api.post('/instances', data),
  update: (id, data) => api.put(`/instances/${id}`, data),
  delete: (id) => api.delete(`/instances/${id}`),
  get: (id) => api.get(`/instances/${id}`),
  start: (id) => api.post(`/instances/${id}/start`),
  stop: (id) => api.post(`/instances/${id}/stop`),
};

// 订单相关API
export const orderAPI = {
  list: (params) => api.get('/orders', { params }),
  get: (id) => api.get(`/orders/${id}`),
  cancel: (id) => api.post(`/orders/${id}/cancel`),
};

// 持仓相关API
export const positionAPI = {
  list: (params) => api.get('/positions', { params }),
  get: (id) => api.get(`/positions/${id}`),
  close: (id) => api.post(`/positions/${id}/close`),
};

// ✅ 新增: 交易对相关API
export const symbolsAPI = {
  /**
   * 获取交易所的交易对列表
   * @param {string} exchange - 交易所名称 (binance, okx, bybit)
   * @param {object} params - 查询参数
   * @param {string} params.contract_type - 合约类型 (perpetual, future)
   * @param {string} params.quote_currency - 计价货币 (USDT, BUSD)
   * @param {boolean} params.force_refresh - 是否强制刷新缓存
   */
  getExchangeSymbols: (exchange, params = {}) => 
    symbolsApi.get(`/symbols/exchanges/${exchange}/symbols`, { params }),
  
  /**
   * 刷新交易所交易对缓存
   * @param {string} exchange - 交易所名称
   */
  refreshSymbols: (exchange) => 
    symbolsApi.post(`/symbols/exchanges/${exchange}/symbols/refresh`),
};

// 系统相关API
export const systemAPI = {
  status: () => api.get('/system/status'),
  stats: () => api.get('/system/stats'),
  getNotificationConfig: () => api.get('/system/notifications/config'),
  updateNotificationConfig: (data) => api.put('/system/notifications/config', data),
  getNotificationHistory: (params) => api.get('/system/notifications/history', { params }),
  testNotificationChannel: (channel, config) => api.post('/system/notifications/test', { channel, config }),
};

export default api;
