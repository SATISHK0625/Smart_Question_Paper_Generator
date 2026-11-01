import React, { useState } from 'react';
import {
  FileCode2,
  ListOrdered,
  Settings,
  Sparkles,
  Upload,
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Layers
} from 'lucide-react';
import { parseQuestions, importQuestionsFile } from '../services/api';
import { SAMPLE_PAPERS } from '../data/samplePapers';
import ManualSectionBuilder from './ManualSectionBuilder';

export default function QuestionWorkspace({
  rawText,
  setRawText,
  sections,
  setSections,
  config,
  setConfig,
  onNext,
  onBack
}) {
  const [activeTab, setActiveTab] = useState(sections.length > 0 ? 'structure' : 'structure'); // 'editor', 'structure', 'metadata'
  const [isParsing, setIsParsing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [showCheatsheet, setShowCheatsheet] = useState(false);

  const totalQuestions = sections.reduce((acc, s) => acc + (s.questions?.length || 0), 0);
  const totalMarks = sections.reduce((acc, s) => {
    const fromField = s.total_marks_available;
    const fromQuestions = (s.questions || []).reduce((qAcc, q) => qAcc + (parseFloat(q.marks) || 0), 0);
    return acc + (fromField || fromQuestions || 0);
  }, 0);

  // Auto-calculate stats from raw text
  const lineCount = rawText ? rawText.split('\n').length : 0;
  const wordCount = rawText ? rawText.trim().split(/\s+/).filter(Boolean).length : 0;

  // Handle parsing raw text
  const handleParse = async () => {
    if (!rawText.trim()) {
      setErrorMsg('Please enter or paste question text before parsing.');
      return;
    }

    setErrorMsg('');
    setSuccessMsg('');
    setIsParsing(true);

    try {
      const data = await parseQuestions(rawText);
      setSections(data.sections || []);

      if (data.extracted_instructions && data.extracted_instructions.length > 0) {
        setConfig(prev => ({
          ...prev,
          general_instructions: data.extracted_instructions
        }));
      }

      const qCount = (data.sections || []).reduce((acc, s) => acc + (s.questions?.length || 0), 0);
      setSuccessMsg(`Successfully parsed ${qCount} questions in ${data.sections.length} sections!`);
      setActiveTab('structure');
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to parse questions.');
    } finally {
      setIsParsing(false);
    }
  };

  // Handle file import (.txt or .docx)
  const handleFileUpload = async (file) => {
    setErrorMsg('');
    setSuccessMsg('');
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();
    if (!['txt', 'docx'].includes(ext)) {
      setErrorMsg('Please upload a .txt or .docx file.');
      return;
    }

    setIsImporting(true);
    try {
      const data = await importQuestionsFile(file);
      setRawText(data.raw_text);
      setSuccessMsg(`Imported text from ${file.name}. Click "Parse Questions" to build sections.`);
    } catch (err) {
      setErrorMsg(err.detail || err.message || 'Failed to import document.');
    } finally {
      setIsImporting(false);
    }
  };

  // Load sample paper presets
  const loadSample = (key) => {
    const sample = SAMPLE_PAPERS[key];
    if (sample) {
      setRawText(sample.rawText);
      setConfig(prev => ({
        ...prev,
        institution_name: sample.institution || prev.institution_name,
        department: sample.department || prev.department,
        exam_name: sample.exam || prev.exam_name,
        subject_name: sample.subject || prev.subject_name,
        subject_code: sample.code || prev.subject_code,
        semester_class: sample.semester || prev.semester_class,
        duration: sample.duration || prev.duration,
        maximum_marks: sample.maxMarks || prev.maximum_marks,
        general_instructions: sample.instructions || prev.general_instructions
      }));
      setSuccessMsg(`Loaded sample paper: ${sample.title}`);
    }
  };

  const handleConfigChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleAddInstruction = () => {
    setConfig(prev => ({
      ...prev,
      general_instructions: [...(prev.general_instructions || []), '']
    }));
  };

  const handleUpdateInstruction = (index, value) => {
    setConfig(prev => {
      const updated = [...(prev.general_instructions || [])];
      updated[index] = value;
      return { ...prev, general_instructions: updated };
    });
  };

  const handleRemoveInstruction = (index) => {
    setConfig(prev => ({
      ...prev,
      general_instructions: (prev.general_instructions || []).filter((_, i) => i !== index)
    }));
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700">
                Stage 2 of 3
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500 font-medium">Question Composition &amp; Hierarchy</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
              Enter Questions
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
              Build sections and questions in the visual editor, or paste raw text for deterministic parsing. Question types, marks, and options are preserved through PDF generation.
            </p>
          </div>

          {/* Preset Samples */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <span className="text-xs font-semibold text-slate-500">Presets:</span>
            <button
              onClick={() => loadSample('cs')}
              className="px-2.5 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>CS: Data Structures</span>
            </button>
            <button
              onClick={() => loadSample('math')}
              className="px-2.5 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Engineering Math</span>
            </button>
          </div>
        </div>

        {/* Workspace Mode Tabs */}
        <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-100 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab('editor')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === 'editor'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <FileCode2 className="w-4 h-4" />
            <span>Raw Text Editor</span>
            {lineCount > 0 && (
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeTab === 'editor' ? 'bg-white/20' : 'bg-slate-200'}`}>
                {lineCount} lines
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('structure')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === 'structure'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Manual Section Builder</span>
            {totalQuestions > 0 && (
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeTab === 'structure' ? 'bg-white/20' : 'bg-slate-200'}`}>
                {totalQuestions} Qs
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('metadata')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === 'metadata'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>Exam Details &amp; Metadata</span>
            {config.subject_name && (
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeTab === 'metadata' ? 'bg-white/20' : 'bg-slate-200'}`}>
                Set
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg('')} className="text-rose-400 hover:text-rose-700">×</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span className="font-medium">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg('')} className="text-emerald-400 hover:text-emerald-700">×</button>
        </div>
      )}

      {/* TAB 1: RAW TEXT EDITOR */}
      {activeTab === 'editor' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">
            
            {/* Toolbar */}
            <div className="p-3 bg-slate-50 border-b border-slate-200/90 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 cursor-pointer shadow-2xs transition-colors">
                  <Upload className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{isImporting ? 'Importing...' : 'Import .TXT / .DOCX'}</span>
                  <input
                    type="file"
                    accept=".txt,.docx"
                    className="hidden"
                    disabled={isImporting}
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  />
                </label>

                <button
                  onClick={() => setShowCheatsheet(!showCheatsheet)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-slate-600 hover:text-indigo-600 text-xs font-medium transition-colors"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>{showCheatsheet ? 'Hide Format Guide' : 'Format Examples'}</span>
                </button>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>{wordCount} words</span>
                <span>·</span>
                <span>{lineCount} lines</span>
                <button
                  onClick={handleParse}
                  disabled={isParsing || !rawText.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-xs disabled:opacity-50 transition-colors"
                >
                  {isParsing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  <span>Parse into Structure</span>
                </button>
              </div>
            </div>

            {/* Collapsible Format Cheatsheet */}
            {showCheatsheet && (
              <div className="p-4 bg-indigo-50/50 border-b border-indigo-100 text-xs text-slate-700 space-y-2">
                <p className="font-bold text-indigo-950">Supported Question Paper Syntax:</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
                  <div className="p-2.5 bg-white rounded-lg border border-indigo-100 font-mono">
                    <p className="font-bold text-indigo-900 mb-1">Section Titles:</p>
                    <p className="text-slate-600">PART A — All Questions</p>
                    <p className="text-slate-600">SECTION 1: THEORY</p>
                    <p className="text-slate-600">### UNIT II</p>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-indigo-100 font-mono">
                    <p className="font-bold text-indigo-900 mb-1">Marks Formats:</p>
                    <p className="text-slate-600">1. Define Big-O. (2 marks)</p>
                    <p className="text-slate-600">2. Explain DFS. [5 marks]</p>
                    <p className="text-slate-600">3. Solve ODE. (10M)</p>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-indigo-100 font-mono">
                    <p className="font-bold text-indigo-900 mb-1">Sub-questions &amp; Choices:</p>
                    <p className="text-slate-600">(a) Define AVL tree. (4M)</p>
                    <p className="text-slate-600">(b) Insert elements. (6M)</p>
                    <p className="text-slate-600">— OR —</p>
                  </div>
                </div>
              </div>
            )}

            {/* Textarea */}
            <div className="p-4">
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste exam questions here... e.g.

PART A — Answer all questions. Each carries 2 marks.

1. What is the difference between a process and a thread? (2 marks)
2. State the four necessary conditions for deadlock. (2 marks)

PART B — Answer any three questions.

3. Explain Dijkstra's shortest path algorithm with an example. (10 marks)
4. Describe virtual memory and demand paging mechanisms. (10 marks)"
                rows={18}
                className="w-full text-xs sm:text-sm font-mono text-slate-800 placeholder-slate-400 bg-transparent resize-y focus:outline-none leading-relaxed"
              />
            </div>

            {/* Bottom Parser Action Bar */}
            <div className="p-4 bg-slate-50 border-t border-slate-200/90 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Wording is never altered. Parsing groups text into deterministic sections and mark allocations.
              </span>

              <button
                onClick={handleParse}
                disabled={isParsing || !rawText.trim()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors"
              >
                {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                <span>Parse Questions &amp; Open Structure →</span>
              </button>
            </div>

          </div>
        </div>
      )}

      {/* TAB 2: MANUAL SECTION BUILDER */}
      {activeTab === 'structure' && (
        <ManualSectionBuilder
          sections={sections}
          setSections={setSections}
          config={config}
          setConfig={setConfig}
          onProceedToGenerate={onNext}
          onBackToReference={onBack}
        />
      )}

      {/* TAB 3: EXAM METADATA & CONFIG */}
      {activeTab === 'metadata' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-indigo-700">
              Exam Details &amp; Heading Banner
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Specify institution and subject details. Any blank fields will be gracefully omitted.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Institution / School Name
              </label>
              <input
                type="text"
                value={config.institution_name || ''}
                onChange={(e) => handleConfigChange('institution_name', e.target.value)}
                placeholder="e.g. Metropolitan Institute of Technology"
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department / Faculty
              </label>
              <input
                type="text"
                value={config.department || ''}
                onChange={(e) => handleConfigChange('department', e.target.value)}
                placeholder="e.g. Department of Computer Science"
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Examination Title
              </label>
              <input
                type="text"
                value={config.exam_name || ''}
                onChange={(e) => handleConfigChange('exam_name', e.target.value)}
                placeholder="e.g. Mid-Term Assessment — Autumn 2026"
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Subject Name
              </label>
              <input
                type="text"
                value={config.subject_name || ''}
                onChange={(e) => handleConfigChange('subject_name', e.target.value)}
                placeholder="e.g. Data Structures and Algorithms"
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-bold"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Subject Code
                </label>
                <input
                  type="text"
                  value={config.subject_code || ''}
                  onChange={(e) => handleConfigChange('subject_code', e.target.value)}
                  placeholder="CS201"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Class / Semester
                </label>
                <input
                  type="text"
                  value={config.semester_class || ''}
                  onChange={(e) => handleConfigChange('semester_class', e.target.value)}
                  placeholder="Semester 4"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Duration
                </label>
                <input
                  type="text"
                  value={config.duration || ''}
                  onChange={(e) => handleConfigChange('duration', e.target.value)}
                  placeholder="3 Hours"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Maximum Marks
                </label>
                <input
                  type="number"
                  value={config.maximum_marks ?? ''}
                  onChange={(e) => handleConfigChange('maximum_marks', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="100"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* General Instructions list */}
          <div className="pt-4 border-t border-slate-100 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                General Instructions
              </span>
              <button
                onClick={handleAddInstruction}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Instruction</span>
              </button>
            </div>

            {config.general_instructions?.map((inst, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 w-5">{i + 1}.</span>
                <input
                  type="text"
                  value={inst}
                  onChange={(e) => handleUpdateInstruction(i, e.target.value)}
                  placeholder="e.g. Draw neat diagrams wherever necessary."
                  className="flex-1 text-xs px-3 py-2 rounded-xl border border-slate-200"
                />
                <button
                  onClick={() => handleRemoveInstruction(i)}
                  className="text-slate-400 hover:text-rose-600"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

        </div>
      )}

      {/* Navigation Footer */}
      {activeTab !== 'structure' && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Reference</span>
          </button>

          <button
            onClick={onNext}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
          >
            <span>Continue to Generate &amp; Review</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

    </div>
  );
}
