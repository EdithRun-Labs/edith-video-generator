import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import type { Avatar, Palette } from "./types";

const ASPECT = 200 / 240;
const GUTTER = 40;
const EDGE = 88;
const CAPTION_BAND = 210;

export const avatarInset = (avatar: Avatar, height: number) => {
  const width = avatar.enabled ? Math.round(height * avatar.size * ASPECT) + GUTTER : 0;
  return {
    width,
    left: avatar.enabled && avatar.position === "full" ? width : 0,
    right: avatar.enabled && avatar.position !== "full" ? width : 0,
  };
};

type Mouth = { open: number; round: number; teeth: boolean; tongue: boolean };

const MOUTHS: Record<string, Mouth> = {
  A: { open: 4, round: 0.7, teeth: false, tongue: false },
  B: { open: 7, round: 0.7, teeth: true, tongue: false },
  C: { open: 14, round: 0.75, teeth: false, tongue: true },
  D: { open: 23, round: 0.9, teeth: false, tongue: true },
  E: { open: 16, round: 1.15, teeth: false, tongue: true },
  F: { open: 9, round: 1.2, teeth: true, tongue: false },
  G: { open: 13, round: 0.8, teeth: true, tongue: false },
  H: { open: 27, round: 0.55, teeth: false, tongue: true },
  X: { open: 3, round: 0.35, teeth: false, tongue: false },
};

const mouth = (shape: string): Mouth => MOUTHS[shape.toUpperCase()] ?? MOUTHS.X;

const DEFAULTS = {
  skin: "#e8b48f",
  skin_shadow: "#dda57e",
  hair: "#2f2a26",
  lip: "#b6736b",
  mouth_in: "#5a2a2c",
  teeth: "#f7f2ea",
  tongue: "#c9646a",
  eye: "#2c2c33",
  sclera: "#fbfaf6",
};

export const Presenter: React.FC<{
  avatar: Avatar;
  shape: string;
  palette: Palette;
  frameHeight: number;
  captionBand: boolean;
}> = ({ avatar, shape, palette, frameHeight, captionBand }) => {
  const frame = useCurrentFrame();
  const height = Math.round(frameHeight * avatar.size);
  const width = Math.round(height * ASPECT);
  const bottom = captionBand ? CAPTION_BAND : EDGE;

  const placement =
    avatar.position === "full"
      ? { justifyContent: "flex-end", alignItems: "flex-start", padding: `0 0 ${bottom}px ${EDGE}px` }
      : avatar.position === "side"
        ? { justifyContent: "center", alignItems: "flex-end", padding: `0 ${EDGE}px 0 0` }
        : { justifyContent: "flex-end", alignItems: "flex-end", padding: `0 ${EDGE}px ${bottom}px 0` };

  const layers = avatar.images;
  const image = layers ? layers[shape.toUpperCase()] ?? layers.X ?? null : null;

  return (
    <AbsoluteFill style={{ ...placement, pointerEvents: "none" }}>
      {image ? (
        <Img src={staticFile(image)} style={{ width, height }} />
      ) : (
        <VectorBust avatar={avatar} shape={shape} palette={palette} width={width} height={height} frame={frame} />
      )}
    </AbsoluteFill>
  );
};

const VectorBust: React.FC<{
  avatar: Avatar;
  shape: string;
  palette: Palette;
  width: number;
  height: number;
  frame: number;
}> = ({ avatar, shape, palette, width, height, frame }) => {
  const colors = {
    ...DEFAULTS,
    clothing: avatar.preset === "office" ? "#2e3a52" : palette.accent,
    ...(avatar.palette ?? {}),
  };
  const { clothing } = colors;

  const open = mouth(shape);
  const blink = frame % 111 < 3;
  const sway = Math.sin(frame / 34) * 1.6;
  const breathe = Math.sin(frame / 47) * 1.2;

  const eye = (cx: number) => (
    <g>
      <ellipse cx={cx} cy={104} rx={10} ry={blink ? 1.6 : 7} fill={colors.sclera} />
      {blink ? null : <circle cx={cx} cy={105} r={4.4} fill={colors.eye} />}
      {blink ? null : <circle cx={cx + 1.4} cy={103.4} r={1.3} fill={colors.sclera} />}
    </g>
  );

  const mouthX = 100;
  const mouthY = 128;
  const rx = 19 * open.round;
  const ry = Math.max(open.open / 2, 2);

  return (
    <svg width={width} height={height} viewBox="0 0 200 240" style={{ display: "block" }}>
      <defs>
        <clipPath id="mouth-clip">
          <ellipse cx={mouthX} cy={mouthY} rx={rx} ry={ry} />
        </clipPath>
        <clipPath id="torso-clip">
          <path d="M22 240 Q22 166 100 166 Q178 166 178 240 Z" />
        </clipPath>
      </defs>

      <g transform={`translate(0 ${breathe})`}>
        <path d="M22 240 Q22 166 100 166 Q178 166 178 240 Z" fill={clothing} />

        {avatar.preset === "workshop" ? (
          <g clipPath="url(#torso-clip)">
            <rect x={22} y={214} width={156} height={9} fill="#f4f1e8" opacity={0.95} />
            <rect x={22} y={196} width={156} height={4} fill="#f4f1e8" opacity={0.7} />
          </g>
        ) : null}

        {avatar.preset === "office" ? (
          <g>
            <path d="M78 170 L100 212 L122 170 Z" fill="#f4f5f8" />
            <path d="M78 170 L100 212 L88 240 L62 240 Z" fill="#26324a" />
            <path d="M122 170 L100 212 L112 240 L138 240 Z" fill="#26324a" />
          </g>
        ) : null}

        <rect x={80} y={146} width={40} height={34} rx={10} fill={colors.skin_shadow} />

        <g transform={`translate(${sway} 0)`}>
          <ellipse cx={54} cy={108} rx={8} ry={14} fill={colors.skin_shadow} />
          <ellipse cx={146} cy={108} rx={8} ry={14} fill={colors.skin_shadow} />
          <ellipse cx={100} cy={100} rx={46} ry={52} fill={colors.skin} />
          <path d="M54 92 Q54 34 100 34 Q146 34 146 92 Q138 60 100 58 Q62 60 54 92 Z" fill={colors.hair} />
          <path d="M64 85 Q77 82 90 85" stroke={colors.hair} strokeWidth={4} fill="none" strokeLinecap="round" />
          <path d="M110 85 Q123 82 136 85" stroke={colors.hair} strokeWidth={4} fill="none" strokeLinecap="round" />
          {eye(82)}
          {eye(118)}
          <ellipse cx={100} cy={114} rx={4} ry={3} fill={colors.skin_shadow} opacity={0.5} />
          {ry <= 2.5 ? (
            <rect x={mouthX - rx * 0.8} y={mouthY - 1.6} width={rx * 1.6} height={3.2} rx={1.6} fill={colors.lip} />
          ) : (
            <>
              <ellipse cx={mouthX} cy={mouthY} rx={rx + 2} ry={ry + 3} fill={colors.lip} />
              <ellipse cx={mouthX} cy={mouthY} rx={rx} ry={ry} fill={colors.mouth_in} />
            </>
          )}
          {open.teeth ? (
            <g clipPath="url(#mouth-clip)">
              <rect x={mouthX - rx} y={mouthY - ry} width={rx * 2} height={Math.max(ry - 1, 1.5)} fill={colors.teeth} />
            </g>
          ) : null}
          {open.tongue ? (
            <g clipPath="url(#mouth-clip)">
              <ellipse cx={mouthX} cy={mouthY + ry * 0.75} rx={rx * 0.7} ry={ry * 0.55} fill={colors.tongue} />
            </g>
          ) : null}
        </g>
      </g>
    </svg>
  );
};
