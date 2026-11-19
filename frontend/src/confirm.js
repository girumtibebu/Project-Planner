/** "Are you sure?" before locking, unlocking, removing or deleting. One dialog, mounted in ProjectShell. */

import { reactive } from 'vue'

export const confirmState = reactive({ open: false, title: '', message: '', action: 'Confirm', danger: false, resolve: null })

/** Resolves true when the user confirms, false when they cancel or close the dialog. */
export function confirmAction({ title, message = '', action = 'Confirm', danger = false }) {
  confirmState.resolve?.(false) // a dialog still open counts as cancelled
  return new Promise((resolve) => Object.assign(confirmState, { open: true, title, message, action, danger, resolve }))
}

export function settle(ok) {
  const resolve = confirmState.resolve
  Object.assign(confirmState, { open: false, resolve: null })
  resolve?.(ok)
}
