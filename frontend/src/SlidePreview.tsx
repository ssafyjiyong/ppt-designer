import { SlideSpec } from './api';

const SLIDE_W_IN = 13.333;
const SLIDE_H_IN = 7.5;
const DPI = 96;
const SLIDE_W = SLIDE_W_IN * DPI;
const SLIDE_H = SLIDE_H_IN * DPI;

export default function SlidePreview({ spec }: { spec: SlideSpec | null }) {
  if (!spec) return null;
  const bg = spec.background?.color || '#FFFFFF';
  const elements = spec.elements || [];

  return (
    <svg viewBox={`0 0 ${SLIDE_W} ${SLIDE_H}`} preserveAspectRatio="xMidYMid meet">
      <rect x="0" y="0" width={SLIDE_W} height={SLIDE_H} fill={bg} />
      {elements.map((el, i) => renderEl(el, i))}
    </svg>
  );
}

function renderEl(el: any, key: number) {
  const x = num(el.x) * DPI;
  const y = num(el.y) * DPI;
  const w = num(el.w) * DPI;
  const h = num(el.h) * DPI;

  if (el.type === 'shape') {
    const strokeW = num(el.line_w || 0) * DPI / 72;
    if (el.shape === 'line') {
      return (
        <line
          key={key}
          x1={x} y1={y} x2={x + w} y2={y + h}
          stroke={el.line || '#1A1A1A'}
          strokeWidth={Math.max(strokeW, 1)}
        />
      );
    }
    const rx = el.shape === 'rounded_rectangle' ? 0.1 * DPI : 0;
    if (el.shape === 'oval') {
      return (
        <ellipse
          key={key}
          cx={x + w / 2} cy={y + h / 2} rx={w / 2} ry={h / 2}
          fill={el.fill || 'transparent'}
          stroke={el.line || 'none'}
          strokeWidth={strokeW}
        />
      );
    }
    return (
      <rect
        key={key}
        x={x} y={y} width={w} height={h} rx={rx} ry={rx}
        fill={el.fill || 'transparent'}
        stroke={el.line || 'none'}
        strokeWidth={strokeW}
      />
    );
  }

  if (el.type === 'text') {
    return renderTextSkeleton(el, key, x, y, w, h);
  }

  if (el.type === 'bullet') {
    return renderBulletSkeleton(el, key, x, y, w, h);
  }

  return null;
}

function renderTextSkeleton(el: any, key: number, x: number, y: number, w: number, h: number) {
  const fs = (num(el.font_size) || 14) * DPI / 72;
  const lineHeight = fs * 1.25;
  const textLen = (el.text || '').length;
  const charsPerLine = Math.max(1, Math.floor(w / (fs * 0.55)));
  const lines = Math.max(1, Math.min(
    Math.floor(h / lineHeight) || 1,
    Math.ceil(textLen / charsPerLine) || 1,
  ));
  const barH = fs * 0.55;
  const color = el.color || '#444444';

  const valign = el.valign;
  const blockH = lines * lineHeight - (lineHeight - barH);
  let startY = y;
  if (valign === 'middle') startY = y + (h - blockH) / 2;
  else if (valign === 'bottom') startY = y + h - blockH;

  const align = el.align;

  const bars = [];
  for (let i = 0; i < lines; i++) {
    let lineLen: number;
    if (lines === 1) {
      lineLen = Math.min(textLen, charsPerLine);
    } else if (i === lines - 1) {
      const remaining = textLen - (lines - 1) * charsPerLine;
      lineLen = Math.max(charsPerLine * 0.3, Math.min(remaining, charsPerLine));
    } else {
      lineLen = charsPerLine;
    }
    const ratio = Math.max(0.15, Math.min(1, lineLen / charsPerLine));
    const barW = w * ratio;
    let barX = x;
    if (align === 'center') barX = x + (w - barW) / 2;
    else if (align === 'right') barX = x + w - barW;
    bars.push(
      <rect
        key={i}
        x={barX}
        y={startY + i * lineHeight}
        width={barW}
        height={barH}
        rx={barH * 0.25}
        fill={color}
        opacity={el.bold ? 0.45 : 0.3}
      />
    );
  }

  return <g key={key}>{bars}</g>;
}

function renderBulletSkeleton(el: any, key: number, x: number, y: number, w: number, h: number) {
  const items: string[] = el.items || [];
  const fs = (num(el.font_size) || 14) * DPI / 72;
  const lineHeight = fs * 1.4;
  const color = el.color || '#444444';
  const dotR = fs * 0.18;
  const barH = fs * 0.5;
  const charsPerLine = Math.max(1, Math.floor((w - fs * 0.9) / (fs * 0.55)));

  const bars = items.slice(0, Math.max(1, Math.floor(h / lineHeight))).map((item, i) => {
    const len = item.length;
    const ratio = Math.max(0.25, Math.min(1, len / charsPerLine));
    const barW = (w - fs * 0.9) * ratio;
    const cy = y + i * lineHeight + lineHeight / 2;
    return (
      <g key={i}>
        <circle cx={x + dotR} cy={cy} r={dotR} fill={color} opacity={0.45} />
        <rect
          x={x + fs * 0.9}
          y={cy - barH / 2}
          width={barW}
          height={barH}
          rx={barH * 0.25}
          fill={color}
          opacity={0.3}
        />
      </g>
    );
  });

  return <g key={key}>{bars}</g>;
}

function num(v: any): number {
  const n = Number(v);
  return isFinite(n) ? n : 0;
}
