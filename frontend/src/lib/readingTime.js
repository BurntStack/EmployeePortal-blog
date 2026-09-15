/** Rough reading-time estimate at 200 words per minute, minimum 1 minute. */
export function estimateReadingTime(text) {
  const words = text.trim().split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / 200))
}
