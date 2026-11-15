// Scroll helpers. Both are safe where the browser API is missing (tests, old browsers).

/**
 * Mark which edges of a scrolling pane have more content beyond them. The `scroll-fade`
 * class in globals.css fades those edges, so a pane never looks cut off mid-line.
 * It writes a data attribute directly, so scrolling does not re-render anything.
 */
export function markScrollEdges(el: HTMLElement | null) {
  if (!el) return;
  const edges: string[] = [];
  if (el.scrollTop > 2) edges.push("top");
  if (el.scrollHeight - el.scrollTop - el.clientHeight > 2) edges.push("bottom");
  const value = edges.join(" ");
  if (el.dataset.fade !== value) el.dataset.fade = value;
}

/**
 * Bring an element to the top of the window, smoothly. With `onlyIfAway`, it moves only
 * when the element's top is off screen or in the lower part of the window, so a click
 * never shifts a page that already shows what was asked for.
 */
export function scrollToElement(el: Element | null | undefined, onlyIfAway = false) {
  if (!el || typeof el.scrollIntoView !== "function") return;
  if (onlyIfAway) {
    const top = el.getBoundingClientRect().top;
    if (top >= 0 && top < window.innerHeight * 0.55) return;
  }
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}
