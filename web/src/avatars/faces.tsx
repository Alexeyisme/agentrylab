import { motion } from "motion/react";
import type { ReactElement, ReactNode } from "react";
import type { FaceId, Mood } from "../types";
import { SHELL, alpha } from "./palettes";

/**
 * Faces draw the head: shell + eyes + mouth, in the 200x240 avatar box.
 * The head sits between y=14 and y=104; the neck is at x=100.
 */
export interface FaceProps {
  accent: string;
  mood: Mood;
  seed: number; // per-persona offset so blinks are not synchronised
}

const blinkTransition = (seed: number) => ({
  duration: 0.28,
  repeat: Infinity,
  repeatDelay: 2.6 + (seed % 7) * 0.45,
  ease: "easeInOut" as const,
  times: [0, 0.4, 0.6, 1],
});

/** Wraps eyes so they blink. */
function Blink({ seed, children, mood }: { seed: number; mood: Mood; children: ReactNode }) {
  return (
    <motion.g
      className="tb"
      animate={mood === "thinking" ? { scaleY: [1, 0.75, 0.75, 1] } : { scaleY: [1, 1, 0.08, 1] }}
      transition={mood === "thinking" ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" } : blinkTransition(seed)}
    >
      {children}
    </motion.g>
  );
}

/** Pupils/irises wander while thinking. */
function Gaze({ mood, children }: { mood: Mood; children: ReactNode }) {
  return (
    <motion.g
      animate={
        mood === "thinking"
          ? { x: [0, 5, -4, 2, 0], y: [0, -3, 1, -2, 0] }
          : mood === "talking"
            ? { x: [0, 1.5, -1.5, 0], y: 0 }
            : { x: 0, y: 0 }
      }
      transition={{ duration: mood === "thinking" ? 2.4 : 0.8, repeat: Infinity, ease: "easeInOut" }}
    >
      {children}
    </motion.g>
  );
}

/** Equaliser-style mouth: bars dance while talking, idle shows a flat line. */
function EqMouth({ accent, mood, x = 100, y = 84, bars = 5, width = 30 }: { accent: string; mood: Mood; x?: number; y?: number; bars?: number; width?: number }) {
  const gap = width / bars;
  return (
    <g>
      {Array.from({ length: bars }).map((_, i) => {
        const cx = x - width / 2 + gap * i + gap / 2;
        const phase = i * 0.11;
        return (
          <motion.rect
            key={i}
            className="tb"
            x={cx - gap * 0.3}
            y={y - 5}
            width={gap * 0.6}
            height={10}
            rx={1.5}
            fill={accent}
            style={{ filter: `drop-shadow(0 0 4px ${alpha(accent, 0.8)})` }}
            animate={
              mood === "talking"
                ? { scaleY: [0.25, 1, 0.45, 0.9, 0.3, 0.75, 0.25], opacity: 1 }
                : { scaleY: 0.22, opacity: mood === "thinking" ? 0.5 : 0.9 }
            }
            transition={
              mood === "talking"
                ? { duration: 0.55, repeat: Infinity, ease: "easeInOut", delay: phase }
                : { duration: 0.3 }
            }
          />
        );
      })}
    </g>
  );
}

function Antenna({ accent, mood, x = 100, y = 26, h = 14 }: { accent: string; mood: Mood; x?: number; y?: number; h?: number }) {
  return (
    <g>
      <rect x={x - 1.5} y={y - h} width={3} height={h} fill={SHELL.light} />
      <motion.circle
        cx={x}
        cy={y - h - 3}
        r={4}
        fill={accent}
        style={{ filter: `drop-shadow(0 0 6px ${accent})` }}
        animate={mood === "thinking" ? { opacity: [0.3, 1, 0.3], scale: [0.9, 1.25, 0.9] } : { opacity: 0.9, scale: 1 }}
        transition={{ duration: 0.7, repeat: Infinity, ease: "easeInOut" }}
        className="tb"
      />
    </g>
  );
}

// --------------------------------------------------------------------- faces
function Visor({ accent, mood, seed }: FaceProps) {
  return (
    <g>
      <Antenna accent={accent} mood={mood} />
      <rect x={58} y={26} width={84} height={76} rx={26} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={66} y={34} width={68} height={10} rx={5} fill={SHELL.light} opacity={0.5} />
      {/* visor band */}
      <rect x={64} y={50} width={72} height={24} rx={12} fill={SHELL.screen} />
      <Blink seed={seed} mood={mood}>
        <Gaze mood={mood}>
          <motion.rect
            x={74}
            y={58}
            width={20}
            height={8}
            rx={4}
            fill={accent}
            style={{ filter: `drop-shadow(0 0 6px ${accent})` }}
            animate={mood === "thinking" ? { x: [0, 26, 0] } : { x: 0 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.rect
            x={106}
            y={58}
            width={20}
            height={8}
            rx={4}
            fill={accent}
            style={{ filter: `drop-shadow(0 0 6px ${accent})` }}
            animate={mood === "thinking" ? { x: [0, -26, 0] } : { x: 0 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
        </Gaze>
      </Blink>
      <EqMouth accent={accent} mood={mood} y={88} width={28} bars={6} />
    </g>
  );
}

function Duo({ accent, mood, seed }: FaceProps) {
  return (
    <g>
      <Antenna accent={accent} mood={mood} h={10} />
      {/* ear pods */}
      <rect x={50} y={52} width={10} height={22} rx={4} fill={SHELL.light} />
      <rect x={140} y={52} width={10} height={22} rx={4} fill={SHELL.light} />
      <circle cx={100} cy={62} r={44} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <ellipse cx={100} cy={46} rx={30} ry={10} fill="white" opacity={0.05} />
      <Blink seed={seed} mood={mood}>
        <Gaze mood={mood}>
          <circle cx={83} cy={58} r={10} fill={SHELL.screen} />
          <circle cx={117} cy={58} r={10} fill={SHELL.screen} />
          <circle cx={83} cy={58} r={6.5} fill={accent} style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
          <circle cx={117} cy={58} r={6.5} fill={accent} style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
          <circle cx={85.5} cy={55.5} r={2} fill="white" opacity={0.85} />
          <circle cx={119.5} cy={55.5} r={2} fill="white" opacity={0.85} />
        </Gaze>
      </Blink>
      <EqMouth accent={accent} mood={mood} y={84} width={26} bars={5} />
    </g>
  );
}

function Cyclops({ accent, mood, seed }: FaceProps) {
  return (
    <g>
      <rect x={62} y={22} width={76} height={80} rx={22} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={70} y={28} width={60} height={6} rx={3} fill={SHELL.light} opacity={0.6} />
      {/* rivets */}
      {[70, 130].map((x) => (
        <circle key={x} cx={x} cy={92} r={2.2} fill={SHELL.light} />
      ))}
      <Blink seed={seed} mood={mood}>
        <circle cx={100} cy={58} r={20} fill={SHELL.screen} />
        <circle cx={100} cy={58} r={16} fill={alpha(accent, 0.18)} />
        <Gaze mood={mood}>
          <circle cx={100} cy={58} r={10} fill={accent} style={{ filter: `drop-shadow(0 0 8px ${accent})` }} />
          <circle cx={100} cy={58} r={4.5} fill={SHELL.screen} />
          <circle cx={104} cy={53} r={2.5} fill="white" opacity={0.9} />
        </Gaze>
      </Blink>
      <EqMouth accent={accent} mood={mood} y={88} width={24} bars={4} />
    </g>
  );
}

function Pixel({ accent, mood, seed }: FaceProps) {
  const px = 5;
  const eye = (ox: number) =>
    [0, 1].flatMap((r) =>
      [0, 1].map((c) => (
        <rect key={`${ox}-${r}-${c}`} x={ox + c * (px + 1)} y={52 + r * (px + 1)} width={px} height={px} fill={accent} style={{ filter: `drop-shadow(0 0 3px ${accent})` }} />
      )),
    );
  const mouthCols = [0, 1, 2, 3, 4, 5, 6];
  return (
    <g>
      <Antenna accent={accent} mood={mood} x={126} y={24} h={10} />
      <rect x={60} y={24} width={80} height={78} rx={12} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={68} y={32} width={64} height={62} rx={6} fill={SHELL.screen} />
      {/* scanlines */}
      {[38, 46, 54, 62, 70, 78, 86].map((y) => (
        <rect key={y} x={68} y={y} width={64} height={1} fill="white" opacity={0.04} />
      ))}
      <Blink seed={seed} mood={mood}>
        <Gaze mood={mood}>
          {eye(78)}
          {eye(111)}
        </Gaze>
      </Blink>
      <g>
        {mouthCols.map((c) => (
          <motion.rect
            key={c}
            className="tb"
            x={79 + c * (px + 1)}
            y={78}
            width={px}
            height={px * 2}
            fill={accent}
            animate={
              mood === "talking"
                ? { scaleY: [0.5, 1, 0.5, 1.4, 0.5], opacity: 1 }
                : { scaleY: 0.5, opacity: 0.8 }
            }
            transition={mood === "talking" ? { duration: 0.5, repeat: Infinity, delay: c * 0.07, ease: "linear" } : { duration: 0.2 }}
          />
        ))}
      </g>
    </g>
  );
}

function Feline({ accent, mood, seed }: FaceProps) {
  return (
    <g>
      {/* ears */}
      <motion.path
        d="M64 44 L58 14 L84 30 Z"
        fill={SHELL.mid}
        stroke={SHELL.line}
        strokeWidth={2}
        className="tb"
        animate={mood === "thinking" ? { rotate: [0, -8, 0] } : mood === "talking" ? { rotate: [0, 3, 0] } : { rotate: 0 }}
        transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.path
        d="M136 44 L142 14 L116 30 Z"
        fill={SHELL.mid}
        stroke={SHELL.line}
        strokeWidth={2}
        className="tb"
        animate={mood === "thinking" ? { rotate: [0, 8, 0] } : mood === "talking" ? { rotate: [0, -3, 0] } : { rotate: 0 }}
        transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
      />
      <path d="M66 20 L60 44 M134 20 L140 44" stroke={accent} strokeWidth={2} opacity={0.6} />
      <path d="M58 56 C58 30 142 30 142 56 C142 90 120 104 100 104 C80 104 58 90 58 56 Z" fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <Blink seed={seed} mood={mood}>
        <Gaze mood={mood}>
          <ellipse cx={82} cy={60} rx={11} ry={7} fill={accent} transform="rotate(-12 82 60)" style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
          <ellipse cx={118} cy={60} rx={11} ry={7} fill={accent} transform="rotate(12 118 60)" style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
          <ellipse cx={82} cy={60} rx={2.5} ry={5.5} fill={SHELL.screen} />
          <ellipse cx={118} cy={60} rx={2.5} ry={5.5} fill={SHELL.screen} />
        </Gaze>
      </Blink>
      {/* whiskers */}
      <path d="M60 80 L76 78 M60 88 L76 84 M140 80 L124 78 M140 88 L124 84" stroke={SHELL.light} strokeWidth={1.5} />
      <motion.path
        d="M92 84 Q100 92 108 84"
        stroke={accent}
        strokeWidth={3}
        fill="none"
        strokeLinecap="round"
        style={{ transformBox: "fill-box", transformOrigin: "50% 0%" }}
        animate={mood === "talking" ? { scaleY: [1, 2.4, 1.3, 2.8, 1] } : { scaleY: 1 }}
        transition={mood === "talking" ? { duration: 0.5, repeat: Infinity, ease: "easeInOut" } : { duration: 0.2 }}
      />
    </g>
  );
}

function Crt({ accent, mood, seed }: FaceProps) {
  const wave = ["M74 84 L84 84 L88 78 L92 90 L96 80 L100 88 L104 82 L108 86 L112 84 L126 84", "M74 84 L82 84 L86 90 L90 76 L94 88 L100 80 L106 92 L110 78 L114 84 L126 84", "M74 84 L86 84 L90 88 L94 80 L98 86 L102 84 L106 88 L110 80 L116 84 L126 84"];
  return (
    <g>
      {/* rabbit ears */}
      <path d="M86 24 L72 8 M114 24 L128 8" stroke={SHELL.light} strokeWidth={3} strokeLinecap="round" />
      <motion.circle cx={72} cy={8} r={3} fill={accent} className="tb" animate={mood === "thinking" ? { opacity: [0.2, 1, 0.2] } : { opacity: 0.8 }} transition={{ duration: 0.6, repeat: Infinity }} />
      <motion.circle cx={128} cy={8} r={3} fill={accent} className="tb" animate={mood === "thinking" ? { opacity: [1, 0.2, 1] } : { opacity: 0.8 }} transition={{ duration: 0.6, repeat: Infinity }} />
      <rect x={54} y={22} width={92} height={80} rx={10} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={62} y={30} width={76} height={58} rx={6} fill={SHELL.screen} />
      <rect x={62} y={30} width={76} height={58} rx={6} fill={alpha(accent, 0.07)} />
      {[36, 42, 48, 54, 60, 66, 72, 78, 84].map((y) => (
        <rect key={y} x={62} y={y} width={76} height={1} fill="white" opacity={0.05} />
      ))}
      {/* knobs */}
      <circle cx={70} cy={95} r={2.5} fill={SHELL.light} />
      <circle cx={78} cy={95} r={2.5} fill={accent} opacity={0.8} />
      <Blink seed={seed} mood={mood}>
        <Gaze mood={mood}>
          <path d="M78 60 L86 52 L94 60" stroke={accent} strokeWidth={4} fill="none" strokeLinecap="round" strokeLinejoin="round" style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
          <path d="M106 60 L114 52 L122 60" stroke={accent} strokeWidth={4} fill="none" strokeLinecap="round" strokeLinejoin="round" style={{ filter: `drop-shadow(0 0 5px ${accent})` }} />
        </Gaze>
      </Blink>
      <motion.path d="M74 84 L126 84" stroke={accent} strokeWidth={2.5} fill="none" strokeLinecap="round" animate={{ opacity: mood === "talking" ? 0 : 0.9 }} transition={{ duration: 0.2 }} />
      {wave.map((d, i) => (
        <motion.path
          key={i}
          d={d}
          stroke={accent}
          strokeWidth={2.5}
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 4px ${accent})` }}
          animate={mood === "talking" ? { opacity: [i === 0 ? 1 : 0, i === 1 ? 1 : 0, i === 2 ? 1 : 0, i === 0 ? 1 : 0] } : { opacity: 0 }}
          transition={mood === "talking" ? { duration: 0.45, repeat: Infinity, ease: "linear" } : { duration: 0.2 }}
        />
      ))}
    </g>
  );
}

export const FACES: Record<FaceId, (p: FaceProps) => ReactElement> = {
  visor: Visor,
  duo: Duo,
  cyclops: Cyclops,
  pixel: Pixel,
  feline: Feline,
  crt: Crt,
};
