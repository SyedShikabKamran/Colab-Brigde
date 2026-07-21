/**
 * ColabBridge JavaScript/TypeScript client
 *
 * Connects your web app to a ColabBridge server running on Google Colab.
 * Handles registry polling, WebSocket connection, auto-reconnect, and HTTP POST.
 *
 * Usage:
 *   import { ColabBridgeClient } from 'colabbridge-client'
 *
 *   const client = new ColabBridgeClient('https://your-registry.up.railway.app')
 *
 *   // HTTP one-shot
 *   const result = await client.post('/classify', { image_b64: '...' })
 *
 *   // WebSocket streaming
 *   await client.connect('/ws')
 *   client.onMessage(result => console.log(result))
 *   client.sendBytes(imageBytes)
 */

export interface ColabBridgeOptions {
  /** URL of your deployed registry service */
  registryUrl: string;
  /** How long to wait between reconnect attempts (ms, default 3000) */
  reconnectDelay?: number;
  /** How often to poll the registry if the server URL is not yet available (ms, default 5000) */
  registryPollInterval?: number;
  /** Max time to wait for the registry to have a URL before giving up (ms, default 300000 = 5 min) */
  registryTimeout?: number;
}

type MessageHandler = (data: unknown) => void;
type StatusHandler = (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;

export class ColabBridgeClient {
  private readonly opts: Required<ColabBridgeOptions>;
  private serverUrl: string | null = null;
  private ws: WebSocket | null = null;
  private messageHandlers = new Map<string, MessageHandler>();
  private statusHandlers = new Map<string, StatusHandler>();
  private shouldReconnect = false;
  private currentPath = '/ws';

  constructor(registryUrlOrOptions: string | ColabBridgeOptions) {
    const options =
      typeof registryUrlOrOptions === 'string'
        ? { registryUrl: registryUrlOrOptions }
        : registryUrlOrOptions;

    this.opts = {
      registryUrl: options.registryUrl.replace(/\/$/, ''),
      reconnectDelay: options.reconnectDelay ?? 3000,
      registryPollInterval: options.registryPollInterval ?? 5000,
      registryTimeout: options.registryTimeout ?? 300_000,
    };
  }

  // ── Registry ─────────────────────────────────────────────────────────────

  /**
   * Fetch the current server URL from the registry.
   * Polls until a URL is available or the timeout expires.
   */
  async getServerUrl(): Promise<string> {
    const deadline = Date.now() + this.opts.registryTimeout;
    while (Date.now() < deadline) {
      try {
        const res = await fetch(`${this.opts.registryUrl}/server-url`);
        if (res.ok) {
          const data = (await res.json()) as { url: string };
          return data.url;
        }
      } catch {
        // server not reachable yet — keep polling
      }
      await sleep(this.opts.registryPollInterval);
    }
    throw new Error(`[ColabBridge] Registry timed out after ${this.opts.registryTimeout / 1000}s`);
  }

  // ── WebSocket streaming ───────────────────────────────────────────────────

  /**
   * Connect to the server's WebSocket endpoint.
   * Resolves once the connection is open.
   * Auto-reconnects on disconnect (re-polls registry in case server URL changed).
   */
  async connect(path = '/ws'): Promise<void> {
    this.currentPath = path;
    this.shouldReconnect = true;
    return this._connect();
  }

  private async _connect(): Promise<void> {
    this._notifyStatus('connecting');

    if (!this.serverUrl) {
      console.log('[ColabBridge] Polling registry for server URL...');
      this.serverUrl = await this.getServerUrl();
      console.log(`[ColabBridge] Server URL: ${this.serverUrl}`);
    }

    const wsUrl = toWss(this.serverUrl) + this.currentPath;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      this.ws = ws;

      ws.onopen = () => {
        console.log(`[ColabBridge] Connected: ${wsUrl}`);
        this._notifyStatus('connected');
        resolve();
      };

      ws.onmessage = (event: MessageEvent) => {
        let data: unknown = event.data;
        if (typeof data === 'string') {
          try { data = JSON.parse(data); } catch { /* leave as string */ }
        }
        this.messageHandlers.forEach(h => h(data));
      };

      ws.onerror = (err) => {
        this._notifyStatus('error');
        reject(err);
      };

      ws.onclose = () => {
        this._notifyStatus('disconnected');
        if (this.shouldReconnect) {
          console.log(`[ColabBridge] Disconnected. Reconnecting in ${this.opts.reconnectDelay}ms...`);
          // Clear cached URL so we re-poll the registry — server may have restarted
          // with a new tunnel URL.
          this.serverUrl = null;
          setTimeout(() => this._connect(), this.opts.reconnectDelay);
        }
      };
    });
  }

  /** Register a handler for incoming WebSocket messages. Returns an unsubscribe function. */
  onMessage(handler: MessageHandler): () => void {
    const id = uid();
    this.messageHandlers.set(id, handler);
    return () => this.messageHandlers.delete(id);
  }

  /** Register a handler for connection status changes. Returns an unsubscribe function. */
  onStatus(handler: StatusHandler): () => void {
    const id = uid();
    this.statusHandlers.set(id, handler);
    return () => this.statusHandlers.delete(id);
  }

  /** Send raw bytes over the WebSocket (e.g. a JPEG frame). */
  sendBytes(data: ArrayBuffer | Uint8Array | Blob): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      console.warn('[ColabBridge] sendBytes: socket not open — message dropped.');
    }
  }

  /** Send a UTF-8 string or JSON-serializable object over the WebSocket. */
  sendText(data: string | object): void {
    const text = typeof data === 'string' ? data : JSON.stringify(data);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(text);
    } else {
      console.warn('[ColabBridge] sendText: socket not open — message dropped.');
    }
  }

  /** Close the WebSocket without reconnecting. */
  disconnect(): void {
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
  }

  // ── HTTP POST ─────────────────────────────────────────────────────────────

  /**
   * Send a one-shot HTTP POST request to the server.
   * Automatically fetches the server URL from the registry if not yet known.
   */
  async post<T = unknown>(path: string, body: Record<string, unknown>): Promise<T> {
    if (!this.serverUrl) {
      this.serverUrl = await this.getServerUrl();
    }
    const res = await fetch(toHttps(this.serverUrl) + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`[ColabBridge] POST ${path} failed (${res.status}): ${text}`);
    }
    return res.json() as Promise<T>;
  }

  /** GET /health from the server. */
  async health(): Promise<Record<string, unknown>> {
    if (!this.serverUrl) {
      this.serverUrl = await this.getServerUrl();
    }
    const res = await fetch(toHttps(this.serverUrl) + '/health');
    return res.json();
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  private _notifyStatus(status: Parameters<StatusHandler>[0]): void {
    this.statusHandlers.forEach(h => h(status));
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function toWss(url: string): string {
  return url.replace(/^https?:\/\//, (m) => (m.startsWith('https') ? 'wss://' : 'ws://'));
}

function toHttps(url: string): string {
  return url.replace(/^wss?:\/\//, (m) => (m.startsWith('wss') ? 'https://' : 'http://'));
}

function uid(): string {
  return Math.random().toString(36).slice(2);
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
