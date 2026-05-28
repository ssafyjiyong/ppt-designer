const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '';

if (!API_BASE) {
  console.warn('VITE_API_BASE not set; using same-origin (likely broken in production).');
}

export type SlideInfo = {
  index: number;
  draft_text: string;
  designed: boolean;
  title: string;
  preview_url: string | null;
};

export type JobStatus = 'created' | 'processing' | 'designing' | 'retrying' | 'completed' | 'failed';

export type Job = {
  job_id: string;
  status: JobStatus;
  error: string | null;
  total_slides: number | null;
  slides: SlideInfo[];
  download_url: string | null;
};

export async function createJob(): Promise<{ job_id: string; upload_url: string }> {
  const res = await fetch(`${API_BASE}/jobs`, { method: 'POST' });
  if (!res.ok) throw new Error(`createJob: ${res.status}`);
  return res.json();
}

export async function uploadToPresigned(url: string, file: File): Promise<void> {
  const res = await fetch(url, {
    method: 'PUT',
    body: file,
  });
  if (!res.ok) throw new Error(`upload: ${res.status}`);
}

export async function startJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/start`, { method: 'POST' });
  if (!res.ok) throw new Error(`startJob: ${res.status}`);
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`getJob: ${res.status}`);
  return res.json();
}

export async function retrySlide(jobId: string, index: number, feedback: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/slides/${index}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  });
  if (!res.ok) throw new Error(`retrySlide: ${res.status}`);
}
