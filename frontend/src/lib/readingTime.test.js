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

  it('strips HTML markup before counting words', () => {
    const words = Array(400).fill('word').join(' ')
    const html = `<h1>Title</h1><p>${words}</p><ul><li>word</li></ul>`
    expect(estimateReadingTime(html)).toBe(2)
  })

  it('does not count image alt text or attribute values as words', () => {
    const altWords = Array(500).fill('alt-word').join(' ')
    const html = `<p>one two three</p><img src="/x.png" alt="${altWords}">`
    expect(estimateReadingTime(html)).toBe(1) // only "one two three" is real prose
  })
})
