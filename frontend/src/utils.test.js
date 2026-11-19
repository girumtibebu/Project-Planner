import { describe, expect, it } from 'vitest'
import { addDays, dayKey, diffDays, groupItems, toDate, treeOrder, withDay } from './utils'

describe('treeOrder', () => {
  const t = (name, parent_task = null) => ({ name, parent_task })
  it('puts sub-items under their own parent, in sibling order', () => {
    // as in the bug: subs of abcd and of work item 2 were listed after the last parent
    const { items, depth } = treeOrder([t('abcd'), t('desos'), t('wi2'), t('4567', 'abcd'), t('adb', 'abcd'), t('789', 'wi2')])
    expect(items.map((i) => i.name)).toEqual(['abcd', '4567', 'adb', 'desos', 'wi2', '789'])
    expect(depth.get('adb')).toBe(1)
    expect(depth.get('desos')).toBe(0)
  })
  it('nests deeper levels and keeps orphans in place', () => {
    const { items, depth } = treeOrder([t('c', 'b'), t('a'), t('x', 'gone'), t('b', 'a')])
    expect(items.map((i) => i.name)).toEqual(['a', 'b', 'c', 'x'])
    expect(depth.get('c')).toBe(2)
  })
  it('survives a parent loop', () => {
    expect(treeOrder([t('a', 'b'), t('b', 'a')]).items.map((i) => i.name).sort()).toEqual(['a', 'b'])
  })
})

describe('dates', () => {
  it('reads ERPNext datetimes, date strings and Date objects', () => {
    expect(dayKey('2026-11-06 18:00:00')).toBe('2026-11-06')
    expect(dayKey('2026-11-06')).toBe('2026-11-06')
    expect(dayKey(new Date(2026, 10, 6, 23, 30))).toBe('2026-11-06')
    expect(toDate('')).toBe(null)
  })

  it('counts days across months', () => {
    expect(diffDays(new Date(2026, 10, 28), '2026-12-03')).toBe(5)
    expect(dayKey(addDays('2026-11-30', 1))).toBe('2026-12-01')
  })

  it('keeps the time of day when moving a datetime', () => {
    expect(withDay('2026-11-10', '2026-11-06 18:00:00')).toBe('2026-11-10 18:00:00')
    expect(withDay(new Date(2026, 10, 10))).toBe('2026-11-10 00:00:00')
  })
})

describe('groupItems', () => {
  it('keeps key order and puts multi-valued items in each group', () => {
    const groups = groupItems([{ a: ['x', 'y'] }, { a: [] }], (i) => i.a, ['y', 'x'])
    expect([...groups.keys()]).toEqual(['y', 'x', ''])
    expect(groups.get('x')).toHaveLength(1)
  })
})
