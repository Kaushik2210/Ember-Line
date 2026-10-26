"use client";

import { create } from "zustand";

export type Phase = "idle" | "running" | "done" | "error";

interface ExploreState {
  // analysis run (progress is streamed from the server)
  phase: Phase;
  stages: string[];
  error: string | null;
  setRunning: () => void;
  addStage: (s: string) => void;
  setDone: () => void;
  setError: (msg: string) => void;
  reset: () => void;

  // a shape uploaded by the user: too large for the URL, so it is not shareable
  geojson: unknown | null;
  geojsonName: string | null;
  setGeojson: (g: unknown | null, name?: string | null) => void;

  // box drawing on the map
  drawing: boolean;
  setDrawing: (v: boolean) => void;

  // map compare slider (0..1 from the left) and time scrubber playback
  slider: number;
  setSlider: (v: number) => void;
  playing: boolean;
  setPlaying: (v: boolean) => void;

  whyOpen: boolean;
  setWhyOpen: (v: boolean) => void;
}

export const useExploreStore = create<ExploreState>((set) => ({
  phase: "idle",
  stages: [],
  error: null,
  setRunning: () => set({ phase: "running", stages: [], error: null }),
  addStage: (s) => set((st) => (st.stages[st.stages.length - 1] === s ? st : { stages: [...st.stages, s] })),
  setDone: () => set({ phase: "done" }),
  setError: (error) => set({ phase: "error", error }),
  reset: () => set({ phase: "idle", stages: [], error: null }),

  geojson: null,
  geojsonName: null,
  setGeojson: (geojson, name = null) => set({ geojson, geojsonName: name }),

  drawing: false,
  setDrawing: (drawing) => set({ drawing }),

  slider: 0.5,
  setSlider: (slider) => set({ slider: Math.min(1, Math.max(0, slider)) }),
  playing: false,
  setPlaying: (playing) => set({ playing }),

  whyOpen: false,
  setWhyOpen: (whyOpen) => set({ whyOpen }),
}));
