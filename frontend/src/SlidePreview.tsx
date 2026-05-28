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
    const fs = (num(el.font_size) || 14) * DPI / 72;
    const valign = el.valign === 'middle' ? 'center' : el.valign === 'bottom' ? 'flex-end' : 'flex-start';
    const textAlign = el.align === 'center' ? 'center' : el.align === 'right' ? 'right' : 'left';
    return (
      <foreignObject key={key} x={x} y={y} width={w} height={h}>
        <div
          xmlns="http://www.w3.org/1999/xhtml"
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: valign,
            overflow: 'hidden',
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              width: '100%',
              color: el.color || '#1A1A1A',
              fontSize: `${fs}px`,
              fontWeight: el.bold ? 700 : 400,
              fontStyle: el.italic ? 'italic' : 'normal',
              fontFamily: 'Pretendard, "Malgun Gothic", system-ui, sans-serif',
              lineHeight: 1.25,
              textAlign,
              whiteSpace: 'pre-wrap',
              wordBreak: 'keep-all',
              overflowWrap: 'break-word',
            }}
          >
            {el.text || ''}
          </div>
        </div>
      </foreignObject>
    );
  }

  if (el.type === 'bullet') {
    const items: string[] = el.items || [];
    const fs = (num(el.font_size) || 14) * DPI / 72;
    return (
      <foreignObject key={key} x={x} y={y} width={w} height={h}>
        <div
          xmlns="http://www.w3.org/1999/xhtml"
          style={{
            width: '100%',
            height: '100%',
            color: el.color || '#1A1A1A',
            fontSize: `${fs}px`,
            fontFamily: 'Pretendard, "Malgun Gothic", system-ui, sans-serif',
            lineHeight: 1.45,
            overflow: 'hidden',
            wordBreak: 'keep-all',
            overflowWrap: 'break-word',
            boxSizing: 'border-box',
          }}
        >
          {items.map((it, i) => (
            <div key={i} style={{ paddingLeft: `${fs * 0.9}px`, textIndent: `-${fs * 0.9}px` }}>
              • {it}
            </div>
          ))}
        </div>
      </foreignObject>
    );
  }
  return null;
}

function num(v: any): number {
  const n = Number(v);
  return isFinite(n) ? n : 0;
}
