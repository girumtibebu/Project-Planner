<script setup lang="ts">
import { onMounted, ref } from "vue";
import Btn from "../Btn.vue";
import Icons from "../Icons.vue";
import { frappeList } from "../../composables/useFrappe";

const props = defineProps<{ row: any }>();
const emit  = defineEmits<{ (e: "save", row: any): void; (e: "close"): void }>();

const form    = ref({ status: "Reserved", quantity: 1, ...props.row });
const bundles = ref<any[]>([]);
const bundleSearch = ref(form.value.equipment_bundle || "");
const showBundleDrop = ref(false);
const selectedBundle = ref<any>(null);
const uoms = ref<any[]>([]);

const STATUSES = ["Reserved", "In Transit", "Delivered", "Missing"];

onMounted(async () => {
  bundles.value = await frappeList("Equipment Bundle", {
    fields: ["name", "bundle_name", "description", "items"],
    limit: 200,
  });
  uoms.value = await frappeList("UOM", { fields: ["name"], limit: 500 });
  if (form.value.equipment_bundle) {
    selectedBundle.value = bundles.value.find((b) => b.bundle_name === form.value.equipment_bundle);
  }
});

const filteredBundles = ref<any[]>([]);
function searchBundle(q: string) {
  filteredBundles.value = !q
    ? bundles.value
    : bundles.value.filter((b) =>
        (b.bundle_name + " " + (b.description || "")).toLowerCase().includes(q.toLowerCase())
      );
}
function pickBundle(b: any) {
  form.value.equipment_bundle = b.bundle_name;
  bundleSearch.value = b.bundle_name;
  selectedBundle.value = b;
  showBundleDrop.value = false;
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="dialog">
        <div class="dialog__head">
          <span>{{ form.equipment_bundle ? "Edit Equipment" : "Add Equipment" }}</span>
          <button @click="emit('close')"><Icons name="close" :size="14" /></button>
        </div>
        <div class="dialog__body">
          <!-- Bundle picker -->
          <div class="field" style="position:relative;">
            <label>Equipment Bundle *</label>
            <input
              v-model="bundleSearch"
              class="ep-input"
              placeholder="Search bundle…"
              @focus="showBundleDrop=true;searchBundle(bundleSearch)"
              @input="searchBundle(bundleSearch)"
              @blur="setTimeout(()=>showBundleDrop=false,200)"
            />
            <div v-if="showBundleDrop" class="dropdown">
              <button
                v-for="b in filteredBundles"
                :key="b.name"
                class="dropdown-item"
                @mousedown="pickBundle(b)"
              >
                <span class="item-name">{{ b.bundle_name }}</span>
                <span class="item-desc">{{ b.description }}</span>
              </button>
            </div>
          </div>

          <!-- Bundle item checklist preview -->
          <div v-if="selectedBundle?.items?.length" class="bundle-items">
            <div class="bundle-items__title">Items in bundle (informational)</div>
            <div class="bundle-items__list">
              <div v-for="it in selectedBundle.items" :key="it.name" class="bundle-items__row">
                <Icons name="check" :size="12" style="color:var(--ok);flex-shrink:0;" />
                {{ it.item_name }}
                <span class="mono" style="color:var(--text-3);font-size:11px;">{{ it.default_quantity }} {{ it.uom }}</span>
              </div>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Quantity</label>
              <input v-model.number="form.quantity" type="number" min="0" step="0.5" class="ep-input" />
            </div>
            <div class="field">
              <label>UOM</label>
              <select v-model="form.uom" class="ep-input">
                <option value="">— Select —</option>
                <option v-for="u in uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
              </select>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Status</label>
              <select v-model="form.status" class="ep-input">
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
            <div class="field">
              <label>Vendor</label>
              <input v-model="form.vendor" class="ep-input" placeholder="Supplier name" />
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Cost</label>
              <input v-model.number="form.cost" type="number" min="0" class="ep-input" placeholder="0.00" />
            </div>
            <div class="field">
              <label>Remark</label>
              <input v-model="form.remark" class="ep-input" />
            </div>
          </div>
        </div>
        <div class="dialog__foot">
          <Btn @click="emit('close')">Cancel</Btn>
          <Btn kind="primary" @click="emit('save', form)">Save</Btn>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay { position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:100; }
.dialog { background:var(--panel);border-radius:12px;width:540px;max-height:88vh;overflow-y:auto;border:1px solid var(--border-2);box-shadow:0 24px 64px rgba(0,0,0,.22);display:flex;flex-direction:column; }
.dialog__head { display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600; }
.dialog__head button { background:none;border:none;cursor:pointer;color:var(--text-3); }
.dialog__body { padding:18px;display:flex;flex-direction:column;gap:12px; }
.dialog__foot { display:flex;justify-content:flex-end;gap:8px;padding:12px 18px;border-top:1px solid var(--border); }
.field { display:flex;flex-direction:column;gap:4px; }
.field label { font-size:11.5px;color:var(--text-3);font-weight:500; }
.field-row { display:grid;grid-template-columns:1fr 1fr;gap:12px; }
.ep-input { padding:7px 9px;border:1px solid var(--border-2);border-radius:6px;font-size:12.5px;font-family:inherit;background:var(--panel-2);color:var(--text);width:100%; }
.ep-input:focus { outline:none;border-color:var(--accent); }
.dropdown { position:absolute;top:100%;left:0;right:0;background:var(--panel);border:1px solid var(--border-2);border-radius:7px;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:10;max-height:200px;overflow-y:auto;margin-top:2px; }
.dropdown-item { display:flex;flex-direction:column;width:100%;padding:8px 12px;background:none;border:none;cursor:pointer;font-family:inherit;font-size:12.5px;text-align:left; }
.dropdown-item:hover { background:var(--row-hover); }
.item-name { font-weight:500; }
.item-desc { font-size:11px;color:var(--text-3); }
.bundle-items { background:var(--bg-2);border:1px solid var(--border);border-radius:6px;padding:10px 12px; }
.bundle-items__title { font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3);margin-bottom:7px; }
.bundle-items__list { display:flex;flex-direction:column;gap:4px; }
.bundle-items__row { display:flex;align-items:center;gap:7px;font-size:12px; }
</style>
