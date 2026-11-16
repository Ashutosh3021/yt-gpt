import type { Segment, Session, SourceDoc, User, Video, Workspace } from '../types';

export const DEMO_EMAIL = 'demo@local';
export const DEMO_PASSWORD = 'demo';

const seg = (start: number, end: number, text: string): Segment => ({ start, end, text });

const segmentsNeural: Segment[] = [
  seg(0, 48, 'This is a three in the sense that it is a picture made of 28 by 28 pixels. Each pixel is a number between zero and one, and the picture is a grid of those numbers.'),
  seg(49, 120, 'A neuron is a thing that holds a number between zero and one. It is not a biological claim. It is a convenient unit for the arithmetic.'),
  seg(121, 240, 'The network is layers of these neurons. The weights are the numbers that get learned, and the bias shifts the threshold of each neuron.'),
  seg(241, 390, 'Before training, the weights are random. The output is nonsense. The point of the next few minutes is to see how the nonsense becomes a decision.'),
  seg(391, 520, 'Gradient descent is the idea of nudging each weight in the direction that lowers the cost. The gradient tells you which direction, and the learning rate tells you how far.'),
  seg(521, 700, 'The cost function measures how wrong the network is on the training data. A small cost means the output is close to the label, not that the model understands anything.'),
  seg(701, 860, 'Backpropagation tells each weight how it contributed to the error. It is the chain rule applied to a graph of operations, computed from the output backward.'),
  seg(861, 1000, 'This is not how the brain works. It is a useful cartoon. The value of the cartoon is that it predicts what the arithmetic will do.'),
  seg(1001, 1153, 'The same machinery scales to language, with one important change: the input is a sequence, and order matters. That change is where attention enters.'),
];

const segmentsGpt: Segment[] = [
  seg(0, 60, 'A transformer predicts the next token. That is the whole job. Everything else is machinery for making that prediction better.'),
  seg(61, 180, 'The context window is the only thing the model sees. There is no memory between calls, no database lookup, no hidden state that survives the request.'),
  seg(181, 340, 'Attention lets each token look at the tokens before it and decide which ones matter. The decision is learned, not hand-coded.'),
  seg(341, 520, 'The query says what this token is looking for. The key says what another token offers. The dot product between them is the match score.'),
  seg(521, 700, 'The value is the information that gets moved. Once the softmax turns scores into weights, the output is a weighted mix of the values.'),
  seg(701, 900, 'Multiple heads look for different relationships at once. One head might track the previous word, another might track the subject of the sentence.'),
  seg(901, 1100, 'The feed-forward block is where most of the parameters live. It processes each position independently after attention has mixed the information.'),
  seg(1101, 1300, 'Position matters, so the model adds positional information to the token embeddings. Without it, the operation would treat the input as a bag of words.'),
  seg(1301, 1500, 'The output is a probability over the vocabulary. Sampling from that distribution is what produces text, and the sampling settings change the feel of the output.'),
  seg(1501, 1634, 'Nothing here is a database. The knowledge is in the weights, distributed across parameters, and it is reconstructed in the forward pass.'),
];

const segmentsPaper: Segment[] = [
  seg(0, 120, 'The paper proposes a new architecture. The title makes the claim: attention is all you need. The contribution is the architecture, not a new attention operation.'),
  seg(121, 300, 'Recurrent networks process one step at a time, which limits parallelism. The paper’s argument is that attention removes that sequential dependency.'),
  seg(301, 520, 'The encoder is a stack of identical layers. Each layer has multi-head attention and a feed-forward block, with a residual connection and layer norm around each.'),
  seg(521, 760, 'Scaled dot-product attention is the core operation. Queries and keys produce scores, the scores are scaled, a softmax turns them into weights, and the weights mix the values.'),
  seg(761, 980, 'The scaling factor keeps the softmax from saturating. Large dot products push the softmax into a regime where gradients are small.'),
  seg(981, 1200, 'Multi-head attention runs several attention functions in parallel. The outputs are concatenated and projected, so the model can attend to different subspaces at once.'),
  seg(1201, 1450, 'The residual connection and layer norm make deep stacks trainable. Without them, the signal and the gradients degrade quickly.'),
  seg(1451, 1700, 'The decoder is masked so it cannot look ahead. That is what makes next-token prediction a valid training objective.'),
  seg(1701, 2000, 'Positional encodings inject order into a set-like operation. The paper uses fixed sinusoids, and later work mostly switched to learned or rotary variants.'),
  seg(2001, 2300, 'The results were strong on translation, and the architecture generalized. The paper reports BLEU scores and training cost, not a theory of why the pattern works.'),
  seg(2301, 2600, 'The paper is light on analysis of why it works. It does not isolate the contribution of individual heads or explain head specialization.'),
  seg(2601, 3000, 'The complexity is quadratic in sequence length, which becomes a problem for long inputs. That is the trade the architecture makes for parallelism.'),
  seg(3001, 3458, 'The takeaway is a general pattern: attention as a routing mechanism. The rest of the field is largely about making that routing cheaper and more reliable.'),
];

const segmentsKarpathy: Segment[] = [
  seg(0, 180, 'We are going to build a character-level transformer. The point is to see every line, not to hide the machine behind a framework.'),
  seg(181, 420, 'The dataset is a single text file. We split it into train and validation, and the model learns to predict the next character.'),
  seg(421, 700, 'A bigram model is the simplest baseline. It looks at one character and predicts the next, and it is bad in an instructive way.'),
  seg(701, 1000, 'The transformer adds communication between positions. Each token can gather information from earlier tokens instead of acting alone.'),
  seg(1001, 1400, 'Attention is a way for tokens to exchange information. The implementation is a few matrix multiplies and a softmax, and the shape of the tensors is the hard part.'),
  seg(1401, 1800, 'We implement one head first, then several. The multi-head version is not a different idea, it is the same idea repeated and mixed.'),
  seg(1801, 2200, 'Residual connections and layer norm keep the signal stable. Without them, the deeper model is harder to train than the shallow one.'),
  seg(2201, 2600, 'Dropout is a regularizer, not a fix for a bad model. It helps the model generalize, and it slows training down.'),
  seg(2601, 3000, 'Training on a laptop is slow but the shape of the loop is the same. The loss goes down, the samples get better, and the curve tells you what happened.'),
  seg(3001, 3400, 'We sample from the model and it produces plausible names. Plausible is not the same as correct, and the difference is the whole evaluation problem.'),
  seg(3401, 3800, 'The loss curve tells you whether the model is learning. A flat curve means the learning rate or the data is wrong, not that the architecture is broken.'),
  seg(3801, 4200, 'Overfitting shows up as a gap between train and validation. The fix is data, regularization or a smaller model, in that order.'),
  seg(4201, 4700, 'Scaling up is mostly more data, more parameters, more compute. The architecture matters, but the scale is what moves the benchmark.'),
  seg(4701, 5200, 'The model does not have a lookup table of facts. It has weights that encode statistical structure, and the structure is not easily inspectable.'),
  seg(5201, 5700, 'Evaluation is harder than training. A good loss does not tell you whether the model is useful, honest or safe.'),
  seg(5701, 6200, 'The same architecture is used for images and audio with small changes. The pattern is general because the operation is general.'),
  seg(6201, 6980, 'The point is to demystify the machine, not to ship a chatbot. Once you have built the small version, the large version is a matter of scale and engineering.'),
];

const video = (
  id: string,
  youtubeId: string,
  title: string,
  channel: string,
  durationS: number,
  transcriptSource: Video['transcriptSource'],
  tokens: number,
  summary: string,
  segments: Segment[],
  addedAt: string,
): Video => ({
  id,
  youtubeId,
  url: `https://www.youtube.com/watch?v=${youtubeId}`,
  title,
  channel,
  durationS,
  language: 'en',
  transcriptSource,
  status: 'ready',
  error: null,
  addedAt,
  tokens,
  summary,
  segments,
  visual: { enabled: false, status: 'none', frames: 0 },
  demo: true,
});

export const demoVideos: Video[] = [
  video(
    'v1',
    'aircAruvnKk',
    'But what is a neural network?',
    '3Blue1Brown',
    1153,
    'manual',
    4210,
    'A visual introduction to neurons, weights, gradient descent and backpropagation, ending at the point where sequence order starts to matter.',
    segmentsNeural,
    '2026-11-12T09:12:00Z',
  ),
  video(
    'v2',
    'wjZofJX0v4M',
    'But what is a GPT? Visual intro to transformers',
    '3Blue1Brown',
    1634,
    'manual',
    6840,
    'A visual walk through next-token prediction, context windows, queries, keys, values and multi-head attention.',
    segmentsGpt,
    '2026-11-12T09:13:00Z',
  ),
  video(
    'v3',
    'iDulHoQ2F48',
    'Attention is all you need, model explanation',
    'Yannic Kilcher',
    3458,
    'auto',
    14220,
    'A paper walkthrough: the encoder and decoder stacks, scaled dot-product attention, multi-head attention, positional encodings and the cost of the design.',
    segmentsPaper,
    '2026-11-12T09:14:00Z',
  ),
  video(
    'v4',
    'kCc8FmEb1nY',
    'Let’s build GPT: from scratch, in code, spelled out',
    'Andrej Karpathy',
    6980,
    'auto',
    28400,
    'A build from a bigram baseline to a small transformer, with the training loop, sampling, overfitting and the limits of the toy model.',
    segmentsKarpathy,
    '2026-11-13T16:40:00Z',
  ),
  {
    id: 'v5',
    youtubeId: 'private-demo',
    url: 'https://www.youtube.com/watch?v=private-demo',
    title: 'Members-only session (sample)',
    channel: 'Northfield Studio',
    durationS: 0,
    language: 'en',
    transcriptSource: 'manual',
    status: 'failed',
    error: 'Video is private. Retry with a cookies file or remove it.',
    addedAt: '2026-11-13T16:42:00Z',
    tokens: 0,
    summary: '',
    segments: [],
    visual: { enabled: false, status: 'none', frames: 0 },
    demo: true,
  },
];

const lectureVersions = [
  {
    id: 'ver-1',
    ts: '2026-11-12T10:02:00Z',
    note: 'First draft',
    content: `# Attention, in practice

## The operation
Each token produces a query, a key and a value. The score between a query and a key is scaled by 1/sqrt(d_k), passed through a softmax, and used to weight the values.
`,
  },
  {
    id: 'ver-2',
    ts: '2026-11-13T11:24:00Z',
    note: 'Tightened the operation section',
    content: `# Attention, in practice

## The operation
Each token produces a query, a key and a value. The query asks, the key advertises, the value carries. The score between a query and a key is scaled by 1/sqrt(d_k), passed through a softmax, and used to weight the values.

## Why several heads
One head can only express one relation at a time. Several heads let the model track syntax, position and reference at once.
`,
  },
  {
    id: 'ver-3',
    ts: '2026-11-14T08:41:00Z',
    note: 'Added open questions',
    content: `# Attention, in practice

## The operation
Each token produces a query, a key and a value. The query asks, the key advertises, the value carries. The score between a query and a key is scaled by 1/sqrt(d_k), passed through a softmax, and used to weight the values.

## Why several heads
One head can only express one relation at a time. Several heads let the model track syntax, position and reference at once.

## What the paper leaves open
The paper reports translation results. It does not isolate the contribution of individual heads.

## Open questions
- How much of the gain is from attention versus depth?
- What happens to head specialization after fine-tuning?
`,
  },
];

export const demoSources: SourceDoc[] = [
  {
    id: 'src-1',
    name: 'Lecture notes.md',
    updatedAt: '2026-11-14T08:41:00Z',
    content: lectureVersions[2].content,
    versions: lectureVersions,
  },
  {
    id: 'src-2',
    name: 'Glossary.md',
    updatedAt: '2026-11-13T09:10:00Z',
    content: `# Glossary

**Token**: a unit of text. Roughly a word piece.

**Query, key, value**: three projections of the same token embedding. The query asks, the key advertises, the value carries.

**Softmax**: turns a vector of scores into weights that sum to one.

**Residual connection**: adds a block’s input to its output so gradients have a short path.

**Context window**: the number of tokens the model can attend to at once.
`,
    versions: [
      {
        id: 'ver-1',
        ts: '2026-11-13T09:10:00Z',
        note: 'First draft',
        content: `# Glossary

**Token**: a unit of text. Roughly a word piece.

**Query, key, value**: three projections of the same token embedding. The query asks, the key advertises, the value carries.

**Softmax**: turns a vector of scores into weights that sum to one.

**Residual connection**: adds a block’s input to its output so gradients have a short path.

**Context window**: the number of tokens the model can attend to at once.
`,
      },
    ],
  },
  {
    id: 'src-3',
    name: 'Open questions.md',
    updatedAt: '2026-11-14T17:05:00Z',
    content: `# Open questions

1. Which claims in the explainers are later work rather than the original paper?
2. Does the quadratic cost matter at the lengths we actually use?
3. What would a citation-verified summary look like for a 2-hour lecture?
`,
    versions: [
      {
        id: 'ver-1',
        ts: '2026-11-13T17:05:00Z',
        note: 'Started',
        content: `# Open questions

1. Which claims in the explainers are later work rather than the original paper?
2. Does the quadratic cost matter at the lengths we actually use?
`,
      },
      {
        id: 'ver-2',
        ts: '2026-11-14T17:05:00Z',
        note: 'Added the summary question',
        content: `# Open questions

1. Which claims in the explainers are later work rather than the original paper?
2. Does the quadratic cost matter at the lengths we actually use?
3. What would a citation-verified summary look like for a 2-hour lecture?
`,
      },
    ],
  },
];

export const demoSessions: Session[] = [
  {
    id: 's1',
    title: 'Where does attention fit?',
    createdAt: '2026-11-13T10:20:00Z',
    updatedAt: '2026-11-14T18:02:00Z',
    settings: {
      grounding: 'strict',
      personaId: 'default',
      personaPrompt: null,
      modelOverride: null,
      useVisuals: false,
    },
    rollingSummary: '',
    messages: [
      {
        id: 'm1',
        role: 'user',
        content: 'What does attention actually do in a transformer?',
        ts: '2026-11-14T17:58:00Z',
      },
      {
        id: 'm2',
        role: 'assistant',
        ts: '2026-11-14T17:58:12Z',
        content: `Attention is a routing step. Each token produces a query, a key and a value. The query says what it is looking for, the key says what it offers, and the softmax over their dot products decides how much of each value to pull in. [[cite:wjZofJX0v4M:341]] [[cite:iDulHoQ2F48:521]]

That is why the operation is not a lookup. The model is not fetching a stored definition. It is deciding which earlier positions matter for this one. [[cite:wjZofJX0v4M:181]]

Two details keep it stable: the dot products are scaled before the softmax, and each block has a residual connection around it. [[cite:iDulHoQ2F48:761]]`,
        citations: [
          { videoId: 'wjZofJX0v4M', start: 341 },
          { videoId: 'iDulHoQ2F48', start: 521 },
        ],
      },
      {
        id: 'm3',
        role: 'user',
        content: 'How is that different from a CNN?',
        ts: '2026-11-14T18:01:00Z',
      },
      {
        id: 'm4',
        role: 'assistant',
        ts: '2026-11-14T18:01:11Z',
        content: `A convolution has a fixed neighborhood. A token at position 40 always looks at positions 39, 38, 37 in the same pattern. Attention learns the neighborhood per token. [[cite:wjZofJX0v4M:701]]

The cost is different too. A convolution scales with the width of the kernel. Attention compares every position with every other position, so it grows quadratically with sequence length. [[cite:iDulHoQ2F48:2601]]

That trade is the reason long-context work is mostly about making attention cheaper, not about adding more layers.`,
        citations: [
          { videoId: 'wjZofJX0v4M', start: 701 },
          { videoId: 'iDulHoQ2F48', start: 2601 },
        ],
      },
    ],
  },
  {
    id: 's2',
    title: 'Explain it like I’m new',
    createdAt: '2026-11-14T09:15:00Z',
    updatedAt: '2026-11-14T09:18:00Z',
    settings: {
      grounding: 'interpretive',
      personaId: 'lecturer',
      personaPrompt: null,
      modelOverride: null,
      useVisuals: false,
    },
    rollingSummary: '',
    messages: [
      {
        id: 'm1',
        role: 'user',
        content: 'Explain attention like I have never seen a transformer.',
        ts: '2026-11-14T09:15:00Z',
      },
      {
        id: 'm2',
        role: 'assistant',
        ts: '2026-11-14T09:15:14Z',
        content: `Imagine a room of people reading a sentence together. Each person holds one word. Before anyone speaks, every person asks the room a question, listens for the answers that fit, and takes a little from each. That is one attention head. [[cite:wjZofJX0v4M:181]]

A transformer runs several of these conversations at once, then mixes the results. [[cite:iDulHoQ2F48:981]]

Inference, marked as such: the useful mental model is routing, not memory. The weights decide where information goes. They do not store a dictionary you can open.`,
        citations: [
          { videoId: 'wjZofJX0v4M', start: 181 },
          { videoId: 'iDulHoQ2F48', start: 981 },
        ],
      },
    ],
  },
  {
    id: 's3',
    title: 'What the paper leaves open',
    createdAt: '2026-11-14T19:22:00Z',
    updatedAt: '2026-11-14T19:25:00Z',
    settings: {
      grounding: 'strict',
      personaId: 'skeptic',
      personaPrompt: null,
      modelOverride: null,
      useVisuals: false,
    },
    rollingSummary: '',
    messages: [
      {
        id: 'm1',
        role: 'user',
        content: 'What do the videos claim that the paper does not support?',
        ts: '2026-11-14T19:22:00Z',
      },
      {
        id: 'm2',
        role: 'assistant',
        ts: '2026-11-14T19:22:16Z',
        content: `The paper is explicit about results and light on mechanism. It reports strong translation numbers and a general architecture, but it does not isolate why multi-head attention helps. [[cite:iDulHoQ2F48:2301]]

The explainer goes further and says the pattern generalizes. That is a reasonable reading, but it is a claim about later work, not a result in the paper. [[cite:iDulHoQ2F48:2001]]

The visual explainers are careful about this: they describe the mechanism and say the knowledge lives in the weights, not in a database. [[cite:wjZofJX0v4M:1501]]`,
        citations: [
          { videoId: 'iDulHoQ2F48', start: 2301 },
          { videoId: 'iDulHoQ2F48', start: 2001 },
          { videoId: 'wjZofJX0v4M', start: 1501 },
        ],
      },
    ],
  },
];

export const demoUser: User = {
  id: 'u_demo',
  email: DEMO_EMAIL,
  name: 'Demo researcher',
  createdAt: '2026-11-12T08:55:00Z',
};

export function seedWorkspace(ownerId: string): Workspace {
  return {
    id: 'ws_attention',
    ownerId,
    name: 'Attention, in practice',
    slug: 'attention-in-practice',
    createdAt: '2026-11-12T09:10:00Z',
    updatedAt: '2026-11-14T19:25:00Z',
    settings: { useVisuals: false, summarize: true },
    videos: structuredClone(demoVideos),
    sessions: structuredClone(demoSessions),
    sources: structuredClone(demoSources),
    demo: true,
  };
}

export const demoTranscript = (videos: Video[]): string => {
  const lines: string[] = ['# Attention, in practice', '', 'Generated from the workspace videos.', ''];
  videos
    .filter((v) => v.status === 'ready')
    .forEach((v) => {
      lines.push(`## ${v.title}`, `${v.channel} · ${Math.round(v.durationS / 60)} min · ${v.transcriptSource} captions`, '');
      v.segments.forEach((s) => {
        const m = Math.floor(s.start / 60);
        const sec = Math.floor(s.start % 60);
        lines.push(`[${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}] ${s.text}`, '');
      });
    });
  return lines.join('\n');
};
