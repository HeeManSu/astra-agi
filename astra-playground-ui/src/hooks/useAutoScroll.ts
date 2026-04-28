import { useEffect, useRef } from "react";

/**
 * Pins a Radix ScrollArea (or any element with a scrollable viewport child)
 * to the bottom whenever any item in `deps` changes. Returns a ref that
 * should be attached to the ScrollArea root — this hook walks down to the
 * Radix viewport (`[data-radix-scroll-area-viewport]`) which is the element
 * that actually scrolls. Falls back to setting scrollTop on the ref itself
 * for non-Radix scroll containers.
 */
export function useAutoScroll<T extends HTMLElement = HTMLDivElement>(
  deps: ReadonlyArray<unknown>,
) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const viewport = root.querySelector<HTMLElement>(
      "[data-radix-scroll-area-viewport]",
    );
    const target = viewport ?? root;
    target.scrollTop = target.scrollHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}
