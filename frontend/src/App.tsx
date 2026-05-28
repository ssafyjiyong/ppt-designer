import { useEffect, useRef, useState } from 'react';
import { createJob, getJob, Job, retrySlide, startJob, uploadToPresigned } from './api';

type Phase = 'idle' | 'uploading' | 'tracking' | 'done' | 'error';

export default function App() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [retryTarget, setRetryTarget] = useState<number | null>(null);
  const [retryFeedback, setRetryFeedback] = useState('');
  const [previewIdx, setPreviewIdx] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => () => stopPolling(), []);

  function stopPolling() {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.pptx')) {
      setError('.pptx 파일만 업로드 가능합니다.');
      return;
    }
    setError(null);
    setPhase('uploading');
    try {
      const { job_id, upload_url } = await createJob();
      await uploadToPresigned(upload_url, file);
      await startJob(job_id);
      setPhase('tracking');
      startPolling(job_id);
    } catch (e: any) {
      setError(e.message || '업로드 실패');
      setPhase('error');
    }
  }

  function startPolling(jobId: string) {
    const tick = async () => {
      try {
        const j = await getJob(jobId);
        setJob(j);
        if (j.status === 'completed') {
          setPhase('done');
          stopPolling();
        } else if (j.status === 'failed') {
          setPhase('error');
          setError(j.error || '처리 실패');
          stopPolling();
        }
      } catch (e: any) {
        console.warn('poll error', e);
      }
    };
    tick();
    pollTimerRef.current = window.setInterval(tick, 3000);
  }

  async function handleRetry() {
    if (retryTarget == null || !job) return;
    try {
      await retrySlide(job.job_id, retryTarget, retryFeedback);
      setRetryTarget(null);
      setRetryFeedback('');
      setPhase('tracking');
      if (!pollTimerRef.current) startPolling(job.job_id);
    } catch (e: any) {
      setError(e.message || '재시도 실패');
    }
  }

  function reset() {
    stopPolling();
    setJob(null);
    setPhase('idle');
    setError(null);
  }

  const progressPct = computeProgress(job);

  return (
    <div className="app">
      <div className="header">
        <h1>🎨 PPTdesigner</h1>
        <span className="tag">텍스트 초안 → 자동 디자인된 PPT</span>
      </div>

      {phase === 'idle' && (
        <div
          className={`drop ${dragOver ? 'active' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f) handleFile(f);
          }}
        >
          <strong>PPT 파일을 끌어다 놓거나 클릭해 업로드</strong>
          <p>각 슬라이드에 텍스트 초안만 들어있는 .pptx</p>
          <p className="muted">Claude가 슬라이드별로 레이아웃을 디자인합니다 (슬라이드 5장당 약 1~2분, 동시 5개 병렬 처리)</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>
      )}

      {phase === 'uploading' && (
        <div className="card"><span className="spinner-inline" /> &nbsp;업로드 중…</div>
      )}

      {(phase === 'tracking' || phase === 'done') && job && (
        <div>
          <div className="card">
            <div className="status-row">
              <span className={`status-chip chip-${job.status}`}>{statusLabel(job.status)}</span>
              {job.total_slides != null && (
                <span className="muted">슬라이드 {designedCount(job)}/{job.total_slides}</span>
              )}
              {phase === 'tracking' && <span className="spinner-inline" />}
            </div>
            <div className="progress"><div style={{ width: `${progressPct}%` }} /></div>
            <div className="toolbar">
              {job.status === 'completed' && job.download_url && (
                <a className="btn" href={job.download_url} download>📥 PPTX 다운로드</a>
              )}
              <button className="btn secondary" onClick={reset}>새 파일 업로드</button>
              <span className="spacer" />
              <span className="muted" style={{ fontFamily: 'monospace' }}>job: {job.job_id}</span>
            </div>
          </div>

          {job.slides.length > 0 && (
            <div className="slides">
              {job.slides.map((s) => {
                const ready = s.designed && !!s.preview_url;
                return (
                  <div key={s.index} className={`slide-card ${ready ? '' : 'pending'}`}>
                    <div className="idx">SLIDE {s.index + 1}</div>
                    <div
                      className={`preview ${ready ? 'clickable' : ''}`}
                      onClick={() => ready && setPreviewIdx(s.index)}
                      title={ready ? '클릭해서 크게 보기' : undefined}
                    >
                      {s.preview_url ? (
                        <img src={s.preview_url} alt={`slide ${s.index + 1} preview`} />
                      ) : null}
                    </div>
                    <div className="title">
                      {s.title || (s.designed ? '(제목 없음)' : '디자인 중…')}
                      {s.designed && !s.preview_url && <span className="muted"> · 이미지 렌더 중</span>}
                    </div>
                    <div className="draft">{s.draft_text}</div>
                    <div className="actions">
                      <button
                        className="btn secondary"
                        disabled={!s.designed || job.status === 'retrying'}
                        onClick={() => { setRetryTarget(s.index); setRetryFeedback(''); }}
                      >
                        🔄 재시도
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {error && <div className="error">⚠️ {error}</div>}

      {previewIdx != null && job && (() => {
        const s = job.slides.find((x) => x.index === previewIdx);
        if (!s || !s.preview_url) return null;
        const ready = job.slides.filter((x) => x.preview_url).sort((a, b) => a.index - b.index);
        const goPrev = () => {
          const pos = ready.findIndex((x) => x.index === previewIdx);
          if (pos > 0) setPreviewIdx(ready[pos - 1].index);
        };
        const goNext = () => {
          const pos = ready.findIndex((x) => x.index === previewIdx);
          if (pos !== -1 && pos < ready.length - 1) setPreviewIdx(ready[pos + 1].index);
        };
        return (
          <div className="modal-bg" onClick={() => setPreviewIdx(null)}>
            <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
              <div className="preview-modal-head">
                <span className="preview-modal-title">SLIDE {s.index + 1} {s.title ? `· ${s.title}` : ''}</span>
                <button className="preview-close" onClick={() => setPreviewIdx(null)} aria-label="닫기">✕</button>
              </div>
              <div className="preview-modal-stage">
                <button className="preview-nav prev" onClick={goPrev} aria-label="이전">‹</button>
                <div className="preview-modal-canvas">
                  <img src={s.preview_url} alt={`slide ${s.index + 1} preview`} />
                </div>
                <button className="preview-nav next" onClick={goNext} aria-label="다음">›</button>
              </div>
            </div>
          </div>
        );
      })()}

      {retryTarget != null && job && (
        <div className="modal-bg" onClick={() => setRetryTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>슬라이드 {retryTarget + 1} 재디자인</h3>
            <p className="muted">개선 방향을 알려주면 Claude가 반영해서 다시 그립니다 (선택).</p>
            <textarea
              value={retryFeedback}
              onChange={(e) => setRetryFeedback(e.target.value)}
              placeholder="예: 제목을 더 크게, 다이어그램으로 표현, 색상을 좀 더 차분하게…"
            />
            <div className="actions">
              <button className="btn secondary" onClick={() => setRetryTarget(null)}>취소</button>
              <button className="btn" onClick={handleRetry}>재시도 실행</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function statusLabel(s: string): string {
  return {
    created: '대기',
    processing: '시작 중',
    designing: '디자인 중',
    retrying: '재시도 중',
    completed: '완료',
    failed: '실패',
  }[s] || s;
}

function designedCount(j: Job): number {
  return j.slides.filter((s) => s.designed).length;
}

function computeProgress(j: Job | null): number {
  if (!j) return 0;
  if (j.status === 'completed') return 100;
  if (j.status === 'failed') return 0;
  if (!j.total_slides) return 5;
  const done = designedCount(j);
  return Math.min(95, 10 + (done / j.total_slides) * 85);
}
