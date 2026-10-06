import { motion } from "motion/react";
import type { ReactElement } from "react";
import type { BodyId, Mood } from "../types";
import { SHELL, alpha } from "./palettes";
import { useAvatar } from "./context";

/**
 * Bodies draw everything below the head (y >= 104) in the 200x240 box.
 * Each exposes a chest light that pulses while thinking and an arm that
 * gestures while talking.
 */
export interface BodyProps {
  accent: string;
  mood: Mood;
}

function ChestLight({ accent, mood, cx, cy, r = 7 }: BodyProps & { cx: number; cy: number; r?: number }) {
  return (
    <motion.circle
      className="tb"
      cx={cx}
      cy={cy}
      r={r}
      fill={accent}
      style={{ filter: `drop-shadow(0 0 8px ${alpha(accent, 0.9)})` }}
      animate={
        mood === "thinking"
          ? { opacity: [0.35, 1, 0.35], scale: [0.85, 1.15, 0.85] }
          : mood === "talking"
            ? { opacity: [0.7, 1, 0.7], scale: [1, 1.08, 1] }
            : { opacity: 0.8, scale: 1 }
      }
      transition={{ duration: mood === "thinking" ? 0.9 : 0.5, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

/** An arm that gestures when talking. `side` is -1 (left) or 1 (right). */
function Arm({ accent, mood, side, x, y, len = 56, w = 14 }: BodyProps & { side: -1 | 1; x: number; y: number; len?: number; w?: number }) {
  const idle = { rotate: side * 2 };
  const talk = side === 1 ? { rotate: [0, -28, -8, -34, 0] } : { rotate: [0, 10, -4, 12, 0] };
  return (
    <motion.g
      style={{ transformBox: "fill-box", transformOrigin: side === 1 ? "50% 8%" : "50% 8%" }}
      animate={mood === "talking" ? talk : mood === "thinking" ? { rotate: side * -6 } : idle}
      transition={mood === "talking" ? { duration: 1.3, repeat: Infinity, ease: "easeInOut" } : { duration: 0.6 }}
    >
      <rect x={x - w / 2} y={y} width={w} height={len} rx={w / 2} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <circle cx={x} cy={y + len - 2} r={w / 2 + 1} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={1.5} />
      <circle cx={x} cy={y + len - 2} r={3} fill={accent} opacity={0.9} />
    </motion.g>
  );
}

// -------------------------------------------------------------------- bodies
function Capsule(p: BodyProps) {
  const { accent } = p;
  return (
    <g>
      <rect x={92} y={102} width={16} height={12} fill={SHELL.light} />
      <Arm {...p} side={-1} x={52} y={118} />
      <Arm {...p} side={1} x={148} y={118} />
      <rect x={62} y={110} width={76} height={92} rx={32} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={72} y={118} width={56} height={14} rx={7} fill="white" opacity={0.05} />
      <ChestLight {...p} cx={100} cy={150} />
      <rect x={84} y={168} width={32} height={4} rx={2} fill={SHELL.light} />
      <rect x={90} y={176} width={20} height={4} rx={2} fill={SHELL.light} />
      {/* legs */}
      <rect x={76} y={198} width={18} height={30} rx={8} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={106} y={198} width={18} height={30} rx={8} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={72} y={222} width={26} height={10} rx={5} fill={SHELL.mid} />
      <rect x={102} y={222} width={26} height={10} rx={5} fill={SHELL.mid} />
      <rect x={76} y={226} width={18} height={2} fill={accent} opacity={0.7} />
      <rect x={106} y={226} width={18} height={2} fill={accent} opacity={0.7} />
    </g>
  );
}

function Boxy(p: BodyProps) {
  const { accent, mood } = p;
  return (
    <g>
      <rect x={90} y={102} width={20} height={12} fill={SHELL.light} />
      {/* shoulders */}
      <rect x={42} y={110} width={26} height={22} rx={6} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={132} y={110} width={26} height={22} rx={6} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <Arm {...p} side={-1} x={55} y={128} len={60} w={16} />
      <Arm {...p} side={1} x={145} y={128} len={60} w={16} />
      <rect x={58} y={112} width={84} height={86} rx={8} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={66} y={120} width={68} height={30} rx={4} fill={SHELL.screen} />
      {/* status lights */}
      {[0, 1, 2].map((i) => (
        <motion.rect
          key={i}
          className="tb"
          x={72 + i * 10}
          y={126}
          width={6}
          height={6}
          rx={1}
          fill={accent}
          animate={mood === "thinking" ? { opacity: [0.2, 1, 0.2] } : { opacity: i === 0 ? 0.9 : 0.35 }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
      <motion.rect
        className="tb"
        x={72}
        y={138}
        width={56}
        height={6}
        rx={1}
        fill={accent}
        opacity={0.6}
        initial={{ scaleX: 0.5 }}
        animate={mood === "talking" ? { scaleX: [0.4, 1, 0.6, 0.9, 0.4] } : { scaleX: 0.5 }}
        style={{ transformOrigin: "left center", transformBox: "fill-box" }}
        transition={{ duration: 0.7, repeat: Infinity, ease: "easeInOut" }}
      />
      <ChestLight {...p} cx={100} cy={170} r={6} />
      <path d="M66 158 H134 M66 184 H134" stroke={SHELL.line} strokeWidth={1.5} />
      {/* legs */}
      <rect x={70} y={196} width={24} height={30} rx={4} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={106} y={196} width={24} height={30} rx={4} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={64} y={222} width={34} height={12} rx={3} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={102} y={222} width={34} height={12} rx={3} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={1.5} />
    </g>
  );
}

function Hover(p: BodyProps) {
  const { accent, mood } = p;
  const { still } = useAvatar();
  return (
    <g>
      <rect x={92} y={102} width={16} height={10} fill={SHELL.light} />
      <Arm {...p} side={-1} x={60} y={118} len={46} w={12} />
      <Arm {...p} side={1} x={140} y={118} len={46} w={12} />
      <path d="M66 112 H134 L124 184 H76 Z" fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} strokeLinejoin="round" />
      <path d="M76 120 H124" stroke="white" strokeWidth={6} opacity={0.05} strokeLinecap="round" />
      <ChestLight {...p} cx={100} cy={146} r={9} />
      <circle cx={100} cy={146} r={14} fill="none" stroke={accent} strokeWidth={1.5} opacity={0.4} />
      {/* thruster disc */}
      <ellipse cx={100} cy={204} rx={44} ry={11} fill={SHELL.light} stroke={SHELL.line} strokeWidth={2} />
      <ellipse cx={100} cy={200} rx={34} ry={6} fill={SHELL.mid} />
      <motion.ellipse
        className="tb"
        cx={100}
        cy={214}
        rx={30}
        ry={6}
        fill={accent}
        style={{ filter: `blur(4px)` }}
        animate={still ? { opacity: 0.45, scaleX: 1 } : { opacity: mood === "talking" ? [0.5, 0.9, 0.5] : [0.3, 0.6, 0.3], scaleX: [0.9, 1.1, 0.9] }}
        transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
      />
      {[72, 86, 100, 114, 128].map((x, i) => (
        <motion.rect key={x} className="tb" x={x - 2} y={205} width={4} height={6} rx={1} fill={accent} animate={still ? { opacity: 0.7 } : { opacity: [0.3, 1, 0.3] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.12 }} />
      ))}
    </g>
  );
}

function Slim(p: BodyProps) {
  const { accent } = p;
  return (
    <g>
      <rect x={94} y={102} width={12} height={12} fill={SHELL.light} />
      <rect x={66} y={112} width={68} height={14} rx={7} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <Arm {...p} side={-1} x={70} y={124} len={64} w={10} />
      <Arm {...p} side={1} x={130} y={124} len={64} w={10} />
      <rect x={78} y={114} width={44} height={94} rx={14} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={98} y={122} width={4} height={74} rx={2} fill={accent} opacity={0.55} />
      <ChestLight {...p} cx={100} cy={136} r={6} />
      <rect x={86} y={160} width={28} height={2} fill={SHELL.light} />
      <rect x={86} y={168} width={28} height={2} fill={SHELL.light} />
      {/* long legs */}
      <rect x={82} y={204} width={12} height={28} rx={5} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={106} y={204} width={12} height={28} rx={5} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={76} y={228} width={22} height={8} rx={4} fill={SHELL.mid} />
      <rect x={102} y={228} width={22} height={8} rx={4} fill={SHELL.mid} />
    </g>
  );
}

function Orb(p: BodyProps) {
  const { accent, mood } = p;
  return (
    <g>
      <rect x={92} y={102} width={16} height={10} fill={SHELL.light} />
      <Arm {...p} side={-1} x={46} y={140} len={36} w={12} />
      <Arm {...p} side={1} x={154} y={140} len={36} w={12} />
      <circle cx={100} cy={164} r={56} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <ellipse cx={86} cy={132} rx={22} ry={10} fill="white" opacity={0.05} />
      <motion.circle
        className="tb"
        cx={100}
        cy={164}
        r={24}
        fill="none"
        stroke={accent}
        strokeWidth={3}
        strokeDasharray="30 14"
        opacity={0.55}
        animate={mood === "thinking" ? { rotate: 360 } : mood === "talking" ? { rotate: [0, 20, -10, 30, 0] } : { rotate: 0 }}
        transition={mood === "thinking" ? { duration: 3, repeat: Infinity, ease: "linear" } : { duration: 1.2, repeat: Infinity }}
      />
      <ChestLight {...p} cx={100} cy={164} r={11} />
      {/* feet */}
      <rect x={74} y={216} width={22} height={14} rx={7} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={104} y={216} width={22} height={14} rx={7} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
    </g>
  );
}

function Tank(p: BodyProps) {
  const { accent, mood } = p;
  return (
    <g>
      <rect x={88} y={102} width={24} height={14} fill={SHELL.light} />
      <rect x={36} y={114} width={30} height={26} rx={8} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <rect x={134} y={114} width={30} height={26} rx={8} fill={SHELL.light} stroke={SHELL.line} strokeWidth={1.5} />
      <Arm {...p} side={-1} x={51} y={138} len={50} w={18} />
      <Arm {...p} side={1} x={149} y={138} len={50} w={18} />
      <rect x={48} y={116} width={104} height={80} rx={16} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={2} />
      <rect x={60} y={126} width={80} height={24} rx={6} fill={SHELL.screen} />
      <motion.rect
        className="tb"
        x={66}
        y={134}
        width={68}
        height={8}
        rx={2}
        fill={accent}
        style={{ transformOrigin: "left center", transformBox: "fill-box", filter: `drop-shadow(0 0 4px ${accent})` }}
        initial={{ scaleX: 0.7 }}
        animate={mood === "thinking" ? { scaleX: [0.1, 1, 0.1] } : mood === "talking" ? { scaleX: [0.5, 0.9, 0.6, 1, 0.5] } : { scaleX: 0.7 }}
        transition={{ duration: mood === "thinking" ? 1.2 : 0.6, repeat: Infinity, ease: "easeInOut" }}
      />
      <ChestLight {...p} cx={100} cy={172} r={7} />
      <rect x={70} y={166} width={16} height={12} rx={2} fill={SHELL.light} />
      <rect x={114} y={166} width={16} height={12} rx={2} fill={SHELL.light} />
      {/* treads */}
      <rect x={42} y={198} width={116} height={32} rx={16} fill={SHELL.light} stroke={SHELL.line} strokeWidth={2} />
      {[60, 80, 100, 120, 140].map((x, i) => (
        <motion.circle key={x} className="tb" cx={x} cy={214} r={8} fill={SHELL.mid} stroke={SHELL.line} strokeWidth={1.5} animate={mood === "talking" ? { rotate: 360 } : { rotate: 0 }} transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: i * 0.05 }} />
      ))}
      {[60, 80, 100, 120, 140].map((x) => (
        <rect key={x} x={x - 1} y={208} width={2} height={5} fill={accent} opacity={0.7} />
      ))}
    </g>
  );
}

export const BODIES: Record<BodyId, (p: BodyProps) => ReactElement> = {
  capsule: Capsule,
  boxy: Boxy,
  hover: Hover,
  slim: Slim,
  orb: Orb,
  tank: Tank,
};
