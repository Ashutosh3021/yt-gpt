# yt-gpt frontend: design and build notes

## Brief

Subject: `yt-gpt`, a local, NotebookLM-style workspace for YouTube. The visitor is a researcher,
student, writer or developer running the app on their own machine. The site's job is to make a
pile of links become a trustworthy, searchable conversation, and to make provenance obvious.

Audience: people who already use LLMs and care where answers come from. They are comfortable
with files, keys and localhost. They do not want a cloud account.

Constraints: the frontend is a prebuilt static bundle served by the FastAPI app at
`127.0.0.1:8765`. No backend exists in this repo yet, so the app ships with a complete demo
runtime. The HTTP client implements the API in `architecture.md` for when the server lands.

## Concept (three candidates)

| | A. Signal desk | B. File room | C. Margin |
|---|---|---|---|
| Territory | material of the profession: broadcast and editing consoles | the architecture's "everything is a file" | reading room and marginalia |
| Idea | The workspace is a local signal desk: videos are channels, answers are readouts, every claim is patched back to a timecode. | The workspace is a filing cabinet: drawers, index cards, paper clips, a stamp for each save. | The transcript is the page and the chat is the margin: answers sit beside the passage they came from. |
| Signature | a vermilion trace draws from the cited source row to the citation chip | a card is pulled out of a drawer and turns over | a pencil line draws from a margin note to the sentence |
| Motion verb | route and light | file and pull | annotate and settle |
| Scores O/F/Fe/P | 4 / 5 / 4 / 2 | 3 / 4 / 3 / 2 | 4 / 3 / 4 / 3 |

Pick A. The anchor is real and specific: every answer in this product is supposed to carry a
`[video_id @ mm:ss]` citation. A signal desk makes provenance the visual system rather than a
badge. The trace is useful, not just decorative: it points at the exact row and minute. The
other two are styles that would survive a move to any note-taking app.

### Concept card

```
Idea:        A local signal desk for YouTube: sources on the left, the conversation in the
             middle, every claim routed back to a timecode.
Metaphor:    broadcast and editing console (channels, ports, readouts, traces).
Signature:   on each grounded answer, a hairline signal draws from the cited video's port in
             the source rack to its citation chip; hovering a chip re-routes the trace and
             opens a small source monitor with the exact line.
Emotion:     calm control. The room is quiet, the signal is live, nothing is hidden.
Motion verb: route and light. Things draw, cue, and settle. No bouncing, no floating cards.
Screenshot:  an answer mid-stream, two vermilion traces crossing the paper gutter into
             timecode chips, source rack lit on the cited video.
```

## Art direction

### Palette

| Role | Value | Use |
|---|---|---|
| ground | `#F2F2ED` | page paper, chat surface |
| panel | `#F8F7F2` | right folio, form fields |
| ink | `#15181B` | text, primary buttons, curtain |
| muted | `#5F666B` | secondary text (5.2:1 on ground) |
| line | `#D9D9D1` | hairlines, dividers, input borders |
| signal | `#D8401A` | traces, live marks, focus accents (4.0:1, lines and large marks only) |
| signal ink | `#A92C0D` | small accent text (6.1:1 on ground) |
| rail | `#171A1D` | source rack, login left panel |
| rail ink | `#ECEDE7` | text on rail (14.8:1) |
| rail muted | `#A8ADAF` | metadata on rail (7.7:1) |
| live | `#14615C` | ready status, strict grounding chip |
| warn | `#7A4A00` | auto captions, pending |
| fail | `#9E2418` | failed jobs |

Status colors are functional, not decorative. Signal vermilion is used for traces, the active
tab marker, the brand LED, and one word in the login headline. No gradients.

### Type

- **Supreme** (Fontshare, 400/500/600/700) for display, UI and reading. Tall x-height, sharp
  terminals; it holds up at 12 px and at 9 rem.
- **DM Mono** (Google, 400/500) for timecodes, counts, paths, tokens and file sizes. The data
  voice, never the body voice.
- Display tracking `-0.045em`, leading `0.92`. Body 16 px, leading 1.55, measure 64ch. UI
  13 px. Meta 12 px in mono with `+0.01em`. Numbers use tabular figures.

### Grid and rhythm

- Global pages: 12 columns, 24 px gutter, max 1440 px, outer margin = gutter.
- Workspace: `304px | minmax(0, 1fr) | 368px`, 1 px hairlines, 20 px inner padding.
  The source rack is dark; the monitor and folio are paper.
- Alignment rule: everything in the monitor starts on the same 20 px inner line; timecodes
  are right-aligned in a mono column. The transcript page uses a 3-column reading grid
  (spine 88 px, measure 64ch, margin notes 220 px).
- Rhythm: topbar 60 px; rail sections 24 px; messages 28 px; page sections 96/128 px. No
  uniform section padding.

### Shape and motion

- Radius: 2 px on controls and chips, 0 on panels and inputs at rest (one rule, one exception
  for the LED dot, which is a circle because it is a lamp).
- Eases: `expo.out` for entrances, `expo.inOut` for curtains, `power3.out` for UI. Durations
  0.24 s feedback, 0.5 to 0.7 s UI, 0.85 s page transitions, 0.7 s trace draw. Stagger 20 to
  60 ms.
- Idle: the signal meter in the topbar breathes on a slow 8 s cycle; the `local` LED pulses
  once every 4 s. Both are driven by the GSAP ticker, pause when the tab is hidden, and are
  static under reduced motion.
- No loader. The app is a tool, not a launch. First paint is the login poster or the workspace.

## Composition plan

### Login

```
┌───────────────────────────────────────────┬──────────────────────────┐
│ yt-gpt            local · 127.0.0.1       │  Sign in                 │
│                                           │  ─────────────────────   │
│ Ask the video.                            │  Email                   │
│ Get the minute.                           │  [                    ]  │
│                                           │  Password                │
│ A local workspace for YouTube             │  [                    ]  │
│ transcripts. Captions first,              │  [ Enter workspace    ]  │
│ citations always.                         │                          │
│                                           │  Use the demo workspace  │
│ [proof strip: question → timecode → line] │  Create a profile        │
│                                           │                          │
│ ───────────────────────────────────────── │  Runs on your machine.   │
│ 03 sources   12 min   0 uploads           │  No telemetry.           │
└───────────────────────────────────────────┴──────────────────────────┘
```

### Workspace index

```
┌ topbar ──────────────────────────────────────────────────────────────┐
│ yt-gpt · Workspaces                        settings   account        │
├──────────────────────────┬───────────────────────────────────────────┤
│ Workspaces               │  Attention, in practice          3 videos  │
│ (display, 2 lines)       │  2 sessions · edited 2h ago       →       │
│                          │  ──────────────────────────────────────   │
│ Each workspace is a      │  How to read a paper              4 videos │
│ folder. Videos,          │  1 session · edited yesterday      →      │
│ sessions and sources     │  ──────────────────────────────────────   │
│ live together.           │  [ New workspace name        ]  Create    │
│                          │                                           │
│ [ New workspace ]        │  local root ~/.yt-gpt · v0.1.0-dev        │
└──────────────────────────┴───────────────────────────────────────────┘
```

### Workspace

```
┌ topbar: mark · workspace switcher · strict · model · local · transcript · settings ┐
├──────────────────┬─────────────────────────────────────┬────────────────────────────┤
│ LIBRARY     3    │ session tabs                        │ SOURCES               2    │
│ ┌──────────────┐ │ ┌─────────────────────────────────┐ │ ┌────────────────────────┐ │
│ │ 01 12:04  ●  │ │ │ you                             │ │ │ Lecture notes.md       │ │
│ │ title        │ │ │ what does attention actually do?│ │ │ 1.8 KB · 3 versions    │ │
│ │ channel      │ │ │                                 │ │ │ ─────────────────────  │ │
│ │ manual  19m  │ │ │ answer                          │ │ │ Glossary.md            │ │
│ │          port│ │ │ Attention weighs each token ... │ │ │ 900 B · 1 version      │ │
│ └──────────────┘ │ │ [02 · 12:04] [03 · 21:18]       │ │ │                        │ │
│ ...              │ └─────────────────────────────────┘ │ │ [ New source ]         │ │
│                  │  ┌─────────────────────────────────┐ │ │                        │ │
│ Add links        │  │ Ask this workspace...           │ │ │ The model can draft    │ │
│ [           ]    │  │                          [Send] │ │ │ here. Every save keeps │ │
│ [ Add links ]    │  └─────────────────────────────────┘ │ │ a version.             │ │
│ Export .md       │                                     │ │                        │ │
└──────────────────┴─────────────────────────────────────┴────────────────────────────┘
```

### Transcript

```
┌ topbar ──────────────────────────────────────────────────────────────┐
│ ← workspace name        Transcript · 3 videos · 18.4k tokens         │
├──────────────┬───────────────────────────────────────┬───────────────┤
│ 00:00        │ Attention, in practice                │ ON THIS PAGE  │
│ 01 19:13     │ Generated from 3 videos · 14 Nov      │ 01 title      │
│ 02 26:10     │ ─────────────────────────────────     │ 02 title      │
│ 03 57:31     │ 00:00  Neural networks are ...        │ 03 title      │
│              │                                       │               │
│ [Download]   │ 02:14  Attention weighs each token... │ [Copy all]    │
│              │                                       │               │
└──────────────┴───────────────────────────────────────┴───────────────┘
```

### 404

A dead oscilloscope line across the page, `No signal at this address.`, and one way back to
the workspaces.

## Genericness test

A generic model would produce: a three-column dashboard of rounded white cards, Inter, a
purple-blue accent, a centered empty state with an icon in a circle, a gradient CTA, and a
settings page of identical cards. Changed here: the dark source rack against paper, the
timecode spine, the citation trace as the one signature, mono data, 2 px controls, the signal
meter, the transcript as a designed reading page, the login proof strip, no loader, no card
grid. The workspace layout follows the product's real three-pane job, not a template.

## Assumptions and placeholders

- No backend exists yet. The demo runtime (localStorage) is complete and every screen works.
  `VITE_API_MODE=http` switches to the FastAPI endpoints in `architecture.md`.
- Demo content is sample data, marked `demo data` in the workspace header and in
  `src/data/demo.ts`. Video titles and channels are real public videos; the transcript lines
  are written samples, not verbatim captions. Replace them with ingested transcripts.
- Provider names and model ids in Settings are examples. Keys are never persisted in the demo
  beyond a masked last-four value.
- Local auth is the default provider. The Pyronites adapter is not represented in the UI.
- The production URL for canonical and OG metadata is `http://127.0.0.1:8765`, the address the
  package serves.
- The app ships without a loader on purpose. The first frame is the designed frame.
