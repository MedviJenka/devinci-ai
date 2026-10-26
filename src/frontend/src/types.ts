export type PydanticFieldType = 'string' | 'integer' | 'float' | 'boolean' | 'enum';

export interface PydanticFieldDef {
  name: string;
  type: PydanticFieldType;
  description: string;
  enum_values: string[];
  required: boolean;
}

export interface NpcSummary {
  slug: string;
  role: string;
  goal: string;
  llm: string;
}

export interface NpcDetail extends NpcSummary {
  backstory: string;
  persona_notes: string;
  pydantic_enabled: boolean;
  pydantic_fields: PydanticFieldDef[];
}

export interface NpcCreateRequest {
  name: string;
  goal?: string;
  backstory?: string;
  llm?: string;
  persona_notes?: string;
}

export interface NpcUpdateRequest {
  goal?: string;
  backstory?: string;
  llm?: string;
  persona_notes?: string;
  pydantic_enabled?: boolean;
  pydantic_fields?: PydanticFieldDef[];
}

// One remembered exchange from GET /npcs/{slug}/history: the player's line, the NPC's
// reply, and whatever structured fields (mood, attitude, tone, custom) came with it.
export interface HistoryTurn {
  ts: string;
  query: string;
  response: string;
  [field: string]: unknown;
}

// OpenAI models suggested in the persona editor - /talk calls OpenAI directly, so other
// providers are rejected on save. The mini models give the fastest replies.
export const SUGGESTED_LLMS = ['openai/gpt-5-mini', 'openai/gpt-4.1-mini', 'openai/gpt-5.4-mini', 'openai/gpt-5.5'];

export interface ChatMessage {
  id: string;
  role: 'player' | 'npc';
  text: string;
  mood?: string;
  attitude?: string;
  tone?: SupportedTone;
  pending?: boolean;
  isJson?: boolean;
  speechText?: string;
}

export interface Storyline {
  id: string;
  title: string;
  npcSlug: string;
  prompt: string;
  createdAt: string;
}

export type SupportedVoice = 'alloy' | 'ash' | 'ballad' | 'coral' | 'echo' | 'fable' | 'nova' | 'onyx' | 'sage' | 'shimmer' | 'verse';

export type SupportedTone = 'neutral' | 'cheerful' | 'dramatic' | 'calm' | 'mysterious' | 'stern' | 'sarcastic' | 'whisper';

export type SupportedLanguage = 'en';

export interface VoiceOptions {
  voices: SupportedVoice[];
  tones: SupportedTone[];
  languages: SupportedLanguage[];
}

export interface ApiKeySummary {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at?: string;
  revoked_at?: string;
}

export interface ApiKeyCreateResponse extends ApiKeySummary {
  key: string;
}
