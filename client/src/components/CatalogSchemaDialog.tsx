"use client";
import type { CatalogProduct } from "@/lib/api";
import { Button, Dialog } from "./ui";
export function CatalogSchemaDialog({ product, onClose }: { product: CatalogProduct; onClose: () => void }) {
  return <Dialog title="Product schema" id="catalog-schema-title" onClose={onClose}><p className="text-sm leading-6 text-slate-600">{product.name}</p><pre className="my-5 max-h-[55dvh] overflow-auto rounded-xl bg-slate-900 p-4 text-xs leading-6 text-slate-100">{JSON.stringify(product.json_ld_schema, null, 2)}</pre><div className="flex justify-end"><Button variant="secondary" onClick={onClose}>Close schema</Button></div></Dialog>;
}