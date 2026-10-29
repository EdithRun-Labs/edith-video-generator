import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import type { Diagram as DiagramData, Palette } from "./types";

type Props = {
  diagram: DiagramData;
  palette: Palette;
  fontFamily: string;
};

const label = (p: Palette) => p.text_muted ?? p.text;
const line = (p: Palette) => p.hairline ?? p.text;

export const Diagram: React.FC<Props> = ({ diagram, palette, fontFamily }) => {
  const data = diagram.data ?? {};
  const surface = palette.surface ?? palette.background;
  const frame = useCurrentFrame();
  const rise = interpolate(frame, [0, 14], [18, 0], { extrapolateRight: "clamp" });
  const fade = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        background: surface,
        border: `1px solid ${line(palette)}`,
        borderRadius: 18,
        padding: 36,
        display: "flex",
        flexDirection: "column",
        gap: 22,
        transform: `translateY(${rise}px)`,
        opacity: fade,
        fontFamily,
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      {diagram.title ? (
        <div
          style={{
            fontSize: 26,
            letterSpacing: 1.5,
            textTransform: "uppercase",
            color: label(palette),
          }}
        >
          {diagram.title}
        </div>
      ) : null}
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        {body(diagram.type, data, palette)}
      </div>
    </div>
  );
};

const empty = (palette: Palette) => (
  <div style={{ color: label(palette), fontSize: 28 }}>no data for this diagram yet</div>
);

const body = (type: DiagramData["type"], data: any, palette: Palette) => {
  switch (type) {
    case "bar": {
      const items: { label: string; value: number }[] = data.items ?? [];
      if (!items.length) return empty(palette);
      const max = Math.max(...items.map((i) => Math.abs(i.value) || 0), 1);
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 20, justifyContent: "center", flex: 1 }}>
          {items.map((item) => (
            <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ width: 260, fontSize: 26, color: palette.text, textAlign: "right" }}>{item.label}</div>
              <div style={{ flex: 1, height: 34, background: palette.background, borderRadius: 8, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.max(4, (Math.abs(item.value) / max) * 100)}%`,
                    height: "100%",
                    background: palette.accent,
                    borderRadius: 8,
                  }}
                />
              </div>
              <div style={{ width: 90, fontSize: 26, color: label(palette) }}>{item.value}</div>
            </div>
          ))}
        </div>
      );
    }
    case "flow": {
      const steps: string[] = data.steps ?? [];
      if (!steps.length) return empty(palette);
      return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, flexWrap: "wrap", flex: 1 }}>
          {steps.map((step, index) => (
            <React.Fragment key={step}>
              <div
                style={{
                  padding: "22px 26px",
                  borderRadius: 14,
                  background: index === steps.length - 1 ? palette.accent : palette.background,
                  color: index === steps.length - 1 ? palette.on_accent ?? "#fff" : palette.text,
                  border: `1px solid ${index === steps.length - 1 ? palette.accent : line(palette)}`,
                  fontSize: 26,
                  maxWidth: 340,
                }}
              >
                {step}
              </div>
              {index < steps.length - 1 ? (
                <div style={{ fontSize: 34, color: label(palette) }}>→</div>
              ) : null}
            </React.Fragment>
          ))}
        </div>
      );
    }
    case "timeline": {
      const marks: { at: string; label: string }[] = data.marks ?? [];
      if (!marks.length) return empty(palette);
      return (
        <div style={{ display: "flex", alignItems: "center", flex: 1, position: "relative" }}>
          <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: line(palette) }} />
          <div style={{ display: "flex", width: "100%", justifyContent: "space-between" }}>
            {marks.map((mark, index) => (
              <div key={`${mark.at}-${index}`} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, flex: 1 }}>
                <div style={{ fontSize: 26, color: palette.accent, fontWeight: 600 }}>{mark.at}</div>
                <div style={{ width: 16, height: 16, borderRadius: 8, background: palette.accent }} />
                <div style={{ fontSize: 24, color: palette.text, textAlign: "center", maxWidth: 260 }}>{mark.label}</div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    case "list": {
      const items: string[] = data.items ?? [];
      if (!items.length) return empty(palette);
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, justifyContent: "center", flex: 1 }}>
          {items.map((item, index) => (
            <div key={index} style={{ display: "flex", gap: 16, fontSize: 28, color: palette.text }}>
              <div style={{ color: palette.accent, fontWeight: 700 }}>{index + 1}</div>
              <div>{item}</div>
            </div>
          ))}
        </div>
      );
    }
    case "table": {
      const columns: string[] = data.columns ?? [];
      const rows: (string | number)[][] = data.rows ?? [];
      if (!columns.length || !rows.length) return empty(palette);
      return (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 24, color: palette.text }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  style={{
                    textAlign: "left",
                    padding: "12px 14px",
                    borderBottom: `2px solid ${palette.accent}`,
                    color: label(palette),
                    textTransform: "uppercase",
                    fontSize: 20,
                    letterSpacing: 1,
                  }}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} style={{ padding: "12px 14px", borderBottom: `1px solid ${line(palette)}` }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    case "comparison": {
      const left = data.left ?? {};
      const right = data.right ?? {};
      if (!left.title && !right.title) return empty(palette);
      const side = (block: any) => (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 26, color: palette.accent, fontWeight: 600 }}>{block.title}</div>
          {(block.items ?? []).map((item: string, index: number) => (
            <div key={index} style={{ fontSize: 24, color: palette.text }}>
              {item}
            </div>
          ))}
        </div>
      );
      return <div style={{ display: "flex", gap: 40, flex: 1, alignItems: "center" }}>{side(left)}{side(right)}</div>;
    }
    case "cycle": {
      const steps: string[] = data.steps ?? [];
      if (!steps.length) return empty(palette);
      const radius = 170;
      return (
        <div style={{ position: "relative", flex: 1 }}>
          {steps.map((step, index) => {
            const angle = (index / steps.length) * Math.PI * 2 - Math.PI / 2;
            return (
              <div
                key={step}
                style={{
                  position: "absolute",
                  left: `calc(50% + ${Math.cos(angle) * radius}px)`,
                  top: `calc(50% + ${Math.sin(angle) * radius}px)`,
                  transform: "translate(-50%, -50%)",
                  padding: "18px 22px",
                  borderRadius: 999,
                  border: `1px solid ${palette.accent}`,
                  color: palette.text,
                  fontSize: 24,
                  maxWidth: 240,
                  textAlign: "center",
                  background: palette.background,
                }}
              >
                {step}
              </div>
            );
          })}
        </div>
      );
    }
    default:
      return empty(palette);
  }
};
