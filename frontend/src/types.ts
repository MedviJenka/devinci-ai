export interface NpcSummary {
  slug: string;
  role: string;
  goal: string;
  llm: string;
}

export interface NpcDetail extends NpcSummary {
  backstory: string;
  persona_notes: string;
}

export type SchemaFieldKind = 'str' | 'int' | 'float' | 'bool' | 'list' | 'dict' | 'optional' | 'literal';

export interface SchemaFieldType {
  kind: SchemaFieldKind;
  item?: SchemaFieldType;
  key?: SchemaFieldType;
  value_type?: SchemaFieldType;
  literal_values?: string[];
}

export interface SchemaFieldSpec {
  name: string;
  type: SchemaFieldType;
  description?: string;
}

export interface NpcCreateRequest {
  name: string;
  goal?: string;
  backstory?: string;
  llm?: string;
  persona_notes?: string;
  response_schema_fields?: SchemaFieldSpec[];
}

export interface NpcUpdateRequest {
  goal?: string;
  backstory?: string;
  llm?: string;
  persona_notes?: string;
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
