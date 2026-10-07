import { lazy, Suspense, useEffect, useState } from 'react';
import { AlertTriangle, ArrowDownToLine, ArrowRight, Box, Check, CheckCircle2, ChevronDown,
  Clock3, FileText, History, Layers3, LoaderCircle, Printer, RefreshCw, ShieldCheck, Sparkles, XCircle } from 'lucide-react';
import { NAMES, type Evidence, type Job, type Parameters, type Spec, type Template } from './types';

const Viewer = lazy(() => import('./Viewer'));

const DEFAULT: Spec = {
  template: 'enclosure', printer: 'bambu-a1', material: 'PLA', nozzle: .4,
  parameters: { width: 80, depth: 55, height: 28, wall: 2.4, clearance: .3, hole_diameter: 3.2,
    inner_diameter: 32, outer_diameter: 60, base_thickness: 4 },
};
const COMMON: [keyof Parameters, string, number, number][] = [
  ['width', 'Width (X)', 20, 400], ['depth', 'Depth (Y)', 20, 400], ['height', 'Height (Z)', 8, 400],
  ['wall', 'Wall thickness', .8, 12], ['clearance', 'Clearance', .05, 2], ['hole_diameter', 'Screw hole', 2, 10],
];
const ADAPTER: [keyof Parameters, string, number, number][] = [
  ['outer_diameter', 'Flange diameter', 20, 300], ['inner_diameter', 'Mating diameter', 4, 280],
  ['height', 'Height (Z)', 8, 400], ['wall', 'Neck wall', .8, 12],
  ['clearance', 'Radial clearance', .05, 2], ['base_thickness', 'Flange thickness', 1.2, 20],
];

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) {
    const detail = typeof result.detail === 'string' ? result.detail :
      Array.isArray(result.detail) ? result.detail.map((item: {msg: string}) => item.msg).join(' ') : 'Request failed.';
    throw new Error(detail);
  }
  return result;
}

export default function App() {
  const [spec, setSpec] = useState<Spec>(DEFAULT);
  const [brief, setBrief] = useState('Electronics enclosure 80 x 55 x 28 mm, wall 2.4 mm, clearance 0.3 mm, PLA.');
  const [job, setJob] = useState<Job>();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [tab, setTab] = useState<'validation' | 'evidence' | 'history'>('validation');
  const [busy, setBusy] = useState<'generate' | 'plan' | 'slice' | 'loading' | ''>('loading');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [slicer, setSlicer] = useState<{ available: boolean; name?: string }>({ available: false });
  const dirty = job ? JSON.stringify(spec) !== JSON.stringify(job.spec) : false;

  useEffect(() => {
    let active = true;
    Promise.all([api<Job[]>('/api/jobs'), api<{available: boolean; name?: string}>('/api/slicer')])
      .then(([history, capabilities]) => {
        if (!active) return;
        setJobs(history); setSlicer(capabilities);
        if (history[0]) { setJob(history[0]); setSpec(history[0].spec); setEvidence(history[0].evidence); }
        setBusy('');
      }).catch(reason => { if (active) { setError(reason.message); setBusy(''); } });
    return () => { active = false; };
  }, []);

  async function generate() {
    setBusy('generate'); setError(''); setNotice('');
    try {
      const result = await api<Job>('/api/jobs', spec);
      setJob(result); setSpec(result.spec); setEvidence(result.evidence);
      setJobs(previous => [result, ...previous].slice(0, 30)); setTab('validation');
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  async function applyBrief() {
    setBusy('plan'); setError('');
    try {
      const result = await api<{spec: Spec; evidence: Evidence[]; matched_parameters: string[]; questions: string[]}>('/api/plan', { brief, spec });
      setSpec(result.spec); setEvidence(result.evidence);
      setNotice(result.matched_parameters.length ? `Applied ${result.matched_parameters.length} parameters` : result.questions[0]);
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  async function slice() {
    if (!job) return;
    setBusy('slice'); setError('');
    try {
      const result = await api<Job>(`/api/jobs/${job.id}/slice`, {});
      setJob(result); setJobs(previous => previous.map(item => item.id === result.id ? result : item));
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  function selectJob(selected: Job) {
    setJob(selected); setSpec(selected.spec); setEvidence(selected.evidence); setError(''); setNotice('');
  }

  return <main className="app">
    <header className="app-header">
      <a className="brand" href="/" aria-label="PrintReady home"><Box size={30} strokeWidth={1.8} /><strong>PrintReady</strong></a>
      <span className="header-divider" />
      <h1>{NAMES[spec.template]}</h1>
      <span className={`save-state ${dirty ? 'pending' : ''}`}><i />{dirty ? 'Changes not generated' : job ? 'Saved locally' : 'New design'}</span>
      <details className="export-menu">
        <summary aria-disabled={!job || dirty}><ArrowDownToLine size={17} /> Export <ChevronDown size={16} /></summary>
        <div className="export-options">
          {job && !dirty ? Object.entries(job.artifacts).filter(([name]) => name !== 'preview.glb').map(([name, artifact]) =>
            <a key={name} href={artifact.url} download><FileText size={15} />{name === 'model.3mf' ? 'Geometry 3MF' : name}</a>) : <span>Generate the current design first</span>}
        </div>
      </details>
    </header>

    {error && <div role="alert" className="error-banner"><XCircle size={18} /><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>Close</button></div>}

    <div className="workspace">
      <aside className="configuration" aria-label="Design parameters">
        <div className="template-tabs" role="tablist" aria-label="Part template">
          {(['enclosure', 'bracket', 'adapter'] as Template[]).map(template =>
            <button key={template} role="tab" aria-selected={spec.template === template} disabled={!!busy}
              onClick={() => { setSpec({ ...spec, template }); setNotice(''); }}>
              {template === 'enclosure' ? <Box size={20} /> : template === 'bracket' ? <Layers3 size={20} /> : <RefreshCw size={20} />}
              {template[0].toUpperCase() + template.slice(1)}
            </button>)}
        </div>

        <div className="sidebar-content">
          <div className="section-title"><h2>Project brief</h2><span className="subtle">Local parser</span></div>
          <textarea aria-label="Project brief" value={brief} maxLength={1500} onChange={event => setBrief(event.target.value)} />
          <div className="brief-actions"><span>{brief.length}/1500</span><button className="text-action" disabled={!!busy || !brief.trim()} onClick={applyBrief} title="Apply explicit dimensions from brief"><Sparkles size={14} /> Apply dimensions</button></div>
          {notice && <p className="notice" role="status">{notice}</p>}

          <h2 className="dimensions-title">Dimensions <span>(mm)</span></h2>
          <div className="parameter-list">
            {(spec.template === 'adapter' ? ADAPTER : COMMON).map(([key, label, min, max]) =>
              <label className="parameter" key={key}><span>{label}</span><div className="number-control">
                <input type="number" aria-label={label} min={min} max={max} step={key === 'clearance' ? .05 : .1}
                  value={spec.parameters[key]} disabled={!!busy} onChange={event => setSpec({ ...spec,
                    parameters: { ...spec.parameters, [key]: Number(event.target.value) } })} /><span>mm</span>
              </div></label>)}
          </div>

          <section className="print-settings">
            <h2>3D printing settings</h2>
            <label className="parameter"><span>Printer</span><select aria-label="Printer" value={spec.printer} disabled={!!busy} onChange={event => setSpec({ ...spec, printer: event.target.value as Spec['printer'] })}><option value="bambu-a1">Bambu Lab A1</option><option value="creality-k1c">Creality K1C</option></select></label>
            <label className="parameter"><span>Material</span><select aria-label="Material" value={spec.material} disabled={!!busy} onChange={event => setSpec({ ...spec, material: event.target.value as Spec['material'] })}><option>PLA</option><option>PETG</option><option>ABS</option></select></label>
            <label className="parameter"><span>Nozzle</span><select aria-label="Nozzle" value={spec.nozzle} disabled={!!busy} onChange={event => setSpec({ ...spec, nozzle: Number(event.target.value) as Spec['nozzle'] })}>{[.2, .4, .6, .8].map(value => <option key={value} value={value}>{value} mm</option>)}</select></label>
          </section>
          <button className="primary generate-button" onClick={generate} disabled={!!busy}>
            {busy === 'generate' ? <LoaderCircle className="spin" size={20} /> : <Box size={21} />}
            {busy === 'generate' ? 'Generating' : 'Generate model'}
          </button>
        </div>
      </aside>

      <Suspense fallback={<section className="viewport" aria-label="Loading model viewport" />}>
        <Viewer url={job?.artifacts['preview.glb']?.url} busy={busy === 'generate'} dimensions={job?.report.dimensions} />
      </Suspense>

      <aside className="inspector" aria-label="Model inspector">
        <div className="inspector-tabs" role="tablist" aria-label="Inspector view">
          {([{id: 'validation', label: 'Validation', icon: ShieldCheck}, {id: 'evidence', label: 'Evidence', icon: FileText}, {id: 'history', label: 'History', icon: History}] as const).map(item =>
            <button key={item.id} role="tab" aria-selected={tab === item.id} onClick={() => setTab(item.id)}><item.icon size={20} />{item.label}</button>)}
        </div>
        <div className="inspector-content">
          {tab === 'validation' && <>
            <h2>Geometry checks</h2>
            {dirty && <p className="inline-warning"><AlertTriangle size={16} />Previous generation</p>}
            {job ? <div className="check-list">{job.report.checks.map(check => <details className="check-row" key={check.id}>
              <summary><span>{check.status === 'pass' ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}{check.label}</span><strong className={check.status}>{check.status === 'pass' ? 'Pass' : check.status === 'fail' ? 'Fail' : 'Review'}</strong></summary>
              <p>{check.detail}</p>
            </details>)}</div> : <p className="empty-state">No validation report</p>}

            <section className="summary-section"><h2>Model summary</h2>
              <dl className="summary-list"><div><dt><Box size={17} />Components</dt><dd>{job?.report.components ?? '—'}</dd></div>
                <div><dt><Layers3 size={17} />Volume</dt><dd>{job ? `${(job.report.volume_mm3 / 1000).toFixed(1)} cm³` : '—'}</dd></div>
                <div><dt><Clock3 size={17} />Generation</dt><dd>{job ? `${(job.duration_ms / 1000).toFixed(1)} s` : '—'}</dd></div></dl>
              {job?.report.parts.map(part => <div className="part-row" key={part.name}><span>{part.name}</span><span>{part.dimensions.map(n => Math.round(n * 10) / 10).join(' × ')} mm</span></div>)}
            </section>

            <section className="slicer-section"><h2>Slicer</h2>
              <dl className="summary-list"><div><dt><Printer size={18} />Status</dt><dd className={job?.slicer.status === 'completed' ? 'pass' : 'warning'}>{busy === 'slice' ? 'Slicing' : job?.slicer.status === 'completed' ? 'Completed' : job?.slicer.status === 'failed' ? 'Failed' : 'Not run'}</dd></div></dl>
              <p className="slicer-name">{slicer.name || 'Local slicer not found'}</p>
              <div className="profile-label">{spec.printer === 'bambu-a1' ? 'Bambu Lab A1' : 'Creality K1C'}<span>{spec.nozzle} mm nozzle · {spec.material}</span></div>
              {job?.slicer.time && <p className="slice-metric">Estimated time <strong>{job.slicer.time}</strong></p>}
              {job?.slicer.filament_g !== undefined && <p className="slice-metric">Filament <strong>{job.slicer.filament_g.toFixed(1)} g</strong></p>}
              {job?.slicer.detail && <p className="inline-warning">{job.slicer.detail}</p>}
              <button className="secondary slice-button" onClick={slice} disabled={!!busy || !job || dirty || !slicer.available || job.report.status === 'failed'}>{busy === 'slice' ? <LoaderCircle className="spin" size={18} /> : <Printer size={18} />}Slice locally</button>
            </section>
            {job?.report.warnings.map(warning => <p className="inline-warning" key={warning}><AlertTriangle size={15} />{warning}</p>)}
          </>}

          {tab === 'evidence' && <><h2>Design evidence</h2>{evidence.length ? evidence.map(item => <article className="evidence-item" key={item.id}><span className="document-id">{item.id}</span><h3>{item.title}</h3><p>{item.text}</p><span className="subtle">Retrieval score {item.score}</span></article>) : <p className="empty-state">No matching evidence</p>}</>}

          {tab === 'history' && <><div className="section-title"><h2>Local history</h2><span className="subtle">{jobs.length} designs</span></div>{jobs.length ? jobs.map(item => <button className={`history-row ${item.id === job?.id ? 'selected' : ''}`} key={item.id} onClick={() => selectJob(item)} disabled={!!busy}><Box size={18} /><span><strong>{NAMES[item.spec.template]}</strong><small>{new Date(item.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</small></span><ArrowRight size={15} /></button>) : <p className="empty-state">No saved designs</p>}</>}
        </div>
      </aside>
    </div>
    <footer className="status-bar"><span>{busy ? <LoaderCircle size={17} className="spin" /> : <Check size={17} />}{busy === 'loading' ? 'Opening workspace' : busy === 'slice' ? 'Running local slicer' : dirty ? 'Parameters changed' : job ? 'Model generated' : 'Workspace ready'}</span><span className="footer-details">{job ? `${job.report.components} components · ${(job.report.volume_mm3 / 1000).toFixed(1)} cm³` : 'STEP · STL · 3MF · GLB'}</span><span className="footer-mode"><i />{job?.slicer.status === 'completed' && !dirty ? 'Slice report available' : 'Geometry workspace'}</span></footer>
  </main>;
}
