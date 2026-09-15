import { describe, expect, it } from 'vitest'
import { estimateReadingTime } from './readingTime.js'

describe('estimateReadingTime', () => {
  it('returns 1 minute minimum for very short text', () => {
    expect(estimateReadingTime('a few words')).toBe(1)
  })

  it('returns 1 minute for empty content', () => {
    expect(estimateReadingTime('')).toBe(1)
  })

  it('rounds to the nearest minute at 200 words per minute', () => {
    const words = Array(500).fill('word').join(' ')
    expect(estimateReadingTime(words)).toBe(3) // 500 / 200 = 2.5 -> rounds to 3
  })

  it('ignores extra whitespace between words', () => {
    const words = Array(400).fill('word').join('   \n  ')
    expect(estimateReadingTime(words)).toBe(2)
  })
})
