import type { Avatar, Brain, Catalog, Me, Message, Persona, RoomListItem, RoomSnapshot } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  catalog: () => request<Catalog>("/api/catalog"),
  room: (id: string) => request<RoomSnapshot>(`/api/rooms/${encodeURIComponent(id)}`),
  rooms: () => request<RoomListItem[]>("/api/rooms"),
  createRoom: (body: { id?: string; topic?: string; brain?: Brain }) =>
    request<RoomSnapshot>("/api/rooms", { method: "POST", body: JSON.stringify(body) }),
  deleteRoom: (id: string) => request<void>(`/api/rooms/${encodeURIComponent(id)}`, { method: "DELETE" }),

  // ---- auth & keys
  me: () => request<Me>("/api/auth/me"),
  register: (email: string, password: string) =>
    request<Me>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<Me>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  unlock: (password: string) => request<Me>("/api/auth/unlock", { method: "POST", body: JSON.stringify({ password }) }),
  saveKey: (provider: string, key: string, remember: boolean) =>
    request<Me>(`/api/auth/keys/${provider}`, { method: "PUT", body: JSON.stringify({ key, remember }) }),
  removeKey: (provider: string) => request<Me>(`/api/auth/keys/${provider}`, { method: "DELETE" }),
  forgetAllKeys: () => request<Me>("/api/auth/keys", { method: "DELETE" }),

  addFromLibrary: (room: string, templateId: string) =>
    request<Persona>(`/api/rooms/${room}/personas`, {
      method: "POST",
      body: JSON.stringify({ template_id: templateId }),
    }),
  addCustom: (
    room: string,
    p: { name: string; tagline: string; personality: string; avatar: Avatar; temperature: number },
  ) => request<Persona>(`/api/rooms/${room}/personas`, { method: "POST", body: JSON.stringify(p) }),
  removePersona: (room: string, personaId: string) =>
    request<void>(`/api/rooms/${room}/personas/${personaId}`, { method: "DELETE" }),

  say: (room: string, content: string, name: string) =>
    request<Message>(`/api/rooms/${room}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, name }),
    }),
  control: (room: string, action: "play" | "pause" | "step" | "clear") =>
    request<{ status: string; speed: number }>(`/api/rooms/${room}/control`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  settings: (room: string, body: { topic?: string; speed?: number; brain?: Brain }) =>
    request<RoomSnapshot>(`/api/rooms/${room}`, { method: "PATCH", body: JSON.stringify(body) }),
};
