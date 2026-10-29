import React from "react";
import { Composition } from "remotion";
import { Video } from "./Video";
import type { Props } from "./types";

const fallback: Props = {
  meta: { title: "Preview", subtitle: "Run edith build to fill this in" },
  canvas: { width: 1920, height: 1080, fps: 30 },
  durationInFrames: 90,
  layout: "screen",
  palette: { background: "#f7f4ee", text: "#1d2430", accent: "#2f6b4f" },
  fonts: { body: { family: "Inter", src: null }, heading: null },
  captions: { position: "bottom", burned_in: true },
  cards: { titleFrames: 75, creditsFrames: 0 },
  disclosure: null,
  avatar: {
    enabled: false,
    name: "Presenter",
    preset: "neutral",
    position: "corner",
    size: 0.34,
    palette: null,
    images: null,
  },
  scenes: [],
};

export const Root: React.FC = () => (
  <Composition
    id="Video"
    component={Video}
    defaultProps={fallback}
    durationInFrames={fallback.durationInFrames}
    fps={fallback.canvas.fps}
    width={fallback.canvas.width}
    height={fallback.canvas.height}
    calculateMetadata={({ props }) => {
      const p = props as Props;
      return {
        durationInFrames: Math.max(1, p.durationInFrames || 1),
        fps: p.canvas?.fps || 30,
        width: p.canvas?.width || 1920,
        height: p.canvas?.height || 1080,
      };
    }}
  />
);
