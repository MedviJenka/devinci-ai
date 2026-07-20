import { useState } from 'react';
import { ApiKeyEntry } from '../types';
import GenerateApiKeyModal from './GenerateApiKeyModal';

const SNIPPETS: Record<string, { label: string; code: string }> = {
  curl: {
    label: 'cURL',
    code: `curl -X POST https://api.devinci.ai/v1/npc/generate \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "template_id": "cyberpunk_merchant_01",
    "context": "Neon District market encounter",
    "personality_weight": 0.85
  }'`,
  },
  node: {
    label: 'Node.js',
    code: `const axios = require('axios');

async function generateNPC() {
  const response = await axios.post('https://api.devinci.ai/v1/npc/generate', {
    template_id: 'cyberpunk_merchant_01',
    context: 'Neon District market encounter',
    personality_weight: 0.85
  }, {
    headers: { 'Authorization': 'Bearer YOUR_API_KEY' }
  });
  console.log(response.data);
}`,
  },
  python: {
    label: 'Python',
    code: `import requests

url = "https://api.devinci.ai/v1/npc/generate"
headers = {"Authorization": "Bearer YOUR_API_KEY"}
payload = {
    "template_id": "cyberpunk_merchant_01",
    "context": "Neon District market encounter",
    "personality_weight": 0.85
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`,
  },
  csharp: {
    label: 'C# (Unity)',
    code: `// Attach to a MonoBehaviour and start as a coroutine
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public class DevinciClient : MonoBehaviour
{
    private const string ApiKey = "YOUR_API_KEY";

    public IEnumerator GenerateNPC()
    {
        string json = "{\\"template_id\\":\\"cyberpunk_merchant_01\\",\\"context\\":\\"Neon District market encounter\\",\\"personality_weight\\":0.85}";

        var request = new UnityWebRequest("https://api.devinci.ai/v1/npc/generate", "POST");
        request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        request.SetRequestHeader("Authorization", $"Bearer {ApiKey}");

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
            Debug.Log(request.downloadHandler.text);
        else
            Debug.LogError(request.error);
    }
}`,
  },
  cpp: {
    label: 'C++ (Unreal)',
    code: `// Requires the "HTTP" module in YourProject.Build.cs
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"

void UDevinciClient::GenerateNPC()
{
    FHttpModule* Http = &FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = Http->CreateRequest();

    Request->SetURL(TEXT("https://api.devinci.ai/v1/npc/generate"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer YOUR_API_KEY"));

    FString Payload = TEXT("{\\"template_id\\":\\"cyberpunk_merchant_01\\",\\"context\\":\\"Neon District market encounter\\",\\"personality_weight\\":0.85}");
    Request->SetContentAsString(Payload);

    Request->OnProcessRequestComplete().BindLambda(
        [](FHttpRequestPtr Req, FHttpResponsePtr Response, bool bSuccess)
        {
            if (bSuccess && Response.IsValid())
                UE_LOG(LogTemp, Log, TEXT("%s"), *Response->GetContentAsString());
        });

    Request->ProcessRequest();
}`,
  },
};

const LANGS = ['curl', 'node', 'python', 'csharp', 'cpp'] as const;

function maskKey(key: string) {
  return `${key.slice(0, 8)}${'•'.repeat(16)}${key.slice(-4)}`;
}

function generateKey() {
  const raw = crypto.randomUUID().replace(/-/g, '');
  return `dv_local_${raw}`;
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKeyEntry[]>([]);
  const [showGenerate, setShowGenerate] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeLang, setActiveLang] = useState<(typeof LANGS)[number]>('curl');
  const [snippetCopied, setSnippetCopied] = useState(false);

  const handleGenerate = (name: string) => {
    setKeys((prev) => [
      { id: crypto.randomUUID(), name, key: generateKey(), createdAt: new Date().toISOString(), revealed: false },
      ...prev,
    ]);
    setShowGenerate(false);
  };

  const toggleReveal = (id: string) => {
    setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, revealed: !k.revealed } : k)));
  };

  const handleCopyKey = (id: string, key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    setTimeout(() => setCopiedId((cur) => (cur === id ? null : cur)), 2000);
  };

  const handleRevoke = (id: string) => {
    if (!window.confirm('Revoke this key? This cannot be undone.')) return;
    setKeys((prev) => prev.filter((k) => k.id !== id));
  };

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(SNIPPETS[activeLang].code);
    setSnippetCopied(true);
    setTimeout(() => setSnippetCopied(false), 2000);
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-surface-container-lowest p-gutter">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">API Keys</h2>
          <p className="mt-1 text-on-surface-variant">Manage credentials for Devinci Orchestrator access.</p>
        </div>
        <button
          onClick={() => setShowGenerate(true)}
          className="flex items-center gap-2 rounded-lg border border-outline-variant px-4 py-2 font-label-caps text-label-caps uppercase transition-all hover:bg-surface-container-highest"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          Generate Key
        </button>
      </div>

      {keys.length === 0 ? (
        <div className="mb-10 flex flex-col items-center justify-center rounded-lg border border-outline-variant bg-surface-container py-24 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
            <span className="material-symbols-outlined text-4xl text-primary/60">vpn_key</span>
          </div>
          <h3 className="mb-2 font-headline-md text-headline-md text-on-surface">No API keys yet</h3>
          <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
            Generate a key to authenticate requests to the Devinci Orchestrator API. Keys are stored locally in this
            session for now — a real credential store isn't wired up yet.
          </p>
          <button
            onClick={() => setShowGenerate(true)}
            className="rounded-lg bg-primary px-8 py-3 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110"
          >
            Generate First Key
          </button>
        </div>
      ) : (
        <div className="mb-10 overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
          <table className="w-full text-left font-body-md">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                  Key Name
                </th>
                <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                  Key String
                </th>
                <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                  Created
                </th>
                <th className="px-6 py-3 text-right font-label-caps text-label-caps uppercase tracking-wider text-outline">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {keys.map((k) => (
                <tr key={k.id} className="group transition-colors hover:bg-surface-container">
                  <td className="px-6 py-4 font-code-md text-code-md">{k.name}</td>
                  <td className="px-6 py-4 font-code-md text-code-md">
                    <div className="flex items-center gap-2 text-on-surface-variant">
                      <span>{k.revealed ? k.key : maskKey(k.key)}</span>
                      <button
                        onClick={() => toggleReveal(k.id)}
                        title={k.revealed ? 'Hide' : 'Reveal'}
                        className="flex items-center transition-colors hover:text-primary"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          {k.revealed ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                      <button
                        onClick={() => handleCopyKey(k.id, k.key)}
                        title="Copy"
                        className="flex items-center transition-colors hover:text-primary"
                      >
                        <span
                          className={`material-symbols-outlined text-[18px] ${copiedId === k.id ? 'text-primary' : ''}`}
                        >
                          {copiedId === k.id ? 'check' : 'content_copy'}
                        </span>
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-on-surface-variant">
                    {new Date(k.createdAt).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRevoke(k.id)}
                      className="rounded-lg border border-error/30 px-3 py-1 font-label-caps text-[10px] font-bold uppercase text-error transition-all hover:bg-error/10"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section>
        <div className="mb-6">
          <h2 className="font-headline-md text-headline-md text-on-surface">Implementation Guide</h2>
          <p className="text-on-surface-variant">Start integrating Devinci NPC endpoints into your stack.</p>
        </div>
        <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
          <div className="flex flex-wrap border-b border-outline-variant bg-surface-container-lowest">
            {LANGS.map((lang) => (
              <button
                key={lang}
                onClick={() => setActiveLang(lang)}
                className={`border-b-2 px-6 py-3 font-label-caps text-label-caps transition-all ${
                  activeLang === lang
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'border-transparent text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {SNIPPETS[lang].label}
              </button>
            ))}
          </div>
          <div className="relative p-6 font-code-md text-code-md shadow-[inset_0_0_20px_rgba(160,120,255,0.05)]">
            <button
              onClick={handleCopySnippet}
              title="Copy"
              className="absolute right-4 top-4 rounded-lg bg-surface-container-highest/50 p-2 text-outline transition-colors hover:bg-surface-container-highest"
            >
              <span className={`material-symbols-outlined text-[18px] ${snippetCopied ? 'text-primary' : ''}`}>
                {snippetCopied ? 'check' : 'content_copy'}
              </span>
            </button>
            <pre className="overflow-x-auto leading-relaxed text-on-surface-variant">{SNIPPETS[activeLang].code}</pre>
          </div>
        </div>
      </section>

      {showGenerate && <GenerateApiKeyModal onGenerate={handleGenerate} onClose={() => setShowGenerate(false)} />}
    </div>
  );
}
