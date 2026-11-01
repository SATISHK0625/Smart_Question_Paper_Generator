import React, { useState, useEffect } from 'react';
import {
  Download,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  FileText,
  ArrowLeft,
  ArrowRight,
  Loader2,
  ExternalLink,
  Columns,
  Sliders,
  Check,
  Eye,
  ShieldCheck,
  Sparkles,
  Layers
} from 'lucide-react';
import {
  fetchPaperPreviewBlob,
  downloadPaperPdf,
  fetchPaperOverview,
  downloadOverviewPdf,
  fetchQualityCheck
} from '../services/api';

export default function PreviewExportSection({
  sections,
  config,
  setConfig,
  referenceStyle,
  referenceUrl,
  onOpenCompare,
  onBack,
  onPreviewReady
}) {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [overviewData, setOverviewData] = useState(null);
  const [qualityReport, setQualityReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloadingPaper, setIsDownloadingPaper] = useState(false);
  const [isDownloadingOverview, setIsDownloadingOverview] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Fine-tuning values
  const [fontSize, setFontSize] = useState(config.override_font_size || referenceStyle?.primary_font_size || 10.0);
  const [marginPt, setMarginPt] = useState(config.override_margins?.left || referenceStyle?.margins?.left || 40.0);
  const [lineSpacing, setLineSpacing] = useState(config.override_line_spacing || 14.0);
  const [hasBorder, setHasBorder] = useState(config.override_page_border ?? (referenceStyle?.has_page_border || false));

  const loadPreview = async (customConfig = config) => {
    if (!sections || sections.length === 0) {
      setErrorMsg('No sections found. Please create sections and questions in the Manual Section Builder before generating preview.');
      return;
    }
    setIsLoading(true);
    setErrorMsg('');

    try {
      const blob = await fetchPaperPreviewBlob(sections, customConfig, referenceStyle);
      if (previewUrl) {
        window.URL.revokeObjectURL(previewUrl);
      }
      const newUrl = window.URL.createObjectURL(blob);
      setPreviewUrl(newUrl);
      if (onPreviewReady) onPreviewReady(true);

      const [ov, qr] = await Promise.all([
        fetchPaperOverview(sections, customConfig, referenceStyle),
        fetchQualityCheck(sections, customConfig, referenceStyle)
      ]);
      setOverviewData(ov);
      setQualityReport(qr);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to generate PDF preview.');
    } finally {
      setIsLoading(false);
    }
  };


  useEffect(() => {
    loadPreview(config);
    return () => {
      if (previewUrl) {
        window.URL.revokeObjectURL(previewUrl);
      }
    };
  }, []);

  const handleApplyTuning = () => {
    const updatedConfig = {
      ...config,
      override_font_size: parseFloat(fontSize) || null,
      override_margins: {
        top: parseFloat(marginPt) || 35.0,
        bottom: parseFloat(marginPt) || 35.0,
        left: parseFloat(marginPt) || 40.0,
        right: parseFloat(marginPt) || 40.0,
      },
      override_line_spacing: parseFloat(lineSpacing) || null,
      override_page_border: hasBorder
    };
    setConfig(updatedConfig);
    loadPreview(updatedConfig);
  };

  const handleDownloadPaper = async () => {
    setIsDownloadingPaper(true);
    try {
      await downloadPaperPdf(sections, config, referenceStyle);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to download question paper.');
    } finally {
      setIsDownloadingPaper(false);
    }
  };

  const handleDownloadOverview = async () => {
    setIsDownloadingOverview(true);
    try {
      await downloadOverviewPdf(sections, config, referenceStyle);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to download overview report.');
    } finally {
      setIsDownloadingOverview(false);
    }
  };

  const hasReference = !!referenceStyle;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700">
                Stage 3 of 3
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500 font-medium">Generation, Review &amp; Export</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
              Generate &amp; Review Question Paper
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
              Generate publication-ready PDF documents matching your reference template. Fine-tune typography spacing in real time and inspect detailed metrics.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={() => loadPreview(config)}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Re-Generate</span>
            </button>

            {hasReference && (
              <button
                onClick={onOpenCompare}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-colors shadow-2xs"
              >
                <Columns className="w-3.5 h-3.5" />
                <span>Compare with Reference</span>
              </button>
            )}

            <button
              onClick={handleDownloadPaper}
              disabled={isDownloadingPaper || isLoading || !previewUrl}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs disabled:opacity-50 transition-colors"
            >
              {isDownloadingPaper ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              <span>Download PDF</span>
            </button>
          </div>
        </div>

        {/* Reference Layout Status Banner */}
        <div className="mt-5 p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${hasReference ? 'bg-emerald-500' : 'bg-slate-400'}`} />
            <span className="font-semibold text-slate-700">Template Layout Mode:</span>
            <span className="text-slate-900 font-bold">
              {hasReference
                ? (referenceStyle.document_type === 'worksheet' ? 'Preserved Worksheet Template' : 'Cloned Reference Layout')
                : 'Standard Clean Layout'}
            </span>
          </div>

          <div className="flex items-center gap-4 text-slate-500 text-[11px]">
            <span>Page: <strong>{config.page_size}</strong></span>
            <span>Border: <strong>{config.override_page_border ?? referenceStyle?.has_page_border ? 'Yes' : 'No'}</strong></span>
            <span>Running Footer: <strong>Page X of Y</strong></span>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => loadPreview(config)}
            className="px-2.5 py-1 rounded bg-rose-100 text-rose-800 font-semibold hover:bg-rose-200"
          >
            Retry
          </button>
        </div>
      )}

      {/* Interactive Fine-Tuning Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
          <Sliders className="w-4 h-4 text-indigo-600" />
          <span>Interactive Fine-Tuning:</span>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Font Size:</span>
            <input
              type="number"
              min="8"
              max="14"
              step="0.5"
              value={fontSize}
              onChange={(e) => setFontSize(e.target.value)}
              className="w-16 px-2 py-1 text-center font-bold bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
            <span className="text-slate-400">pt</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Margins:</span>
            <input
              type="number"
              min="20"
              max="60"
              step="1"
              value={marginPt}
              onChange={(e) => setMarginPt(e.target.value)}
              className="w-16 px-2 py-1 text-center font-bold bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
            <span className="text-slate-400">pt</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Line Spacing:</span>
            <input
              type="number"
              min="10"
              max="22"
              step="0.5"
              value={lineSpacing}
              onChange={(e) => setLineSpacing(e.target.value)}
              className="w-16 px-2 py-1 text-center font-bold bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
            <span className="text-slate-400">pt</span>
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={hasBorder}
              onChange={(e) => setHasBorder(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
            />
            <span className="text-slate-700 font-semibold">Page Border</span>
          </label>

          <button
            onClick={handleApplyTuning}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply Adjustments</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Grid: PDF Viewer + Overview Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* PDF Preview Frame (8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden flex flex-col min-h-[680px]">
          <div className="p-3 bg-slate-50 border-b border-slate-200/90 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-bold text-slate-800">Generated PDF Document</span>
            </div>

            {previewUrl && (
              <a
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium"
              >
                <span>Open in Tab</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>

          <div className="flex-1 bg-slate-100/70 flex items-center justify-center p-3 relative">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center text-slate-500 py-24">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
                <p className="text-xs font-semibold text-slate-700">Rendering publication-ready PDF...</p>
                <p className="text-[11px] text-slate-400 mt-1">Measuring flowables &amp; calculating two-pass running footers</p>
              </div>
            ) : previewUrl ? (
              <iframe
                src={`${previewUrl}#toolbar=1&navpanes=0`}
                title="Question Paper Preview"
                className="w-full h-[680px] rounded-xl border border-slate-200 shadow-xs bg-white"
              />
            ) : null}
          </div>
        </div>

        {/* Metrics & Downloads Panel (4 cols) */}
        <div className="lg:col-span-4 space-y-5">
          
          {/* Document Metrics Card */}
          {overviewData && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider text-indigo-700">
                Document Metrics
              </h3>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-slate-400 font-bold uppercase text-[10px]">Total Questions</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5">{overviewData.total_questions_count}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{overviewData.total_sections_count} Section(s)</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-slate-400 font-bold uppercase text-[10px]">Total Marks</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5">
                    {overviewData.total_marks_sum ?? overviewData.total_marks ?? 0}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    Student: {overviewData.calculated_student_marks ?? overviewData.student_marks ?? overviewData.total_marks_sum ?? 0}
                  </p>
                </div>
              </div>

              {/* Sections Breakdown */}
              <div className="space-y-2 pt-1 border-t border-slate-100">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Sections Breakdown
                </p>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {overviewData.section_summaries.map((s, idx) => (
                    <div key={s.section_id || `sec-summary-${idx}`} className="p-2.5 rounded-xl bg-slate-50 text-xs flex items-center justify-between border border-slate-100">
                      <span className="font-semibold text-slate-800 truncate max-w-[150px]">{s.section_title}</span>
                      <span className="text-slate-500 font-medium shrink-0">{s.question_count} Qs · {s.total_marks_available ?? s.total_marks ?? 0}M</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Validation Warnings if any */}
              {overviewData.validation_issues?.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 space-y-2">
                  <p className="font-bold flex items-center gap-1.5 text-amber-950">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Audit Notes</span>
                  </p>
                  <div className="space-y-1.5">
                    {overviewData.validation_issues.map((iss, i) => {
                      const isObj = iss && typeof iss === 'object';
                      const message = isObj ? (iss.message || JSON.stringify(iss)) : String(iss || '');
                      const location = isObj && iss.location ? iss.location : null;
                      const severity = isObj && iss.severity ? iss.severity.toLowerCase() : 'warning';
                      const key = isObj && (iss.id || `${location || 'iss'}-${i}`) ? (iss.id || `${location || 'iss'}-${i}`) : `iss-${i}`;

                      return (
                        <div key={key} className="flex items-start gap-1.5 text-[11px] text-amber-900 leading-snug">
                          <span className="font-bold shrink-0">•</span>
                          <div className="flex-1">
                            {location && (
                              <span className="font-semibold text-amber-950 mr-1.5">
                                [{location}]
                              </span>
                            )}
                            <span>{message}</span>
                          </div>
                          {severity && (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider shrink-0 ${
                              severity === 'error'
                                ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                : severity === 'info'
                                ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                : 'bg-amber-100 text-amber-800 border border-amber-200'
                            }`}>
                              {severity}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Feature 2: Pre-Export Quality Assurance Checker Dashboard */}
          {qualityReport && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <ShieldCheck className={`w-4 h-4 ${qualityReport.can_export ? 'text-emerald-600' : 'text-rose-600'}`} />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Pre-Export Quality Assurance
                  </h3>
                </div>

                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  qualityReport.status === 'blocked'
                    ? 'bg-rose-100 text-rose-800 border border-rose-200'
                    : qualityReport.status === 'has_warnings'
                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                    : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                }`}>
                  {qualityReport.status === 'blocked' ? 'Export Blocked' : qualityReport.status === 'has_warnings' ? 'Needs Review' : 'Verified Ready'}
                </span>
              </div>

              {/* Status Banner */}
              <div className={`p-3 rounded-xl text-xs flex items-center justify-between gap-2 ${
                qualityReport.status === 'blocked'
                  ? 'bg-rose-50 border border-rose-200 text-rose-800'
                  : qualityReport.status === 'has_warnings'
                  ? 'bg-amber-50 border border-amber-200 text-amber-900'
                  : 'bg-emerald-50 border border-emerald-200 text-emerald-900'
              }`}>
                <div className="flex items-center gap-2">
                  {qualityReport.status === 'blocked' ? (
                    <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  )}
                  <span className="font-semibold text-[11px]">
                    {qualityReport.status === 'blocked'
                      ? `${qualityReport.error_count} blocking issue(s) detected. Fix errors to download.`
                      : qualityReport.status === 'has_warnings'
                      ? `${qualityReport.warning_count} layout/marks warning(s) found. Review before export.`
                      : 'All quality checks passed. Document is ready for export.'}
                  </span>
                </div>
              </div>

              {/* Metric Counters Grid */}
              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] text-slate-400 font-bold uppercase">Errors</span>
                  <span className={`text-base font-extrabold ${qualityReport.error_count > 0 ? 'text-rose-600' : 'text-slate-800'}`}>
                    {qualityReport.error_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] text-slate-400 font-bold uppercase">Warnings</span>
                  <span className={`text-base font-extrabold ${qualityReport.warning_count > 0 ? 'text-amber-600' : 'text-slate-800'}`}>
                    {qualityReport.warning_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] text-slate-400 font-bold uppercase">Questions</span>
                  <span className="text-base font-extrabold text-slate-800">
                    {qualityReport.total_questions}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] text-slate-400 font-bold uppercase">Marks</span>
                  <span className="text-base font-extrabold text-slate-800">
                    {qualityReport.total_marks}
                  </span>
                </div>
              </div>

              {/* Grouped Findings List */}
              {qualityReport.findings?.length > 0 && (
                <div className="space-y-2 pt-1 border-t border-slate-100">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Detailed Findings ({qualityReport.findings.length})
                  </p>
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {qualityReport.findings.map((f, fIdx) => (
                      <div
                        key={`finding-${fIdx}`}
                        className={`p-2.5 rounded-xl border text-xs space-y-1 ${
                          f.severity === 'error'
                            ? 'bg-rose-50/60 border-rose-200 text-rose-900'
                            : f.severity === 'warning'
                            ? 'bg-amber-50/60 border-amber-200 text-amber-900'
                            : 'bg-blue-50/60 border-blue-200 text-blue-900'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-[11px] leading-tight">
                            {f.location?.section && <strong className="mr-1">[{f.location.section}]</strong>}
                            {f.location?.question_number && <span className="mr-1">Q{f.location.question_number}:</span>}
                            {f.message}
                          </span>
                          <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase tracking-wider shrink-0 ${
                            f.severity === 'error'
                              ? 'bg-rose-200 text-rose-800'
                              : f.severity === 'warning'
                              ? 'bg-amber-200 text-amber-800'
                              : 'bg-blue-200 text-blue-800'
                          }`}>
                            {f.severity}
                          </span>
                        </div>
                        {f.suggested_action && (
                          <p className="text-[10px] text-slate-600 font-medium">
                            💡 <span className="underline">Fix</span>: {f.suggested_action}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Export Downloads Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider text-slate-700">
              Export Outputs
            </h3>

            {qualityReport && !qualityReport.can_export && (
              <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-[11px] flex items-center gap-1.5 font-medium">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-rose-600" />
                <span>PDF Download is disabled until all blocking quality errors are fixed.</span>
              </div>
            )}

            <button
              onClick={handleDownloadPaper}
              disabled={isDownloadingPaper || isLoading || !previewUrl || (qualityReport && !qualityReport.can_export)}
              className="w-full flex items-center justify-center gap-2 p-3 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isDownloadingPaper ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span>{qualityReport && !qualityReport.can_export ? 'Export Blocked (Fix Errors)' : 'Download Question Paper PDF'}</span>
            </button>

            <button
              onClick={handleDownloadOverview}
              disabled={isDownloadingOverview || isLoading}
              className="w-full flex items-center justify-center gap-2 p-2.5 text-xs font-semibold text-slate-700 hover:text-indigo-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors"
            >
              {isDownloadingOverview ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-indigo-600" />}
              <span>Download Standalone Overview Report PDF</span>
            </button>
          </div>


          {/* Link to Compare Workspace */}
          {hasReference && (
            <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-900 to-slate-900 text-white shadow-xs space-y-3">
              <div className="flex items-center gap-2">
                <Columns className="w-4 h-4 text-indigo-300" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-200">
                  Visual Fidelity Audit
                </h4>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Compare your generated document against the uploaded reference with side-by-side view and visual difference heatmap overlay.
              </p>
              <button
                onClick={onOpenCompare}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-white text-slate-900 text-xs font-bold hover:bg-slate-100 transition-colors"
              >
                <span>Open Interactive Comparison Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

        </div>

      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Question Editor</span>
        </button>

        {hasReference && (
          <button
            onClick={onOpenCompare}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
          >
            <span>Proceed to Visual Compare Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

    </div>
  );
}
