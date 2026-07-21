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

export interface ChatMessage {
  id: string;
  role: 'player' | 'npc';
  text: string;
  mood?: string;
  pending?: boolean;
}

export interface Storyline {
  id: string;
  title: string;
  npcSlug: string;
  prompt: string;
  createdAt: string;
}

export interface ApiKeyEntry {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  revealed: boolean;
}
