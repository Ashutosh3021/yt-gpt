import { cleanup, leave } from '../engine';

let pending = false;

export async function transitionNavigate(navigate: (to: string) => void, to: string) {
  if (pending) return;
  pending = true;
  await leave();
  cleanup();
  navigate(to);
}

export function takePendingTransition() {
  const p = pending;
  pending = false;
  return p;
}
