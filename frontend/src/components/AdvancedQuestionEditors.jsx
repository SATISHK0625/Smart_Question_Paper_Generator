import React from 'react';
import {
  Plus,
  Trash2,
  CheckCircle2,
  Upload,
  Columns,
  MapPin,
  Shuffle,
  Image as ImageIcon
} from 'lucide-react';

/**
 * Match the Following Editor
 * Renders editable Column A / Column B pairs with shuffle toggle and answer key.
 */
export function MatchingEditor({
  q, secIdx, qIdx,
  handleUpdateQuestion,
  handleAddMatchingRow,
  handleUpdateMatchingRow,
  handleRemoveMatchingRow,
  handleUpdateMatchingAnswer
}) {
  return (
    <div className="mt-3 sm:ml-16 p-3.5 bg-teal-50/40 rounded-xl border border-teal-200/80 space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-teal-800 uppercase tracking-wider flex items-center gap-1.5">
            <Columns className="w-3.5 h-3.5 text-teal-600" />
            <span>Column A &amp; Column B Pairs</span>
          </span>
          <span className="text-[10px] text-teal-600 font-medium bg-teal-100/70 px-2 py-0.5 rounded-full">
            {(q.matching_left || []).length} Pairs
          </span>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer bg-white px-2 py-1 rounded-lg border border-teal-200 shadow-2xs">
            <input
              type="checkbox"
              checked={q.shuffle_right ?? true}
              onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'shuffle_right', e.target.checked)}
              className="w-3.5 h-3.5 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
            />
            <Shuffle className="w-3 h-3 text-teal-600" />
            <span className="text-[11px] font-medium">Shuffle Column B</span>
          </label>

          <button
            onClick={() => handleAddMatchingRow(secIdx, qIdx)}
            className="text-[11px] font-semibold text-teal-700 hover:text-teal-900 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-100 hover:bg-teal-200/80 border border-teal-300/60 transition-colors"
          >
            <Plus className="w-3 h-3" />
            <span>Add Pair</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-teal-200/80 overflow-hidden shadow-2xs divide-y divide-teal-100">
        <div className="grid grid-cols-12 gap-2 p-2 bg-teal-100/50 text-[10px] font-bold text-teal-900 uppercase tracking-wider">
          <div className="col-span-5">Column A (Premise)</div>
          <div className="col-span-5">Column B (Response)</div>
          <div className="col-span-2 text-right">Answer</div>
        </div>

        {(q.matching_left || []).map((lItem, rIdx) => {
          const leftKey = String.fromCharCode(65 + rIdx);
          const rItem = (q.matching_right || [])[rIdx] || '';
          const currentAnswer = (q.matching_answers || {})[leftKey] || String(rIdx + 1);

          return (
            <div key={rIdx} className="grid grid-cols-12 gap-2 p-2 items-center hover:bg-teal-50/30 transition-colors">
              <div className="col-span-5 flex items-center gap-1.5">
                <span className="w-5 text-center font-bold text-xs text-teal-800 shrink-0">{leftKey}.</span>
                <input
                  type="text"
                  value={lItem}
                  onChange={(e) => handleUpdateMatchingRow(secIdx, qIdx, 'left', rIdx, e.target.value)}
                  placeholder={`Item ${leftKey}`}
                  className="flex-1 text-xs bg-slate-50 focus:bg-white border border-slate-200 rounded-md px-2 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div className="col-span-5 flex items-center gap-1.5">
                <span className="w-5 text-center font-bold text-xs text-teal-800 shrink-0">{rIdx + 1}.</span>
                <input
                  type="text"
                  value={rItem}
                  onChange={(e) => handleUpdateMatchingRow(secIdx, qIdx, 'right', rIdx, e.target.value)}
                  placeholder={`Match ${rIdx + 1}`}
                  className="flex-1 text-xs bg-slate-50 focus:bg-white border border-slate-200 rounded-md px-2 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div className="col-span-2 flex items-center justify-end gap-1.5">
                <select
                  value={currentAnswer}
                  onChange={(e) => handleUpdateMatchingAnswer(secIdx, qIdx, leftKey, e.target.value)}
                  className="text-[11px] font-semibold bg-teal-50 border border-teal-200 rounded px-1.5 py-0.5 text-teal-900"
                  title="Correct match"
                >
                  {(q.matching_right || []).map((_, optI) => (
                    <option key={optI} value={String(optI + 1)}>
                      {leftKey} → {optI + 1}
                    </option>
                  ))}
                </select>
                {(q.matching_left || []).length > 2 && (
                  <button
                    onClick={() => handleRemoveMatchingRow(secIdx, qIdx, rIdx)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                    title="Remove pair"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Answer Key Footer */}
      <div className="text-[11px] text-teal-700 bg-teal-100/40 border border-teal-200 rounded-lg p-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
          <span>Answer Key: {Object.entries(q.matching_answers || {}).map(([k, v]) => `${k}→${v}`).join(', ')}</span>
        </span>
        <span className="text-[10px] text-teal-600 italic">Excluded from student paper</span>
      </div>
    </div>
  );
}


/**
 * Image-Based Question Editor
 * Supports file upload and clipboard paste, preview, caption, and width control.
 */
export function ImageBasedEditor({
  q, secIdx, qIdx,
  handleUpdateQuestion,
  handleImagePaste,
  handleImageFileInput
}) {
  return (
    <div className="mt-3 sm:ml-16 p-3.5 bg-sky-50/40 rounded-xl border border-sky-200/80 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold text-sky-900 uppercase tracking-wider flex items-center gap-1.5">
          <ImageIcon className="w-3.5 h-3.5 text-sky-600" />
          <span>Question Image Attachment</span>
        </span>
        <span className="text-[10px] text-slate-500 font-medium">PNG, JPEG, WebP (Max 5MB)</span>
      </div>

      {!q.image_base64 ? (
        <div
          onPaste={(e) => handleImagePaste(e, secIdx, qIdx)}
          tabIndex={0}
          className="border-2 border-dashed border-sky-300 hover:border-sky-400 bg-white rounded-xl p-5 text-center focus:outline-none focus:ring-2 focus:ring-sky-500/40 transition-all cursor-pointer"
          onClick={() => document.getElementById(`file-upload-${secIdx}-${qIdx}`)?.click()}
        >
          <Upload className="w-6 h-6 text-sky-500 mx-auto mb-2" />
          <div className="text-xs font-semibold text-slate-800">
            Click to upload image or <span className="text-sky-600 font-bold underline">Paste from Clipboard (Ctrl+V)</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Supports figures, charts, apparatus setups, or graphs</div>
          <input
            id={`file-upload-${secIdx}-${qIdx}`}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => handleImageFileInput(e, secIdx, qIdx)}
          />
        </div>
      ) : (
        <div className="space-y-3">
          <div className="relative bg-slate-900/5 rounded-xl p-2 border border-slate-200 flex flex-col items-center">
            <img src={q.image_base64} alt="Question attachment" className="max-h-52 object-contain rounded-lg shadow-xs" />
            <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/90 backdrop-blur-xs px-2 py-1 rounded-lg border border-slate-200 shadow-xs">
              <button
                onClick={() => document.getElementById(`file-replace-${secIdx}-${qIdx}`)?.click()}
                className="text-[11px] font-semibold text-slate-700 hover:text-indigo-600"
              >Replace</button>
              <input
                id={`file-replace-${secIdx}-${qIdx}`}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(e) => handleImageFileInput(e, secIdx, qIdx)}
              />
              <span className="text-slate-300">|</span>
              <button
                onClick={() => handleUpdateQuestion(secIdx, qIdx, 'image_base64', null)}
                className="text-[11px] font-semibold text-rose-600 hover:text-rose-800"
              >Remove</button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
            <div className="sm:col-span-8 flex items-center gap-2">
              <label className="text-[11px] font-bold text-slate-500 uppercase shrink-0">Caption:</label>
              <input
                type="text"
                value={q.image_caption || ''}
                onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'image_caption', e.target.value)}
                placeholder="e.g. Figure 1: Internal Structure of Plant Cell"
                className="flex-1 text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500 italic"
              />
            </div>
            <div className="sm:col-span-4 flex items-center justify-end gap-2">
              <label className="text-[11px] font-bold text-slate-500 uppercase shrink-0">Width:</label>
              <select
                value={q.image_width_ratio || 0.65}
                onChange={(e) => handleUpdateQuestion(secIdx, qIdx, 'image_width_ratio', parseFloat(e.target.value))}
                className="text-xs bg-white border border-slate-300 rounded-md px-2 py-1 text-slate-800"
              >
                <option value={0.40}>Small (40%)</option>
                <option value={0.65}>Standard (65%)</option>
                <option value={0.80}>Large (80%)</option>
                <option value={0.95}>Full Width (95%)</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


/**
 * Diagram Identification Editor
 * Click-to-place markers on a diagram image, with numbered badges and answer-key labels.
 */
export function DiagramIdentifyEditor({
  q, secIdx, qIdx,
  handleUpdateQuestion,
  handleImagePaste,
  handleImageFileInput,
  handleDiagramClick,
  handleUpdateDiagramMarker,
  handleRemoveDiagramMarker
}) {
  return (
    <div className="mt-3 sm:ml-16 p-3.5 bg-indigo-50/40 rounded-xl border border-indigo-200/80 space-y-3">
      {/* Header + Mode Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-indigo-900 uppercase tracking-wider flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-indigo-600" />
            <span>Diagram Identification Editor</span>
          </span>
          <span className="text-[10px] text-indigo-700 font-medium bg-indigo-100 px-2 py-0.5 rounded-full">
            {(q.diagram_markers || []).length} Markers
          </span>
        </div>

        <div className="flex items-center gap-1 bg-white p-0.5 rounded-lg border border-indigo-200">
          <button
            onClick={() => handleUpdateQuestion(secIdx, qIdx, 'diagram_mode', 'numbered_markers')}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
              (q.diagram_mode || 'numbered_markers') === 'numbered_markers'
                ? 'bg-indigo-600 text-white shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Mode 1: Numbered Badges
          </button>
          <button
            onClick={() => handleUpdateQuestion(secIdx, qIdx, 'diagram_mode', 'blank_lines')}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
              q.diagram_mode === 'blank_lines'
                ? 'bg-indigo-600 text-white shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Mode 2: Blank Label Lines
          </button>
        </div>
      </div>

      {/* Image Upload / Diagram Canvas */}
      {!q.image_base64 ? (
        <div
          onPaste={(e) => handleImagePaste(e, secIdx, qIdx)}
          tabIndex={0}
          className="border-2 border-dashed border-indigo-300 hover:border-indigo-400 bg-white rounded-xl p-5 text-center focus:outline-none focus:ring-2 focus:ring-indigo-500/40 transition-all cursor-pointer"
          onClick={() => document.getElementById(`diagram-upload-${secIdx}-${qIdx}`)?.click()}
        >
          <Upload className="w-6 h-6 text-indigo-500 mx-auto mb-2" />
          <div className="text-xs font-semibold text-slate-800">
            Click to upload diagram or <span className="text-indigo-600 font-bold underline">Paste from Clipboard (Ctrl+V)</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Upload anatomy, apparatus, chemical structure, or engineering diagram</div>
          <input
            id={`diagram-upload-${secIdx}-${qIdx}`}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => handleImageFileInput(e, secIdx, qIdx)}
          />
        </div>
      ) : (
        <div className="space-y-3">
          {/* Clickable Diagram Canvas */}
          <div className="bg-slate-900/5 rounded-xl p-3 border border-indigo-200">
            <div className="text-[11px] text-indigo-800 font-semibold mb-2 flex items-center justify-between">
              <span>Click on the diagram to place markers:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => document.getElementById(`diagram-replace-${secIdx}-${qIdx}`)?.click()}
                  className="text-[10px] text-indigo-600 hover:underline font-bold"
                >Replace Diagram</button>
                <input
                  id={`diagram-replace-${secIdx}-${qIdx}`}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(e) => handleImageFileInput(e, secIdx, qIdx)}
                />
                <button
                  onClick={() => handleUpdateQuestion(secIdx, qIdx, 'image_base64', null)}
                  className="text-[10px] text-rose-600 hover:underline font-bold"
                >Clear</button>
              </div>
            </div>

            <div
              onClick={(e) => handleDiagramClick(e, secIdx, qIdx)}
              className="relative mx-auto max-w-lg cursor-crosshair rounded-lg overflow-hidden border border-slate-300 bg-white select-none"
            >
              <img src={q.image_base64} alt="Diagram" className="w-full h-auto block pointer-events-none" />
              {(q.diagram_markers || []).map((marker, mIdx) => (
                <div
                  key={marker.id || mIdx}
                  style={{
                    left: `${marker.x * 100}%`,
                    top: `${marker.y * 100}%`,
                    transform: 'translate(-50%, -50%)',
                  }}
                  className="absolute flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs border-2 border-white shadow-md pointer-events-auto cursor-pointer hover:scale-110 transition-transform"
                  title={`Marker ${marker.number}: ${marker.label || 'Unlabeled'} — Click to remove`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveDiagramMarker(secIdx, qIdx, marker.id);
                  }}
                >
                  {marker.number || mIdx + 1}
                </div>
              ))}
            </div>
          </div>

          {/* Marker Answer Key Table */}
          <div className="bg-white rounded-lg border border-indigo-200 overflow-hidden divide-y divide-indigo-100">
            <div className="p-2 bg-indigo-100/60 text-[10px] font-bold text-indigo-900 uppercase tracking-wider flex items-center justify-between">
              <span>Parts Answer Key (Excluded from Student Paper)</span>
              <span>Position</span>
            </div>

            {(q.diagram_markers || []).length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-500 italic">
                No markers placed yet. Click on the diagram above to add identification points.
              </div>
            ) : (
              (q.diagram_markers || []).map((marker, mIdx) => (
                <div key={marker.id || mIdx} className="p-2 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
                    {marker.number || mIdx + 1}
                  </span>
                  <input
                    type="text"
                    value={marker.label || ''}
                    onChange={(e) => handleUpdateDiagramMarker(secIdx, qIdx, marker.id, 'label', e.target.value)}
                    placeholder={`Part ${marker.number} correct name, e.g. Chloroplast`}
                    className="flex-1 text-xs bg-slate-50 focus:bg-white border border-slate-200 rounded-md px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {Math.round(marker.x * 100)}%, {Math.round(marker.y * 100)}%
                  </span>
                  <button
                    onClick={() => handleRemoveDiagramMarker(secIdx, qIdx, marker.id)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    title="Remove marker"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
