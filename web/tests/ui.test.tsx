import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SensorBadge } from "@/components/ui/SensorBadge";
import { Stat } from "@/components/ui/Stat";

describe("ui kit", () => {
  it("renders a sensor badge", () => {
    render(<SensorBadge sensor="viirs" />);
    expect(screen.getByText("VIIRS")).toBeTruthy();
  });
  it("renders a stat", () => {
    render(<Stat label="Detections" value="1,204" />);
    expect(screen.getByText("1,204")).toBeTruthy();
  });
});
