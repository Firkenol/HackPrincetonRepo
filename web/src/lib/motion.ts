import type { Transition, Variants } from "framer-motion";

// One set of motion settings for the whole console, so everything moves the same way.
// Springs are close to critically damped: things settle quickly and do not bounce.
// Nothing here delays a number by more than a fraction of a second.

/** Small things arriving: chips, rows, badges. */
export const SNAP: Transition = { type: "spring", stiffness: 420, damping: 34, mass: 0.8 };

/** Larger things settling: cards, the sliding selection marker. */
export const SETTLE: Transition = { type: "spring", stiffness: 260, damping: 30, mass: 0.9 };

/** A weighted fill, such as the comparison gauge. */
export const WEIGHT: Transition = { type: "spring", stiffness: 90, damping: 20, mass: 1 };

/** For height and opacity, where a spring would overshoot. */
export const EASE_OUT = [0.22, 1, 0.36, 1] as const;
export const UNFOLD: Transition = { duration: 0.28, ease: EASE_OUT };

/** A parent that reveals its children one after another. */
export function stagger(each = 0.06, delay = 0): Variants {
  return { hidden: {}, show: { transition: { staggerChildren: each, delayChildren: delay } } };
}

/** A child of `stagger`: rises a few pixels into place. */
export const RISE: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: SETTLE },
};

/** Reveal once, when the element scrolls into view. */
export const IN_VIEW = { once: true, margin: "0px 0px -8% 0px" } as const;
