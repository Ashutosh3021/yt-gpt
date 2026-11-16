# yt-gpt promotional site

## Concept

**The minute is the unit.**

yt-gpt turns a pile of YouTube links into a transcript library you can question. The product's promise is not "chat with video." It is "get the exact minute that answers you." The site is built around that unit: timecodes, playheads, citation traces, and the moment an answer locks to a source.

Working line: **Ask the video. Get the minute.**

## Audience

People who already learn from long YouTube videos: developers, researchers, students, and anyone who keeps a watch-later list longer than their patience. They care about citations, local files, token cost, and choosing their own model. They are skeptical of another cloud wrapper.

## Story

1. The desk: a local research workspace, not another chat box.
2. The minute: a 58 minute video becomes an 11 second answer with a timestamp.
3. The pipeline: links in, captions first, retrieval, cited answer.
4. The evidence: real interface frames, including a citation opening its source.
5. The rules: strict mode is structural, and the site says what it cannot promise.
6. The local part: plain folders, localhost, your provider, no telemetry.
7. The setup: two commands and a five minute guide.

## Art direction

An editing bay crossed with a research desk. Warm paper ground, near-black ink, hairline rules, monospaced timecode labels, and one signal orange used only for evidence and action. The page should feel measured and operational, not cinematic for its own sake. Screenshots sit in frames with status bars, as if they are monitors on the desk.

- Ground: `#f1f0e9`
- Paper: `#f8f7f2`
- Ink: `#15181b`
- Muted: `#5d6469`
- Faint: `#646a6e`
- Rule: `#d5d4cb`
- Signal: `#d8401a`
- Signal ink: `#a92c0d`
- Signal deep: `#b53212`
- Rail: `#141719`
- Rail ink: `#ecede7`
- Rail muted: `#b9bdba`

## Type

- **Supreme** for display and body. Tight, plainspoken, and a little editorial. Display sizes use `clamp()` with a hard ceiling so 1920 px screens do not turn into billboards.
- **DM Mono** for timecodes, labels, status, file trees, and command output. Uppercase labels are short and functional.
- Display: `clamp(3.6rem, 9.2vw, 9.5rem)`, line-height `0.86`, tracking `-0.055em`.
- Body: `1.0625rem / 1.62`, measure around 58 to 68 characters.

## Layout

- Max width `1560px`, fluid side padding `clamp(1.25rem, 4vw, 5rem)`.
- 12 column desktop grid. Hero uses a 7/5 split. Guide uses a sticky 3 column table of contents and a 9 column article.
- Section labels sit on a hairline with a timecode on the right.
- Screenshots are framed, never full bleed. Each frame carries a status bar and a demo-data label where appropriate.
- Breakpoints: 1100, 900, 640. At 900 the hero stacks, the minute stage stops being sticky, and the guide table of contents becomes a normal block. At 640 the header keeps only the essential links, figures lose their offset, and display type is checked at 390 px for mid-word breaks.

## Motion

Motion verb: **scrub and lock**.

- Intro: a short timecode curtain, then the two hero lines rise into place. Under 1.2 seconds of theatre.
- Scroll: one reveal treatment for content, a 24 px rise and fade. No reveal on every paragraph.
- Signature: the sticky minute stage. As the three evidence chapters pass, the timecode, quote, source, and playhead move together. The chapters remain full text in the document.
- Micro-interactions: one primary treatment per role. Buttons flood from the left and the arrow travels. Nav links draw an underline. Citation chips open a source card on hover or focus. Screenshot frames scale their image by 1.02 inside a clipped frame.
- Idle: the site is still at rest. The concept is carried by the scroll signature, the citation chip, and the hero composition. This is a deliberate choice for a quiet, research-focused product.
- Reduced motion: no Lenis, no ScrollTrigger reveals, no intro curtain, no scrub. All content is visible and the citation card still opens on focus.

## Content rules

- Sentence case. Concrete nouns and verbs. No em dashes, no "elevate", "seamless", "unleash", "cutting-edge", or "where X meets Y".
- Use the product's real language: workspace, session, source, transcript, citation, strict, interpretive, localhost.
- Say what is true today. The package is **in design**, not released. Screenshots use demo data.
- The production URL is unknown. `https://yt-gptt.vercel.app/` is a placeholder for canonical, Open Graph, robots, and sitemap. Replace it before deploy.
- The demo workspace is fictional sample data. It is labelled in the interface and on the site.

## Accessibility

- One `h1` per page, ordered headings, landmarks, skip link.
- AA contrast for all text. Orange is used for large type, rules, and non-text accents; small orange text uses the darker signal ink.
- Every hover state is reachable on `:focus-visible`. The citation demo opens with keyboard focus.
- Native cursor. Touch targets at least 44 px for primary actions.
- Reduced motion path is complete, not a degraded page.
- Screenshots have descriptive alt text and explicit dimensions.
- No content exists only inside animation.

## Performance

- Local fonts, WOFF2 only. Supreme 400 and 700 preloaded.
- Local GSAP, ScrollTrigger, and Lenis. No framework, no build step.
- Screenshots are WebP, lazy below the fold, with width and height set.
- One hero image is eager and high priority. All other images are lazy.
- Target: under 3 MB total, LCP under 2.5 s on a throttled phone, no layout shift.

## Files

- `index.html`: home page
- `guide.html`: setup and usage
- `404.html`: no signal
- `styles.css`: design system and page styles
- `script.js`: intro, reveals, minute scrub, citation demo, copy buttons
- `assets/img`: optimized screenshots and social image
- `assets/fonts`: self-hosted type
- `assets/vendor`: GSAP, ScrollTrigger, Lenis
- `robots.txt`, `sitemap.xml`: placeholder production URLs
