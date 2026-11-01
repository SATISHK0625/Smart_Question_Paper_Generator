export const QUESTION_TYPES = [
  { id: 'mixed', label: 'Mixed Types' },
  { id: 'mcq', label: 'Multiple Choice (MCQ)' },
  { id: 'short_answer', label: 'Short Answer' },
  { id: 'long_answer', label: 'Long Answer' },
  { id: 'fill_in_the_blanks', label: 'Fill in the Blanks' },
  { id: 'true_false', label: 'True / False' },
  { id: 'matching', label: 'Match the Following' },
  { id: 'image_based', label: 'Image-Based Question' },
  { id: 'diagram_identify', label: 'Identify the Parts of a Diagram' },
];

export const DEFAULT_OPTIONS_MCQ = ['a) Option A', 'b) Option B', 'c) Option C', 'd) Option D'];
export const DEFAULT_OPTIONS_TF = ['a) True', 'b) False'];

function uid(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

export function moveItem(list, index, direction) {
  const target = index + direction;
  if (target < 0 || target >= list.length) return list;
  const copy = [...list];
  const [moved] = copy.splice(index, 1);
  copy.splice(target, 0, moved);
  return copy;
}

export function createSection(existingCount, qType = 'mixed') {
  const nextChar = String.fromCharCode(65 + existingCount);
  return {
    id: uid('sec'),
    title: `SECTION ${nextChar}`,
    instructions: 'Answer all questions.',
    question_type: qType,
    questions: [],
    total_marks_available: 0,
    expected_marks: 0,
    required_count: null,
  };
}

export function defaultMarksForType(questionType) {
  if (questionType === 'mcq' || questionType === 'true_false' || questionType === 'fill_in_the_blanks') {
    return 1.0;
  }
  if (questionType === 'long_answer') {
    return 5.0;
  }
  if (questionType === 'matching') {
    return 4.0;
  }
  if (questionType === 'image_based') {
    return 3.0;
  }
  if (questionType === 'diagram_identify') {
    return 5.0;
  }
  return 2.0;
}

export function defaultOptionsForType(questionType) {
  if (questionType === 'mcq') return [...DEFAULT_OPTIONS_MCQ];
  if (questionType === 'true_false') return [...DEFAULT_OPTIONS_TF];
  return [];
}

export function createQuestion(number, questionType) {
  const isMatching = questionType === 'matching';
  const isDiagram = questionType === 'diagram_identify';

  return {
    id: uid('q'),
    number: String(number),
    text: isMatching
      ? 'Match the items in Column A with Column B:'
      : isDiagram
      ? 'Identify the parts marked in the diagram below:'
      : '',
    marks: defaultMarksForType(questionType),
    question_type: questionType,
    options: defaultOptionsForType(questionType),
    subquestions: [],
    // Advanced Question Types
    matching_left: isMatching ? ['A. Item 1', 'B. Item 2', 'C. Item 3'] : [],
    matching_right: isMatching ? ['1. Match 1', '2. Match 2', '3. Match 3'] : [],
    shuffle_right: true,
    matching_answers: isMatching ? { 'A': '1', 'B': '2', 'C': '3' } : {},
    image_base64: null,
    image_caption: '',
    image_width_ratio: 0.65,
    diagram_mode: isDiagram ? 'numbered_markers' : null,
    diagram_markers: [],
    is_flagged: false,
    flag_reason: null,
  };
}

export function recomputeSectionMarks(section) {
  const total = (section.questions || []).reduce((acc, q) => acc + (parseFloat(q.marks) || 0), 0);
  const rounded = Math.round(total * 100) / 100;
  return {
    ...section,
    total_marks_available: rounded,
    expected_marks: rounded,
  };
}

export function recomputeAllMarks(sections) {
  return sections.map(recomputeSectionMarks);
}

export function nextQuestionNumber(sections) {
  let total = 0;
  for (const sec of sections) {
    total += sec.questions?.length || 0;
  }
  return String(total + 1);
}

export function addSection(sections, qType = 'mixed') {
  return recomputeAllMarks([...sections, createSection(sections.length, qType)]);
}

export function removeSection(sections, secIdx) {
  return recomputeAllMarks(sections.filter((_, i) => i !== secIdx));
}

export function moveSection(sections, secIdx, direction) {
  return moveItem(sections, secIdx, direction);
}

export function updateSection(sections, secIdx, field, value) {
  const copy = [...sections];
  copy[secIdx] = recomputeSectionMarks({ ...copy[secIdx], [field]: value });
  return copy;
}

export function addQuestion(sections, secIdx, customType = null) {
  const sec = sections[secIdx];
  const effectiveType = customType || (sec.question_type !== 'mixed' ? sec.question_type : 'short_answer');
  const newQ = createQuestion(nextQuestionNumber(sections), effectiveType);
  const copy = [...sections];
  copy[secIdx] = recomputeSectionMarks({
    ...copy[secIdx],
    questions: [...(copy[secIdx].questions || []), newQ],
  });
  return copy;
}

export function removeQuestion(sections, secIdx, qIdx) {
  const copy = [...sections];
  copy[secIdx] = recomputeSectionMarks({
    ...copy[secIdx],
    questions: copy[secIdx].questions.filter((_, i) => i !== qIdx),
  });
  return copy;
}

export function moveQuestion(sections, secIdx, qIdx, direction) {
  const copy = [...sections];
  copy[secIdx] = {
    ...copy[secIdx],
    questions: moveItem(copy[secIdx].questions, qIdx, direction),
  };
  return copy;
}

export function updateQuestion(sections, secIdx, qIdx, field, value) {
  const copy = [...sections];
  const q = { ...copy[secIdx].questions[qIdx], [field]: value };
  if (field === 'question_type') {
    if (value === 'mcq' && (!q.options || q.options.length === 0)) {
      q.options = defaultOptionsForType('mcq');
    } else if (value === 'true_false' && (!q.options || q.options.length === 0)) {
      q.options = defaultOptionsForType('true_false');
    }
  }
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = q;
  copy[secIdx] = recomputeSectionMarks({ ...copy[secIdx], questions });
  return copy;
}

export function addOption(sections, secIdx, qIdx) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const currentOpts = q.options || [];
  const nextLetter = String.fromCharCode(97 + currentOpts.length);
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, options: [...currentOpts, `${nextLetter}) `] };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function updateOption(sections, secIdx, qIdx, optIdx, value) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const optsCopy = [...(q.options || [])];
  optsCopy[optIdx] = value;
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, options: optsCopy };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function removeOption(sections, secIdx, qIdx, optIdx) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, options: (q.options || []).filter((_, i) => i !== optIdx) };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function addSubQuestion(sections, secIdx, qIdx) {
  const subLabels = ['(a)', '(b)', '(c)', '(d)', '(e)', '(f)'];
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const currentSubs = q.subquestions || [];
  const nextLabel = subLabels[currentSubs.length] || `(${currentSubs.length + 1})`;
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = {
    ...q,
    subquestions: [
      ...currentSubs,
      { id: uid('sq'), label: nextLabel, text: '', marks: null },
    ],
  };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function updateSubQuestion(sections, secIdx, qIdx, sqIdx, field, value) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const subsCopy = [...(q.subquestions || [])];
  subsCopy[sqIdx] = { ...subsCopy[sqIdx], [field]: value };
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, subquestions: subsCopy };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function removeSubQuestion(sections, secIdx, qIdx, sqIdx) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, subquestions: (q.subquestions || []).filter((_, i) => i !== sqIdx) };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

// ─── Matching Helpers ─────────────────────────────
export function addMatchingRow(sections, secIdx, qIdx) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const left = [...(q.matching_left || [])];
  const right = [...(q.matching_right || [])];
  const answers = { ...(q.matching_answers || {}) };
  const nextIdx = left.length;
  const nextKey = String.fromCharCode(65 + nextIdx);
  left.push('');
  right.push('');
  answers[nextKey] = String(nextIdx + 1);
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, matching_left: left, matching_right: right, matching_answers: answers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function updateMatchingRow(sections, secIdx, qIdx, side, rowIdx, value) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const arr = [...(side === 'left' ? q.matching_left : q.matching_right) || []];
  arr[rowIdx] = value;
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, [side === 'left' ? 'matching_left' : 'matching_right']: arr };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function removeMatchingRow(sections, secIdx, qIdx, rowIdx) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const left = (q.matching_left || []).filter((_, i) => i !== rowIdx);
  const right = (q.matching_right || []).filter((_, i) => i !== rowIdx);
  // Rebuild answer mapping with new keys
  const answers = {};
  left.forEach((_, i) => {
    const key = String.fromCharCode(65 + i);
    answers[key] = String(i + 1);
  });
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, matching_left: left, matching_right: right, matching_answers: answers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function updateMatchingAnswer(sections, secIdx, qIdx, leftKey, rightValue) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const answers = { ...(q.matching_answers || {}), [leftKey]: rightValue };
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, matching_answers: answers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

// ─── Diagram Marker Helpers ──────────────────────
export function addDiagramMarker(sections, secIdx, qIdx, x, y) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const markers = [...(q.diagram_markers || [])];
  const nextNum = markers.length + 1;
  markers.push({
    id: `marker-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    number: nextNum,
    x: Math.round(x * 10000) / 10000,
    y: Math.round(y * 10000) / 10000,
    label: '',
  });
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, diagram_markers: markers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function updateDiagramMarker(sections, secIdx, qIdx, markerId, field, value) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const markers = (q.diagram_markers || []).map((m) =>
    m.id === markerId ? { ...m, [field]: value } : m
  );
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, diagram_markers: markers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function removeDiagramMarker(sections, secIdx, qIdx, markerId) {
  const copy = [...sections];
  const q = copy[secIdx].questions[qIdx];
  const markers = (q.diagram_markers || [])
    .filter((m) => m.id !== markerId)
    .map((m, i) => ({ ...m, number: i + 1 }));
  const questions = [...copy[secIdx].questions];
  questions[qIdx] = { ...q, diagram_markers: markers };
  copy[secIdx] = { ...copy[secIdx], questions };
  return copy;
}

export function renumberQuestions(sections) {
  let current = 1;
  return sections.map((sec) => ({
    ...sec,
    questions: (sec.questions || []).map((q) => ({
      ...q,
      number: String(current++),
    })),
  }));
}

export function computeStats(sections) {
  let qCount = 0;
  let marksSum = 0;
  const typeCounts = {
    mcq: 0,
    short_answer: 0,
    long_answer: 0,
    fill_in_the_blanks: 0,
    true_false: 0,
    matching: 0,
    image_based: 0,
    diagram_identify: 0,
    other: 0,
  };

  sections.forEach((s) => {
    (s.questions || []).forEach((q) => {
      qCount += 1;
      marksSum += parseFloat(q.marks) || 0;
      const effectiveType = (q.question_type || s.question_type || 'short_answer').toLowerCase();
      if (typeCounts[effectiveType] !== undefined) {
        typeCounts[effectiveType] += 1;
      } else {
        typeCounts.other += 1;
      }
    });
  });

  return {
    sectionCount: sections.length,
    questionCount: qCount,
    marksSum: Math.round(marksSum * 100) / 100,
    typeCounts,
  };
}

export function validateSections(sections) {
  const errors = [];
  if (sections.length === 0) {
    errors.push({
      type: 'general',
      message: 'At least one section must be created before generating a paper.',
    });
    return errors;
  }

  sections.forEach((sec, sIdx) => {
    const sNum = sIdx + 1;
    const sTitle = sec.title?.trim();
    if (!sTitle) {
      errors.push({
        type: 'section_title',
        secIndex: sIdx,
        message: `Section ${sNum}: Section title is required.`,
      });
    }

    if (!sec.questions || sec.questions.length === 0) {
      errors.push({
        type: 'empty_section',
        secIndex: sIdx,
        message: `Section ${sNum} (${sTitle || 'Untitled'}): Add at least one question.`,
      });
    }

    (sec.questions || []).forEach((q, qIdx) => {
      const qNum = q.number ? `Question ${q.number}` : `Question #${qIdx + 1}`;
      if (!q.text?.trim()) {
        errors.push({
          type: 'question_text',
          secIndex: sIdx,
          qIndex: qIdx,
          message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Question text cannot be empty.`,
        });
      }

      const effectiveType = (q.question_type || sec.question_type || '').toLowerCase();
      if (effectiveType === 'mcq') {
        const validOpts = (q.options || []).filter((o) => o && o.trim().length > 0);
        if (validOpts.length < 2) {
          errors.push({
            type: 'mcq_options',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: MCQ requires at least 2 non-empty options.`,
          });
        }
      }

      if (effectiveType === 'matching') {
        const left = q.matching_left || [];
        const right = q.matching_right || [];
        if (left.length < 2 || right.length < 2) {
          errors.push({
            type: 'matching_count',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Match the Following requires at least 2 pairs.`,
          });
        } else if (left.length !== right.length) {
          errors.push({
            type: 'matching_mismatch',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Column A and Column B must have equal item counts.`,
          });
        }
      }

      if (effectiveType === 'image_based') {
        if (!q.image_base64) {
          errors.push({
            type: 'image_missing',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Please upload or paste an image for this question.`,
          });
        }
      }

      if (effectiveType === 'diagram_identify') {
        if (!q.image_base64) {
          errors.push({
            type: 'diagram_missing',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Please upload or paste a diagram image.`,
          });
        } else if (!q.diagram_markers || q.diagram_markers.length === 0) {
          errors.push({
            type: 'markers_missing',
            secIndex: sIdx,
            qIndex: qIdx,
            message: `Section ${sNum} (${sTitle || 'Untitled'}), ${qNum}: Add at least one marker on the diagram.`,
          });
        }
      }
    });
  });

  return errors;
}
