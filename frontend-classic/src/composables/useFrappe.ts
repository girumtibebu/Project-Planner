/**
 * Thin wrappers around Frappe's JS API (window.frappe).
 * In dev the SPA proxies /api to the bench — frappe-ui's createResource
 * is not bundled here to keep deps minimal; instead we use raw fetch
 * which matches Frappe's REST API.
 */
import { ref, watch, type Ref } from "vue";

let csrfFetchPromise: Promise<void> | null = null;

/* ── helpers ─────────────────────────────────────────────────────────────── */

/** Token injected by `<!-- csrf_token -->` on `/planner` or by ensureCsrfToken(). */
function csrfToken(): string {
  const g = typeof globalThis !== "undefined" ? (globalThis as any) : null;
  const fromWin = g?.frappe?.csrf_token;
  if (typeof fromWin === "string" && fromWin.length > 0 && fromWin !== "None") {
    return fromWin;
  }
  return (document.cookie.match(/csrf_token=([^;]+)/) || [])[1]?.trim() || "";
}

async function ensureCsrfToken(): Promise<void> {
  if (csrfToken()) return;
  if (!csrfFetchPromise) {
    csrfFetchPromise = (async () => {
      const res = await fetch(
        "/api/method/event_planner.api.get_planner_csrf_token",
        { credentials: "include", method: "GET" }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.exc_type) {
        const msg = data._server_messages || data.exception || data.exc_type || res.statusText;
        throw new Error(`CSRF bootstrap failed (${res.status}): ${JSON.stringify(msg)}`);
      }
      const raw = data.message;
      const token = typeof raw === "string" ? raw : "";
      const g = globalThis as any;
      g.frappe = g.frappe || {};
      g.frappe.csrf_token = token;
      if (!token) throw new Error("CSRF bootstrap returned an empty token.");
    })().finally(() => {
      csrfFetchPromise = null;
    });
  }
  await csrfFetchPromise;
}

/** Must be called before POST / PUT — raises if token cannot be obtained. */
async function requireCsrfToken(): Promise<string> {
  await ensureCsrfToken();
  const t = csrfToken();
  if (!t) {
    throw new Error(
      "Missing CSRF token. Open the planner from this site while logged in, then hard-refresh."
    );
  }
  return t;
}

async function frappeGet(doctype: string, name: string): Promise<any> {
  const res = await fetch(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  return data.data;
}

async function frappeList(
  doctype: string,
  opts: Record<string, any> = {}
): Promise<any[]> {
  const params = new URLSearchParams();
  if (opts.fields) params.set("fields", JSON.stringify(opts.fields));
  if (opts.filters) params.set("filters", JSON.stringify(opts.filters));
  if (opts.limit) params.set("limit", String(opts.limit || 500));
  if (opts.order_by) params.set("order_by", opts.order_by);
  const res = await fetch(
    `/api/resource/${encodeURIComponent(doctype)}?${params}`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  return data.data || [];
}

async function frappeCall(method: string, args: Record<string, any>): Promise<any> {
  const token = await requireCsrfToken();
  const res = await fetch("/api/method/" + method, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": token,
    },
    /* Server pops csrf_token from form_dict during CSRF check — not passed to Python. */
    body: JSON.stringify({ ...args, csrf_token: token }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  return data.message;
}

async function frappeSave(doctype: string, name: string | null, values: Record<string, any>): Promise<any> {
  const token = await requireCsrfToken();
  const payload = { doctype, ...values };
  const isNew = !name;
  const url = isNew
    ? `/api/resource/${encodeURIComponent(doctype)}`
    : `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name!)}`;
  const res = await fetch(url, {
    method: isNew ? "POST" : "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": token,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  return data.data;
}

/* ── composables ─────────────────────────────────────────────────────────── */

export function useFrappeDoc(doctype: string, name: Ref<string>) {
  const doc = ref<any>(null);
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function load(n: string) {
    if (!n) return;
    loading.value = true;
    error.value = null;
    try {
      doc.value = await frappeGet(doctype, n);
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  watch(name, load, { immediate: true });

  async function reload() {
    await load(name.value);
  }

  return { doc, loading, error, reload };
}

export function useFrappeList(
  doctype: string,
  opts: Ref<Record<string, any>>
) {
  const rows = ref<any[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      rows.value = await frappeList(doctype, opts.value);
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  watch(opts, load, { immediate: true, deep: true });

  return { rows, loading, error, reload: load };
}

export { frappeGet, frappeList, frappeCall, frappeSave, ensureCsrfToken, requireCsrfToken };
