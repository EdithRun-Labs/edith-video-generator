import React from "react";
import { AbsoluteFill } from "remotion";
import type { Props } from "./types";

export const Credits: React.FC<{ props: Props; fontFamily: string }> = ({ props, fontFamily }) => {
  const { palette, meta } = props;
  return (
    <AbsoluteFill
      style={{
        padding: "120px 140px",
        justifyContent: "center",
        alignItems: "flex-start",
        fontFamily,
      }}
    >
      <div style={{ fontSize: 34, color: palette.text }}>{meta.author}</div>
      <div style={{ marginTop: 12, fontSize: 26, color: palette.text_muted ?? palette.text }}>
        {meta.date}
      </div>
      <div
        style={{
          marginTop: 40,
          width: 120,
          height: 4,
          borderRadius: 2,
          background: palette.accent,
        }}
      />
      {props.disclosure ? (
        <div style={{ marginTop: 28, fontSize: 20, color: palette.text_muted ?? palette.text }}>
          {props.disclosure}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
