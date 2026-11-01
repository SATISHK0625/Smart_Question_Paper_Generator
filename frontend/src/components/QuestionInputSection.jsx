import React, { useState } from 'react';
import { FileUp, Sparkles, AlertCircle, ArrowRight, ArrowLeft, Loader2, BookOpen, Check } from 'lucide-react';
import { importQuestionsFile, parseQuestions } from '../services/api';
import { SAMPLE_PAPERS } from '../data/samplePapers';

export default function QuestionInputSection({
  rawText,
  setRawText,
  onParsed,
  onBack,
  config,
  setConfig
}) {
  const [isImporting, setIsImporting] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleFileUpload = async (file) => {
    setErrorMsg('');
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
    } catch (err) {
      setErrorMsg(err.message || 'Failed to import file text.');
    } finally {
      setIsImporting(false);
    }
  };

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
    }
  };

  const handleParse = async () => {
    if (!rawText.trim()) {
      setErrorMsg('Please enter or import question text before proceeding.');
      return;
    }

    setErrorMsg('');
    setIsParsing(true);
    try {
      const parsedData = await parseQuestions(rawText);
      onParsed(parsedData);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to parse questions.');
    } finally {
      setIsParsing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Title & Presets Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Enter Questions</h2>
            <p className="text-sm text-slate-600 mt-1">
              Paste raw text below or import a TXT or DOCX document. Exact wording is strictly preserved.
            </p>
          </div>

          {/* Sample Presets */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Sample Papers:</span>
            <button
              onClick={() => loadSample('cs')}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>CS: Data Structures</span>
            </button>
            <button
              onClick={() => loadSample('math')}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-1.5"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Engineering Math</span>
            </button>
          </div>
        </div>
      </div>

      {/* Editor Container */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
        
        {/* Editor Toolbar */}
        <div className="p-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <label className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 cursor-pointer shadow-2xs transition-colors">
              <FileUp className="w-3.5 h-3.5 text-indigo-600" />
              <span>Import TXT / DOCX</span>
              <input
                type="file"
                accept=".txt,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              />
            </label>

            {isImporting && (
              <span className="inline-flex items-center gap-1.5 text-xs text-indigo-600">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Reading file...
              </span>
            )}
          </div>

          <div className="text-[11px] text-slate-400">
            {rawText.split('\n').length} lines · {rawText.length} characters
          </div>
        </div>

        {/* Text Area */}
        <div className="p-4">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={16}
            placeholder="PART A — Answer all questions.&#10;&#10;1. Define an algorithm. (2 marks)&#10;2. Explain a data structure. (2 marks)&#10;&#10;PART B — Answer any two questions.&#10;&#10;11. Explain binary search. (10 marks)&#10;12. Describe a sorting algorithm. (10 marks)"
            className="w-full p-4 text-xs font-mono bg-slate-900 text-slate-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-y leading-relaxed"
            spellCheck="false"
          />
        </div>

        {/* Syntax guide footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-semibold text-slate-700">Supported Formats:</span>
          <span>Sections: <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">PART A</code></span>
          <span>Questions: <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">1.</code>, <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">Q1.</code></span>
          <span>Subquestions: <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">(a)</code>, <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">i)</code></span>
          <span>Marks: <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">(2 marks)</code>, <code className="text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">[10M]</code></span>
        </div>

      </div>

      {/* Error message */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Reference</span>
        </button>

        <button
          onClick={handleParse}
          disabled={isParsing || !rawText.trim()}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
        >
          {isParsing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Parsing Questions...</span>
            </>
          ) : (
            <>
              <span>Parse &amp; Configure Paper</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>

    </div>
  );
}
