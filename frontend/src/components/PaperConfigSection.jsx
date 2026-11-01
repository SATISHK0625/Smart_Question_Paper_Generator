import React from 'react';
import { Settings, Plus, Trash2, ArrowRight, ArrowLeft, Info, CheckCircle2 } from 'lucide-react';

export default function PaperConfigSection({
  config,
  setConfig,
  referenceStyle,
  onNext,
  onBack
}) {
  const handleChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAddInstruction = () => {
    setConfig(prev => ({
      ...prev,
      general_instructions: [...(prev.general_instructions || []), '']
    }));
  };

  const handleInstructionChange = (index, value) => {
    setConfig(prev => {
      const updated = [...(prev.general_instructions || [])];
      updated[index] = value;
      return { ...prev, general_instructions: updated };
    });
  };

  const handleRemoveInstruction = (index) => {
    setConfig(prev => ({
      ...prev,
      general_instructions: prev.general_instructions.filter((_, i) => i !== index)
    }));
  };

  const isWorksheet = referenceStyle?.document_type === 'worksheet';

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Paper Configuration</h2>
        <p className="text-sm text-slate-600 mt-1">
          Specify paper metadata, layout preferences, and header options. Unspecified fields will not appear in the generated document.
        </p>

        {isWorksheet && (
          <div className="mt-4 p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200/60 text-xs text-indigo-900 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-indigo-950">Worksheet / School Paper Layout Active</p>
              <p className="text-[11px] text-indigo-800 mt-0.5">
                The generator will mirror the reference's page border, centered school titles, and unshaded section headings.
                University metadata boxes (Subject code, Semester, Max Marks) are omitted automatically unless you enter them below.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
        
        {/* Section 1: Institution & Examination Header */}
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-indigo-700">
              1. Institution &amp; Heading Banner
            </h3>

            {referenceStyle?.header_lines?.length > 0 && (
              <label className="flex items-center gap-2 text-xs font-semibold text-indigo-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.use_reference_header}
                  onChange={(e) => handleChange('use_reference_header', e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <span>Reuse Reference School &amp; Worksheet Header</span>
              </label>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Institution / School Name <span className="text-slate-400 font-normal">(Optional override)</span>
              </label>
              <input
                type="text"
                placeholder={referenceStyle?.header_lines?.[0]?.text || "e.g. SRC GLOBAL CBSE SCHOOL"}
                value={config.institution_name}
                onChange={(e) => handleChange('institution_name', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department / Faculty <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Science Department"
                value={config.department || ''}
                onChange={(e) => handleChange('department', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Examination / Document Title <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder={referenceStyle?.header_lines?.[2]?.text || "e.g. WORKSHEET"}
                value={config.exam_name}
                onChange={(e) => handleChange('exam_name', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Grade / Semester / Class <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Grade 4 – SCIENCE"
                value={config.semester_class || ''}
                onChange={(e) => handleChange('semester_class', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>
          </div>
        </div>

        <hr className="border-slate-100" />

        {/* Section 2: Subject & Marks (Optional for worksheets) */}
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-indigo-700 mb-4">
            2. Subject &amp; Marks Details <span className="text-slate-400 font-normal text-xs">(Leave blank if not needed)</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Subject Name
              </label>
              <input
                type="text"
                placeholder="e.g. Science / Mathematics"
                value={config.subject_name}
                onChange={(e) => handleChange('subject_name', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Subject Code <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. None"
                value={config.subject_code || ''}
                onChange={(e) => handleChange('subject_code', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Maximum Marks <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="number"
                min="1"
                step="0.5"
                placeholder="None"
                value={config.maximum_marks ?? ''}
                onChange={(e) => handleChange('maximum_marks', e.target.value === '' ? null : parseFloat(e.target.value))}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 font-bold text-indigo-900"
              />
            </div>

          </div>
        </div>

        <hr className="border-slate-100" />

        {/* Section 3: Formatting & Layout */}
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-indigo-700 mb-4">
            3. Page &amp; Layout Controls
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Page Size
              </label>
              <select
                value={config.page_size}
                onChange={(e) => handleChange('page_size', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 bg-white"
              >
                <option value="A4">A4 (210 × 297 mm)</option>
                <option value="Letter">Letter (8.5 × 11 in)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Header Style
              </label>
              <select
                value={config.header_style}
                onChange={(e) => handleChange('header_style', e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 bg-white"
              >
                <option value="auto">Auto (Follow Reference)</option>
                <option value="minimal">Minimal / Unbordered</option>
                <option value="underlined">Underlined Clean</option>
                <option value="boxed">Boxed Border Table</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Page Border Frame
              </label>
              <label className="flex items-center gap-2 mt-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.override_page_border ?? (referenceStyle?.has_page_border || false)}
                  onChange={(e) => handleChange('override_page_border', e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <span className="text-xs text-slate-700 font-medium">Draw Outer Page Border</span>
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Page Numbers in Footer
              </label>
              <label className="flex items-center gap-2 mt-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.show_page_numbers}
                  onChange={(e) => handleChange('show_page_numbers', e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <span className="text-xs text-slate-700 font-medium">Show 'Page X of Y'</span>
              </label>
            </div>

          </div>
        </div>

        <hr className="border-slate-100" />

        {/* Section 4: General Instructions */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-indigo-700">
                4. General Examination Instructions <span className="text-slate-400 font-normal text-xs">(Optional)</span>
              </h3>
            </div>
            <button
              onClick={handleAddInstruction}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Instruction</span>
            </button>
          </div>

          <div className="space-y-2">
            {(config.general_instructions || []).map((instr, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 w-5">{idx + 1}.</span>
                <input
                  type="text"
                  value={instr}
                  onChange={(e) => handleInstructionChange(idx, e.target.value)}
                  placeholder={`Instruction ${idx + 1}`}
                  className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                />
                <button
                  onClick={() => handleRemoveInstruction(idx)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Remove instruction"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {(!config.general_instructions || config.general_instructions.length === 0) && (
              <p className="text-xs text-slate-400 italic">No instructions specified (worksheet mode default).</p>
            )}
          </div>
        </div>

      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Questions</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
        >
          <span>Review Structure &amp; Marks</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
}
