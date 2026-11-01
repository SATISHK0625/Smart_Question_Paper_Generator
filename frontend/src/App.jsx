import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import ReferenceSection from './components/ReferenceSection';
import QuestionWorkspace from './components/QuestionWorkspace';
import PreviewExportSection from './components/PreviewExportSection';
import ComparisonWorkspace from './components/ComparisonWorkspace';
import QuestionBankSection from './components/QuestionBankSection';
import { checkHealth, downloadPaperPdf } from './services/api';

const DEFAULT_CONFIG = {
  institution_name: '',
  department: '',
  exam_name: '',
  subject_name: '',
  subject_code: '',
  semester_class: '',
  date_str: '',
  duration: '',
  maximum_marks: null,
  general_instructions: [],
  page_size: 'A4',
  header_style: 'auto',
  use_reference_header: true,
  show_page_numbers: false,
  overview_placement: 'none',

  // Layout fine-tuning overrides
  override_font_size: null,
  override_margins: null,
  override_line_spacing: null,
  override_page_border: null,
  override_heading_align: null,
  override_section_spacing: null,
  reference_id: null,
  reference_pdf_path: null
};

export default function App() {
  // Navigation view: 'reference' | 'questions' | 'generate' | 'compare'
  const [currentView, setCurrentView] = useState('reference');
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [backendHealth, setBackendHealth] = useState(null);

  // Workflow State
  const [referenceFile, setReferenceFile] = useState(null);
  const [referenceUrl, setReferenceUrl] = useState(null);
  const [referenceStyle, setReferenceStyle] = useState(null);
  const [rawText, setRawText] = useState('');
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [sections, setSections] = useState([]);
  const [previewGenerated, setPreviewGenerated] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Check backend health on boot
  const pingHealth = async () => {
    const res = await checkHealth();
    setBackendHealth(res);
  };

  useEffect(() => {
    pingHealth();
  }, []);

  const handleReset = () => {
    if (window.confirm('Start a new document? Unsaved changes will be cleared.')) {
      if (referenceUrl) {
        window.URL.revokeObjectURL(referenceUrl);
      }
      setReferenceFile(null);
      setReferenceUrl(null);
      setReferenceStyle(null);
      setRawText('');
      setConfig(DEFAULT_CONFIG);
      setSections([]);
      setPreviewGenerated(false);
      setCurrentView('reference');
    }
  };

  const handleReferenceAnalyzed = (file, analysis) => {
    setReferenceFile(file);
    if (file) {
      if (referenceUrl) window.URL.revokeObjectURL(referenceUrl);
      const url = window.URL.createObjectURL(file);
      setReferenceUrl(url);
    } else {
      if (referenceUrl) window.URL.revokeObjectURL(referenceUrl);
      setReferenceUrl(null);
    }
    setReferenceStyle(analysis);

    if (analysis) {
      setConfig((prev) => ({
        ...prev,
        page_size: analysis.page_size === 'Letter' ? 'Letter' : 'A4',
        show_page_numbers: analysis.has_page_numbers,
        use_reference_header: true,
        reference_id: analysis.reference_id || prev.reference_id,
        reference_pdf_path: analysis.reference_pdf_path || prev.reference_pdf_path,
        institution_name: analysis.header_lines?.[0]?.text || prev.institution_name,
        exam_name: analysis.header_lines?.[2]?.text || (analysis.header_lines?.[1]?.text || prev.exam_name),
      }));
    }
  };

  const handleDownloadPaper = async () => {
    if (sections.length === 0) return;
    setIsDownloading(true);
    try {
      await downloadPaperPdf(sections, config, referenceStyle);
    } catch (err) {
      alert(err.message || 'Failed to download PDF.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row text-slate-900 font-sans antialiased">
      
      {/* Professional Sidebar Shell */}
      <Sidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        referenceStyle={referenceStyle}
        referenceFile={referenceFile}
        sections={sections}
        config={config}
        previewGenerated={previewGenerated}
        backendHealth={backendHealth}
        onReset={handleReset}
        onCheckHealth={pingHealth}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      />

      {/* Main Content Workspace Column */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Navigation */}
        <TopNav
          currentView={currentView}
          setCurrentView={setCurrentView}
          referenceStyle={referenceStyle}
          sections={sections}
          previewGenerated={previewGenerated}
          onReset={handleReset}
          onDownloadPaper={handleDownloadPaper}
          isDownloading={isDownloading}
          onToggleMobile={() => setIsMobileOpen(true)}
        />

        {/* Dynamic Workspace Stage */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          
          {currentView === 'reference' && (
            <ReferenceSection
              referenceStyle={referenceStyle}
              referenceFile={referenceFile}
              referenceUrl={referenceUrl}
              onReferenceAnalyzed={handleReferenceAnalyzed}
              config={config}
              setConfig={setConfig}
              onNext={() => setCurrentView('questions')}
              onSkip={() => setCurrentView('questions')}
            />
          )}

          {currentView === 'questions' && (
            <QuestionWorkspace
              rawText={rawText}
              setRawText={setRawText}
              sections={sections}
              setSections={setSections}
              config={config}
              setConfig={setConfig}
              referenceStyle={referenceStyle}
              onNext={() => setCurrentView('generate')}
              onBack={() => setCurrentView('reference')}
            />
          )}

          {currentView === 'bank' && (
            <QuestionBankSection
              sections={sections}
              setSections={setSections}
              onNavigateToBuilder={() => setCurrentView('questions')}
            />
          )}

          {currentView === 'generate' && (
            <PreviewExportSection
              sections={sections}
              config={config}
              setConfig={setConfig}
              referenceStyle={referenceStyle}
              referenceUrl={referenceUrl}
              onOpenCompare={() => setCurrentView('compare')}
              onBack={() => setCurrentView('questions')}
              onPreviewReady={(ready) => setPreviewGenerated(ready)}
            />
          )}

          {currentView === 'compare' && (
            <ComparisonWorkspace
              sections={sections}
              config={config}
              setConfig={setConfig}
              referenceStyle={referenceStyle}
              referenceUrl={referenceUrl}
              onBackToGenerate={() => setCurrentView('generate')}
              onGoToReference={() => setCurrentView('reference')}
            />
          )}

        </main>

        {/* Subtle Workspace Footer */}
        <footer className="bg-white border-t border-slate-200/80 py-4 px-6 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>© 2026 Smart Paper · Deterministic Layout-Driven Formatting Engine</p>
          <p className="text-[11px] text-slate-400">100% Private Local Processing · Zero Paid APIs Required</p>
        </footer>

      </div>

    </div>
  );
}
