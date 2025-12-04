import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type WebSocketEvent = {
  type: "record_added" | "record_removed" | "record_updated";
  record_id: string;
  data?: any;
};

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  enabled?: boolean; // Allow disabling WebSocket
}

// Global singleton to prevent multiple connections in dev mode
let globalWs: WebSocket | null = null;
let globalReconnectAttempts = 0;
let globalReconnectTimeout: NodeJS.Timeout | null = null;
let globalPingInterval: NodeJS.Timeout | null = null;

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    pingInterval = 30000,
    enabled = true, // Default to enabled
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  // Use refs to store callbacks to avoid recreating connection on callback changes
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  }, [onMessage, onConnect, onDisconnect, onError]);

  const clearReconnectTimeout = useCallback(() => {
    if (globalReconnectTimeout) {
      clearTimeout(globalReconnectTimeout);
      globalReconnectTimeout = null;
    }
  }, []);

  const clearPingInterval = useCallback(() => {
    if (globalPingInterval) {
      clearInterval(globalPingInterval);
      globalPingInterval = null;
    }
  }, []);

  const startPingInterval = useCallback(() => {
    clearPingInterval();
    globalPingInterval = setInterval(() => {
      if (globalWs?.readyState === WebSocket.OPEN) {
        globalWs.send(JSON.stringify({ type: "ping" }));
      }
    }, pingInterval);
  }, [pingInterval, clearPingInterval]);

  const connect = useCallback(() => {
    // If already connected, reuse existing connection
    if (globalWs?.readyState === WebSocket.OPEN) {
      setStatus("connected");
      return;
    }

    // If connecting, wait
    if (globalWs?.readyState === WebSocket.CONNECTING) {
      setStatus("connecting");
      return;
    }

    // Don't attempt to reconnect if we've exceeded max attempts
    if (globalReconnectAttempts >= maxReconnectAttempts) {
      setStatus("error");
      return;
    }

    setStatus("connecting");
    clearReconnectTimeout();

    try {
      const ws = new WebSocket(`${WS_URL}/api/ws`);
      globalWs = ws;

      ws.onopen = () => {
        setStatus("connected");
        globalReconnectAttempts = 0;
        startPingInterval();
        onConnectRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Ignore pong messages
          if (data.type === "pong") {
            return;
          }

          const wsEvent: WebSocketEvent = {
            type: data.type,
            record_id: data.record_id,
            data: data.data,
          };

          setLastEvent(wsEvent);
          onMessageRef.current?.(wsEvent);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        setStatus("error");
        onErrorRef.current?.(error);
      };

      ws.onclose = (event) => {
        setStatus("disconnected");
        clearPingInterval();
        onDisconnectRef.current?.();

        // Only reconnect if not a normal closure and under max attempts
        if (event.code !== 1000 && globalReconnectAttempts < maxReconnectAttempts) {
          const delay = Math.min(
            reconnectInterval * Math.pow(2, globalReconnectAttempts),
            30000
          );

          globalReconnectTimeout = setTimeout(() => {
            globalReconnectAttempts++;
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setStatus("error");
    }
  }, [
    reconnectInterval,
    maxReconnectAttempts,
    startPingInterval,
    clearPingInterval,
    clearReconnectTimeout,
  ]);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    clearPingInterval();

    if (globalWs) {
      globalWs.close(1000, "Component unmounted"); // Normal closure
      globalWs = null;
    }

    globalReconnectAttempts = 0;
    setStatus("disconnected");
  }, [clearReconnectTimeout, clearPingInterval]);

  const send = useCallback((data: any) => {
    if (globalWs?.readyState === WebSocket.OPEN) {
      globalWs.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket is not connected. Cannot send message.");
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    connect();

    // Don't disconnect on unmount in dev mode to prevent reconnection loops
    // The global singleton will be reused
    return () => {
      // Only disconnect if this is the last component using the WebSocket
      // In production, this would be handled differently
    };
  }, [enabled, connect]);

  return {
    status,
    lastEvent,
    connect,
    disconnect,
    send,
  };
}
