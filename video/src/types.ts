export type Palette = {
  background: string;
  text: string;
  accent: string;
  surface?: string;
  text_muted?: string;
  on_accent?: string;
  hairline?: string;
};

export type FontSpec = { family: string; src: string | null } | null;

export type Diagram = {
  type: "flow" | "timeline" | "comparison" | "bar" | "table" | "cycle" | "list";
  title?: string | null;
  data: any;
};

export type MouthCue = { startFrame: number; endFrame: number; shape: string };

export type Paragraph = {
  startFrame: number;
  durationInFrames: number;
  text: string;
  pages: number[];
  diagram: Diagram | null;
  audio: string;
  mouth: MouthCue[];
};

export type Avatar = {
  enabled: boolean;
  name: string;
  preset: "neutral" | "workshop" | "office";
  position: "corner" | "side" | "full";
  size: number;
  palette: Record<string, string> | null;
  images: Record<string, string> | null;
};

export type Cue = { startFrame: number; endFrame: number; text: string };

export type Scene = {
  id: string;
  title: string;
  startFrame: number;
  durationInFrames: number;
  paragraphs: Paragraph[];
  captions: Cue[];
};

export type Props = {
  meta: {
    title: string;
    subtitle?: string | null;
    author?: string | null;
    date?: string | null;
    branding?: string | null;
    language?: string;
  };
  canvas: { width: number; height: number; fps: number };
  durationInFrames: number;
  layout: "screen" | "fullbleed" | "split";
  palette: Palette;
  fonts: { body: FontSpec; heading: FontSpec };
  captions: { position: "bottom" | "top"; burned_in: boolean };
  cards: { titleFrames: number; creditsFrames: number };
  disclosure: string | null;
  avatar: Avatar;
  scenes: Scene[];
};
