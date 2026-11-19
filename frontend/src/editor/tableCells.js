/**
 * Table cells for the page editor: a background colour per cell, and the row/column actions of the
 * Plane-style table menus. Every action works on one cell (its position before the cell node, taken
 * when the menu opened) and ends with the cursor back in that cell.
 */

import { Extension } from '@tiptap/core'
import { TextSelection } from '@tiptap/pm/state'
import { CellSelection, cellAround, selectedRect } from '@tiptap/pm/tables'

// soft fills that keep text readable; stored as plain CSS colours in the page HTML
export const CELL_COLORS = [
  { name: 'Gray', value: '#E5E7EB' },
  { name: 'Red', value: '#FEE2E2' },
  { name: 'Pink', value: '#FCE7F3' },
  { name: 'Orange', value: '#FFEDD5' },
  { name: 'Yellow', value: '#FEF9C3' },
  { name: 'Green', value: '#DCFCE7' },
  { name: 'Teal', value: '#CCFBF1' },
  { name: 'Blue', value: '#DBEAFE' },
  { name: 'Purple', value: '#EDE9FE' },
]

export const TableCellBackground = Extension.create({
  name: 'tableCellBackground',
  addGlobalAttributes() {
    return [
      {
        types: ['tableCell', 'tableHeader'],
        attributes: {
          background: {
            default: null,
            // our own attribute, or an inline fill pasted from Word, Excel or a web page
            parseHTML: (el) => el.getAttribute('data-background') || el.style.backgroundColor || el.getAttribute('bgcolor') || null,
            renderHTML: (attrs) => (attrs.background ? { 'data-background': attrs.background, style: `background-color: ${attrs.background}` } : {}),
          },
        },
      },
    ]
  },
})

/** Position of the cell the user is in: the cursor's cell, or the anchor of a row/column selection. */
export function cellPosAt(state) {
  const $cell = state.selection instanceof CellSelection ? state.selection.$anchorCell : cellAround(state.selection.$anchor)
  return $cell ? $cell.pos : null
}

function lineOf(state, cellPos, kind) {
  const $cell = state.doc.resolve(cellPos)
  return kind === 'row' ? CellSelection.rowSelection($cell) : CellSelection.colSelection($cell)
}

/** Put the cursor back in the cell, wherever it moved to in this transaction, and apply it. */
function finish(editor, tr, cellPos) {
  tr.setSelection(TextSelection.near(tr.doc.resolve(tr.mapping.map(cellPos) + 1)))
  editor.view.dispatch(tr)
  editor.view.focus()
}

/** Highlight the whole row or column while its menu is open. */
export function highlightLine(editor, cellPos, kind) {
  editor.view.dispatch(editor.state.tr.setSelection(lineOf(editor.state, cellPos, kind)))
}

export function backToCell(editor, cellPos) {
  finish(editor, editor.state.tr, cellPos)
}

export function colorLine(editor, cellPos, kind, color) {
  const { state } = editor
  const tr = state.tr
  lineOf(state, cellPos, kind).forEachCell((cell, pos) => tr.setNodeMarkup(pos, null, { ...cell.attrs, background: color }))
  finish(editor, tr, cellPos)
}

export function clearLine(editor, cellPos, kind) {
  const { state } = editor
  const cells = []
  lineOf(state, cellPos, kind).forEachCell((cell, pos) => cells.push([cell, pos]))
  const tr = state.tr
  // from the end, so earlier positions stay valid
  for (const [cell, pos] of cells.reverse()) tr.replaceWith(pos + 1, pos + cell.nodeSize - 1, cell.type.contentMatch.defaultType.createAndFill())
  finish(editor, tr, cellPos)
}

/** Copy the row or column, contents and colours, next to it. */
export function duplicateLine(editor, cellPos, kind) {
  const { state } = editor
  const rect = selectedRect(state.apply(state.tr.setSelection(new CellSelection(state.doc.resolve(cellPos)))))
  const { map, table, tableStart } = rect
  const tr = state.tr
  if (kind === 'row') {
    let pos = tableStart
    for (let i = 0; i < rect.top; i++) pos += table.child(i).nodeSize
    const row = table.child(rect.top)
    tr.insert(pos + row.nodeSize, row.type.create(row.attrs, row.content))
  } else {
    // shortcut: a merged cell spanning the column is copied once, not split; fine for plain tables
    const seen = new Set()
    for (let r = map.height - 1; r >= 0; r--) {
      const offset = map.map[r * map.width + rect.left]
      if (seen.has(offset)) continue
      seen.add(offset)
      const cell = table.nodeAt(offset)
      tr.insert(tableStart + offset + cell.nodeSize, cell.type.create(cell.attrs, cell.content))
    }
  }
  finish(editor, tr, cellPos)
}

/** Run a TipTap table command (addRowAfter, deleteColumn…) as if the cursor were in the cell. */
export function atCell(editor, cellPos, command) {
  editor
    .chain()
    .focus()
    .command(({ tr }) => {
      tr.setSelection(TextSelection.near(tr.doc.resolve(cellPos + 1)))
      return true
    })
    [command]()
    .run()
}
