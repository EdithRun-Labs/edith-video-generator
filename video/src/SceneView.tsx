import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Diagram } from "./Diagram";
import { avatarInset, Presenter } from "./Presenter";
import type { Props, Scene } from "./types";

type Props2 = { scene: Scene; props: Props; fontFamily: string };

export const SceneView: React.FC<Props2> = ({ scene, props, fontFamily }) => {
  const frame = useCurrentFrame();
  const absolute = scene.startFrame + frame;
  const paragraphs = scene.paragraphs;
  const active =
    [...paragraphs].reverse().find((paragraph) => paragraph.startFrame <= absolute) ?? paragraphs[0];
  const sinceParagraph = absolute - active.startFrame;
  const opacity = interpolate(sinceParagraph, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const lift = interpolate(sinceParagraph, [0, 10], [16, 0], { extrapolateRight: "clamp" });

  const { palette } = props;
  const captionBand = props.captions.burned_in && props.captions.position === "bottom";
  const bottomPad = captionBand ? 210 : 72;
  const inset = avatarInset(props.avatar, props.canvas.height);
  const padding = `72px ${88 + inset.right}px ${bottomPad}px ${88 + inset.left}px`;
  const muted = palette.text_muted ?? palette.text;
  const rules = palette.hairline ?? palette.text;

  const local = absolute - active.startFrame;
  const shape =
    active.mouth.find((cue) => local >= cue.startFrame && local < cue.endFrame)?.shape ?? "X";
  const presenter = props.avatar.enabled ? (
    <Presenter
      avatar={props.avatar}
      shape={shape}
      palette={palette}
      frameHeight={props.canvas.height}
      captionBand={captionBand}
    />
  ) : null;

  const text = (
    <div style={{ opacity, transform: `translateY(${lift}px)` }}>
      <div
        style={{
          fontSize: 52,
          lineHeight: 1.28,
          color: palette.text,
          fontFamily,
          maxWidth: 980,
        }}
      >
        {active.text}
      </div>
      {active.pages.length ? (
        <div style={{ marginTop: 18, fontSize: 22, color: muted, letterSpacing: 1 }}>
          {active.pages.map((page) => `p. ${page}`).join(" · ")}
        </div>
      ) : null}
    </div>
  );

  const heading = (
    <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginBottom: 34 }}>
      <div style={{ width: 10, height: 30, background: palette.accent, borderRadius: 3 }} />
      <div style={{ fontSize: 30, letterSpacing: 1, color: muted, fontFamily }}>{scene.title}</div>
      <div style={{ flex: 1, height: 1, background: rules, opacity: 0.6 }} />
      <div style={{ fontSize: 20, color: muted, fontFamily }}>{scene.id}</div>
    </div>
  );

  const diagram = active.diagram ? (
    <div style={{ width: "100%", height: "100%", minHeight: 0 }}>
      <Diagram diagram={active.diagram} palette={palette} fontFamily={fontFamily} />
    </div>
  ) : null;

  const audio = paragraphs.map((paragraph) => (
    <Sequence
      key={`${scene.id}-${paragraph.startFrame}`}
      from={paragraph.startFrame - scene.startFrame}
      durationInFrames={paragraph.durationInFrames}
    >
      <Audio src={staticFile(paragraph.audio)} />
    </Sequence>
  ));

  const layer = (body: React.ReactNode) => (
    <>
      {body}
      {presenter}
    </>
  );

  if (props.layout === "split" && diagram) {
    return layer(
      <AbsoluteFill style={{ padding, flexDirection: "column" }}>
        {audio}
        {heading}
        <div style={{ display: "flex", gap: 56, flex: 1, minHeight: 0 }}>
          <div style={{ flex: 0.9, display: "flex", alignItems: "center" }}>{text}</div>
          <div style={{ flex: 1.1, minHeight: 0 }}>{diagram}</div>
        </div>
      </AbsoluteFill>,
    );
  }

  if (props.layout === "fullbleed" && diagram) {
    return layer(
      <AbsoluteFill style={{ padding, flexDirection: "column" }}>
        {audio}
        {heading}
        <div style={{ flex: 1, minHeight: 0 }}>{diagram}</div>
        <div
          style={{
            marginTop: 36,
            padding: "26px 30px",
            borderRadius: 16,
            background: palette.surface ?? palette.background,
            border: `1px solid ${rules}`,
            opacity,
          }}
        >
          {text}
        </div>
      </AbsoluteFill>,
    );
  }

  return layer(
    <AbsoluteFill style={{ padding, flexDirection: "column" }}>
      {audio}
      {heading}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 40, justifyContent: "center", minHeight: 0 }}>
        <div style={{ display: "flex", justifyContent: "center" }}>{text}</div>
        {diagram ? <div style={{ flex: 1, minHeight: 0 }}>{diagram}</div> : null}
      </div>
    </AbsoluteFill>,
  );
};
