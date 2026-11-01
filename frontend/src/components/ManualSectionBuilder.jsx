import React, { useState, useMemo } from 'react';
import {
  Layers,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Hash,
  MoveUp,
  MoveDown,
  ArrowRight,
  ArrowLeft,
  Eye,
  Edit3,
  Image as ImageIcon,
  Shuffle,
  Upload,
  Columns,
  MapPin
} from 'lucide-react';
import {
  addSection,
  removeSection,
  moveSection,
  updateSection,
  addQuestion,
  removeQuestion,
  moveQuestion,
  updateQuestion,
  addOption,
  updateOption,
  removeOption,
  addSubQuestion,
  updateSubQuestion,
  removeSubQuestion,
  renumberQuestions,
  computeStats,
  validateSections
} from '../utils/sectionBuilderState';
import { MatchingEditor, ImageBasedEditor, DiagramIdentifyEditor } from './AdvancedQuestionEditors';

const QUESTION_TYPES = [
  { id: 'mixed', label: 'Mixed Types', badge: 'bg-slate-100 text-slate-700', desc: 'Allows any mix of question types in this section' },
  { id: 'mcq', label: 'Multiple Choice (MCQ)', badge: 'bg-blue-50 text-blue-700', desc: 'Questions with options (A, B, C, D)' },
  { id: 'short_answer', label: 'Short Answer', badge: 'bg-emerald-50 text-emerald-700', desc: 'Concise answers & definitions (1–3 marks)' },
  { id: 'long_answer', label: 'Long Answer', badge: 'bg-purple-50 text-purple-700', desc: 'In-depth explanations & derivations (4+ marks)' },
  { id: 'fill_in_the_blanks', label: 'Fill in the Blanks', badge: 'bg-amber-50 text-amber-700', desc: 'Sentence completion with blank lines (___)' },
  { id: 'true_false', label: 'True / False', badge: 'bg-rose-50 text-rose-700', desc: 'Binary verification statements' },
  { id: 'matching', label: 'Match the Following', badge: 'bg-teal-50 text-teal-700', desc: 'Column A & Column B pairing table' },
  { id: 'image_based', label: 'Image-Based Question', badge: 'bg-sky-50 text-sky-700', desc: 'Question with attached illustration/figure' },
  { id: 'diagram_identify', label: 'Identify Diagram Parts', badge: 'bg-indigo-50 text-indigo-700', desc: 'Diagram with numbered markers or blank callout lines' },
];

export default function ManualSectionBuilder({
  sections,
  setSections,
  config,
  onProceedToGenerate,
  onBackToReference
}) {
  const [collapsedSections, setCollapsedSections] = useState({});
  const [activeView, setActiveView] = useState('builder'); // 'builder' | 'review'

  const stats = useMemo(() => computeStats(sections), [sections]);
  const validationErrors = useMemo(() => validateSections(sections), [sections]);
  const hasBlockingErrors = validationErrors.length > 0;

  const toggleCollapse = (secId) => {
    setCollapsedSections(prev => ({ ...prev, [secId]: !prev[secId] }));
  };

  const handleAddSection = (qType = 'mixed') => {
    setSections(prev => addSection(prev, qType));
  };

  const handleRemoveSection = (secIdx) => {
    const sec = sections[secIdx];
    if (sec.questions?.length > 0) {
      if (!window.confirm(`Delete "${sec.title || `Section ${secIdx + 1}`}" and its ${sec.questions.length} questions?`)) {
        return;
      }
    }
    setSections(prev => removeSection(prev, secIdx));
  };

  const handleMoveSection = (secIdx, direction) => {
    setSections(prev => moveSection(prev, secIdx, direction));
  };

  const handleUpdateSection = (secIdx, field, value) => {
    setSections(prev => updateSection(prev, secIdx, field, value));
  };

  const handleAddQuestion = (secIdx, customType = null) => {
    setSections(prev => addQuestion(prev, secIdx, customType));
  };

  const handleRemoveQuestion = (secIdx, qIdx) => {
    setSections(prev => removeQuestion(prev, secIdx, qIdx));
  };

  const handleMoveQuestion = (secIdx, qIdx, direction) => {
    setSections(prev => moveQuestion(prev, secIdx, qIdx, direction));
  };

  const handleUpdateQuestion = (secIdx, qIdx, field, value) => {
    setSections(prev => updateQuestion(prev, secIdx, qIdx, field, value));
  };

  const handleAddOption = (secIdx, qIdx) => {
    setSections(prev => addOption(prev, secIdx, qIdx));
  };

  const handleUpdateOption = (secIdx, qIdx, optIdx, value) => {
    setSections(prev => updateOption(prev, secIdx, qIdx, optIdx, value));
  };

  const handleRemoveOption = (secIdx, qIdx, optIdx) => {
    setSections(prev => removeOption(prev, secIdx, qIdx, optIdx));
  };

  const handleAddSubQuestion = (secIdx, qIdx) => {
    setSections(prev => addSubQuestion(prev, secIdx, qIdx));
  };

  const handleUpdateSubQuestion = (secIdx, qIdx, sqIdx, field, value) => {
    setSections(prev => updateSubQuestion(prev, secIdx, qIdx, sqIdx, field, value));
  };

  const handleRemoveSubQuestion = (secIdx, qIdx, sqIdx) => {
    setSections(prev => removeSubQuestion(prev, secIdx, qIdx, sqIdx));
  };

  const handleRenumberAll = () => {
    setSections(prev => renumberQuestions(prev));
  };

  // --- Advanced Question Types Helpers ---
  const processImageFile = (file, secIdx, qIdx) => {
    if (!file.type.match(/^image\/(png|jpeg|jpg|webp)$/i)) {
      alert('Unsupported file format. Please upload a PNG, JPEG, or WebP image.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('Image file is too large. Maximum size allowed is 5MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      handleUpdateQuestion(secIdx, qIdx, 'image_base64', ev.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleImagePaste = (e, secIdx, qIdx) => {
    const clipboardData = e.clipboardData || window.clipboardData;
    if (!clipboardData) return;
    const items = clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          processImageFile(file, secIdx, qIdx);
          e.preventDefault();
          return;
        }
      }
    }
  };

  const handleImageFileInput = (e, secIdx, qIdx) => {
    const file = e.target.files?.[0];
    if (file) {
      processImageFile(file, secIdx, qIdx);
    }
  };

  const handleAddMatchingRow = (secIdx, qIdx) => {
    const q = sections[secIdx].questions[qIdx];
    const left = [...(q.matching_left || [])];
    const right = [...(q.matching_right || [])];
    const nextLeftKey = String.fromCharCode(65 + left.length);
    const nextRightNum = String(right.length + 1);
    left.push(`${nextLeftKey}. Item ${left.length + 1}`);
    right.push(`${nextRightNum}. Match ${right.length + 1}`);
    const answers = { ...(q.matching_answers || {}), [nextLeftKey]: nextRightNum };
    handleUpdateQuestion(secIdx, qIdx, 'matching_left', left);
    handleUpdateQuestion(secIdx, qIdx, 'matching_right', right);
    handleUpdateQuestion(secIdx, qIdx, 'matching_answers', answers);
  };

  const handleUpdateMatchingRow = (secIdx, qIdx, side, rowIdx, value) => {
    const q = sections[secIdx].questions[qIdx];
    if (side === 'left') {
      const left = [...(q.matching_left || [])];
      left[rowIdx] = value;
      handleUpdateQuestion(secIdx, qIdx, 'matching_left', left);
    } else {
      const right = [...(q.matching_right || [])];
      right[rowIdx] = value;
      handleUpdateQuestion(secIdx, qIdx, 'matching_right', right);
    }
  };

  const handleRemoveMatchingRow = (secIdx, qIdx, rowIdx) => {
    const q = sections[secIdx].questions[qIdx];
    const left = (q.matching_left || []).filter((_, i) => i !== rowIdx);
    const right = (q.matching_right || []).filter((_, i) => i !== rowIdx);
    const answers = {};
    left.forEach((_, i) => {
      const k = String.fromCharCode(65 + i);
      answers[k] = String(i + 1);
    });
    handleUpdateQuestion(secIdx, qIdx, 'matching_left', left);
    handleUpdateQuestion(secIdx, qIdx, 'matching_right', right);
    handleUpdateQuestion(secIdx, qIdx, 'matching_answers', answers);
  };

  const handleUpdateMatchingAnswer = (secIdx, qIdx, leftKey, rightVal) => {
    const q = sections[secIdx].questions[qIdx];
    const answers = { ...(q.matching_answers || {}), [leftKey]: rightVal };
    handleUpdateQuestion(secIdx, qIdx, 'matching_answers', answers);
  };

  const handleDiagramClick = (e, secIdx, qIdx) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0.02), 0.98);
    const y = Math.min(Math.max((e.clientY - rect.top) / rect.height, 0.02), 0.98);
    const q = sections[secIdx].questions[qIdx];
    const currentMarkers = q.diagram_markers || [];
    const newNumber = currentMarkers.length + 1;
    const newMarker = {
      id: `m-${Date.now()}-${newNumber}`,
      number: newNumber,
      x: Math.round(x * 1000) / 1000,
      y: Math.round(y * 1000) / 1000,
      label: `Part ${newNumber}`
    };
    handleUpdateQuestion(secIdx, qIdx, 'diagram_markers', [...currentMarkers, newMarker]);
  };

  const handleUpdateDiagramMarker = (secIdx, qIdx, markerId, field, value) => {
    const q = sections[secIdx].questions[qIdx];
    const updated = (q.diagram_markers || []).map(m => m.id === markerId ? { ...m, [field]: value } : m);
    handleUpdateQuestion(secIdx, qIdx, 'diagram_markers', updated);
  };

  const handleRemoveDiagramMarker = (secIdx, qIdx, markerId) => {
    const q = sections[secIdx].questions[qIdx];
    const remaining = (q.diagram_markers || []).filter(m => m.id !== markerId);
    const renumbered = remaining.map((m, idx) => ({ ...m, number: idx + 1 }));
    handleUpdateQuestion(secIdx, qIdx, 'diagram_markers', renumbered);
  };

  const handleContinue = () => {
    if (hasBlockingErrors || stats.questionCount === 0) return;
    if (activeView !== 'review') {
      setActiveView('review');
      return;
    }
    onProceedToGenerate();
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Live Summary Card */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/90 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700">
                Manual Section Builder
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500 font-medium">Direct Visual Structure &amp; Question Crafting</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5 flex items-center gap-2">
              <span>Section &amp; Question Builder</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
              Create, reorder, and configure paper sections and question types with live marks and question counters.
            </p>
          </div>

          {/* Mode Switch: Builder vs Review */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="bg-slate-100 p-1 rounded-xl flex items-center gap-1">
              <button
                onClick={() => setActiveView('builder')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeView === 'builder'
                    ? 'bg-white text-indigo-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Builder</span>
              </button>
              <button
                onClick={() => setActiveView('review')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeView === 'review'
                    ? 'bg-white text-indigo-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Structure Review</span>
                {validationErrors.length > 0 && (
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Live Counters Metric Bar */}
        <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Sections</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-bold text-slate-900">{stats.sectionCount}</span>
              <span className="text-xs text-slate-500 font-medium">defined</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Total Questions</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-bold text-indigo-600">{stats.questionCount}</span>
              <span className="text-xs text-slate-500 font-medium">questions</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Marks Allocation</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-bold text-slate-900">{stats.marksSum}</span>
              {config.maximum_marks ? (
                <span className="text-xs text-slate-500 font-medium">/ {config.maximum_marks} max</span>
              ) : (
                <span className="text-xs text-slate-400 font-medium">marks</span>
              )}
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Question Mix</span>
            <div className="flex flex-wrap items-center gap-1.5 mt-1 text-[11px] font-medium text-slate-600">
              {stats.typeCounts.mcq > 0 && <span className="text-blue-600 font-semibold">{stats.typeCounts.mcq} MCQ</span>}
              {stats.typeCounts.short_answer > 0 && <span className="text-emerald-600 font-semibold">{stats.typeCounts.short_answer} Short</span>}
              {stats.typeCounts.long_answer > 0 && <span className="text-purple-600 font-semibold">{stats.typeCounts.long_answer} Long</span>}
              {stats.typeCounts.fill_in_the_blanks > 0 && <span className="text-amber-600 font-semibold">{stats.typeCounts.fill_in_the_blanks} Blanks</span>}
              {stats.typeCounts.true_false > 0 && <span className="text-rose-600 font-semibold">{stats.typeCounts.true_false} T/F</span>}
              {stats.questionCount === 0 && <span className="text-slate-400 italic">None yet</span>}
            </div>
          </div>
        </div>

        {/* Validation Errors Callout if any */}
        {validationErrors.length > 0 && (
          <div className="mt-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs space-y-1">
            <div className="flex items-center gap-2 font-bold text-rose-900">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>Please resolve {validationErrors.length} validation {validationErrors.length === 1 ? 'issue' : 'issues'} before generating PDF:</span>
            </div>
            <ul className="list-disc list-inside space-y-0.5 pl-1 pt-1 text-[11px] text-rose-700">
              {validationErrors.slice(0, 5).map((err, idx) => (
                <li key={idx}>{err.message}</li>
              ))}
              {validationErrors.length > 5 && (
                <li className="font-semibold text-rose-900">...and {validationErrors.length - 5} more issues.</li>
              )}
            </ul>
          </div>
        )}
      </div>

      {/* VIEW 1: INTERACTIVE BUILDER VIEW */}
      {activeView === 'builder' && (
        <div className="space-y-4">
          
          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleAddSection('mixed')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Section</span>
              </button>

              <button
                onClick={handleRenumberAll}
                disabled={stats.questionCount === 0}
                className="flex items-center gap-1 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-2xs transition-colors disabled:opacity-50"
                title="Automatically renumber all questions 1..N sequentially"
              >
                <Hash className="w-3.5 h-3.5 text-indigo-600" />
                <span>Renumber All 1..N</span>
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>Quick add section:</span>
              <button
                onClick={() => handleAddSection('mcq')}
                className="px-2 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold"
              >
                + MCQ Section
              </button>
              <button
                onClick={() => handleAddSection('short_answer')}
                className="px-2 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-semibold"
              >
                + Short Ans
              </button>
              <button
                onClick={() => handleAddSection('long_answer')}
                className="px-2 py-1 rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 font-semibold"
              >
                + Long Ans
              </button>
            </div>
          </div>

          {/* Empty State */}
          {sections.length === 0 ? (
            <div className="bg-white p-12 text-center rounded-2xl border border-dashed border-slate-300">
              <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">No Sections in Document</h3>
              <p className="text-xs text-slate-500 mt-1 mb-5 max-w-md mx-auto">
                Start crafting your exam paper by adding a new section. You can configure section titles, question types (MCQ, Short, Long, Fill-in-blanks, True/False), marks, and options.
              </p>
              <button
                onClick={() => handleAddSection('mixed')}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Create First Section</span>
              </button>
            </div>
          ) : (
            /* Sections List */
            <div className="space-y-5">
              {sections.map((section, secIdx) => {
                const secId = section.id || `sec-${secIdx}`;
                const isCollapsed = collapsedSections[secId];
                const secQCount = section.questions?.length || 0;
                const secMarks = (section.questions || []).reduce((acc, q) => acc + (parseFloat(q.marks) || 0), 0);
                const hasTitleError = !section.title?.trim();

                return (
                  <div
                    key={secId}
                    className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden transition-all"
                  >
                    
                    {/* Section Card Top Header */}
                    <div className="p-4 bg-slate-50/90 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                      
                      {/* Left: Section Title & Collapse */}
                      <div className="flex items-center gap-2 flex-1 min-w-[320px]">
                        <button
                          onClick={() => toggleCollapse(secId)}
                          className="p-1 rounded-lg text-slate-500 hover:bg-slate-200 transition-colors"
                          title={isCollapsed ? 'Expand section' : 'Collapse section'}
                        >
                          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>

                        <div className="flex items-center gap-2 flex-1">
                          <span className="w-7 h-7 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-2xs">
                            §{secIdx + 1}
                          </span>
                          
                          <div className="flex-1">
                            <input
                              type="text"
                              value={section.title}
                              onChange={(e) => handleUpdateSection(secIdx, 'title', e.target.value)}
                              placeholder="Section Title (e.g. PART A — MULTIPLE CHOICE)"
                              className={`w-full font-bold text-sm bg-white border rounded-lg px-2.5 py-1 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 ${
                                hasTitleError ? 'border-rose-400 bg-rose-50/30' : 'border-slate-300'
                              }`}
                            />
                            {hasTitleError && (
                              <span className="text-[10px] text-rose-600 font-semibold block mt-0.5">
                                Section title cannot be empty
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Center/Right: Question Type Selector, Stats & Actions */}
                      <div className="flex flex-wrap items-center gap-3 text-xs">
                        
                        {/* Section Default Question Type */}
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-500 text-[11px] font-semibold">Type:</span>
                          <select
                            value={section.question_type || 'mixed'}
                            onChange={(e) => handleUpdateSection(secIdx, 'question_type', e.target.value)}
                            className="bg-white border border-slate-300 rounded-lg px-2 py-1 font-semibold text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          >
                            {QUESTION_TYPES.map(t => (
                              <option key={t.id} value={t.id}>{t.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* Summary Pill */}
                        <div className="px-2.5 py-1 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-800 font-semibold">
                          {secQCount} Qs · {secMarks} Marks
                        </div>

                        {/* Reorder Section Buttons */}
                        <div className="flex items-center bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
                          <button
                            onClick={() => handleMoveSection(secIdx, -1)}
                            disabled={secIdx === 0}
                            className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-transparent"
                            title="Move section up"
                          >
                            <MoveUp className="w-3.5 h-3.5" />
                          </button>
                          <div className="w-[1px] h-4 bg-slate-200" />
                          <button
                            onClick={() => handleMoveSection(secIdx, 1)}
                            disabled={secIdx === sections.length - 1}
                            className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-transparent"
                            title="Move section down"
                          >
                            <MoveDown className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Delete Section Button */}
                        <button
                          onClick={() => handleRemoveSection(secIdx)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                          title="Delete section"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                    </div>

                    {/* Section Body (When expanded) */}
                    {!isCollapsed && (
                      <div className="p-4 sm:p-5 space-y-4">
                        
                        {/* Section Instructions Field */}
                        <div className="flex items-center gap-2 bg-slate-50 p-2.5 rounded-xl border border-slate-200/70">
                          <span className="text-xs font-semibold text-slate-600 shrink-0">Section Instructions:</span>
                          <input
                            type="text"
                            value={section.instructions || ''}
                            onChange={(e) => handleUpdateSection(secIdx, 'instructions', e.target.value)}
                            placeholder="e.g. Answer all questions / Each question carries 2 marks"
                            className="flex-1 text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          />
                        </div>

                        {/* Questions List */}
                        <div className="space-y-3.5">
                          {secQCount === 0 ? (
                            <div className="py-6 text-center bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                              <p className="text-xs text-slate-500 italic mb-2">No questions in this section yet.</p>
                              <button
                                onClick={() => handleAddQuestion(secIdx)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors"
                              >
                                <Plus className="w-3.5 h-3.5" />
                                <span>Add First Question</span>
                              </button>
                            </div>
                          ) : (
                            section.questions.map((q, qIdx) => {
                              const qId = q.id || `q-${qIdx}`;
                              const effectiveQType = (q.question_type || section.question_type || 'short_answer').toLowerCase();
                              const isMCQ = effectiveQType === 'mcq';
                              const isTF = effectiveQType === 'true_false';
                              const isMatching = effectiveQType === 'matching';
                              const isImageBased = effectiveQType === 'image_based';
                              const isDiagram = effectiveQType === 'diagram_identify';
                              const hasTextError = !q.text?.trim();
                              const hasOptionError = isMCQ && (q.options || []).filter(o => o && o.trim()).length < 2;

                              return (
                                <div
                                  key={qId}
                                  className={`p-3.5 sm:p-4 rounded-xl border transition-all ${
                                    hasTextError || hasOptionError
                                      ? 'border-rose-300 bg-rose-50/10'
                                      : 'border-slate-200/90 bg-white hover:border-slate-300 shadow-2xs'
                                  }`}
                                >
                                  
                                  {/* Row 1: Number, Type Selector, Question Text, Marks, Controls */}
                                  <div className="flex flex-col sm:flex-row items-start gap-3">
                                    
                                    {/* Number & Type Badge */}
                                    <div className="flex items-center sm:flex-col gap-2 shrink-0">
                                      <div className="flex items-center gap-1">
                                        <label className="text-[10px] font-bold text-slate-400 uppercase hidden sm:block">Q#</label>
                                        <input
                                          type="text"
                                          value={q.number || ''}
                                          onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'number', e.target.value)}
                                          placeholder="1"
                                          className="w-12 text-center font-bold text-xs bg-slate-50 border border-slate-200 rounded-lg py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        />
                                      </div>

                                      {/* Individual Question Type */}
                                      <select
                                        value={effectiveQType}
                                        onChange={(e) => {
                                          const newType = e.target.value;
                                          handleUpdateQuestion(secIdx, qIdx, 'question_type', newType);
                                          if (newType === 'matching') {
                                            if (!q.matching_left || q.matching_left.length === 0) {
                                              handleUpdateQuestion(secIdx, qIdx, 'matching_left', ['A. Item 1', 'B. Item 2', 'C. Item 3']);
                                              handleUpdateQuestion(secIdx, qIdx, 'matching_right', ['1. Match 1', '2. Match 2', '3. Match 3']);
                                              handleUpdateQuestion(secIdx, qIdx, 'matching_answers', { 'A': '1', 'B': '2', 'C': '3' });
                                              if (!q.text) handleUpdateQuestion(secIdx, qIdx, 'text', 'Match the items in Column A with Column B:');
                                            }
                                          } else if (newType === 'diagram_identify') {
                                            if (!q.diagram_mode) handleUpdateQuestion(secIdx, qIdx, 'diagram_mode', 'numbered_markers');
                                            if (!q.text) handleUpdateQuestion(secIdx, qIdx, 'text', 'Identify the parts marked in the diagram below:');
                                          }
                                        }}
                                        className="text-[11px] font-semibold bg-slate-50 border border-slate-200 rounded-md px-1.5 py-1 text-slate-700"
                                      >
                                        <option value="mcq">MCQ</option>
                                        <option value="short_answer">Short Ans</option>
                                        <option value="long_answer">Long Ans</option>
                                        <option value="fill_in_the_blanks">Fill Blanks</option>
                                        <option value="true_false">True/False</option>
                                        <option value="matching">Match</option>
                                        <option value="image_based">Image</option>
                                        <option value="diagram_identify">Diagram</option>
                                      </select>
                                    </div>

                                    {/* Question Textarea */}
                                    <div className="flex-1 min-w-0 w-full">
                                      <textarea
                                        rows={2}
                                        value={q.text || ''}
                                        onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'text', e.target.value)}
                                        placeholder={
                                          isMCQ
                                            ? 'Enter multiple choice question statement...'
                                            : isTF
                                            ? 'Enter true/false statement...'
                                            : effectiveQType === 'fill_in_the_blanks'
                                            ? 'Enter sentence with blanks, e.g. Plants synthesize food via _________ using sunlight.'
                                            : effectiveQType === 'matching'
                                            ? 'Enter matching instructions, e.g. Match the items in Column A with Column B:'
                                            : effectiveQType === 'diagram_identify'
                                            ? 'Enter diagram instructions, e.g. Identify the parts marked in the diagram below:'
                                            : 'Enter question text...'
                                        }
                                        className={`w-full text-xs font-sans text-slate-900 bg-white border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 resize-y leading-relaxed ${
                                          hasTextError ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                                        }`}
                                      />
                                      {hasTextError && (
                                        <span className="text-[10px] text-rose-600 font-semibold block mt-0.5">
                                          Question text cannot be empty.
                                        </span>
                                      )}
                                    </div>

                                    {/* Marks & Row Controls */}
                                    <div className="flex items-center gap-2 self-start shrink-0 pt-0.5">
                                      {/* Marks input */}
                                      <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
                                        <input
                                          type="number"
                                          step="0.5"
                                          min="0"
                                          value={q.marks ?? ''}
                                          onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'marks', e.target.value === '' ? null : parseFloat(e.target.value))}
                                          placeholder="Marks"
                                          className="w-12 text-right font-bold text-xs bg-transparent text-indigo-700 focus:outline-none"
                                        />
                                        <span className="text-[10px] font-bold text-slate-400">M</span>
                                      </div>

                                      {/* Move Up/Down */}
                                      <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg overflow-hidden">
                                        <button
                                          onClick={() => handleMoveQuestion(secIdx, qIdx, -1)}
                                          disabled={qIdx === 0}
                                          className="p-1 text-slate-400 hover:text-slate-800 disabled:opacity-25"
                                          title="Move question up"
                                        >
                                          <ChevronUp className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                          onClick={() => handleMoveQuestion(secIdx, qIdx, 1)}
                                          disabled={qIdx === section.questions.length - 1}
                                          className="p-1 text-slate-400 hover:text-slate-800 disabled:opacity-25"
                                          title="Move question down"
                                        >
                                          <ChevronDown className="w-3.5 h-3.5" />
                                        </button>
                                      </div>

                                      {/* Delete Question */}
                                      <button
                                        onClick={() => handleRemoveQuestion(secIdx, qIdx)}
                                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                                        title="Delete question"
                                      >
                                        <Trash2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>

                                  </div>

                                  {/* Row 2: MCQ Options (If MCQ or True/False) */}
                                  {(isMCQ || isTF) && (
                                    <div className="mt-3 sm:ml-16 p-3 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-2">
                                      <div className="flex items-center justify-between">
                                        <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                                          <span>{isTF ? 'True / False Options:' : 'Multiple Choice Options:'}</span>
                                          {hasOptionError && (
                                            <span className="text-rose-600 font-semibold text-[10px] lowercase">
                                              (at least 2 options required)
                                            </span>
                                          )}
                                        </span>

                                        <div className="flex items-center gap-1.5">
                                          {isMCQ && (
                                            <button
                                              onClick={() => handleAddOption(secIdx, qIdx)}
                                              className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 px-2 py-0.5 rounded bg-white border border-slate-200"
                                            >
                                              <Plus className="w-3 h-3" />
                                              <span>Add Option</span>
                                            </button>
                                          )}
                                        </div>
                                      </div>

                                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                                        {(q.options || []).map((opt, optIdx) => (
                                          <div key={optIdx} className="flex items-center gap-1.5">
                                            <input
                                              type="text"
                                              value={opt}
                                              onChange={(e) => handleUpdateOption(secIdx, qIdx, optIdx, e.target.value)}
                                              placeholder={`e.g. ${String.fromCharCode(97 + optIdx)}) Option text`}
                                              className="flex-1 text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
                                            />
                                            {isMCQ && (q.options || []).length > 2 && (
                                              <button
                                                onClick={() => handleRemoveOption(secIdx, qIdx, optIdx)}
                                                className="text-slate-400 hover:text-rose-600 p-1 rounded"
                                                title="Remove option"
                                              >
                                                <Trash2 className="w-3 h-3" />
                                              </button>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Advanced Question Type: Match the Following */}
                                  {isMatching && (
                                    <MatchingEditor
                                      q={q}
                                      secIdx={secIdx}
                                      qIdx={qIdx}
                                      handleUpdateQuestion={handleUpdateQuestion}
                                      handleAddMatchingRow={handleAddMatchingRow}
                                      handleUpdateMatchingRow={handleUpdateMatchingRow}
                                      handleRemoveMatchingRow={handleRemoveMatchingRow}
                                      handleUpdateMatchingAnswer={handleUpdateMatchingAnswer}
                                    />
                                  )}

                                  {/* Advanced Question Type: Image-Based Question */}
                                  {isImageBased && (
                                    <ImageBasedEditor
                                      q={q}
                                      secIdx={secIdx}
                                      qIdx={qIdx}
                                      handleUpdateQuestion={handleUpdateQuestion}
                                      handleImagePaste={handleImagePaste}
                                      handleImageFileInput={handleImageFileInput}
                                    />
                                  )}

                                  {/* Advanced Question Type: Diagram Identification */}
                                  {isDiagram && (
                                    <DiagramIdentifyEditor
                                      q={q}
                                      secIdx={secIdx}
                                      qIdx={qIdx}
                                      handleUpdateQuestion={handleUpdateQuestion}
                                      handleImagePaste={handleImagePaste}
                                      handleImageFileInput={handleImageFileInput}
                                      handleDiagramClick={handleDiagramClick}
                                      handleUpdateDiagramMarker={handleUpdateDiagramMarker}
                                      handleRemoveDiagramMarker={handleRemoveDiagramMarker}
                                    />
                                  )}

                                  {/* Row 3: Subquestions (for long answer / complex questions) */}
                                  {q.subquestions && q.subquestions.length > 0 && (
                                    <div className="mt-3 sm:ml-16 pl-3 border-l-2 border-indigo-200 space-y-2">
                                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Subquestions:</span>
                                      {q.subquestions.map((sq, sqIdx) => (
                                        <div key={sq.id || sqIdx} className="flex items-center gap-2">
                                          <input
                                            type="text"
                                            value={sq.label}
                                            onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'label', e.target.value)}
                                            className="w-12 text-center text-xs font-semibold bg-white border border-slate-300 rounded-md py-1"
                                            placeholder="(a)"
                                          />
                                          <input
                                            type="text"
                                            value={sq.text}
                                            onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'text', e.target.value)}
                                            placeholder="Subquestion content..."
                                            className="flex-1 text-xs bg-white border border-slate-300 rounded-md px-2 py-1"
                                          />
                                          <input
                                            type="number"
                                            step="0.5"
                                            value={sq.marks ?? ''}
                                            onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'marks', e.target.value ? parseFloat(e.target.value) : null)}
                                            placeholder="Marks"
                                            className="w-16 text-right text-xs bg-white border border-slate-300 rounded-md px-1.5 py-1 text-indigo-700 font-bold"
                                          />
                                          <button
                                            onClick={() => handleRemoveSubQuestion(secIdx, qIdx, sqIdx)}
                                            className="text-slate-400 hover:text-rose-600 p-1"
                                          >
                                            <Trash2 className="w-3 h-3" />
                                          </button>
                                        </div>
                                      ))}
                                    </div>
                                  )}

                                  {/* Subquestion Add Trigger */}
                                  {!isMCQ && !isTF && !isMatching && !isDiagram && (
                                    <div className="mt-2 sm:ml-16 flex items-center gap-2">
                                      <button
                                        onClick={() => handleAddSubQuestion(secIdx, qIdx)}
                                        className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                                      >
                                        <Plus className="w-3 h-3" />
                                        <span>Add Sub-question (a, b)</span>
                                      </button>
                                    </div>
                                  )}

                                </div>
                              );
                            })
                          )}
                        </div>

                        {/* Add Question Button in Section Footer */}
                        <div className="pt-2 flex flex-wrap items-center gap-2">
                          <button
                            onClick={() => handleAddQuestion(secIdx)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            <span>Add Question</span>
                          </button>

                          {section.question_type === 'mixed' && (
                            <div className="flex items-center gap-1.5 text-xs text-slate-500 pl-2">
                              <span>Add specific type:</span>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'mcq')}
                                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-[11px]"
                              >
                                + MCQ
                              </button>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'short_answer')}
                                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-[11px]"
                              >
                                + Short
                              </button>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'long_answer')}
                                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-[11px]"
                              >
                                + Long
                              </button>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'matching')}
                                className="px-2 py-1 rounded bg-teal-50 hover:bg-teal-100 text-teal-700 font-medium text-[11px]"
                              >
                                + Match
                              </button>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'image_based')}
                                className="px-2 py-1 rounded bg-sky-50 hover:bg-sky-100 text-sky-700 font-medium text-[11px]"
                              >
                                + Image
                              </button>
                              <button
                                onClick={() => handleAddQuestion(secIdx, 'diagram_identify')}
                                className="px-2 py-1 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium text-[11px]"
                              >
                                + Diagram
                              </button>
                            </div>
                          )}
                        </div>

                      </div>
                    )}

                  </div>
                );
              })}
            </div>
          )}

        </div>
      )}

      {/* VIEW 2: STRUCTURE REVIEW STEP BEFORE GENERATING */}
      {activeView === 'review' && (
        <div className="space-y-5">
          
          <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-4 mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Pre-Generation Structure Review</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Inspect the structured hierarchy, allocated marks, question ordering, and completeness before creating the final PDF.
                </p>
              </div>

              <div className="flex items-center gap-2">
                {hasBlockingErrors ? (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 text-rose-700 text-xs font-bold border border-rose-200">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>{validationErrors.length} issues blocking generation</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>All validation checks pass!</span>
                  </span>
                )}
              </div>
            </div>

            {/* Document Header Outline */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 text-sm">{config.institution_name || 'Institution / School Name (Not Set)'}</span>
                <span className="font-bold text-indigo-700">{config.maximum_marks ? `${config.maximum_marks} Marks` : 'Marks not configured'}</span>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-slate-600 text-[11px]">
                {config.subject_name && <span>Subject: <strong>{config.subject_name}</strong></span>}
                {config.semester_class && <span>Class: <strong>{config.semester_class}</strong></span>}
                {config.duration && <span>Duration: <strong>{config.duration}</strong></span>}
              </div>
            </div>

            {/* Structure Outline Table */}
            <div className="mt-4 space-y-4">
              {sections.map((sec, sIdx) => {
                const sMarks = (sec.questions || []).reduce((acc, q) => acc + (parseFloat(q.marks) || 0), 0);
                return (
                  <div key={sec.id || sIdx} className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="p-3 bg-slate-100 flex items-center justify-between font-bold text-xs text-slate-900">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-indigo-600 text-white text-[10px]">§{sIdx + 1}</span>
                        <span>{sec.title}</span>
                        {sec.instructions && <span className="font-normal text-slate-500 italic">({sec.instructions})</span>}
                      </div>
                      <span className="text-indigo-800">{sec.questions?.length || 0} questions · {sMarks} marks</span>
                    </div>

                    <div className="divide-y divide-slate-100">
                      {(sec.questions || []).map((q, qIdx) => {
                        const qType = (q.question_type || sec.question_type || 'short_answer').toLowerCase();
                        return (
                          <div key={q.id || qIdx} className="p-3 text-xs flex items-start justify-between gap-4">
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900">Q{q.number || qIdx + 1}.</span>
                                <span className="font-medium text-slate-800">{q.text || <em className="text-rose-500">Missing question text</em>}</span>
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-semibold uppercase">{qType}</span>
                              </div>

                              {/* MCQ options preview */}
                              {q.options && q.options.length > 0 && (
                                <div className="pl-6 pt-1 flex flex-wrap gap-2 text-[11px] text-slate-600">
                                  {q.options.map((opt, oIdx) => (
                                    <span key={oIdx} className="px-2 py-0.5 rounded bg-slate-50 border border-slate-200">
                                      {opt}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {/* Subquestions preview */}
                              {q.subquestions && q.subquestions.length > 0 && (
                                <div className="pl-6 pt-1 space-y-1 text-[11px]">
                                  {q.subquestions.map((sq, sqIdx) => (
                                    <div key={sqIdx} className="text-slate-600">
                                      <strong>{sq.label}</strong> {sq.text} {sq.marks ? `[${sq.marks}M]` : ''}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>

                            <span className="font-bold text-indigo-600 shrink-0">
                              {q.marks !== null && q.marks !== undefined ? `[${q.marks}M]` : '-'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

          </div>

        </div>
      )}

      {/* Bottom Navigation Bar */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBackToReference}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Reference PDF</span>
        </button>

        <button
          onClick={handleContinue}
          disabled={hasBlockingErrors || stats.questionCount === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>
            {activeView === 'review'
              ? 'Continue to Generate & Review PDF'
              : 'Review Structure Before Generating'}
          </span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
}
