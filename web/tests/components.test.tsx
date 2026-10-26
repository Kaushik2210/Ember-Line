import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Drawer } from "@/components/ui/Drawer";
import { Switch } from "@/components/ui/Field";
import { Section } from "@/components/ui/Section";
import { Segmented } from "@/components/ui/Segmented";
import { Stat } from "@/components/ui/Stat";

afterEach(cleanup);

const OPTIONS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
] as const;

describe("Segmented", () => {
  it("exposes radios and marks the selected one", () => {
    render(<Segmented label="Pick" value="b" options={[...OPTIONS]} onChange={() => undefined} />);
    expect(screen.getByRole("radiogroup", { name: "Pick" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Beta" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByRole("radio", { name: "Alpha" }).getAttribute("aria-checked")).toBe("false");
  });

  it("only the selected radio is in the tab order", () => {
    render(<Segmented label="Pick" value="b" options={[...OPTIONS]} onChange={() => undefined} />);
    expect(screen.getByRole("radio", { name: "Beta" }).getAttribute("tabindex")).toBe("0");
    expect(screen.getByRole("radio", { name: "Alpha" }).getAttribute("tabindex")).toBe("-1");
  });

  it("changes on click and moves with the arrow keys, wrapping around", () => {
    const onChange = vi.fn();
    render(<Segmented label="Pick" value="c" options={[...OPTIONS]} onChange={onChange} />);
    fireEvent.click(screen.getByRole("radio", { name: "Alpha" }));
    expect(onChange).toHaveBeenLastCalledWith("a");
    const group = screen.getByRole("radiogroup");
    fireEvent.keyDown(group, { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("a"); // c wraps to a
    fireEvent.keyDown(group, { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith("b");
  });
});

describe("Section", () => {
  it("starts collapsed and shows its summary, then opens on click", () => {
    render(
      <Section title="Quality policy" summary="MODIS ≥ 30">
        <p>Inner controls</p>
      </Section>,
    );
    const btn = screen.getByRole("button", { name: /Quality policy/ });
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Inner controls")).toBeNull();
    expect(screen.getByText("MODIS ≥ 30")).toBeTruthy();
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Inner controls")).toBeTruthy();
    expect(screen.queryByText("MODIS ≥ 30")).toBeNull(); // summary hides once open
  });

  it("can start open", () => {
    render(
      <Section title="Region" defaultOpen>
        <p>Presets</p>
      </Section>,
    );
    expect(screen.getByText("Presets")).toBeTruthy();
  });
});

describe("Switch", () => {
  it("is a labelled switch that reports the new value", () => {
    const onChange = vi.fn();
    render(<Switch label="Log scale" checked={false} onChange={onChange} />);
    const sw = screen.getByRole("switch", { name: "Log scale" });
    expect(sw.getAttribute("aria-checked")).toBe("false");
    fireEvent.click(sw);
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("does nothing when disabled", () => {
    const onChange = vi.fn();
    render(<Switch label="Locked" checked disabled onChange={onChange} />);
    fireEvent.click(screen.getByRole("switch", { name: "Locked" }));
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("Drawer", () => {
  function Harness({ onClose }: { onClose?: () => void }) {
    const [open, setOpen] = useState(false);
    return (
      <>
        <button onClick={() => setOpen(true)}>Open</button>
        <Drawer
          open={open}
          title="Details"
          onClose={() => {
            onClose?.();
            setOpen(false);
          }}
        >
          <p>Body</p>
        </Drawer>
      </>
    );
  }

  it("opens as a dialog, closes on Escape and gives focus back to the opener", () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);
    const opener = screen.getByRole("button", { name: "Open" });
    opener.focus();
    fireEvent.click(opener);
    expect(screen.getByRole("dialog", { name: "Details" })).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Close Details" }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(opener);
  });

  it("closes with its close button", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    fireEvent.click(screen.getByRole("button", { name: "Close Details" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("Stat", () => {
  it("shows label, value and hint", () => {
    render(<Stat label="Detections" value="8,358" hint="on 4 Nov 2013" />);
    expect(screen.getByText("Detections")).toBeTruthy();
    expect(screen.getByText("8,358")).toBeTruthy();
    expect(screen.getByText("on 4 Nov 2013")).toBeTruthy();
  });
});
