/** Tiny className joiner. Filters out falsy values. */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}
