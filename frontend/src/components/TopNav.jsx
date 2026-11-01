import React from 'react';
import {
  Menu,
  Download,
  RefreshCw,
  Columns
} from 'lucide-react';

export default function TopNav({
  currentView,
  setCurrentView,
  referenceStyle,
  sections,
  previewGenerated,
  onReset,
  onDownloadPaper,
  isDownloading,
  onToggleMobile
}) {
  const titles = {
    reference: {
      title: 'Stage 1: Reference PDF Analysis',
      subtitle: 'Upload any exam paper or worksheet to clone layout, margins, and typography.'
    },
    questions: {
      title: 'Stage 2: Enter Questions & Structure',
      subtitle: 'Compose or import exam questions with section grouping, marks, and format validation.'
    },
    bank: {
      title: 'Feature 3: Reusable Question Bank',
      subtitle: 'Persistent question repository: search, filter, author, and clone questions into paper drafts.'
    },
    generate: {
      title: 'Stage 3: Generate, Fine-Tune & Export',
      subtitle: 'Preview publication-ready PDF, fine-tune geometry, and export.'
    },

    compare: {
      title: 'Interactive Comparison Workspace',
      subtitle: 'Pixel-accurate visual diff, layout verification, and fidelity audit.'
    }
  };

  const activeTitle = titles[currentView] || titles.reference;
  const totalQuestions = sections.reduce((acc, s) => acc + (s.questions?.length || 0), 0);

  // Status Badge calculation
  let statusBadge = {
    text: 'Draft Document',
    color: 'bg-slate-100 text-slate-700 border-slate-200'
  };
  if (previewGenerated) {
    statusBadge = {
      text: 'PDF Ready to Export',
      color: 'bg-emerald-50 text-emerald-700 border-emerald-200'
    };
  } else if (totalQuestions > 0) {
    statusBadge = {
      text: `${totalQuestions} Questions Parsed`,
      color: 'bg-indigo-50 text-indigo-700 border-indigo-200'
    };
  } else if (referenceStyle) {
    statusBadge = {
      text: 'Reference Analyzed',
      color: 'bg-blue-50 text-blue-700 border-blue-200'
    };
  }

  return (
    <header className="bg-white border-b border-slate-200/90 sticky top-0 z-20 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Left: Hamburger (mobile) + Page Title */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onToggleMobile}
            className="md:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight truncate">
                {activeTitle.title}
              </h1>
              <span
                className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${statusBadge.color}`}
              >
                {statusBadge.text}
              </span>
            </div>
            <p className="text-xs text-slate-500 truncate hidden lg:block">
              {activeTitle.subtitle}
            </p>
          </div>
        </div>

        {/* Right: Quick Contextual Actions */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          
          {/* Quick Compare Shortcut */}
          {currentView !== 'compare' && (
            <button
              onClick={() => setCurrentView('compare')}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50/60 border border-slate-200 rounded-xl transition-colors"
            >
              <Columns className="w-3.5 h-3.5 text-indigo-600" />
              <span>Compare View</span>
            </button>
          )}

          {/* Quick Download Button if Preview Exists */}
          {previewGenerated && (
            <button
              onClick={onDownloadPaper}
              disabled={isDownloading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Download PDF</span>
            </button>
          )}

          {/* Reset / New Paper Button */}
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
            title="Start new question paper"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset Draft</span>
          </button>

        </div>

      </div>
    </header>
  );
}
