import { create } from "zustand";
import { api } from "./api";
import type { Brain, Catalog, Me, Message, Persona, ProviderInfo, RoomEvent, RoomListItem, RoomSnapshot, RoomStatus } from "./types";

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

export type Modal = "add" | "auth" | "keys" | "newRoom" | null;

interface RoomState {
  roomId: string;
  connected: boolean;
  catalog: Catalog | null;
  provider: ProviderInfo | null;
  me: Me | null;
  rooms: RoomListItem[];
  modal: Modal;

  topic: string;
  status: RoomStatus;
  speed: number;
  turn: number;
  ownerId: string | null;
  brain: Brain;
  personas: Persona[];
  messages: Message[];
  thinking: string | null;
  speaking: Speaking | null;
  toasts: Toast[];

  userName: string;
  setUserName: (n: string) => void;
  openModal: (m: Modal) => void;

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
  setBrain: (brain: Brain) => Promise<boolean>;

  // auth & keys (errors are thrown so forms can show them inline)
  refreshMe: () => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  unlock: (password: string) => Promise<void>;
  saveKey: (provider: string, key: string, remember: boolean) => Promise<void>;
  removeKey: (provider: string) => Promise<void>;
  forgetAllKeys: () => Promise<void>;

  // rooms
  loadRooms: () => Promise<void>;
  createRoom: (body: { id?: string; topic?: string; brain?: Brain }) => Promise<string>;
  deleteRoom: (id: string) => Promise<void>;
}

const roomFromUrl = () => new URLSearchParams(location.search).get("room")?.trim() || "main";

export function goToRoom(id: string) {
  location.href = id === "main" ? location.pathname : `${location.pathname}?room=${encodeURIComponent(id)}`;
}

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
  me: null,
  rooms: [],
  modal: null,

  topic: "",
  status: "running",
  speed: 3,
  turn: 0,
  ownerId: null,
  brain: { provider: "server", model: null },
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
  openModal: (m) => set({ modal: m }),

  init: async () => {
    const { roomId } = get();
    try {
      const [catalog, me] = await Promise.all([api.catalog(), api.me()]);
      set({ catalog, provider: catalog.provider, me });
      if (me.user && !get().userName) get().setUserName(me.user.email.split("@")[0]);
    } catch (e) {
      get().toast(`Could not reach the server: ${(e as Error).message}`, "error");
    }
    void get().loadRooms();
    if (roomId !== "main") {
      try {
        await api.room(roomId);
      } catch (e) {
        get().toast(`Could not open room '${roomId}': ${(e as Error).message}`, "error");
        window.setTimeout(() => goToRoom("main"), 1800);
        return;
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
      case "brain":
        set({ brain: e.brain, provider: e.provider });
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
  setBrain: async (brain) => {
    try {
      await api.settings(get().roomId, { brain });
      return true;
    } catch (e) {
      get().toast((e as Error).message, "error");
      return false;
    }
  },

  refreshMe: async () => {
    try {
      set({ me: await api.me() });
    } catch {
      /* offline */
    }
  },
  register: async (email, password) => {
    const me = await api.register(email, password);
    set({ me });
    if (!get().userName) get().setUserName(email.split("@")[0]);
    void get().loadRooms();
  },
  login: async (email, password) => {
    const me = await api.login(email, password);
    set({ me });
    if (!get().userName) get().setUserName(email.split("@")[0]);
    void get().loadRooms();
  },
  logout: async () => {
    await guard(get, () => api.logout());
    set({ me: { user: null, keys: [], vault_unlocked: false, signup_enabled: get().me?.signup_enabled ?? true } });
    get().toast("Signed out. Your API keys were wiped from the server's memory.");
    if (get().ownerId) goToRoom("main");
    else void get().loadRooms();
  },
  unlock: async (password) => set({ me: await api.unlock(password) }),
  saveKey: async (provider, key, remember) => set({ me: await api.saveKey(provider, key, remember) }),
  removeKey: async (provider) => set({ me: await api.removeKey(provider) }),
  forgetAllKeys: async () => set({ me: await api.forgetAllKeys() }),

  loadRooms: async () => {
    try {
      set({ rooms: await api.rooms() });
    } catch {
      /* ignore */
    }
  },
  createRoom: async (body) => {
    const snap = await api.createRoom(body);
    return snap.id;
  },
  deleteRoom: async (id) => {
    await guard(get, () => api.deleteRoom(id));
    if (get().roomId === id) goToRoom("main");
    else void get().loadRooms();
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
    ownerId: r.owner_id,
    brain: r.brain,
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
  ws.onclose = (ev) => {
    onConnected(false);
    if (ev.code === 4003 || ev.code === 4004) {
      // Not ours / gone: bounce to the public stage.
      window.setTimeout(() => goToRoom("main"), 1200);
      return;
    }
    window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(() => connect(roomId, onEvent, onConnected), 1500);
  };
  ws.onerror = () => ws.close();
}
