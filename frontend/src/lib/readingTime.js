/**
 * Rough reading-time estimate at 200 words per minute, minimum 1 minute.
 * `content` is the editor's HTML — tags and their attributes (including
 * image alt text) are stripped first so only visible prose is counted.
 */
export function estimateReadingTime(content) {
  const text = String(content || '').replace(/<[^>]*>/g, ' ')
  const words = text.trim().split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / 200))
}
