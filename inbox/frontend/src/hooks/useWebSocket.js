import { useEffect, useRef, useState } from 'react';

/**
 * WebSocket Hook - 实时接收后端推送的数据
 * 
 * @param {Function} onMessage - 接收消息的回调函数
 * @returns {Object} - { connected, error, send }
 */
export function useWebSocket(onMessage) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef(null);
  
  const MAX_RECONNECT_ATTEMPTS = 10;
  const RECONNECT_INTERVAL = 3000; // 3秒后重连
  const PING_INTERVAL = 30000; // 30秒发送一次ping

  const connect = () => {
    try {
      // 获取WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws`;
      
      console.log('🔌 连接WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ WebSocket已连接');
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        
        // 启动ping心跳
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
            console.log('🏓 发送ping');
          }
        }, PING_INTERVAL);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 处理pong响应
          if (data.type === 'pong') {
            console.log('🏓 收到pong');
            return;
          }
          
          console.log('📨 收到WebSocket消息:', data.type);
          
          if (onMessage) {
            onMessage(data);
          }
        } catch (err) {
          console.error('❌ 解析WebSocket消息失败:', err);
        }
      };
      
      ws.onerror = (event) => {
        console.error('❌ WebSocket错误:', event);
        setError('WebSocket连接错误');
      };
      
      ws.onclose = () => {
        console.log('❌ WebSocket已断开');
        setConnected(false);
        
        // 停止ping心跳
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // 自动重连
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          console.log(`🔄 ${RECONNECT_INTERVAL/1000}秒后尝试重连 (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_INTERVAL);
        } else {
          setError('WebSocket重连失败，请刷新页面');
        }
      };
      
      wsRef.current = ws;
      
    } catch (err) {
      console.error('❌ 创建WebSocket连接失败:', err);
      setError('无法创建WebSocket连接');
    }
  };

  const send = (data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket未连接，无法发送消息');
    }
  };

  useEffect(() => {
    connect();
    
    // 清理函数
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { connected, error, send };
}
