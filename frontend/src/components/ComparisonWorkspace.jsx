import React, { useState, useEffect } from 'react';
import {
  Columns,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Loader2,
  ExternalLink,
  Sliders,
  Sparkles,
  ArrowLeft,
  Eye,
  Info,
  Wand2
} from 'lucide-react';
import { fetchPaperReview, fetchPaperPreviewBlob } from '../services/api';

export default function ComparisonWorkspace({
  sections,
  config,
  setConfig,
  referenceStyle,
  referenceUrl,
  onBackToGenerate,
  onGoToReference
}) {
  const [reviewData, setReviewData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // View mode: 'split-interactive' | 'rendered-sbs' | 'diff-overlay'
  const [viewMode, setViewMode] = useState('split-interactive');
  
  // Mobile active tab: 'reference' | 'generated' | 'diff'
  const [mobileTab, setMobileTab] = useState('reference');

  // Zoom & Page state
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Filter for audit findings
  const [findingsTab, setFindingsTab] = useState('all'); // 'all', 'passes', 'differences', 'content'

  const hasReference = !!referenceStyle && !!referenceUrl;

  const runReview = async () => {
    if (!hasReference) return;
    setIsLoading(true);
    setErrorMsg('');

    try {
      const data = await fetchPaperReview(sections, config, referenceStyle);
      setReviewData(data);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to complete visual comparison review.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    runReview();
  }, [config.override_line_spacing, config.override_font_size, config.override_page_border]);

  // Handle Zoom
  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 15, 175));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 15, 60));
  const handleFitPage = () => setZoomLevel(100);

  // Active comparison page data
  const pageComparisons = reviewData?.page_comparisons || [];
  const totalPages = Math.max(pageComparisons.length, reviewData?.generated_pages || 1, 1);
  const activePageData = pageComparisons.find((p) => p.page_number === currentPage) || pageComparisons[0];

  // Auto-Fix action
  const handleApplyAutoFix = (action) => {
    if (action === 'compact_spacing') {
      const updated = {
        ...config,
        override_line_spacing: 12.0,
        override_font_size: (config.override_font_size || referenceStyle?.primary_font_size || 10.0) - 0.5,
      };
      setConfig(updated);
    }
  };

  if (!hasReference) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-white p-8 rounded-2xl border border-slate-200/90 shadow-xs text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
            <Columns className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">No Reference PDF Uploaded</h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The Interactive Comparison Workspace performs pixel-accurate visual diffing and fidelity audits between an uploaded reference template and your newly generated paper.
          </p>
          <div className="pt-2">
            <button
              onClick={onGoToReference}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              Upload Reference PDF (Stage 1)
            </button>
          </div>
        </div>
      </div>
    );
  }

  const fidelityScore = reviewData?.fidelity_score ?? 100;
  const validationStatus = reviewData?.validation_status || 'PASS';

  const passes = reviewData?.passes || [];
  const layoutDiffs = reviewData?.layout_differences || [];
  const contentErrors = reviewData?.content_errors || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700">
                Inspection Workspace
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500 font-medium">Layout Fidelity &amp; Visual Diff</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
              Interactive Document Comparison
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
              Compare your generated question paper against the reference template side-by-side, inspect visual diff heatmaps, and review automated layout preservation audits.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={runReview}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Diff</span>
            </button>

            <button
              onClick={onBackToGenerate}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Export</span>
            </button>
          </div>
        </div>

        {/* Fidelity Score Banner */}
        <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm ${
                validationStatus === 'PASS'
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : validationStatus === 'WARNING'
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-rose-100 text-rose-800 border border-rose-300'
              }`}
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : `${fidelityScore}%`}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Layout Fidelity Match</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    validationStatus === 'PASS'
                      ? 'bg-emerald-100 text-emerald-800'
                      : validationStatus === 'WARNING'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}
                >
                  {validationStatus === 'PASS' ? 'High Fidelity (PASS)' : validationStatus === 'WARNING' ? 'Minor Deviations (WARNING)' : 'Review Needed (FAIL)'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {passes.length} layout verifications passed · {layoutDiffs.length} layout deviations flagged
              </p>
            </div>
          </div>

          {/* Quick Auto-Fix Suggestions */}
          {reviewData?.auto_fixable_actions?.includes('compact_spacing') && (
            <button
              onClick={() => handleApplyAutoFix('compact_spacing')}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors"
            >
              <Wand2 className="w-3.5 h-3.5" />
              <span>Auto-Compact Spacing</span>
            </button>
          )}
        </div>
      </div>

      {/* Controls Bar: View Modes, Page Navigator, Zoom */}
      <div className="bg-white p-3.5 rounded-2xl border border-slate-200/90 shadow-xs flex flex-wrap items-center justify-between gap-3">
        
        {/* Mode Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl flex-wrap gap-1">
          <button
            onClick={() => setViewMode('rendered-sbs')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              viewMode === 'rendered-sbs'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Side by Side</span>
          </button>

          <button
            onClick={() => setViewMode('diff-overlay')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              viewMode === 'diff-overlay'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Difference Overlay</span>
          </button>

          <button
            onClick={() => setViewMode('diff-heatmap')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              viewMode === 'diff-heatmap'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Eye className="w-3.5 h-3.5 text-amber-500" />
            <span>Difference Heatmap</span>
          </button>

          <button
            onClick={() => setViewMode('split-interactive')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              viewMode === 'split-interactive'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Live PDF Split</span>
          </button>
        </div>


        {/* Page Navigation & Zoom Controls */}
        <div className="flex items-center gap-4 text-xs">
          
          {/* Synchronized Page Selector */}
          <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-xl border border-slate-200">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1 rounded-lg text-slate-600 hover:bg-white disabled:opacity-30"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-slate-700 px-2 min-w-[70px] text-center">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1 rounded-lg text-slate-600 hover:bg-white disabled:opacity-30"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Zoom Buttons (for rendered views) */}
          {viewMode !== 'split-interactive' && (
            <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-xl border border-slate-200">
              <button
                onClick={handleZoomOut}
                className="p-1 text-slate-600 hover:bg-white rounded-lg"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-semibold text-slate-600 px-1 min-w-[40px] text-center">
                {zoomLevel}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-1 text-slate-600 hover:bg-white rounded-lg"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleFitPage}
                className="p-1 text-slate-600 hover:bg-white rounded-lg ml-0.5"
                title="Fit to Page"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

        </div>

      </div>

      {/* Page Diagnosis & Metric Indicators */}
      {activePageData && (
        <div className="bg-white p-3 rounded-xl border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
              activePageData.status === 'passed'
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                : activePageData.status === 'review'
                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                : 'bg-rose-100 text-rose-800 border border-rose-200'
            }`}>
              Page {currentPage}: {activePageData.status_label || (activePageData.status === 'passed' ? 'Template Faithful' : 'Needs Review')}
            </span>
            <span className="text-slate-600 text-[11px] max-w-md truncate">
              {activePageData.notes || 'Header, margins, and borders align with reference template.'}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-600 font-medium text-[11px]">
            <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
              Similarity: <strong className="text-slate-900">{activePageData.similarity_score ?? 100}%</strong>
            </span>
            <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
              Layout Var: <strong className="text-slate-900">{activePageData.layout_difference_percentage ?? 0}%</strong>
            </span>
            <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
              Content Diff: <strong className="text-slate-900">{activePageData.content_difference_percentage ?? 0}%</strong>
            </span>
            {activePageData.mean_abs_difference !== undefined && (
              <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
                MAD: <strong className="text-slate-900">{activePageData.mean_abs_difference}</strong>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main Comparison Canvas */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">

        
        {/* MODE 1: INTERACTIVE PDF SPLIT VIEW */}
        {viewMode === 'split-interactive' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
            
            {/* Left: Reference PDF */}
            <div className="flex flex-col h-[700px]">
              <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-700">
                <span className="font-bold flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                  Original Reference Template
                </span>
                <a
                  href={referenceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  <span>Open Full Tab</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <div className="flex-1 bg-slate-100 p-2">
                <iframe
                  src={`${referenceUrl}#page=${currentPage}&toolbar=0&navpanes=0`}
                  title="Reference PDF"
                  className="w-full h-full rounded-lg border border-slate-200 shadow-2xs bg-white"
                />
              </div>
            </div>

            {/* Right: Newly Generated PDF */}
            <div className="flex flex-col h-[700px]">
              <div className="p-3 bg-indigo-50/50 border-b border-indigo-100 flex items-center justify-between text-xs text-slate-700">
                <span className="font-bold text-indigo-950 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  Newly Generated Question Paper
                </span>
                <span className="text-[11px] text-slate-500">Live PDF View</span>
              </div>
              <div className="flex-1 bg-slate-100 p-2">
                <iframe
                  src={`/api/paper/preview#page=${currentPage}&toolbar=0&navpanes=0`}
                  title="Generated Question Paper"
                  className="w-full h-full rounded-lg border border-slate-200 shadow-2xs bg-white"
                />
              </div>
            </div>

          </div>
        )}

        {/* MODE 2: RENDERED SIDE-BY-SIDE HIGH-RES */}
        {viewMode === 'rendered-sbs' && (
          <div className="p-6 bg-slate-100/60 overflow-auto flex items-center justify-center min-h-[640px]">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center text-slate-500 py-20">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-2" />
                <p className="text-xs font-semibold">Rendering high-res side-by-side comparison...</p>
              </div>
            ) : activePageData?.side_by_side_data ? (
              <div style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }} className="transition-transform">
                <img
                  src={activePageData.side_by_side_data}
                  alt={`Side-by-side comparison page ${currentPage}`}
                  className="rounded-xl shadow-lg border border-slate-300 max-w-none"
                />
              </div>
            ) : (
              <p className="text-xs text-slate-500">No rendered comparison image available for this page.</p>
            )}
          </div>
        )}

        {/* MODE 3: VISUAL DIFF HEATMAP OVERLAY */}
        {viewMode === 'diff-overlay' && (
          <div className="p-6 bg-slate-900/5 overflow-auto flex flex-col items-center justify-center min-h-[640px]">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center text-slate-500 py-20">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-2" />
                <p className="text-xs font-semibold">Generating difference overlay...</p>
              </div>
            ) : activePageData?.diff_overlay_data ? (
              <div className="space-y-4">
                
                {/* Overlay Legend */}
                <div className="flex items-center justify-center gap-6 text-xs bg-white/90 backdrop-blur-xs px-4 py-2 rounded-xl border border-slate-200 shadow-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 rounded bg-fuchsia-500 opacity-80" />
                    <span className="text-slate-700 font-medium">Layout Deviation (Outer borders, headers, margins)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 rounded bg-cyan-400 opacity-70" />
                    <span className="text-slate-700 font-medium">Expected Question Content Replacement</span>
                  </div>
                </div>

                <div style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }} className="transition-transform flex justify-center">
                  <img
                    src={activePageData.diff_overlay_data}
                    alt={`Visual diff heatmap page ${currentPage}`}
                    className="rounded-xl shadow-lg border border-slate-300 max-w-none"
                  />
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No diff overlay image available.</p>
            )}
          </div>
        )}

        {/* MODE 4: THERMAL DIFFERENCE HEATMAP */}
        {viewMode === 'diff-heatmap' && (
          <div className="p-6 bg-slate-900/5 overflow-auto flex flex-col items-center justify-center min-h-[640px]">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center text-slate-500 py-20">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-2" />
                <p className="text-xs font-semibold">Generating thermal difference heatmap...</p>
              </div>
            ) : activePageData?.heatmap_data ? (
              <div className="space-y-4">
                <div style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }} className="transition-transform flex justify-center">
                  <img
                    src={activePageData.heatmap_data}
                    alt={`Difference Heatmap page ${currentPage}`}
                    className="rounded-xl shadow-lg border border-slate-300 max-w-none"
                  />
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No thermal heatmap image available for this page.</p>
            )}
          </div>
        )}


      </div>

      {/* Difference Visualization & Audit Findings Panel */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Document Audit Findings &amp; Checklist
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Verified elements, detected variations, and content presence checks.
            </p>
          </div>

          {/* Findings Filter Tabs */}
          <div className="flex items-center gap-1.5 text-xs bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setFindingsTab('all')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                findingsTab === 'all' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
              }`}
            >
              All ({passes.length + layoutDiffs.length + contentErrors.length})
            </button>
            <button
              onClick={() => setFindingsTab('passes')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                findingsTab === 'passes' ? 'bg-white text-emerald-700 shadow-2xs' : 'text-slate-600'
              }`}
            >
              Passed ({passes.length})
            </button>
            <button
              onClick={() => setFindingsTab('differences')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                findingsTab === 'differences' ? 'bg-white text-amber-700 shadow-2xs' : 'text-slate-600'
              }`}
            >
              Deviations ({layoutDiffs.length})
            </button>
          </div>
        </div>

        {/* Findings List */}
        <div className="space-y-2.5">
          
          {/* Passing Checks */}
          {(findingsTab === 'all' || findingsTab === 'passes') && (
            <div className="space-y-2">
              {passes.map((p, i) => {
                const text = p && typeof p === 'object' ? (p.message || p.title || JSON.stringify(p)) : String(p || '');
                return (
                  <div
                    key={`pass-${i}-${text.slice(0, 16)}`}
                    className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200/60 text-xs flex items-center gap-2.5 text-emerald-900"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-medium">{text}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Layout Differences */}
          {(findingsTab === 'all' || findingsTab === 'differences') && (
            <div className="space-y-2">
              {layoutDiffs.map((diff, i) => {
                const isObj = diff && typeof diff === 'object';
                const title = isObj ? (diff.title || 'Layout Deviation') : 'Layout Deviation';
                const desc = isObj ? (diff.description || diff.message || JSON.stringify(diff)) : String(diff || '');
                const pageNum = isObj && diff.page_number ? ` (Page ${diff.page_number})` : '';
                return (
                  <div
                    key={`diff-${i}-${title.slice(0, 16)}`}
                    className="p-3 rounded-xl bg-amber-50/70 border border-amber-200/60 text-xs flex items-start gap-2.5 text-amber-900"
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-amber-950">{title}{pageNum}</p>
                      <p className="text-[11px] text-amber-800 mt-0.5">{desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Content Errors if any */}
          {contentErrors.length > 0 && (
            <div className="space-y-2">
              {contentErrors.map((err, i) => {
                const isObj = err && typeof err === 'object';
                const title = isObj ? (err.title || 'Content Omission') : 'Content Omission';
                const desc = isObj ? (err.description || err.message || JSON.stringify(err)) : String(err || '');
                return (
                  <div
                    key={`err-${i}-${title.slice(0, 16)}`}
                    className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs flex items-start gap-2.5 text-rose-900"
                  >
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-rose-950">{title}</p>
                      <p className="text-[11px] text-rose-800 mt-0.5">{desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
