import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { Props } from "./types";

export const TitleCard: React.FC<{ props: Props; fontFamily: string }> = ({ props, fontFamily }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  const { palette, meta } = props;

  return (
    <AbsoluteFill style={{ padding: "120px 140px", justifyContent: "center", fontFamily }}>
      <div style={{ opacity, maxWidth: 1400 }}>
        {meta.branding ? (
          <div
            style={{
              fontSize: 24,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: palette.accent,
              marginBottom: 30,
            }}
          >
            {meta.branding}
          </div>
        ) : null}
        <div style={{ fontSize: 96, lineHeight: 1.12, color: palette.text }}>{meta.title}</div>
        {meta.subtitle ? (
          <div style={{ marginTop: 28, fontSize: 40, color: palette.text_muted ?? palette.text }}>
            {meta.subtitle}
          </div>
        ) : null}
        <div
          style={{
            marginTop: 46,
            width: 180,
            height: 6,
            borderRadius: 3,
            background: palette.accent,
          }}
        />
        {meta.author || meta.date ? (
          <div style={{ marginTop: 26, fontSize: 24, color: palette.text_muted ?? palette.text }}>
            {[meta.author, meta.date].filter(Boolean).join(" · ")}
          </div>
        ) : null}
      </div>
      {props.disclosure ? (
        <div
          style={{
            position: "absolute",
            left: 140,
            bottom: 64,
            fontSize: 20,
            color: palette.text_muted ?? palette.text,
            opacity: 0.9,
          }}
        >
          {props.disclosure}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
