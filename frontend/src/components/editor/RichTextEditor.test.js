import { describe, expect, it } from 'vitest'
import { MARKDOWN_SIGNAL } from './RichTextEditor.jsx'

describe('MARKDOWN_SIGNAL', () => {
  it('detects bold markdown', () => {
    expect(MARKDOWN_SIGNAL.test('How much will it cost? **It depends.**')).toBe(true)
  })

  it('detects headings', () => {
    expect(MARKDOWN_SIGNAL.test('## A heading\nSome text.')).toBe(true)
  })

  it('detects bullet lists', () => {
    expect(MARKDOWN_SIGNAL.test('- first point\n- second point')).toBe(true)
  })

  it('detects numbered lists', () => {
    expect(MARKDOWN_SIGNAL.test('1. first step\n2. second step')).toBe(true)
  })

  it('detects markdown links', () => {
    expect(MARKDOWN_SIGNAL.test('See [our site](https://burntstack.com) for more.')).toBe(true)
  })

  it('does not flag ordinary prose', () => {
    expect(MARKDOWN_SIGNAL.test('This is a normal sentence about our product roadmap.')).toBe(false)
  })

  it('does not flag a single stray asterisk', () => {
    expect(MARKDOWN_SIGNAL.test('Pricing starts at $50* per month, terms apply.')).toBe(false)
  })
})
