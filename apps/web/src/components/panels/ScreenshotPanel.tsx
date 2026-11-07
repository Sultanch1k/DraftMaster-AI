'use client';

import { useRef, useState } from 'react';
import { ImageUp, Loader2, ScanLine, Upload } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import type { ScreenshotResult } from '@/lib/types';
import { cn } from '@/lib/format';
import { Card } from '@/components/Card';
import { HeroPortrait } from '@/components/HeroPortrait';
import { ReportView } from '@/components/ReportView';

export function ScreenshotPanel() {
  const [result, setResult] = useState<ScreenshotResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    setError(null);
    setLoading(true);
    setResult(null);
    setPreview(URL.createObjectURL(file));
    try {
      const res = await api.screenshot(file);
      setResult(res);
    } catch (e) {
      setError((e as ApiError).message ?? 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card title="Screenshot Analyzer" icon={<ScanLine className="h-4 w-4 text-radiant" />} action={<span className="chip">hero detection → full report</span>}>
        <p className="mb-3 text-sm text-slate-400">
          Drop a draft or pick-screen screenshot. DraftMaster detects the hero portraits and runs the
          complete analysis automatically — no manual selection.
        </p>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (f) upload(f);
          }}
          className={cn(
            'flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center transition',
            dragging ? 'border-radiant bg-radiant/5' : 'border-base-600 bg-base-900/40',
          )}
        >
          <ImageUp className="h-8 w-8 text-slate-500" />
          <p className="text-sm text-slate-300">Drag &amp; drop a PNG or JPG here</p>
          <button type="button" onClick={() => inputRef.current?.click()} className="btn-ghost" disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Choose file
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
            }}
          />
          <p className="text-[11px] text-slate-500">Max 8 MB. Detection works best on the in-game draft bar.</p>
        </div>

        {error && <p className="mt-3 rounded-lg border border-dire/50 bg-dire/10 p-2.5 text-sm text-dire">{error}</p>}

        {(preview || result) && (
          <div className="mt-4 grid gap-4 lg:grid-cols-[300px_1fr]">
            {preview && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Uploaded draft" className="max-h-72 w-full rounded-lg border border-base-700 object-contain" />
            )}
            <div className="flex flex-col gap-3">
              {loading && (
                <p className="flex items-center gap-2 text-sm text-slate-300">
                  <Loader2 className="h-4 w-4 animate-spin text-radiant" /> Detecting heroes…
                </p>
              )}
              {result && (
                <>
                  <p className="text-sm text-slate-300">{result.note}</p>
                  {result.detection.detected.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {result.detection.detected.map((d) => (
                        <div key={`${d.hero_id}-${d.x}-${d.y}`} className="flex items-center gap-2 rounded-lg border border-base-700 bg-base-850/70 px-2 py-1.5">
                          <HeroPortrait icon={null} name={d.localized_name} size={32} />
                          <div className="leading-tight">
                            <p className="text-xs font-semibold text-white">{d.localized_name}</p>
                            <p className="text-[10px] text-slate-400">
                              {Math.round(d.confidence * 100)}% match
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </Card>

      {result?.report && (
        <div className="flex flex-col gap-3">
          <h2 className="section-title px-1">Auto-generated report from screenshot</h2>
          <ReportView report={result.report} />
        </div>
      )}
    </div>
  );
}
