import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Captions } from "./Captions";
import { Credits } from "./Credits";
import { avatarInset } from "./Presenter";
import { SceneView } from "./SceneView";
import { TitleCard } from "./TitleCard";
import type { Props } from "./types";

const fontFaces = (props: Props): string => {
  const fonts = [props.fonts.body, props.fonts.heading].filter((f) => f && f.src);
  return fonts
    .map(
      (f) =>
        `@font-face { font-family: '${f!.family}'; src: url('${staticFile(f!.src!)}'); font-display: block; }`,
    )
    .join("\n");
};

const stack = (family?: string | null): string =>
  family
    ? `${family}, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif`
    : "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif";

export const Video: React.FC<Props> = (props) => {
  const body = stack(props.fonts.body?.family);
  const heading = stack(props.fonts.heading?.family ?? props.fonts.body?.family);
  const cues = props.scenes.flatMap((scene) => scene.captions);
  const inset = avatarInset(props.avatar, props.canvas.height);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: props.palette.background,
        color: props.palette.text,
        fontFamily: body,
      }}
    >
      <style>{fontFaces(props)}</style>

      <Sequence from={0} durationInFrames={props.cards.titleFrames}>
        <TitleCard props={props} fontFamily={heading} />
      </Sequence>

      {props.scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={scene.startFrame}
          durationInFrames={scene.durationInFrames}
        >
          <SceneView scene={scene} props={props} fontFamily={heading} />
        </Sequence>
      ))}

      {props.cards.creditsFrames > 0 ? (
        <Sequence
          from={props.durationInFrames - props.cards.creditsFrames}
          durationInFrames={props.cards.creditsFrames}
        >
          <Credits props={props} fontFamily={heading} />
        </Sequence>
      ) : null}

      {props.captions.burned_in ? (
        <Captions cues={cues} palette={props.palette} position={props.captions.position} inset={inset} />
      ) : null}
    </AbsoluteFill>
  );
};
