import { useEffect, useState } from 'react';
import { NpcDetail, NpcUpdateRequest, PydanticFieldDef, PydanticFieldType } from '../types';
import { generateCharacter } from '../api';

interface Props {
  npc: NpcDetail;
  onSave: (fields: NpcUpdateRequest) => Promise<void>;
}

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';

const FIELD_TYPES: PydanticFieldType[] = ['string', 'integer', 'float', 'boolean', 'enum'];

const emptyField = (): PydanticFieldDef => ({
  name: '',
  type: 'string',
  description: '',
  enum_values: [],
  required: true,
});

export default function PersonaEditor({ npc, onSave }: Props) {
  const [goal, setGoal] = useState(npc.goal);
  const [backstory, setBackstory] = useState(npc.backstory);
  const [llm, setLlm] = useState(npc.llm);
  const [personaNotes, setPersonaNotes] = useState(npc.persona_notes);
  const [pydanticEnabled, setPydanticEnabled] = useState(npc.pydantic_enabled);
  const [pydanticFields, setPydanticFields] = useState(npc.pydantic_fields);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [genPrompt, setGenPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    setGoal(npc.goal);
    setBackstory(npc.backstory);
    setLlm(npc.llm);
    setPersonaNotes(npc.persona_notes);
    setPydanticEnabled(npc.pydantic_enabled);
    setPydanticFields(npc.pydantic_fields);
    setSaved(false);
    setSaveError(null);
  }, [npc]);

  const updateField = (index: number, patch: Partial<PydanticFieldDef>) => {
    setPydanticFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  };

  const removeField = (index: number) => {
    setPydanticFields((prev) => prev.filter((_, i) => i !== index));
  };

  const addField = () => {
    setPydanticFields((prev) => [...prev, emptyField()]);
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    setSaveError(null);
    try {
      await onSave({
        goal,
        backstory,
        llm,
        persona_notes: personaNotes,
        pydantic_enabled: pydanticEnabled,
        pydantic_fields: pydanticFields,
      });
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  const generate = async () => {
    setGenerating(true);
    setGenError(null);
    try {
      const result = await generateCharacter(npc.role, genPrompt.trim());
      if (!result.success) throw new Error(result.error || 'Generation failed.');
      if (result.description) setBackstory(result.description);
      if (result.persona) setPersonaNotes(result.persona);
      setSaved(false);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : 'Failed to generate persona.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-gutter">
      <div className="space-y-6 rounded-lg border border-outline-variant bg-surface-container p-6">
        <div className="mb-4 flex items-center gap-3 border-b border-outline-variant pb-4">
          <span className="material-symbols-outlined text-primary">id_card</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">Identity</h3>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Goal</label>
          <input value={goal} onChange={(e) => setGoal(e.target.value)} className={inputClass} />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Backstory (short)</label>
          <input value={backstory} onChange={(e) => setBackstory(e.target.value)} className={inputClass} />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>LLM</label>
          <input value={llm} onChange={(e) => setLlm(e.target.value)} className={inputClass} />
        </div>
      </div>

      <div className="space-y-6 rounded-lg border border-outline-variant bg-surface-container p-6">
        <div className="mb-4 flex items-center gap-3 border-b border-outline-variant pb-4">
          <span className="material-symbols-outlined text-primary">psychology_alt</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">Persona Notes</h3>
        </div>

        <div className="space-y-3 rounded-lg border border-outline-variant bg-surface-container-lowest/50 p-4">
          <div className="space-y-2">
            <label className={labelClass}>Generation prompt (optional)</label>
            <input
              value={genPrompt}
              onChange={(e) => setGenPrompt(e.target.value)}
              placeholder="e.g. gruff blacksmith who lost his son in the war"
              className={inputClass}
            />
          </div>

          {genError && <p className="text-sm text-error">{genError}</p>}

          <div className="flex items-center gap-3">
            <button
              onClick={generate}
              disabled={generating}
              className="flex items-center gap-2 rounded bg-primary px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-primary transition-all hover:brightness-110 disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              {generating ? 'Generating...' : 'Generate with AI'}
            </button>
            <span className="font-code-md text-[11px] text-outline">
              Writes a SKILL.md character sheet into Backstory &amp; the field below — review before saving.
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-end justify-between">
            <label className={labelClass}>Full character sheet</label>
            <span className="font-code-md text-[10px] uppercase text-outline-variant opacity-60">Free text</span>
          </div>
          <textarea
            value={personaNotes}
            onChange={(e) => setPersonaNotes(e.target.value)}
            rows={16}
            className={`${inputClass} font-code-md text-code-md`}
          />
        </div>
      </div>

      <div className="space-y-6 rounded-lg border border-outline-variant bg-surface-container p-6">
        <div className="mb-4 flex items-center justify-between border-b border-outline-variant pb-4">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary">data_object</span>
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Structured Output</h3>
          </div>
          <label className="flex items-center gap-2 font-label-caps text-label-caps uppercase text-outline">
            <input
              type="checkbox"
              checked={pydanticEnabled}
              onChange={(e) => setPydanticEnabled(e.target.checked)}
              className="h-4 w-4 accent-primary"
            />
            {pydanticEnabled ? 'Enabled' : 'Disabled'}
          </label>
        </div>

        {!pydanticEnabled && (
          <p className="font-code-md text-[11px] text-outline">
            Responses will be plain text only — no mood or other structured fields will be extracted.
          </p>
        )}

        {pydanticEnabled && (
          <div className="space-y-4">
            {pydanticFields.map((field, index) => (
              <div
                key={index}
                className="space-y-3 rounded-lg border border-outline-variant bg-surface-container-lowest/50 p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1 space-y-2">
                    <label className={labelClass}>Field name</label>
                    <input
                      value={field.name}
                      onChange={(e) => updateField(index, { name: e.target.value })}
                      placeholder="e.g. mood"
                      className={inputClass}
                    />
                  </div>
                  <div className="w-40 space-y-2">
                    <label className={labelClass}>Type</label>
                    <select
                      value={field.type}
                      onChange={(e) => updateField(index, { type: e.target.value as PydanticFieldType })}
                      className={inputClass}
                    >
                      {FIELD_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={() => removeField(index)}
                    title="Remove field"
                    className="mt-7 rounded p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-error"
                  >
                    <span className="material-symbols-outlined">delete</span>
                  </button>
                </div>

                <div className="space-y-2">
                  <label className={labelClass}>Description</label>
                  <input
                    value={field.description}
                    onChange={(e) => updateField(index, { description: e.target.value })}
                    placeholder="What the LLM should put in this field"
                    className={inputClass}
                  />
                </div>

                {field.type === 'enum' && (
                  <div className="space-y-2">
                    <label className={labelClass}>Allowed values (comma-separated)</label>
                    <input
                      value={field.enum_values.join(', ')}
                      onChange={(e) =>
                        updateField(index, {
                          enum_values: e.target.value
                            .split(',')
                            .map((v) => v.trim())
                            .filter(Boolean),
                        })
                      }
                      placeholder="e.g. Angry, Sad, Happy, Furious, Calm"
                      className={inputClass}
                    />
                  </div>
                )}

                <label className="flex items-center gap-2 font-label-caps text-label-caps uppercase text-outline">
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(e) => updateField(index, { required: e.target.checked })}
                    className="h-4 w-4 accent-primary"
                  />
                  Required
                </label>
              </div>
            ))}

            <button
              onClick={addField}
              className="flex items-center gap-2 rounded border border-outline-variant px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              Add field
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 pb-12">
        <button
          onClick={save}
          disabled={saving}
          className="rounded bg-primary px-5 py-2.5 font-label-caps text-label-caps uppercase text-on-primary transition-all hover:brightness-110 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save changes'}
        </button>
        {saved && <span className="font-label-caps text-label-caps uppercase text-primary">Saved</span>}
        {saveError && <span className="font-label-caps text-label-caps text-error">{saveError}</span>}
      </div>
    </div>
  );
}
