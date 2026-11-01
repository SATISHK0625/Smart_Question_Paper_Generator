import React, { useState } from 'react';
import { Plus, Trash2, AlertTriangle, AlertCircle, CheckCircle2, ArrowRight, ArrowLeft, Layers, HelpCircle, Split } from 'lucide-react';

export default function QuestionStructureEditor({
  sections,
  setSections,
  config,
  onNext,
  onBack
}) {
  const [expandedSection, setExpandedSection] = useState(null);

  // Section operations
  const handleAddSection = () => {
    const newSec = {
      id: `sec-${Date.now().toString(36)}`,
      title: `SECTION ${String.fromCharCode(65 + sections.length)}`,
      instructions: 'Answer all questions.',
      questions: [],
      total_marks_available: 0,
      expected_marks: 0,
      required_count: null
    };
    setSections([...sections, newSec]);
  };

  const handleRemoveSection = (secIdx) => {
    setSections(sections.filter((_, i) => i !== secIdx));
  };

  const handleUpdateSection = (secIdx, field, value) => {
    setSections(prev => {
      const copy = [...prev];
      copy[secIdx] = { ...copy[secIdx], [field]: value };
      return copy;
    });
  };

  // Question operations
  const handleAddQuestion = (secIdx) => {
    const sec = sections[secIdx];
    const nextNum = (sec.questions.length + 1).toString();
    const newQ = {
      id: `q-${Date.now().toString(36)}`,
      number: nextNum,
      text: '',
      marks: null,
      subquestions: [],
      is_flagged: true,
      flag_reason: 'Please enter question text and marks.'
    };
    setSections(prev => {
      const copy = [...prev];
      copy[secIdx] = { ...copy[secIdx], questions: [...copy[secIdx].questions, newQ] };
      return copy;
    });
  };

  const handleRemoveQuestion = (secIdx, qIdx) => {
    setSections(prev => {
      const copy = [...prev];
      copy[secIdx] = {
        ...copy[secIdx],
        questions: copy[secIdx].questions.filter((_, i) => i !== qIdx)
      };
      return copy;
    });
  };

  const handleUpdateQuestion = (secIdx, qIdx, field, value) => {
    setSections(prev => {
      const copy = [...prev];
      const q = { ...copy[secIdx].questions[qIdx], [field]: value };
      
      // Update flag
      if (q.marks === null || isNaN(q.marks)) {
        q.is_flagged = true;
        q.flag_reason = 'No marks detected';
      } else {
        q.is_flagged = false;
        q.flag_reason = null;
      }

      copy[secIdx].questions[qIdx] = q;
      return copy;
    });
  };

  // Subquestion operations
  const handleAddSubQuestion = (secIdx, qIdx) => {
    const q = sections[secIdx].questions[qIdx];
    const subLabels = ['(a)', '(b)', '(c)', '(d)', '(e)', '(f)'];
    const nextLabel = subLabels[q.subquestions.length] || `(${q.subquestions.length + 1})`;

    const newSub = {
      id: `sq-${Date.now().toString(36)}`,
      label: nextLabel,
      text: '',
      marks: null
    };

    setSections(prev => {
      const copy = [...prev];
      const targetQ = { ...copy[secIdx].questions[qIdx] };
      targetQ.subquestions = [...targetQ.subquestions, newSub];
      copy[secIdx].questions[qIdx] = targetQ;
      return copy;
    });
  };

  const handleRemoveSubQuestion = (secIdx, qIdx, sqIdx) => {
    setSections(prev => {
      const copy = [...prev];
      const targetQ = { ...copy[secIdx].questions[qIdx] };
      targetQ.subquestions = targetQ.subquestions.filter((_, i) => i !== sqIdx);
      copy[secIdx].questions[qIdx] = targetQ;
      return copy;
    });
  };

  const handleUpdateSubQuestion = (secIdx, qIdx, sqIdx, field, value) => {
    setSections(prev => {
      const copy = [...prev];
      const targetQ = { ...copy[secIdx].questions[qIdx] };
      const subCopy = [...targetQ.subquestions];
      subCopy[sqIdx] = { ...subCopy[sqIdx], [field]: value };
      targetQ.subquestions = subCopy;

      // Recalculate parent question marks if subquestion marks are provided
      const subMarks = subCopy.map(s => parseFloat(s.marks)).filter(m => !isNaN(m));
      if (subMarks.length > 0) {
        targetQ.marks = subMarks.reduce((a, b) => a + b, 0);
        targetQ.is_flagged = false;
        targetQ.flag_reason = null;
      }

      copy[secIdx].questions[qIdx] = targetQ;
      return copy;
    });
  };

  // Calculate live summary
  const totalQuestions = sections.reduce((sum, s) => sum + s.questions.length, 0);
  const totalAvailableMarks = sections.reduce((sum, s) => {
    return sum + s.questions.reduce((qsum, q) => qsum + (parseFloat(q.marks) || 0), 0);
  }, 0);

  return (
    <div className="space-y-6">
      
      {/* Header and Quick Stats */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Structured Questions &amp; Marks Editor</h2>
            <p className="text-sm text-slate-600 mt-1">
              Review and adjust parsed questions, assign marks, set optional requirements, and resolve flags.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-center">
              <span className="block text-[10px] text-slate-400 font-bold uppercase">Total Questions</span>
              <span className="text-sm font-bold text-slate-900">{totalQuestions}</span>
            </div>
            <div className="px-3 py-1.5 bg-indigo-50 border border-indigo-200 rounded-xl text-center">
              <span className="block text-[10px] text-indigo-500 font-bold uppercase">Sum of Marks</span>
              <span className="text-sm font-bold text-indigo-900">{totalAvailableMarks}</span>
            </div>
            <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-center">
              <span className="block text-[10px] text-slate-400 font-bold uppercase">Target Max</span>
              <span className="text-sm font-bold text-slate-900">{config.maximum_marks}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sections List */}
      <div className="space-y-6">
        {sections.map((section, secIdx) => {
          const secMarksSum = section.questions.reduce((sum, q) => sum + (parseFloat(q.marks) || 0), 0);

          return (
            <div
              key={section.id || secIdx}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden"
            >
              
              {/* Section Header */}
              <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3 flex-1 min-w-[280px]">
                  <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
                    §{secIdx + 1}
                  </span>
                  <input
                    type="text"
                    value={section.title}
                    onChange={(e) => handleUpdateSection(secIdx, 'title', e.target.value)}
                    placeholder="Section Title (e.g. PART A)"
                    className="font-bold text-sm text-slate-900 bg-white border border-slate-300 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 w-44"
                  />
                  <input
                    type="text"
                    value={section.instructions || ''}
                    onChange={(e) => handleUpdateSection(secIdx, 'instructions', e.target.value)}
                    placeholder="Instructions (e.g. Answer all questions / Answer any two)"
                    className="text-xs text-slate-600 bg-white border border-slate-300 rounded-lg px-2.5 py-1 flex-1 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-slate-500">
                    Total: <strong className="text-slate-900 font-bold">{secMarksSum} marks</strong> ({section.questions.length} questions)
                  </span>

                  <button
                    onClick={() => handleAddQuestion(secIdx)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Question</span>
                  </button>

                  <button
                    onClick={() => handleRemoveSection(secIdx)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded-lg transition-colors"
                    title="Remove Section"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Questions within Section */}
              <div className="p-4 space-y-4">
                {section.questions.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-4 italic">
                    No questions in this section. Click "Add Question" to create one.
                  </p>
                ) : (
                  section.questions.map((q, qIdx) => (
                    <div
                      key={q.id || qIdx}
                      className={`p-3 rounded-xl border transition-all ${
                        q.is_flagged
                          ? 'border-amber-300 bg-amber-50/20'
                          : 'border-slate-200 bg-slate-50/40 hover:bg-white'
                      }`}
                    >
                      {/* Question Top Row */}
                      <div className="flex items-start gap-3">
                        {/* Number input */}
                        <div className="w-16 shrink-0">
                          <label className="block text-[10px] font-bold text-slate-400 uppercase">Q No.</label>
                          <input
                            type="text"
                            value={q.number}
                            onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'number', e.target.value)}
                            className="w-full text-xs font-bold text-slate-900 bg-white border border-slate-300 rounded-lg px-2 py-1 text-center focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          />
                        </div>

                        {/* Question Text */}
                        <div className="flex-1 min-w-0">
                          <label className="block text-[10px] font-bold text-slate-400 uppercase">Question Text</label>
                          <textarea
                            rows={2}
                            value={q.text}
                            onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'text', e.target.value)}
                            placeholder="Enter question text..."
                            className="w-full text-xs text-slate-800 bg-white border border-slate-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 resize-y"
                          />
                        </div>

                        {/* Marks */}
                        <div className="w-20 shrink-0">
                          <label className="block text-[10px] font-bold text-slate-400 uppercase">Marks</label>
                          <input
                            type="number"
                            min="0"
                            step="0.5"
                            value={q.marks ?? ''}
                            onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'marks', e.target.value === '' ? null : parseFloat(e.target.value))}
                            placeholder="Marks"
                            className="w-full text-xs font-bold text-slate-900 bg-white border border-slate-300 rounded-lg px-2 py-1 text-right focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                          />
                        </div>

                        {/* Actions */}
                        <div className="pt-4 flex items-center gap-1">
                          <button
                            onClick={() => handleAddSubQuestion(secIdx, qIdx)}
                            className="p-1 text-xs text-indigo-600 hover:bg-indigo-50 rounded-lg font-medium"
                            title="Add subquestion (e.g. (a), (b))"
                          >
                            +Sub
                          </button>
                          <button
                            onClick={() => handleRemoveQuestion(secIdx, qIdx)}
                            className="p-1 text-slate-400 hover:text-rose-600 rounded-lg transition-colors"
                            title="Delete question"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Flag notification if uncertain */}
                      {q.is_flagged && (
                        <div className="mt-2 text-[11px] text-amber-700 flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          <span>{q.flag_reason || 'Missing marks or needs review'}</span>
                        </div>
                      )}

                      {/* Subquestions List */}
                      {q.subquestions && q.subquestions.length > 0 && (
                        <div className="mt-3 ml-6 pl-3 border-l-2 border-indigo-200 space-y-2">
                          {q.subquestions.map((sq, sqIdx) => (
                            <div key={sq.id || sqIdx} className="flex items-center gap-2">
                              <input
                                type="text"
                                value={sq.label}
                                onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'label', e.target.value)}
                                className="w-12 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md px-1.5 py-1 text-center"
                              />
                              <input
                                type="text"
                                value={sq.text}
                                onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'text', e.target.value)}
                                placeholder="Subquestion content..."
                                className="flex-1 text-xs text-slate-800 bg-white border border-slate-300 rounded-md px-2 py-1"
                              />
                              <input
                                type="number"
                                min="0"
                                step="0.5"
                                value={sq.marks ?? ''}
                                onChange={(e) => handleUpdateSubQuestion(secIdx, qIdx, sqIdx, 'marks', e.target.value === '' ? null : parseFloat(e.target.value))}
                                placeholder="Marks"
                                className="w-16 text-xs font-semibold text-slate-800 bg-white border border-slate-300 rounded-md px-1.5 py-1 text-right"
                              />
                              <button
                                onClick={() => handleRemoveSubQuestion(secIdx, qIdx, sqIdx)}
                                className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                                title="Remove subquestion"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                    </div>
                  ))
                )}
              </div>

            </div>
          );
        })}
      </div>

      {/* Add New Section button */}
      <div className="text-center pt-1">
        <button
          onClick={handleAddSection}
          className="inline-flex items-center gap-2 px-4 py-2 border-2 border-dashed border-slate-300 hover:border-indigo-400 hover:bg-indigo-50/40 text-xs font-semibold text-slate-600 hover:text-indigo-700 rounded-xl transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add Another Section</span>
        </button>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Configuration</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
        >
          <span>Generate Preview &amp; Overview</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
}
