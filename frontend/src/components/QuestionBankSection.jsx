import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  Plus,
  Trash2,
  Edit3,
  CheckSquare,
  Square,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Lock,
  FolderPlus
} from 'lucide-react';

import {
  fetchBankQuestions,
  fetchBankSubjects,
  createBankQuestion,
  updateBankQuestion,
  deleteBankQuestion,
  getBankQuestionSnapshot
} from '../services/api';

const QUESTION_TYPES = [
  { id: 'mcq', label: 'Multiple Choice (MCQ)' },
  { id: 'short_answer', label: 'Short Answer' },
  { id: 'long_answer', label: 'Long Answer' },
  { id: 'fill_in_the_blanks', label: 'Fill in the Blanks' },
  { id: 'true_false', label: 'True / False' },
  { id: 'matching', label: 'Match the Following' },
  { id: 'image_based', label: 'Image-Based Question' },
  { id: 'diagram_identify', label: 'Diagram Parts Identification' }
];

export default function QuestionBankSection({
  sections,
  setSections,
  onNavigateToBuilder
}) {
  const [questions, setQuestions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [availableSubjects, setAvailableSubjects] = useState([]);

  // Selection state for adding to paper
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [targetSectionId, setTargetSectionId] = useState(sections?.[0]?.id || '');

  // Modal state for create / edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [formText, setFormText] = useState('');
  const [formType, setFormType] = useState('mcq');
  const [formSubject, setFormSubject] = useState('');
  const [formClass, setFormClass] = useState('');
  const [formChapter, setFormChapter] = useState('');
  const [formTopic, setFormTopic] = useState('');
  const [formDifficulty, setFormDifficulty] = useState('medium');
  const [formMarks, setFormMarks] = useState(1.0);
  const [formOptions, setFormOptions] = useState(['', '', '', '']);
  const [formCorrectAnswer, setFormCorrectAnswer] = useState('');
  const [formExplanation, setFormExplanation] = useState('');
  const [formTags, setFormTags] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const loadQuestions = async (targetPage = page) => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await fetchBankQuestions({
        search,
        subject: subjectFilter,
        difficulty: difficultyFilter,
        question_type: typeFilter,
        limit: 12,
        offset: (targetPage - 1) * 12
      });
      setQuestions(res.items || []);
      setTotal(res.total || 0);
      setPage(res.page || 1);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load question bank.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadSubjects = async () => {
    try {
      const res = await fetchBankSubjects();
      setAvailableSubjects(res.subjects || []);
    } catch {
      // Non-critical
    }
  };

  useEffect(() => {
    loadSubjects();
  }, []);

  useEffect(() => {
    loadQuestions(1);
  }, [search, subjectFilter, difficultyFilter, typeFilter]);

  // Handle Multi-select
  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllOnPage = () => {
    if (selectedIds.size === questions.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(questions.map((q) => q.id)));
    }
  };

  // Open Create Modal
  const handleOpenCreate = () => {
    setEditingQuestion(null);
    setFormText('');
    setFormType('mcq');
    setFormSubject('');
    setFormClass('');
    setFormChapter('');
    setFormTopic('');
    setFormDifficulty('medium');
    setFormMarks(1.0);
    setFormOptions(['', '', '', '']);
    setFormCorrectAnswer('');
    setFormExplanation('');
    setFormTags('');
    setIsModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (q) => {
    setEditingQuestion(q);
    setFormText(q.text || '');
    setFormType(q.question_type || 'mcq');
    setFormSubject(q.subject || '');
    setFormClass(q.class_level || '');
    setFormChapter(q.chapter || '');
    setFormTopic(q.topic || '');
    setFormDifficulty(q.difficulty || 'medium');
    setFormMarks(q.marks || 1.0);
    setFormOptions(q.options?.length ? [...q.options] : ['', '', '', '']);
    setFormCorrectAnswer(q.correct_answer || '');
    setFormExplanation(q.explanation || '');
    setFormTags((q.tags || []).join(', '));
    setIsModalOpen(true);
  };

  // Save Question Form
  const handleSaveQuestion = async (e) => {
    e.preventDefault();
    if (!formText.trim()) {
      alert('Question text cannot be empty.');
      return;
    }

    setIsSaving(true);
    const tagsArray = formTags.split(',').map((t) => t.trim()).filter(Boolean);
    const validOpts = formType === 'mcq' ? formOptions.filter((o) => o && o.trim()) : [];

    const payload = {
      text: formText.trim(),
      question_type: formType,
      subject: formSubject.trim(),
      class_level: formClass.trim(),
      chapter: formChapter.trim(),
      topic: formTopic.trim(),
      difficulty: formDifficulty,
      marks: parseFloat(formMarks) || 1.0,
      options: validOpts,
      correct_answer: formCorrectAnswer.trim(),
      explanation: formExplanation.trim(),
      tags: tagsArray
    };

    try {
      if (editingQuestion) {
        await updateBankQuestion(editingQuestion.id, payload);
        setSuccessMsg('Question updated successfully.');
      } else {
        await createBankQuestion(payload);
        setSuccessMsg('Question saved to bank.');
      }
      setIsModalOpen(false);
      loadQuestions(page);
      loadSubjects();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      alert(err.message || 'Failed to save question.');
    } finally {
      setIsSaving(false);
    }
  };

  // Delete Question
  const handleDelete = async (id, text) => {
    if (!window.confirm(`Delete question: "${text.slice(0, 40)}..."?`)) return;
    try {
      await deleteBankQuestion(id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      loadQuestions(page);
    } catch (err) {
      alert(err.message || 'Failed to delete question.');
    }
  };

  // Add Selected Questions to Paper as Independent Snapshots
  const handleAddToPaper = async () => {
    if (selectedIds.size === 0) return;
    if (!sections || sections.length === 0) {
      alert('Your paper currently has no sections. Please create a section in the Section Builder first.');
      if (onNavigateToBuilder) onNavigateToBuilder();
      return;
    }

    const secId = targetSectionId || sections[0].id;
    const targetSection = sections.find((s) => s.id === secId) || sections[0];

    const questionsToAdd = questions.filter((q) => selectedIds.has(q.id));
    const snapshotPromises = questionsToAdd.map(async (bankQ, idx) => {
      const nextNum = (targetSection.questions?.length || 0) + idx + 1;
      return await getBankQuestionSnapshot(bankQ.id, String(nextNum));
    });

    try {
      const newSnapshots = await Promise.all(snapshotPromises);

      // Deep copy snapshot update into the selected section
      const updatedSections = sections.map((sec) => {
        if (sec.id === targetSection.id) {
          const currentQs = sec.questions || [];
          return {
            ...sec,
            questions: [...currentQs, ...newSnapshots]
          };
        }
        return sec;
      });

      setSections(updatedSections);
      setSuccessMsg(`Added ${newSnapshots.length} question(s) to "${targetSection.title}".`);
      setSelectedIds(new Set());
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      alert(err.message || 'Failed to add questions to paper.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Reusable Question Bank</h2>
            <span className="text-xs bg-indigo-100 text-indigo-800 font-bold px-2 py-0.5 rounded-full">
              {total} questions
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Search, manage, and clone questions across different exam papers. Questions added to a paper become independent snapshots so subsequent bank edits never alter existing examination drafts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Question</span>
          </button>
        </div>
      </div>

      {/* Feedback alerts */}
      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2 font-medium">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          
          {/* Keyword Search */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by question text, topic, chapter, or keyword..."
              className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
            />
          </div>

          {/* Subject Filter */}
          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="w-full md:w-44 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Subjects</option>
            {availableSubjects.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Difficulty Filter */}
          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(e.target.value)}
            className="w-full md:w-36 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full md:w-44 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Question Types</option>
            {QUESTION_TYPES.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>

        </div>

        {/* Action Bar when items selected */}
        {selectedIds.size > 0 && (
          <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-indigo-50/50 p-2.5 rounded-xl border border-indigo-100">
            <div className="flex items-center gap-2 text-xs text-indigo-950 font-bold">
              <span>{selectedIds.size} question(s) selected</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-600 font-medium">Add to section:</span>
              <select
                value={targetSectionId}
                onChange={(e) => setTargetSectionId(e.target.value)}
                className="px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-800"
              >
                {sections?.map((s) => (
                  <option key={s.id} value={s.id}>{s.title || 'Untitled Section'}</option>
                ))}
              </select>

              <button
                onClick={handleAddToPaper}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors"
              >
                <FolderPlus className="w-3.5 h-3.5" />
                <span>Add Selected to Paper</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Question Cards Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-500 px-1">
          <div className="flex items-center gap-2">
            <button
              onClick={selectAllOnPage}
              className="flex items-center gap-1 hover:text-slate-800 font-medium"
            >
              {selectedIds.size > 0 && selectedIds.size === questions.length ? (
                <CheckSquare className="w-4 h-4 text-indigo-600" />
              ) : (
                <Square className="w-4 h-4 text-slate-400" />
              )}
              <span>Select All on Page</span>
            </button>
          </div>
          <span>Showing {questions.length} of {total}</span>
        </div>

        {isLoading ? (
          <div className="bg-white p-16 rounded-2xl border border-slate-200/90 text-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-600">Loading Question Bank entries...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="bg-white p-12 rounded-2xl border border-slate-200/90 text-center space-y-3">
            <BookOpen className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">No Questions Found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {search || subjectFilter || difficultyFilter || typeFilter
                ? 'Try adjusting your search criteria or clear active filters.'
                : 'Start populating your reusable question bank by creating your first question.'}
            </p>
            <button
              onClick={handleOpenCreate}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
            >
              Add First Question
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {questions.map((q) => {
              const isSelected = selectedIds.has(q.id);
              return (
                <div
                  key={q.id}
                  className={`bg-white p-4 rounded-2xl border transition-all space-y-3 flex flex-col justify-between ${
                    isSelected
                      ? 'border-indigo-500 ring-2 ring-indigo-500/10 shadow-xs'
                      : 'border-slate-200/90 hover:border-slate-300 shadow-2xs'
                  }`}
                >
                  <div className="space-y-2">
                    {/* Card Top: Badges & Select */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-100">
                          {q.question_type}
                        </span>

                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                          {q.marks || 1}M
                        </span>

                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          q.difficulty === 'easy'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : q.difficulty === 'hard'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}>
                          {q.difficulty || 'medium'}
                        </span>

                        {q.subject && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-50 text-slate-600 border border-slate-200">
                            {q.subject}
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => toggleSelect(q.id)}
                        className="text-slate-400 hover:text-indigo-600 p-0.5"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-indigo-600" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </div>

                    {/* Question Text */}
                    <p className="text-xs font-semibold text-slate-800 leading-relaxed">
                      {q.text}
                    </p>

                    {/* Options preview for MCQ */}
                    {q.options?.length > 0 && (
                      <div className="grid grid-cols-2 gap-1.5 pt-1">
                        {q.options.map((opt, oIdx) => (
                          <div key={oIdx} className="text-[11px] p-1.5 rounded-lg bg-slate-50 border border-slate-100 text-slate-600 truncate">
                            <span className="font-bold text-slate-400 mr-1">{String.fromCharCode(65 + oIdx)}.</span>
                            {opt}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Teacher Answer Key Badge (Protected) */}
                    {q.correct_answer && (
                      <div className="p-2 rounded-lg bg-amber-50/70 border border-amber-200 text-[11px] text-amber-900 flex items-start gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-amber-950">Answer Key: </strong>
                          <span>{q.correct_answer}</span>
                          <span className="block text-[9px] text-amber-700 mt-0.5">
                            (Stored for grading; strictly excluded from student exam papers)
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Card Footer: Metadata & Actions */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                    <span className="text-[10px] text-slate-400 truncate max-w-[180px]">
                      {q.topic || q.chapter || 'General'}
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenEdit(q)}
                        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-slate-50 rounded-lg transition-colors"
                        title="Edit Question"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(q.id, q.text)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        title="Delete Question"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="bg-white p-3 rounded-2xl border border-slate-200/90 shadow-2xs flex items-center justify-between text-xs">
            <button
              onClick={() => loadQuestions(Math.max(1, page - 1))}
              disabled={page <= 1 || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 disabled:opacity-30 hover:bg-slate-50 font-medium"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            <span className="font-semibold text-slate-700">
              Page {page} of {totalPages}
            </span>

            <button
              onClick={() => loadQuestions(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 disabled:opacity-30 hover:bg-slate-50 font-medium"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Create / Edit Question Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-2xl rounded-2xl border border-slate-200 shadow-xl overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                {editingQuestion ? 'Edit Question' : 'Save Question to Bank'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-xs font-bold p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveQuestion} className="p-5 overflow-y-auto space-y-4 text-xs">
              
              {/* Question Text */}
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Question Text / Prompt *</label>
                <textarea
                  rows={3}
                  value={formText}
                  onChange={(e) => setFormText(e.target.value)}
                  placeholder="Enter the question text..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
                  required
                />
              </div>

              {/* Type, Marks, Difficulty */}
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Question Type</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {QUESTION_TYPES.map((t) => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Marks</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={formMarks}
                    onChange={(e) => setFormMarks(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Difficulty</label>
                  <select
                    value={formDifficulty}
                    onChange={(e) => setFormDifficulty(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              {/* Subject, Class, Chapter, Topic */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Subject</label>
                  <input
                    type="text"
                    value={formSubject}
                    onChange={(e) => setFormSubject(e.target.value)}
                    placeholder="e.g. Science"
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Class / Grade</label>
                  <input
                    type="text"
                    value={formClass}
                    onChange={(e) => setFormClass(e.target.value)}
                    placeholder="e.g. Class 5"
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Chapter</label>
                  <input
                    type="text"
                    value={formChapter}
                    onChange={(e) => setFormChapter(e.target.value)}
                    placeholder="e.g. Plants"
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Topic</label>
                  <input
                    type="text"
                    value={formTopic}
                    onChange={(e) => setFormTopic(e.target.value)}
                    placeholder="e.g. Photosynthesis"
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>
              </div>

              {/* MCQ Options (if MCQ) */}
              {formType === 'mcq' && (
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <label className="font-bold text-slate-700">Multiple Choice Options</label>
                  <div className="grid grid-cols-2 gap-2">
                    {formOptions.map((opt, idx) => (
                      <div key={idx} className="flex items-center gap-1.5">
                        <span className="font-bold text-slate-400 w-5 text-center">
                          {String.fromCharCode(65 + idx)}.
                        </span>
                        <input
                          type="text"
                          value={opt}
                          onChange={(e) => {
                            const next = [...formOptions];
                            next[idx] = e.target.value;
                            setFormOptions(next);
                          }}
                          placeholder={`Option ${String.fromCharCode(65 + idx)}`}
                          className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Teacher Answer Key & Explanation */}
              <div className="space-y-2 pt-2 border-t border-slate-100 bg-amber-50/50 p-3 rounded-xl border border-amber-200/80">
                <div className="flex items-center gap-1.5 text-amber-950 font-bold">
                  <Lock className="w-3.5 h-3.5 text-amber-600" />
                  <span>Teacher Answer Key &amp; Solution (Protected)</span>
                </div>
                <p className="text-[10px] text-amber-800">
                  This field is preserved in your Question Bank repository for automatic scoring, but is strictly isolated from student-facing PDF output.
                </p>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Correct Answer</label>
                  <input
                    type="text"
                    value={formCorrectAnswer}
                    onChange={(e) => setFormCorrectAnswer(e.target.value)}
                    placeholder="e.g. Option A (Photosynthesis)"
                    className="w-full p-2 bg-white border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Explanation / Solution Steps</label>
                  <textarea
                    rows={2}
                    value={formExplanation}
                    onChange={(e) => setFormExplanation(e.target.value)}
                    placeholder="Optional solution or explanation..."
                    className="w-full p-2 bg-white border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>
              </div>

              {/* Tags */}
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Tags (comma separated)</label>
                <input
                  type="text"
                  value={formTags}
                  onChange={(e) => setFormTags(e.target.value)}
                  placeholder="biology, plants, mid-term"
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                />
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-xl font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center gap-1.5 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-xs disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{editingQuestion ? 'Update Question' : 'Save to Bank'}</span>
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
