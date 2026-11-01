import React, { useState } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  X,
  ArrowRight,
  Loader2,
  Shield,
  Layers,
  Layout,
  Type,
  FileCode,
  Image as ImageIcon,
  ExternalLink,
  Sparkles,
  HelpCircle,
  FileCheck2
} from 'lucide-react';
import { analyzeReferencePdf } from '../services/api';

export default function ReferenceSection({
  referenceStyle,
  referenceFile,
  referenceUrl,
  onReferenceAnalyzed,
  config,
  setConfig,
  onNext,
  onSkip
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [showFullPreview, setShowFullPreview] = useState(false);

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const handleFileChange = async (selectedFile) => {
    setErrorMsg('');
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setErrorMsg('Please upload a valid PDF document (.pdf).');
      return;
    }

    if (selectedFile.size > 15 * 1024 * 1024) {
      setErrorMsg('File size exceeds the 15MB upload limit.');
      return;
    }

    setIsUploading(true);

    try {
      const analysis = await analyzeReferencePdf(selectedFile);
      onReferenceAnalyzed(selectedFile, analysis);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to analyze reference PDF.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleRemove = () => {
    onReferenceAnalyzed(null, null);
    setErrorMsg('');
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      
      {/* Introduction Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700">
                Stage 1 of 3
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500 font-medium">Template &amp; Layout Cloning</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
              Reference PDF Analysis
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
              Upload an existing exam paper or worksheet. Our deterministic analyzer measures outer borders, header hierarchy, logo emblems, divider rules, and typography to precisely match the target layout.
            </p>
          </div>

          <button
            onClick={onSkip}
            className="self-start md:self-auto text-xs font-semibold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50/70 border border-slate-200 px-4 py-2.5 rounded-xl transition-colors shrink-0 flex items-center gap-1.5"
          >
            <span>Skip &amp; Use Clean Standard Layout</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg('')} className="text-rose-400 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Upload Zone & Selected File Card */}
      {!referenceFile ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`bg-white border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all ${
            dragOver ? 'border-indigo-500 bg-indigo-50/40' : 'border-slate-300/80 hover:border-slate-400'
          }`}
        >
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-4 shadow-xs">
            {isUploading ? (
              <Loader2 className="w-7 h-7 animate-spin" />
            ) : (
              <UploadCloud className="w-7 h-7" />
            )}
          </div>

          <h3 className="text-base font-bold text-slate-900">
            {isUploading ? 'Analyzing Document Geometry & Fonts...' : 'Drag and drop your reference PDF here'}
          </h3>
          <p className="text-xs text-slate-500 mt-1.5 mb-6 max-w-md mx-auto leading-relaxed">
            Upload school worksheets, university question papers, or board exams. Supports text-based and scanned PDFs up to 15MB.
          </p>

          <div className="flex items-center justify-center gap-3">
            <label className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl cursor-pointer shadow-xs transition-colors">
              <UploadCloud className="w-4 h-4" />
              <span>Browse PDF File</span>
              <input
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                disabled={isUploading}
                onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
              />
            </label>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-center justify-center gap-6 text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              100% Deterministic Parsing
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              Private Local Processing
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              Preserves Logos, Borders &amp; Fonts
            </span>
          </div>
        </div>
      ) : (
        /* Selected & Analyzed File Workspace */
        <div className="space-y-6">
          
          {/* Active File Header Bar */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
                <FileText className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900 truncate">
                    {referenceFile.name}
                  </h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                    Analyzed
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {formatFileSize(referenceFile.size)} · Uploaded and measured
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
              <label className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 cursor-pointer transition-colors">
                <span>Replace File</span>
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
                />
              </label>

              <button
                onClick={handleRemove}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 transition-colors flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Remove</span>
              </button>
            </div>
          </div>

          {/* Scanned Document Alert if Applicable */}
          {referenceStyle?.is_scanned && (
            <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-amber-950">Scanned / Image-Based Worksheet Detected</p>
                <p className="text-amber-800 mt-0.5 leading-relaxed">
                  This document contains scanned image pages. The generator will preserve the original background template, outer border, and graphic logos directly while overlaying new crisp question text.
                </p>
              </div>
            </div>
          )}

          {/* Extracted Intelligence Chips & Geometry Panel */}
          {referenceStyle && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-5">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider text-indigo-700">
                  Extracted Document Geometry &amp; Typography
                </h4>
                <span className="text-[11px] text-slate-400">
                  Ref ID: <span className="mono-font">{referenceStyle.reference_id?.slice(0, 8)}...</span>
                </span>
              </div>

              {/* Compact Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Page Count</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5">
                    {referenceStyle.page_count} {referenceStyle.page_count === 1 ? 'Page' : 'Pages'}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {referenceStyle.is_scanned ? 'Image scans' : 'Text selectable'}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Dimensions</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5">
                    {referenceStyle.page_size}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5 mono-font">
                    {referenceStyle.page_dimensions?.width_pt?.toFixed(0)} × {referenceStyle.page_dimensions?.height_pt?.toFixed(0)} pt
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Primary Font</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5 truncate">
                    {referenceStyle.primary_font || 'Helvetica'}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {referenceStyle.primary_font_size ? `${referenceStyle.primary_font_size} pt body` : 'Standard'}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Doc Layout Type</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5 capitalize">
                    {referenceStyle.document_type || 'Standard Exam'}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {referenceStyle.document_type === 'worksheet' ? 'Centered school title' : 'University header'}
                  </p>
                </div>
              </div>

              {/* Detected Layout Features Pills */}
              <div className="pt-2 border-t border-slate-100">
                <p className="text-[11px] font-semibold text-slate-600 mb-2.5">
                  Preserved Layout Elements:
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${
                      referenceStyle.has_page_border
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Outer Page Border: {referenceStyle.has_page_border ? 'Enclosed' : 'None'}</span>
                  </span>

                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${
                      referenceStyle.has_header_divider
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Header Rule: {referenceStyle.has_header_divider ? 'Detected' : 'None'}</span>
                  </span>

                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${
                      referenceStyle.image_count > 0
                        ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    <span>Logos / Emblems: {referenceStyle.image_count || 0} preserved</span>
                  </span>

                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${
                      referenceStyle.has_running_header
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Running Header: {referenceStyle.has_running_header ? 'Multi-page' : 'Single'}</span>
                  </span>
                </div>
              </div>

              {/* Reference Header preview lines if present */}
              {referenceStyle.header_lines?.length > 0 && (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Detected Header Text
                  </p>
                  {referenceStyle.header_lines.slice(0, 3).map((line, idx) => (
                    <p key={idx} className="font-semibold text-slate-800 truncate">
                      {line.text}
                    </p>
                  ))}
                </div>
              )}

              {/* Collapsible PDF Previewer */}
              {referenceUrl && (
                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <button
                      onClick={() => setShowFullPreview(!showFullPreview)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1.5"
                    >
                      <Layout className="w-3.5 h-3.5" />
                      <span>{showFullPreview ? 'Hide PDF Preview' : 'Show PDF Preview'}</span>
                    </button>

                    <a
                      href={referenceUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-slate-500 hover:text-indigo-600 flex items-center gap-1"
                    >
                      <span>Open in new tab</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  {showFullPreview && (
                    <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-100 h-[480px]">
                      <iframe
                        src={`${referenceUrl}#toolbar=0&navpanes=0`}
                        title="Reference PDF Preview"
                        className="w-full h-full"
                      />
                    </div>
                  )}
                </div>
              )}

            </div>
          )}

          {/* Action Row */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={onSkip}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              Skip Reference
            </button>

            <button
              onClick={onNext}
              className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
            >
              <span>Continue to Enter Questions</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </div>
      )}

    </div>
  );
}
