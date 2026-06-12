import { describe, it, expect } from 'vitest'
import { homeRouteFor } from './homeRoute'

describe('homeRouteFor', () => {
  it('routes teachers to homerooms', () => {
    expect(homeRouteFor({ is_teacher: true, is_guardian: false })).toBe('TeacherHomerooms')
  })
  it('routes guardians to children overview', () => {
    expect(homeRouteFor({ is_guardian: true, is_teacher: false })).toBe('Children')
  })
  it('prefers teacher when user is both', () => {
    expect(homeRouteFor({ is_teacher: true, is_guardian: true })).toBe('TeacherHomerooms')
  })
  it('falls back to NoAccess', () => {
    expect(homeRouteFor({})).toBe('NoAccess')
  })
})
