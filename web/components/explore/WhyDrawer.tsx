"use client";

import { Drawer } from "@/components/ui/Drawer";

export function WhyDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Drawer open={open} title="Why the sensors differ" onClose={onClose}>
      <div className="p-4 text-sm text-muted">Explanations arrive in a later step.</div>
    </Drawer>
  );
}
