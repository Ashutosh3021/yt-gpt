import { gsap } from 'gsap';
import { setTransition } from '../engine';
import { ease, prefersReducedMotion } from '../engine/env';
import { startSignal } from './signal';

let done = false;

export function setupMotion() {
  if (done) return;
  done = true;

  setTransition({
    leave: (curtain) => {
      const label = curtain.querySelector<HTMLElement>('.curtain__label');
      if (label) label.textContent = 'Routing';
      return gsap
        .timeline()
        .set(curtain, { autoAlpha: 1 })
        .fromTo(
          curtain.querySelector('.curtain__panel'),
          { xPercent: 100 },
          { xPercent: 0, duration: 0.62, ease: ease.inOut },
        );
    },
    enter: (curtain) => {
      const label = curtain.querySelector<HTMLElement>('.curtain__label');
      if (label) label.textContent = 'Ready';
      return gsap
        .timeline()
        .to(curtain.querySelector('.curtain__panel'), { xPercent: -100, duration: 0.7, ease: ease.inOut })
        .set(curtain, { autoAlpha: 0 })
        .set(curtain.querySelector('.curtain__panel'), { xPercent: 100 });
    },
  });

  if (!prefersReducedMotion()) startSignal();
  else startSignal();
}
