import { SlideSpec } from './api';

const SLIDE_W = 13.333;
const SLIDE_H = 7.5;

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
  const x = num(el.x);
  const y = num(el.y);
  const w = num(el.w);
  const h = num(el.h);
  if (el.type === 'shape') {
    if (el.shape === 'line') {
      return <line key={key} x1={x} y1={y} x2={x + w} y2={y + h} stroke={el.line || '#1A1A1A'} strokeWidth={(el.line_w || 1) / 24} />;
    }
    const rx = el.shape === 'rounded_rectangle' ? 0.1 : 0;
    const isOval = el.shape === 'oval';
    if (isOval) {
      return <ellipse key={key} cx={x + w / 2} cy={y + h / 2} rx={w / 2} ry={h / 2} fill={el.fill || 'transparent'} stroke={el.line || 'none'} strokeWidth={(el.line_w || 0) / 24} />;
    }
    return <rect key={key} x={x} y={y} width={w} height={h} rx={rx} ry={rx} fill={el.fill || 'transparent'} stroke={el.line || 'none'} strokeWidth={(el.line_w || 0) / 24} />;
  }
  if (el.type === 'text') {
    const fs = (el.font_size || 14) / 72;
    const anchor = el.align === 'center' ? 'middle' : el.align === 'right' ? 'end' : 'start';
    const ax = el.align === 'center' ? x + w / 2 : el.align === 'right' ? x + w : x;
    return (
      <foreignObject key={key} x={x} y={y} width={w} height={h}>
        <div style={{
          width: '100%', height: '100%',
          display: 'flex',
          alignItems: el.valign === 'middle' ? 'center' : el.valign === 'bottom' ? 'flex-end' : 'flex-start',
          justifyContent: el.align === 'center' ? 'center' : el.align === 'right' ? 'flex-end' : 'flex-start',
          color: el.color || '#1A1A1A',
          fontSize: `${fs * 0.85}px`,
          fontWeight: el.bold ? 700 : 400,
          fontStyle: el.italic ? 'italic' : 'normal',
          fontFamily: 'Pretendard, system-ui, sans-serif',
          lineHeight: 1.2,
          overflow: 'hidden',
          whiteSpace: 'pre-wrap',
          padding: 0,
        }}>
          {el.text || ''}
        </div>
      </foreignObject>
    );
  }
  if (el.type === 'bullet') {
    const items: string[] = el.items || [];
    const fs = (el.font_size || 14) / 72;
    return (
      <foreignObject key={key} x={x} y={y} width={w} height={h}>
        <div style={{
          color: el.color || '#1A1A1A',
          fontSize: `${fs * 0.85}px`,
          fontFamily: 'Pretendard, system-ui, sans-serif',
          lineHeight: 1.4,
          overflow: 'hidden',
        }}>
          {items.map((it, i) => <div key={i}>• {it}</div>)}
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
