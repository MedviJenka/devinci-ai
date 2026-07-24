import { useEffect, useState } from 'react';
import { Plus, KeyRound, Check, Copy } from 'lucide-react';
import { ApiKeyCreateResponse, ApiKeySummary } from '../types';
import { createApiKey, listApiKeys, revokeApiKey } from '../api';
import GenerateApiKeyModal from './GenerateApiKeyModal';

const SNIPPETS: Record<string, { label: string; code: string }> = {
  curl: {
    label: 'cURL',
    code: `curl "http://localhost:5555/api/v1/npcs/YOUR_NPC_SLUG/talk?query=hello" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
  },
  node: {
    label: 'Node.js',
    code: `const EventSource = require('eventsource');

const source = new EventSource(
  'http://localhost:5555/api/v1/npcs/YOUR_NPC_SLUG/talk?query=hello',
  { headers: { Authorization: 'Bearer YOUR_API_KEY' } }
);

source.onmessage = (event) => console.log(JSON.parse(event.data));`,
  },
  python: {
    label: 'Python',
    code: `import requests

url = "http://localhost:5555/api/v1/npcs/YOUR_NPC_SLUG/talk"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

response = requests.get(url, params={"query": "hello"}, headers=headers, stream=True)
for line in response.iter_lines(decode_unicode=True):
    if line.startswith("data: "):
        print(line[len("data: "):])`,
  },
  csharp: {
    label: 'C# (Unity)',
    code: `// Attach to a MonoBehaviour and start as a coroutine
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class DevinciClient : MonoBehaviour
{
    private const string ApiKey = "YOUR_API_KEY";

    public IEnumerator Talk(string npcSlug, string query)
    {
        var url = $"http://localhost:5555/api/v1/npcs/{npcSlug}/talk?query={UnityWebRequest.EscapeURL(query)}";
        var request = UnityWebRequest.Get(url);
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

void UDevinciClient::Talk(const FString& NpcSlug, const FString& Query)
{
    FHttpModule* Http = &FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = Http->CreateRequest();

    Request->SetURL(FString::Printf(TEXT("http://localhost:5555/api/v1/npcs/%s/talk?query=%s"), *NpcSlug, *Query));
    Request->SetVerb(TEXT("GET"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer YOUR_API_KEY"));

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

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKeySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [justCreated, setJustCreated] = useState<ApiKeyCreateResponse | null>(null);
  const [copiedNewKey, setCopiedNewKey] = useState(false);
  const [activeLang, setActiveLang] = useState<(typeof LANGS)[number]>('curl');
  const [snippetCopied, setSnippetCopied] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      setKeys(await listApiKeys());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to load api keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleGenerate = async (name: string) => {
    const created = await createApiKey(name);
    setJustCreated(created);
    setShowGenerate(false);
    await refresh();
  };

  const handleCopyNewKey = () => {
    if (!justCreated) return;
    navigator.clipboard.writeText(justCreated.key);
    setCopiedNewKey(true);
    setTimeout(() => setCopiedNewKey(false), 2000);
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('Revoke this key? This cannot be undone.')) return;
    await revokeApiKey(id);
    await refresh();
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
          <Plus size={18} strokeWidth={1.75} />
          Generate Key
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-error">{error}</div>
      )}

      {justCreated && (
        <div className="mb-6 rounded-lg border border-primary/40 bg-primary/5 p-4">
          <p className="mb-2 font-label-caps text-label-caps uppercase text-primary">
            Copy this key now — it won't be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-surface-container-lowest px-3 py-2 font-code-md text-code-md text-on-surface">
              {justCreated.key}
            </code>
            <button
              onClick={handleCopyNewKey}
              className="rounded-lg border border-outline-variant px-3 py-2 font-label-caps text-label-caps uppercase transition-colors hover:bg-surface-container-highest"
            >
              {copiedNewKey ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={() => setJustCreated(null)}
              className="rounded-lg border border-outline-variant px-3 py-2 font-label-caps text-label-caps uppercase transition-colors hover:bg-surface-container-highest"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {!loading && keys.length === 0 ? (
        <div className="mb-10 flex flex-col items-center justify-center rounded-lg border border-outline-variant bg-surface-container py-24 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
            <KeyRound size={36} strokeWidth={1.5} className="text-primary/60" />
          </div>
          <h3 className="mb-2 font-headline-md text-headline-md text-on-surface">No API keys yet</h3>
          <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
            Generate a key to authenticate requests to the Devinci Orchestrator API from outside the browser.
          </p>
          <button
            onClick={() => setShowGenerate(true)}
            className="rounded-lg bg-primary px-8 py-3 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110"
          >
            Generate First Key
          </button>
        </div>
      ) : (
        keys.length > 0 && (
          <div className="mb-10 overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
            <table className="w-full text-left font-body-md">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-lowest">
                  <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                    Key Name
                  </th>
                  <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                    Key
                  </th>
                  <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                    Created
                  </th>
                  <th className="px-6 py-3 font-label-caps text-label-caps uppercase tracking-wider text-outline">
                    Status
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
                    <td className="px-6 py-4 font-code-md text-code-md text-on-surface-variant">
                      {k.key_prefix}••••••••••••••••
                    </td>
                    <td className="px-6 py-4 text-on-surface-variant">
                      {new Date(k.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-6 py-4">
                      {k.revoked_at ? (
                        <span className="text-error">Revoked</span>
                      ) : (
                        <span className="text-primary">Active</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {!k.revoked_at && (
                        <button
                          onClick={() => handleRevoke(k.id)}
                          className="rounded-lg border border-error/30 px-3 py-1 font-label-caps text-[10px] font-bold uppercase text-error transition-all hover:bg-error/10"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
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
              {snippetCopied ? (
                <Check size={18} strokeWidth={1.75} className="text-primary" />
              ) : (
                <Copy size={18} strokeWidth={1.75} />
              )}
            </button>
            <pre className="overflow-x-auto leading-relaxed text-on-surface-variant">{SNIPPETS[activeLang].code}</pre>
          </div>
        </div>
      </section>

      {showGenerate && <GenerateApiKeyModal onGenerate={handleGenerate} onClose={() => setShowGenerate(false)} />}
    </div>
  );
}
