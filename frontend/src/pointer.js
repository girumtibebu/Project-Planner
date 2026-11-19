/** Mouse/pen drag helper: calls onMove(dx, dy) while dragging and onEnd(dx, dy, moved) on release. */
export function startDrag(event, { onMove, onEnd, threshold = 3 }) {
  if (event.button !== undefined && event.button !== 0) return
  const x0 = event.clientX
  const y0 = event.clientY
  let moved = false
  const move = (e) => {
    const dx = e.clientX - x0
    const dy = e.clientY - y0
    if (!moved && Math.abs(dx) < threshold && Math.abs(dy) < threshold) return
    moved = true
    e.preventDefault()
    onMove?.(dx, dy, e)
  }
  const up = (e) => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    onEnd?.(e.clientX - x0, e.clientY - y0, moved, e)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
