import { useState } from 'react';
import { NpcCreateRequest, SchemaFieldKind, SchemaFieldSpec, SchemaFieldType } from '../types';

interface Props {
  onCreate: (req: NpcCreateRequest) => Promise<void>;
  onClose: () => void;
}

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';
const selectClass =
  'rounded border border-outline-variant bg-surface-container-lowest p-2 font-body-md text-on-surface outline-none transition-colors focus:border-primary';

type PrimitiveKind = 'str' | 'int' | 'float' | 'bool';

const PRIMITIVE_KINDS: { value: PrimitiveKind; label: string }[] = [
  { value: 'str', label: 'Text (str)' },
  { value: 'int', label: 'Whole number (int)' },
  { value: 'float', label: 'Decimal (float)' },
  { value: 'bool', label: 'True/False (bool)' },
];

const FIELD_KINDS: { value: SchemaFieldKind; label: string }[] = [
  ...PRIMITIVE_KINDS,
  { value: 'list', label: 'List of... (typing.List)' },
  { value: 'dict', label: 'Dictionary (typing.Dict)' },
  { value: 'optional', label: 'Optional... (typing.Optional)' },
  { value: 'literal', label: 'One of... (typing.Literal)' },
];

interface FieldRow {
  id: string;
  name: string;
  kind: SchemaFieldKind;
  itemKind: PrimitiveKind;
  keyKind: PrimitiveKind;
  valueKind: PrimitiveKind;
  literalValues: string;
  description: string;
}

const newRow = (): FieldRow => ({
  id: crypto.randomUUID(),
  name: '',
  kind: 'str',
  itemKind: 'str',
  keyKind: 'str',
  valueKind: 'str',
  literalValues: '',
  description: '',
});

function rowToFieldSpec(row: FieldRow): SchemaFieldSpec | null {
  const name = row.name.trim();
  if (!name) return null;

  let type: SchemaFieldType;
  switch (row.kind) {
    case 'list':
      type = { kind: 'list', item: { kind: row.itemKind } };
      break;
    case 'optional':
      type = { kind: 'optional', item: { kind: row.itemKind } };
      break;
    case 'dict':
      type = { kind: 'dict', key: { kind: row.keyKind }, value_type: { kind: row.valueKind } };
      break;
    case 'literal': {
      const values = row.literalValues
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean);
      if (values.length === 0) return null;
      type = { kind: 'literal', literal_values: values };
      break;
    }
    default:
      type = { kind: row.kind };
  }

  return { name, type, description: row.description.trim() || undefined };
}

export default function CreateNpcModal({ onCreate, onClose }: Props) {
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [backstory, setBackstory] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [structuredOutput, setStructuredOutput] = useState(false);
  const [fields, setFields] = useState<FieldRow[]>([newRow()]);

  const updateField = (id: string, patch: Partial<FieldRow>) => {
    setFields((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeField = (id: string) => {
    setFields((rows) => rows.filter((r) => r.id !== id));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const response_schema_fields = structuredOutput
        ? fields.map(rowToFieldSpec).filter((f): f is SchemaFieldSpec => f !== null)
        : undefined;
      await onCreate({
        name,
        goal: goal || undefined,
        backstory: backstory || undefined,
        response_schema_fields,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create NPC.');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="max-h-[90vh] w-full max-w-md space-y-5 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container p-6 shadow-[0_0_40px_-10px_rgba(208,188,255,0.15)]"
      >
        <div className="flex items-center gap-3 border-b border-outline-variant pb-4">
          <span className="material-symbols-outlined text-primary">person_add</span>
          <h2 className="font-headline-sm text-headline-sm text-on-surface">Create NPC</h2>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Aldric the Smith"
            className={inputClass}
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Goal (optional)</label>
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="interactive npc"
            className={inputClass}
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Backstory (optional)</label>
          <textarea
            value={backstory}
            onChange={(e) => setBackstory(e.target.value)}
            rows={3}
            placeholder="Short teaser backstory..."
            className={inputClass}
          />
        </div>

        <div className="space-y-3 border-t border-outline-variant pt-4">
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="flex w-full items-center justify-between text-left"
          >
            <span className={labelClass}>Advanced options</span>
            <span className="material-symbols-outlined text-outline">
              {showAdvanced ? 'expand_less' : 'expand_more'}
            </span>
          </button>

          {showAdvanced && (
            <div className="space-y-3 rounded-lg border border-outline-variant bg-surface-container-lowest/50 p-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={structuredOutput}
                  onChange={(e) => setStructuredOutput(e.target.checked)}
                />
                <span className="font-body-md text-on-surface">Return structured output (Pydantic model_dump)</span>
              </label>
              <p className="font-code-md text-[11px] text-outline">
                Off: the NPC replies with a raw string. On: replies are validated against a{' '}
                <code>ResponseSchema</code> you define below and returned as a dict.
              </p>

              {structuredOutput && (
                <div className="space-y-3">
                  {fields.map((row) => (
                    <div key={row.id} className="space-y-2 rounded border border-outline-variant p-3">
                      <div className="flex items-center gap-2">
                        <input
                          value={row.name}
                          onChange={(e) => updateField(row.id, { name: e.target.value })}
                          placeholder="field_name"
                          className={`${inputClass} flex-1`}
                        />
                        <select
                          value={row.kind}
                          onChange={(e) => updateField(row.id, { kind: e.target.value as SchemaFieldKind })}
                          className={selectClass}
                        >
                          {FIELD_KINDS.map((k) => (
                            <option key={k.value} value={k.value}>
                              {k.label}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => removeField(row.id)}
                          className="text-outline hover:text-error"
                          aria-label="Remove field"
                        >
                          <span className="material-symbols-outlined text-[18px]">delete</span>
                        </button>
                      </div>

                      {(row.kind === 'list' || row.kind === 'optional') && (
                        <div className="flex items-center gap-2">
                          <span className="font-code-md text-[11px] text-outline">of</span>
                          <select
                            value={row.itemKind}
                            onChange={(e) => updateField(row.id, { itemKind: e.target.value as PrimitiveKind })}
                            className={selectClass}
                          >
                            {PRIMITIVE_KINDS.map((k) => (
                              <option key={k.value} value={k.value}>
                                {k.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {row.kind === 'dict' && (
                        <div className="flex items-center gap-2">
                          <span className="font-code-md text-[11px] text-outline">keys</span>
                          <select
                            value={row.keyKind}
                            onChange={(e) => updateField(row.id, { keyKind: e.target.value as PrimitiveKind })}
                            className={selectClass}
                          >
                            {PRIMITIVE_KINDS.map((k) => (
                              <option key={k.value} value={k.value}>
                                {k.label}
                              </option>
                            ))}
                          </select>
                          <span className="font-code-md text-[11px] text-outline">values</span>
                          <select
                            value={row.valueKind}
                            onChange={(e) => updateField(row.id, { valueKind: e.target.value as PrimitiveKind })}
                            className={selectClass}
                          >
                            {PRIMITIVE_KINDS.map((k) => (
                              <option key={k.value} value={k.value}>
                                {k.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {row.kind === 'literal' && (
                        <input
                          value={row.literalValues}
                          onChange={(e) => updateField(row.id, { literalValues: e.target.value })}
                          placeholder="Angry, Sad, Happy"
                          className={inputClass}
                        />
                      )}

                      <input
                        value={row.description}
                        onChange={(e) => updateField(row.id, { description: e.target.value })}
                        placeholder="Description (optional, guides the LLM)"
                        className={inputClass}
                      />
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={() => setFields((rows) => [...rows, newRow()])}
                    className="flex items-center gap-1 font-label-caps text-label-caps uppercase text-primary hover:brightness-110"
                  >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                    Add field
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {error && <p className="text-sm text-error">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1.5 font-label-caps text-label-caps uppercase text-on-surface-variant hover:bg-surface-container-high"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || submitting}
            className="rounded bg-primary px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-primary hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  );
}
