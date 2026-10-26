/** Save a data URL or Blob as a file in the browser. */
export function saveFile(href: string, filename: string): void {
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** A safe, readable file name: lowercase, dashes, no path characters. */
export function fileName(...parts: (string | number | null | undefined)[]): string {
  return parts
    .filter((p) => p !== null && p !== undefined && p !== "")
    .join("-")
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

/** Draw a canvas onto an opaque background so a PNG of a transparent chart is readable anywhere. */
export function canvasToPng(src: HTMLCanvasElement, background: string, credit?: string): string {
  const pad = credit ? 22 : 0;
  const out = document.createElement("canvas");
  out.width = src.width;
  out.height = src.height + pad;
  const ctx = out.getContext("2d");
  if (!ctx) return src.toDataURL("image/png");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(src, 0, 0);
  if (credit) {
    ctx.fillStyle = "#9aa7b5";
    ctx.font = "11px sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillText(credit, 8, src.height + pad / 2);
  }
  return out.toDataURL("image/png");
}

export const CREDIT = "EMBERLINE · data: NASA FIRMS (MODIS, VIIRS) · imagery: NASA GIBS";
