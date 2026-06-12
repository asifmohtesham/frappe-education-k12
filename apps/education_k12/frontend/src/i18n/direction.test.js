import { describe, it, expect } from 'vitest'
import { directionFor } from './direction'

describe('directionFor', () => {
  it('returns rtl for Arabic', () => {
    expect(directionFor('ar')).toBe('rtl')
  })
  it('returns ltr for English and unknown locales', () => {
    expect(directionFor('en')).toBe('ltr')
    expect(directionFor('fr')).toBe('ltr')
  })
})
