import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { User, Bot, Send, Volume2, Loader2 } from 'lucide-react';
import { streamTalk, synthesizeSpeech } from '../api';
import { ChatMessage } from '../types';

interface Props {
  slug: string;
}

export default function Chat({ slug }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [loadingSpeechId, setLoadingSpeechId] = useState<string | null>(null);
  const closeRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const stopSpeech = () => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setSpeakingId(null);
  };

  const toggleSpeak = async (message: ChatMessage) => {
    if (speakingId === message.id) {
      stopSpeech();
      return;
    }
    stopSpeech();
    setLoadingSpeechId(message.id);
    try {
      const blob = await synthesizeSpeech(message.text);
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setSpeakingId((id) => (id === message.id ? null : id));
      audio.onerror = () => setSpeakingId((id) => (id === message.id ? null : id));
      setLoadingSpeechId(null);
      setSpeakingId(message.id);
      await audio.play();
    } catch {
      setLoadingSpeechId(null);
    }
  };

  useEffect(() => {
    closeRef.current?.();
    stopSpeech();
    setMessages([]);
    setPending(false);
    setStreamingId(null);
  }, [slug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pending]);

  useEffect(() => () => {
    closeRef.current?.();
    stopSpeech();
  }, []);

  const send = () => {
    const text = input.trim();
    if (!text || pending) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: 'player', text }]);
    setPending(true);

    const npcMessageId = crypto.randomUUID();
    let started = false;

    closeRef.current = streamTalk(slug, text, {
      onChunk: (delta) => {
        if (!started) {
          started = true;
          setStreamingId(npcMessageId);
          setMessages((m) => [...m, { id: npcMessageId, role: 'npc', text: delta }]);
        } else {
          setMessages((m) => m.map((msg) => (msg.id === npcMessageId ? { ...msg, text: msg.text + delta } : msg)));
        }
      },
      onDone: (rawText, mood) => {
        let responseText = rawText;
        try {
          responseText = JSON.parse(rawText).response ?? rawText;
        } catch {
          // backend didn't return valid JSON, fall back to raw text
        }
        setMessages((m) =>
          started
            ? m.map((msg) => (msg.id === npcMessageId ? { ...msg, text: responseText, mood } : msg))
            : [...m, { id: npcMessageId, role: 'npc', text: responseText, mood }],
        );
        setStreamingId(null);
        setPending(false);
      },
      onError: (message) => {
        setMessages((m) => [...m, { id: crypto.randomUUID(), role: 'npc', text: message }]);
        setStreamingId(null);
        setPending(false);
      },
    });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full flex-col bg-surface-container-lowest">
      <div className="flex-1 space-y-6 overflow-y-auto custom-scrollbar p-6">
        {messages.length === 0 && !pending && (
          <div className="flex justify-center">
            <span className="rounded-full border border-outline-variant/20 bg-surface-container-high px-3 py-1 font-code-md text-[11px] uppercase tracking-widest text-outline-variant">
              NPC Sequence Initiated
            </span>
          </div>
        )}
        {messages.map((m) =>
          m.role === 'player' ? (
            <div key={m.id} className="ml-auto flex max-w-[85%] flex-row-reverse gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-secondary/30 bg-secondary/20">
                <User size={18} strokeWidth={1.75} className="text-secondary" />
              </div>
              <div className="space-y-2 text-right">
                <div className="rounded-xl rounded-tr-none bg-primary p-4 text-on-primary">
                  <p className="font-body-md leading-relaxed">{m.text}</p>
                </div>
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex max-w-[85%] gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/20">
                <Bot size={18} strokeWidth={1.75} className="text-primary" />
              </div>
              <div className="space-y-2">
                <div className="rounded-xl rounded-tl-none border border-outline-variant/30 bg-surface-container-high p-4 shadow-[0_0_40px_-10px_rgba(208,188,255,0.1)]">
                  {m.mood && (
                    <span className="mb-1 block font-label-caps text-[10px] uppercase tracking-wide text-primary">
                      {m.mood}
                    </span>
                  )}
                  <p className="font-body-md italic leading-relaxed text-on-surface">{m.text}</p>
                </div>
                {m.id !== streamingId && m.text && (
                  <button
                    onClick={() => toggleSpeak(m)}
                    disabled={loadingSpeechId === m.id}
                    aria-label={speakingId === m.id ? 'Stop speech' : 'Play speech'}
                    className="flex items-center gap-1 text-outline-variant transition-colors hover:text-primary disabled:opacity-30"
                  >
                    {loadingSpeechId === m.id ? (
                      <Loader2 size={14} strokeWidth={1.75} className="animate-spin" />
                    ) : (
                      <Volume2 size={14} strokeWidth={1.75} className={speakingId === m.id ? 'animate-pulse text-primary' : ''} />
                    )}
                  </button>
                )}
              </div>
            </div>
          ),
        )}
        {pending && !streamingId && (
          <div className="flex max-w-[85%] gap-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/20">
              <Bot size={18} strokeWidth={1.75} className="text-primary" />
            </div>
            <div className="flex items-center gap-1 rounded-xl rounded-tl-none border border-outline-variant/30 bg-surface-container-high p-4">
              <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40" />
              <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40" style={{ animationDelay: '0.2s' }} />
              <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40" style={{ animationDelay: '0.4s' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-outline-variant bg-surface-container/30 p-6 backdrop-blur-md">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Say something... (Shift+Enter for a new line)"
            rows={1}
            className="max-h-40 w-full resize-none rounded-lg border border-outline-variant bg-surface-container-lowest p-4 pr-12 font-body-md text-on-surface outline-none transition-colors focus:border-primary"
          />
          <button
            onClick={send}
            disabled={pending || !input.trim()}
            className="absolute bottom-3 right-3 text-primary transition-transform hover:scale-110 disabled:opacity-30"
          >
            <Send size={18} strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </div>
  );
}
