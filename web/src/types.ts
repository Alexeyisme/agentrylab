export type FaceId = "visor" | "duo" | "cyclops" | "pixel" | "feline" | "crt";
export type BodyId = "capsule" | "boxy" | "hover" | "slim" | "orb" | "tank";
export type PaletteId = "cyan" | "magenta" | "lime" | "amber" | "coral" | "violet" | "mint" | "ice";

export interface Avatar {
  face: FaceId;
  body: BodyId;
  palette: PaletteId;
}

export interface Persona {
  id: string;
  name: string;
  tagline: string;
  personality: string;
  avatar: Avatar;
  temperature: number;
  voice: string[];
  template_id: string | null;
}

export type MessageKind = "persona" | "user" | "system";

export interface Message {
  id: string;
  t: number;
  turn: number;
  kind: MessageKind;
  speaker_id: string;
  speaker_name: string;
  content: string;
}

export type RoomStatus = "running" | "paused";

export interface ProviderInfo {
  kind: string;
  model: string;
  demo: boolean;
}

export interface Brain {
  provider: string;
  model: string | null;
}

export interface RoomSnapshot {
  id: string;
  topic: string;
  status: RoomStatus;
  speed: number;
  turn: number;
  thinking: string | null;
  owner_id: string | null;
  brain: Brain;
  provider: ProviderInfo;
  personas: Persona[];
  messages: Message[];
}

export interface Part {
  id: string;
  label: string;
}

export interface ProviderSpec {
  id: string;
  label: string;
  default_model: string;
  models: string[];
  key_hint?: string;
  docs?: string;
  base_url?: string;
}

export interface Catalog {
  avatars: {
    faces: Part[];
    bodies: Part[];
    palettes: (Part & { accent: string })[];
  };
  library: Persona[];
  provider: ProviderInfo;
  providers: ProviderSpec[];
  limits: { min_speed: number; max_speed: number; max_personas: number; max_rooms: number };
}

export interface KeyInfo {
  provider: string;
  hint: string;
  remembered: boolean;
  available: boolean;
}

export interface Me {
  user: { id: string; email: string } | null;
  keys: KeyInfo[];
  vault_unlocked: boolean;
  signup_enabled: boolean;
}

export interface RoomListItem {
  id: string;
  topic: string;
  status: RoomStatus;
  owner_id: string | null;
  mine: boolean;
  brain: ProviderInfo;
  personas: number;
  messages: number;
}

export type RoomEvent =
  | { type: "snapshot"; room: RoomSnapshot }
  | { type: "message"; message: Message; latency_ms?: number }
  | { type: "thinking"; persona_id: string }
  | { type: "persona_joined"; persona: Persona }
  | { type: "persona_left"; persona_id: string }
  | { type: "status"; status: RoomStatus; speed: number }
  | { type: "topic"; topic: string }
  | { type: "brain"; brain: Brain; provider: ProviderInfo }
  | { type: "cleared" }
  | { type: "error"; persona_id: string | null; error: string };

export type Mood = "idle" | "thinking" | "talking";
