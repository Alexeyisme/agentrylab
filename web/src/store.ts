import { create } from "zustand";
import { api } from "./api";
import type { Catalog, Message, Persona, ProviderInfo, RoomEvent, RoomSnapshot, RoomStatus } from "./types";

export interface Toast {
  id: number;
  text: string;
  tone: "info" | "error";
}

interface Speaking {
  personaId: string;
  messageId: string;
  startedAt: number;
}

interface RoomState {
  roomId: string;
  connected: boolean;
  catalog: Catalog | null;
  provider: ProviderInfo | null;

  topic: string;
  status: RoomStatus;
  speed: number;
  turn: number;
  personas: Persona[];
  messages: Message[];
  thinking: string | null;
  speaking: Speaking | null;
  toasts: Toast[];

  userName: string;
  setUserName: (n: string) => void;

  init: () => Promise<void>;
  applyEvent: (e: RoomEvent) => void;
  finishedSpeaking: (messageId: string) => void;
  toast: (text: string, tone?: Toast["tone"]) => void;
  dismissToast: (id: number) => void;

  addFromLibrary: (templateId: string) => Promise<void>;
  addCustom: (p: Parameters<typeof api.addCustom>[1]) => Promise<void>;
  removePersona: (id: string) => Promise<void>;
  say: (content: string) => Promise<void>;
  control: (action: "play" | "pause" | "step" | "clear") => Promise<void>;
  setTopic: (topic: string) => Promise<void>;
  setSpeed: (speed: number) => Promise<void>;
}

const roomFromUrl = () => new URLSearchParams(location.search).get("room")?.trim() || "main";

let toastSeq = 0;
let socket: WebSocket | null = null;
let reconnectTimer: number | undefined;

function wsUrl(roomId: string) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws/rooms/${encodeURIComponent(roomId)}`;
}

export const useRoom = create<RoomState>((set, get) => ({
  roomId: roomFromUrl(),
  connected: false,
  catalog: null,
  provider: null,

  topic: "",
  status: "running",
  speed: 3,
  turn: 0,
  personas: [],
  messages: [],
  thinking: null,
  speaking: null,
  toasts: [],

  userName: localStorage.getItem("agentrylab.name") ?? "",
  setUserName: (n) => {
    localStorage.setItem("agentrylab.name", n);
    set({ userName: n });
  },

  init: async () => {
    const { roomId } = get();
    try {
      const catalog = await api.catalog();
      set({ catalog, provider: catalog.provider });
    } catch (e) {
      get().toast(`Could not load catalog: ${(e as Error).message}`, "error");
    }
    if (roomId !== "main") {
      try {
        await api.room(roomId);
      } catch {
        try {
          await api.createRoom(roomId);
        } catch (e) {
          get().toast(`Could not open room '${roomId}': ${(e as Error).message}`, "error");
        }
      }
    }
    connect(roomId, get().applyEvent, (connected) => set({ connected }));
  },

  applyEvent: (e) => {
    switch (e.type) {
      case "snapshot":
        set(fromSnapshot(e.room));
        break;
      case "message": {
        const m = e.message;
        set((s) => ({
          messages: [...s.messages.slice(-400), m],
          turn: m.kind === "persona" ? m.turn : s.turn,
          thinking: m.kind === "persona" && s.thinking === m.speaker_id ? null : s.thinking,
          speaking: m.kind === "persona" ? { personaId: m.speaker_id, messageId: m.id, startedAt: Date.now() } : s.speaking,
        }));
        break;
      }
      case "thinking":
        set({ thinking: e.persona_id });
        break;
      case "persona_joined":
        set((s) => ({ personas: s.personas.some((p) => p.id === e.persona.id) ? s.personas : [...s.personas, e.persona] }));
        break;
      case "persona_left":
        set((s) => ({
          personas: s.personas.filter((p) => p.id !== e.persona_id),
          thinking: s.thinking === e.persona_id ? null : s.thinking,
          speaking: s.speaking?.personaId === e.persona_id ? null : s.speaking,
        }));
        break;
      case "status":
        set({ status: e.status, speed: e.speed });
        break;
      case "topic":
        set({ topic: e.topic });
        break;
      case "cleared":
        set({ messages: [], speaking: null, thinking: null, turn: 0 });
        break;
      case "error":
        set((s) => ({ thinking: s.thinking === e.persona_id ? null : s.thinking }));
        get().toast(e.error, "error");
        break;
    }
  },

  finishedSpeaking: (messageId) =>
    set((s) => (s.speaking?.messageId === messageId ? { speaking: null } : {})),

  toast: (text, tone = "info") => {
    const id = ++toastSeq;
    set((s) => ({ toasts: [...s.toasts.slice(-3), { id, text, tone }] }));
    window.setTimeout(() => get().dismissToast(id), tone === "error" ? 6000 : 3200);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  addFromLibrary: async (templateId) => guard(get, () => api.addFromLibrary(get().roomId, templateId)),
  addCustom: async (p) => guard(get, () => api.addCustom(get().roomId, p)),
  removePersona: async (id) => guard(get, () => api.removePersona(get().roomId, id)),
  say: async (content) => guard(get, () => api.say(get().roomId, content, get().userName || "You")),
  control: async (action) => guard(get, () => api.control(get().roomId, action)),
  setTopic: async (topic) => guard(get, () => api.settings(get().roomId, { topic })),
  setSpeed: async (speed) => {
    set({ speed });
    await guard(get, () => api.settings(get().roomId, { speed }));
  },
}));

async function guard(get: () => RoomState, fn: () => Promise<unknown>) {
  try {
    await fn();
  } catch (e) {
    get().toast((e as Error).message, "error");
  }
}

function fromSnapshot(r: RoomSnapshot) {
  return {
    topic: r.topic,
    status: r.status,
    speed: r.speed,
    turn: r.turn,
    personas: r.personas,
    messages: r.messages,
    thinking: r.thinking,
    speaking: null,
    provider: r.provider,
  };
}

function connect(roomId: string, onEvent: (e: RoomEvent) => void, onConnected: (c: boolean) => void) {
  if (socket) {
    socket.onclose = null;
    socket.close();
  }
  const ws = new WebSocket(wsUrl(roomId));
  socket = ws;
  ws.onopen = () => onConnected(true);
  ws.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data) as RoomEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  ws.onclose = () => {
    onConnected(false);
    window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(() => connect(roomId, onEvent, onConnected), 1500);
  };
  ws.onerror = () => ws.close();
}

/** Send a lightweight command straight over the socket (falls back to REST in the store). */
export function wsSend(payload: Record<string, unknown>): boolean {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
    return true;
  }
  return false;
}
