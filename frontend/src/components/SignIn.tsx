import { useRef, useState } from 'react';
import { supabase } from '../supabaseClient';

type Step = 'email' | 'otp';

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';

interface Props {
  onSignedIn: () => void;
}

export default function SignIn({ onSignedIn }: Props) {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [digits, setDigits] = useState<string[]>(Array(6).fill(''));
  const [submitting, setSubmitting] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const digitRefs = useRef<(HTMLInputElement | null)[]>([]);

  const signInWithGoogle = async () => {
    setGoogleLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
    if (error) {
      setError(error.message);
      setGoogleLoading(false);
    }
    // on success, the browser navigates away to Google's consent screen
  };

  const sendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    setInfo(null);
    const { error } = await supabase.auth.signInWithOtp({ email: email.trim() });
    setSubmitting(false);
    if (error) {
      setError(error.message);
      return;
    }
    setInfo(`Code sent to ${email.trim()}.`);
    setDigits(Array(6).fill(''));
    setStep('otp');
    setTimeout(() => digitRefs.current[0]?.focus(), 0);
  };

  const handleDigitChange = (index: number, value: string) => {
    const clean = value.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = clean;
    setDigits(next);
    if (clean && index < 5) digitRefs.current[index + 1]?.focus();
  };

  const handleDigitKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      digitRefs.current[index - 1]?.focus();
    }
  };

  const handleDigitPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    const next = Array(6).fill('');
    for (let i = 0; i < pasted.length; i++) next[i] = pasted[i];
    setDigits(next);
    digitRefs.current[Math.min(pasted.length, 5)]?.focus();
  };

  const verifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = digits.join('');
    if (token.length !== 6) {
      setError('Enter all 6 digits.');
      return;
    }
    setSubmitting(true);
    setError(null);
    const { error } = await supabase.auth.verifyOtp({
      email: email.trim(),
      token,
      type: 'email',
    });
    setSubmitting(false);
    if (error) {
      setError(error.message);
      return;
    }
    onSignedIn();
  };

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 rounded-lg border border-outline-variant bg-surface-container p-8 shadow-[0_0_40px_-10px_rgba(208,188,255,0.15)]">
        <div className="flex flex-col items-center gap-3 border-b border-outline-variant pb-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-primary">
            <span
              className="material-symbols-outlined text-[22px] text-on-primary"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              bolt
            </span>
          </div>
          <h1 className="font-headline-md text-headline-md font-bold leading-none tracking-tight text-on-surface">
            Devinci
          </h1>
          <p className="font-label-caps text-[9px] uppercase tracking-[0.2em] text-primary">NPC Studio</p>
        </div>

        <button
          type="button"
          onClick={signInWithGoogle}
          disabled={googleLoading}
          className="flex w-full items-center justify-center gap-3 rounded border border-outline-variant bg-transparent py-3 font-label-caps text-label-caps text-on-surface transition-colors hover:bg-surface-container-high disabled:opacity-50"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62z"
            />
            <path
              fill="#34A853"
              d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.96v2.33A9 9 0 0 0 9 18z"
            />
            <path
              fill="#FBBC05"
              d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.03l2.99-2.33z"
            />
            <path
              fill="#EA4335"
              d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.97l2.99 2.33C4.66 5.17 6.65 3.58 9 3.58z"
            />
          </svg>
          {googleLoading ? 'Redirecting...' : 'Continue with Google'}
        </button>

        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-outline-variant" />
          <span className="font-label-caps text-[10px] uppercase text-outline">or</span>
          <div className="h-px flex-1 bg-outline-variant" />
        </div>

        {step === 'email' ? (
          <form onSubmit={sendCode} className="space-y-5">
            <div className="space-y-2">
              <label className={labelClass}>Email</label>
              <input
                autoFocus
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputClass}
              />
            </div>

            {error && <p className="text-sm text-error">{error}</p>}

            <button
              type="submit"
              disabled={!email.trim() || submitting}
              className="flex w-full items-center justify-center gap-2 rounded bg-primary py-3 font-label-caps text-label-caps text-on-primary transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            >
              {submitting ? 'Sending...' : 'Send code'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="space-y-5">
            <div className="space-y-2">
              <label className={labelClass}>6-digit code</label>
              <p className="font-body-md text-sm text-on-surface-variant">Sent to {email.trim()}</p>
              <div className="flex justify-between gap-2">
                {digits.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      digitRefs.current[i] = el;
                    }}
                    value={digit}
                    onChange={(e) => handleDigitChange(i, e.target.value)}
                    onKeyDown={(e) => handleDigitKeyDown(i, e)}
                    onPaste={handleDigitPaste}
                    inputMode="numeric"
                    maxLength={1}
                    className="h-12 w-full rounded border border-outline-variant bg-surface-container-lowest text-center font-code-md text-lg text-on-surface outline-none transition-colors focus:border-primary"
                  />
                ))}
              </div>
            </div>

            {error && <p className="text-sm text-error">{error}</p>}

            <button
              type="submit"
              disabled={digits.some((d) => !d) || submitting}
              className="flex w-full items-center justify-center gap-2 rounded bg-primary py-3 font-label-caps text-label-caps text-on-primary transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            >
              {submitting ? 'Verifying...' : 'Verify & sign in'}
            </button>

            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => {
                  setStep('email');
                  setError(null);
                  setInfo(null);
                }}
                className="text-on-surface-variant hover:text-on-surface"
              >
                Change email
              </button>
              <button
                type="button"
                onClick={sendCode}
                disabled={submitting}
                className="text-primary hover:brightness-110 disabled:opacity-50"
              >
                Resend code
              </button>
            </div>
          </form>
        )}

        {info && step === 'otp' && <p className="text-center text-sm text-on-surface-variant">{info}</p>}
      </div>
    </div>
  );
}
