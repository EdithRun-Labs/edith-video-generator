import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { Cue, Palette } from "./types";

export const Captions: React.FC<{
  cues: Cue[];
  palette: Palette;
  position: "bottom" | "top";
}> = ({ cues, palette, position }) => {
  const frame = useCurrentFrame();
  const cue = cues.find((c) => frame >= c.startFrame && frame < c.endFrame);
  if (!cue) return null;

  const opacity = interpolate(
    frame,
    [cue.startFrame, cue.startFrame + 3, cue.endFrame - 3, cue.endFrame],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: position === "bottom" ? "flex-end" : "flex-start",
        alignItems: "center",
        padding: position === "bottom" ? "0 96px 64px" : "120px 96px 0",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity: opacity * 0.92,
          maxWidth: 1400,
          textAlign: "center",
          fontSize: 36,
          lineHeight: 1.32,
          color: palette.background,
          background: palette.text,
          borderRadius: 12,
          padding: "16px 26px",
          whiteSpace: "pre-line",
        }}
      >
        {cue.text}
      </div>
    </AbsoluteFill>
  );
};
