import React from 'react';
import {
  FileText,
  Upload,
  FileCode2,
  CheckCircle2,
  FileCheck,
  Columns,
  PlusCircle,
  ChevronRight,
  Database,
  X
} from 'lucide-react';

export default function Sidebar({
  currentView,
  setCurrentView,
  referenceStyle,
  referenceFile,
  sections,
  config,
  previewGenerated,
  backendHealth,
  onReset,
  onCheckHealth,
  isMobileOpen,
  setIsMobileOpen
}) {
  const isHealthy = backendHealth?.status === 'healthy';
  const totalQuestions = sections.reduce((acc, s) => acc + (s.questions?.length || 0), 0);

  const navItems = [
    {
      id: 'reference',
      stage: 'Stage 1',
      label: 'Reference PDF',
      sublabel: referenceFile ? `${referenceFile.name.slice(0, 18)}...` : 'Upload & style analysis',
      icon: Upload,
      isComplete: !!referenceStyle,
      badge: referenceStyle ? (referenceStyle.is_scanned ? 'Scanned' : 'Analyzed') : null
    },
    {
      id: 'questions',
      stage: 'Stage 2',
      label: 'Enter Questions',
      sublabel: totalQuestions > 0 ? `${totalQuestions} questions in ${sections.length} sections` : 'Editor & structure',
      icon: FileCode2,
      isComplete: totalQuestions > 0,
      badge: totalQuestions > 0 ? `${totalQuestions} Qs` : null
    },
    {
      id: 'bank',
      stage: 'Feature 3',
      label: 'Question Bank',
      sublabel: 'Reusable questions & repository',
      icon: Database,
      isComplete: true,
      badge: 'Local DB'
    },
    {
      id: 'generate',
      stage: 'Stage 3',
      label: 'Generate & Review',
      sublabel: previewGenerated ? 'PDF ready for export' : 'Preview & layout tuning',
      icon: FileCheck,
      isComplete: previewGenerated,
      badge: previewGenerated ? 'Ready' : null
    },
    {
      id: 'compare',
      stage: 'Workspace',
      label: 'Compare Documents',
      sublabel: 'Side-by-side & diff heatmap',
      icon: Columns,
      isComplete: previewGenerated && !!referenceStyle,
      badge: referenceStyle ? 'Active' : 'Optional'
    }
  ];


  const handleNavClick = (id) => {
    setCurrentView(id);
    if (setIsMobileOpen) setIsMobileOpen(false);
  };

  const content = (
    <div className="flex flex-col h-full bg-slate-900 text-slate-200 select-none border-r border-slate-800">
      
      {/* Brand Header */}
      <div className="p-5 flex items-center justify-between border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-950/50">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-white tracking-tight">Smart Paper</span>
              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-950 text-indigo-300 rounded border border-indigo-800/60">
                v1.2
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Layout-Driven Formatting Engine</p>
          </div>
        </div>

        {setIsMobileOpen && (
          <button
            onClick={() => setIsMobileOpen(false)}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* New Document Button */}
      <div className="p-4 border-b border-slate-800/60">
        <button
          onClick={onReset}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700/80 text-white text-xs font-semibold border border-slate-700/80 transition-all shadow-xs group"
        >
          <PlusCircle className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          <span>New Document</span>
        </button>
      </div>

      {/* Workflow Navigation */}
      <div className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Document Workflow
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs transition-all group ${
                isActive
                  ? 'bg-indigo-600 text-white font-medium shadow-sm shadow-indigo-950/40'
                  : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : item.isComplete
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-800 text-slate-400 group-hover:text-slate-200'
                }`}
              >
                {item.isComplete && !isActive ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-slate-800 text-slate-300 border border-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
                <p
                  className={`text-[11px] truncate mt-0.5 ${
                    isActive ? 'text-indigo-100' : 'text-slate-400'
                  }`}
                >
                  {item.sublabel}
                </p>
              </div>

              <ChevronRight
                className={`w-3.5 h-3.5 shrink-0 transition-transform ${
                  isActive ? 'opacity-100 translate-x-0.5 text-white' : 'opacity-0 -translate-x-1 group-hover:opacity-60 text-slate-400'
                }`}
              />
            </button>
          );
        })}
      </div>

      {/* Document Meta Summary */}
      <div className="p-4 mx-3 mb-3 rounded-xl bg-slate-800/40 border border-slate-800 text-[11px] space-y-2 text-slate-400">
        <div className="flex items-center justify-between">
          <span>Active Subject:</span>
          <span className="font-semibold text-slate-200 truncate max-w-[120px]">
            {config.subject_name || 'Untitled Exam'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Target Page:</span>
          <span className="font-semibold text-slate-200">{config.page_size || 'A4'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Border:</span>
          <span className="font-semibold text-slate-200">
            {config.override_page_border ?? referenceStyle?.has_page_border ? 'Enclosed' : 'None'}
          </span>
        </div>
      </div>

      {/* Backend Health Status Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 flex items-center justify-between text-xs">
        <button
          onClick={onCheckHealth}
          title="Click to re-check backend connection"
          className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
        >
          <span className="relative flex h-2 w-2">
            {isHealthy && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isHealthy ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            ></span>
          </span>
          <span className="text-[11px] font-medium text-slate-300">
            {isHealthy ? 'Backend Active' : 'Backend Offline'}
          </span>
        </button>

        <span className="text-[10px] text-slate-400 mono-font">127.0.0.1:8000</span>
      </div>

    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-64 lg:w-72 shrink-0 h-screen sticky top-0 z-30">
        {content}
      </aside>

      {/* Mobile Drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
            onClick={() => setIsMobileOpen(false)}
          />
          <div className="relative flex-1 flex flex-col max-w-xs w-full h-full z-10">
            {content}
          </div>
        </div>
      )}
    </>
  );
}
