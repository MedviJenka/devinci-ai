# Frontend Test Plan

Scope: `frontend/src`. Stack is CRA + Jest + React Testing Library (already installed: `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`). No component tests exist yet except the default `App.test.tsx` smoke test.

## 1. Shared test infrastructure (build this first)

These mocks are needed by nearly every test below — set them up once in `src/test-utils/` before writing component tests.

| Dependency | Why it needs mocking | Approach |
|---|---|---|
| `src/supabaseClient.ts` | Every component that touches auth (`App`, `SignIn`, `api.ts`) imports the real Supabase client, which will try to hit the network. | `jest.mock('../supabaseClient')` with a fake object exposing `auth.getSession`, `auth.onAuthStateChange`, `auth.signOut`, `auth.signInWithOtp`, `auth.verifyOtp`, `auth.signInWithOAuth`. |
| `global.fetch` | `api.ts` (`listNpcs`, `createNpc`, `getNpc`, `updateNpc`, `deleteNpc`) calls `fetch` directly. | `jest.spyOn(global, 'fetch')` or `jest-fetch-mock`, reset per test. |
| `global.EventSource` | `streamTalk` in `api.ts` (used by `Chat`) uses `EventSource`, which doesn't exist in jsdom. | Hand-rolled fake `EventSource` class assigned to `global.EventSource`, capturing the instance so tests can fire `onmessage`/`onerror` manually. |
| `crypto.randomUUID` | Used in `Chat`, `Storylines`, `ApiKeys` for id generation. jsdom's implementation is inconsistent across Node versions. | Stub via `jest.spyOn(global.crypto, 'randomUUID')` returning deterministic sequential ids. |
| `navigator.clipboard.writeText` | Used in `ApiKeys` (copy key / copy snippet). Not implemented in jsdom. | `Object.assign(navigator, { clipboard: { writeText: jest.fn() } })`. |
| `window.confirm` | Used in `App.handleDelete` and `ApiKeys.handleRevoke`. | `jest.spyOn(window, 'confirm')`. |
| `window.location` / OAuth redirect | `SignIn.signInWithGoogle` reads `window.location.origin`. | jsdom default is fine; just assert the call args. |
| Timers | `ApiKeys` copy feedback and OTP resend use `setTimeout`. | `jest.useFakeTimers()` where the 2s copy-feedback reset is asserted. |

Add a small `renderWithProviders` helper only if a real provider/context gets introduced later — currently no context providers exist, so plain RTL `render` is sufficient.

## 2. `api.ts` (unit tests, no component needed)

- `listNpcs` / `getNpc` / `createNpc` / `updateNpc` / `deleteNpc`: builds correct URL (`API_BASE` + path), correct method/body, attaches `Authorization: Bearer <token>` when a session exists, omits the header when there is none.
- Non-OK response: throws an `Error` using `body.detail` when present, falls back to `request failed (<status>)` when the error body isn't JSON.
- `204` response: resolves to `undefined` instead of trying to parse a body.
- `streamTalk`:
  - Builds the `EventSource` URL with `query` and (when present) `token` as query params, URL-encoding `slug`.
  - Dispatches `onChunk` for `{type: 'chunk'}` messages, `onDone` for `{type:'done'}` (and closes the source), `onError` for `{type:'error'}` (and closes the source).
  - `onerror` on the EventSource itself calls `handlers.onError('Connection lost.')` and closes the source.
  - Returned cleanup function closes the source; if called before the async token lookup resolves, the subsequently-created `EventSource` is still closed (`closed` flag race).

## 3. Component test plans

### `Sidebar`
- Renders all nav items; the item matching `activeScreen` gets the active styling class, others don't.
- Clicking an enabled nav item calls `onNavigate` with its `screen`.
- The disabled "Usage & Billing" item shows a "Soon" badge, is not clickable (no `onNavigate` call), and never receives the active style even if it somehow matched.
- Clicking "New NPC" calls `onCreate`.
- When `userEmail` is set, email is shown (with `title` attr for truncation) and sign-out button calls `onSignOut`.
- When `userEmail` is `undefined`/`null`, the email/sign-out block doesn't render at all.

### `Library`
- Renders a table row per NPC with role, goal, slug, llm.
- Empty state: `npcs = []` shows "The Archive is Silent" + "Create First NPC" button wired to `onCreate`.
- Search: typing a query filters by role/slug/goal (case-insensitive substring); no matches shows "No matches found" (and no "Create First NPC" button, since `npcs.length !== 0`).
- Clicking a row calls `onOpenChat(slug)`.
- Clicking the edit icon calls `onOpenPersona(slug)` **and** does not also trigger `onOpenChat` (verifies `stopPropagation`).
- Clicking the delete icon calls `onDelete(slug)` and does not trigger `onOpenChat`.
- Pressing `/` while focus is outside any input/textarea/contentEditable focuses the search box and prevents default; pressing `/` while an input is focused does not steal focus (e.g. simulate focus in the search box itself, or another text field).
- Footer count text reads "Showing X of Y NPCs" and updates as the query narrows results.
- Effect cleanup: unmounting removes the `keydown` listener (no state update warnings / no double-handling after remount).

### `Dashboard`
- Empty (`npcs=[]`): shows "The Archive is Silent" and empty-state button calls `onCreate`; stat tiles show `0`, `0`, `—`.
- Non-empty: "Total NPCs" = `npcs.length`; "LLMs in use" = distinct llm count; "Most used LLM" = the llm with the highest count (tie-break: verify against a fixed input rather than assuming stable sort behavior, since `Map` insertion order breaks ties).
- LLM breakdown list renders one row per distinct llm, sorted descending by count, with correct singular/plural ("1 npc" vs "N npcs").
- Roster list renders one button per NPC; clicking calls `onOpenChat(slug)`.

### `Chat`
- Initial state shows "NPC Sequence Initiated" placeholder when there are no messages and not pending.
- Sending a message (Enter key or send button):
  - Appends a player message immediately and clears the input.
  - Send button is disabled when input is blank/whitespace-only, and while `pending`.
  - Enter key with empty/whitespace input is a no-op.
- Streaming completion (`onDone`): appends an npc message; if `rawText` is valid JSON with a `response` field, displays that field; if `rawText` is plain text (JSON.parse throws), falls back to displaying `rawText` verbatim. Also verify `mood` renders as a badge when present, and is absent when `mood` is undefined.
- Streaming error (`onError`): appends an npc message with the error text as content, and clears `pending` (send button re-enabled).
- Changing `slug` prop (re-render with a new prop): closes the previous stream (`closeRef.current` called), resets `messages` to `[]` and `pending` to `false`.
- Unmount while a stream is open: cleanup calls `closeRef.current()` (assert underlying fake EventSource's `close` was called — guards against leaked connections).
- Auto-scroll: `scrollIntoView` is called on the sentinel div when messages/pending change (mock `Element.prototype.scrollIntoView`, since jsdom doesn't implement it).

### `PersonaEditor`
- Initializes all four fields (`goal`, `backstory`, `llm`, `persona_notes`) from the `npc` prop.
- Editing a field updates its value (controlled input).
- Re-rendering with a different `npc` prop resets all fields to the new npc's values and clears the "Saved" indicator (covers the `useEffect` keyed on `npc`).
- Clicking "Save changes": button shows "Saving..." and is disabled while the `onSave` promise is pending; on resolve, shows "Saved" indicator and re-enables the button; on **reject**, the `finally` still re-enables the button but "Saved" is not shown (currently no visible error surface — worth flagging as a gap, see §5).
- Calls `onSave` with exactly `{ goal, backstory, llm, persona_notes }` reflecting current field state, not the original `npc` values, after edits.

### `CreateNpcModal`
- Submit button disabled when `name` is blank/whitespace; enabled once a non-whitespace name is entered.
- Submitting trims nothing on `goal`/`backstory` — verify empty string is sent as `undefined` (per `goal || undefined`), non-empty string passed through as typed.
- Successful `onCreate`: button shows "Creating..." while pending (assert via a controllable promise), modal doesn't self-close (parent controls that via `onClose`/state).
- Failed `onCreate` (rejected promise): displays `err.message`, or the generic fallback string if the rejection isn't an `Error` instance; `submitting` resets so the button is usable again.
- "Cancel" button calls `onClose` without calling `onCreate`.
- Form submits on Enter within a text field (native form behavior) as well as via the submit button click.

### `CreateStorylineModal`
- Default `npcSlug` is `npcs[0]?.slug`; when `npcs` is empty, defaults to `''`.
- Submit disabled when `title` is blank or `npcSlug` is falsy (e.g., `npcs=[]`).
- Submitting calls `onCreate({ title: trimmed, npcSlug, prompt: trimmed })` — verify both `title` and `prompt` are trimmed even if the button-disabled check only trims `title`.
- Changing the `<select>` updates `npcSlug` and the value passed to `onCreate`.
- "Cancel" calls `onClose` without calling `onCreate`.

### `Storylines`
- Empty state copy differs based on whether `npcs` is empty ("Create an NPC first...") vs non-empty ("Draft your first narrative arc...").
- "New Storyline" button is disabled (with a title tooltip) when `npcs.length === 0`.
- Creating a storyline via the modal prepends it to the list (newest first) and closes the modal.
- `npcRole(slug)` resolution: displays the matching NPC's `role`; falls back to the raw slug if the NPC was deleted from `npcs` after the storyline was created (simulate by creating with one npcs array, then re-rendering `Storylines` with a shorter `npcs` prop).
- Deleting a storyline removes only that card, leaving others intact.
- `prompt` is conditionally rendered — a storyline created with an empty prompt shows no prompt paragraph.

### `ApiKeys`
- Empty state renders "No API keys yet" with a "Generate First Key" button.
- Generating a key (via `GenerateApiKeyModal`) prepends a new entry with `revealed: false`, closes the modal, and the table now renders with that row.
- `maskKey`: displayed string shows first 8 chars, 16 mask dots, last 4 chars when `revealed` is false; full key shown when `revealed` is true. Toggling the reveal icon flips only that row's `revealed` state (others unaffected).
- Copy key button: calls `navigator.clipboard.writeText(key)`, shows a "check" icon for that row for ~2s, then reverts (use fake timers); copying a different key's row doesn't reset the first row's copied state prematurely — but copying while a previous copy's timeout is still pending should not incorrectly clear the *new* copiedId (check the `cur === id` guard in `setCopiedId`).
- Revoke: confirms via `window.confirm`; declining leaves the key list untouched; confirming removes only the targeted key.
- Language tabs: clicking a tab switches `activeLang` and the displayed `<pre>` snippet; the active tab has the highlighted style.
- Copy snippet button: writes the current language's code to clipboard and shows temporary "copied" feedback independent of the per-key copy state.

### `GenerateApiKeyModal`
- Submit disabled when `name` is blank/whitespace.
- Submitting calls `onGenerate(name.trim())` (verify surrounding whitespace is stripped).
- "Cancel" calls `onClose` without calling `onGenerate`.

### `SignIn`
- Google button: click calls `supabase.auth.signInWithOAuth` with `{ provider: 'google', options: { redirectTo: window.location.origin } }`; shows "Redirecting..." and disables the button while pending; on error response, re-enables the button and displays the error message (no navigation actually happens in jsdom, so "success" just means the promise never resolves in the test — assert the loading state only, not a redirect).
- Email step: submit disabled until a non-blank email is entered; submitting calls `supabase.auth.signInWithOtp({ email: trimmed })`.
  - Success: shows "Code sent to \<email\>.", clears digit state, transitions to the OTP step, and focuses the first digit input.
  - Failure: shows `error.message`, stays on the email step.
- OTP step:
  - Typing a digit advances focus to the next box; only the last character of pasted/typed input is kept, non-digits stripped.
  - Backspace on an empty box moves focus to the previous box; backspace on a non-empty box does not move focus.
  - Pasting a 6-digit string distributes one digit per box and focuses the box after the last filled one (or the last box if paste length >= 6).
  - Submit disabled while any digit is empty.
  - Submitting with fewer than 6 digits (edge case reachable via programmatic paste of <6 digits then direct submit) shows "Enter all 6 digits." without calling `verifyOtp`.
  - Successful `verifyOtp` calls `onSignedIn`.
  - Failed `verifyOtp` shows `error.message` and does not call `onSignedIn`.
  - "Change email" returns to the email step and clears error/info.
  - "Resend code" re-invokes `sendCode` (assert `signInWithOtp` called again) and is disabled while submitting.

### `App` (integration-level, mock `api.ts` + `supabaseClient` at the module boundary)

- **Auth gating**: while `getSession` is unresolved, renders only the blank loading screen; once resolved with `session: null`, renders `SignIn`; once resolved with a session, renders the authenticated shell (`Sidebar` + `main`).
- On mount with a session, calls `listNpcs` and renders results; a rejected `listNpcs` surfaces the error banner with `err.message`.
- `onAuthStateChange` callback firing with a new session (e.g., simulating sign-out) updates `session` state and re-renders accordingly (simulate `SIGNED_OUT` -> back to `SignIn`).
- Navigation: clicking each Sidebar nav item swaps the rendered screen (`Dashboard` / `Library` / `Storylines` / `ApiKeys`) and clears `selected`.
- Opening an NPC (`onOpenChat` from `Dashboard`/`Library`) calls `getNpc(slug)`, then shows the detail header (role, llm badge) with the `Chat` tab active by default from chat entry points, `PersonaEditor` tab active from persona entry points.
  - Failed `getNpc` shows the error banner and does not change `selected`/`screen`.
- Tab switching between "Chat" and "Persona" inside the detail view toggles which child renders, preserving `selected`.
- "Back to library" button clears `selected` without changing `screen`.
- Create flow: "New NPC" opens `CreateNpcModal`; submitting calls `createNpc`, then `listNpcs` again (refresh), sets the new NPC as `selected` with `tab='persona'`, and closes the modal.
- Delete flow: `window.confirm` declined -> `deleteNpc` not called; confirmed -> calls `deleteNpc(slug)`, refreshes the list, and if the deleted NPC was `selected`, clears `selected` (returns to Library).
- Save flow (`PersonaEditor.onSave` -> `App.handleSave`): calls `updateNpc(selected.slug, fields)`, updates `selected` with the response, and refreshes the list (so Library/Dashboard reflect the rename immediately).
- Sign out: clicking Sidebar's sign-out button calls `supabase.auth.signOut()`.

## 4. Suggested priority order

1. Shared test infra (`fetch`, `EventSource`, `supabase` mocks) — nothing else can be tested reliably without it.
2. `api.ts` — pure logic, highest leverage, no rendering needed.
3. `Chat` and `SignIn` — most complex state machines, highest regression risk (streaming, OTP flow).
4. `Library`, `Dashboard`, `Sidebar` — pure-ish presentational logic with filtering/derived state.
5. Modals (`CreateNpcModal`, `CreateStorylineModal`, `GenerateApiKeyModal`) — simple, repetitive, quick wins.
6. `PersonaEditor`, `ApiKeys`, `Storylines` — local-state CRUD components.
7. `App` integration tests last, once children are individually covered — they mostly re-verify wiring, not logic.

## 5. Gaps observed while reading the code (flag, don't silently test around them)

- `PersonaEditor.save()`: if `onSave` rejects, the error is swallowed (only `finally` runs) — there's no user-visible failure state. Worth confirming with the team whether this is intentional before writing a test that asserts "no error shown," since that's asserting a possible bug rather than a behavior.
- `Storylines` and `ApiKeys` are entirely local `useState` (no persistence) — tests should treat their data as session-only and not assume any backend integration.
