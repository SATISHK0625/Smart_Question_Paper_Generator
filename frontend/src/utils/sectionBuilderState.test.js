import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  addSection,
  removeSection,
  moveSection,
  addQuestion,
  removeQuestion,
  moveQuestion,
  updateQuestion,
  updateSection,
  addOption,
  updateOption,
  removeOption,
  validateSections,
  computeStats,
  renumberQuestions,
} from './sectionBuilderState.js';

describe('manual section builder state', () => {
  it('adds, edits, deletes, and reorders sections', () => {
    let sections = [];
    sections = addSection(sections, 'mcq');
    sections = addSection(sections, 'short_answer');
    sections = addSection(sections, 'long_answer');
    assert.equal(sections.length, 3);
    assert.equal(sections[0].title, 'SECTION A');
    assert.equal(sections[0].question_type, 'mcq');

    sections = updateSection(sections, 1, 'title', 'PART B — SHORT ANSWER');
    assert.equal(sections[1].title, 'PART B — SHORT ANSWER');

    sections = moveSection(sections, 2, -1);
    assert.equal(sections[1].question_type, 'long_answer');
    assert.equal(sections[2].title, 'PART B — SHORT ANSWER');

    sections = removeSection(sections, 0);
    assert.equal(sections.length, 2);
    assert.equal(sections[0].question_type, 'long_answer');
  });

  it('adds, edits, deletes, and reorders questions and MCQ options', () => {
    let sections = addSection([], 'mixed');
    sections = addQuestion(sections, 0, 'mcq');
    sections = addQuestion(sections, 0, 'short_answer');
    sections = addQuestion(sections, 0, 'long_answer');
    assert.equal(sections[0].questions.length, 3);
    assert.equal(sections[0].questions[0].question_type, 'mcq');
    assert.equal(sections[0].questions[0].options.length, 4);

    sections = updateQuestion(sections, 0, 0, 'text', 'Which process converts light energy into chemical energy?');
    sections = updateOption(sections, 0, 0, 0, 'a) Photosynthesis in chloroplasts using chlorophyll');
    sections = addOption(sections, 0, 0);
    assert.equal(sections[0].questions[0].options.length, 5);
    sections = removeOption(sections, 0, 0, 4);
    assert.equal(sections[0].questions[0].options.length, 4);

    sections = moveQuestion(sections, 0, 2, -1);
    assert.equal(sections[0].questions[1].question_type, 'long_answer');
    assert.equal(sections[0].questions[2].question_type, 'short_answer');

    sections = removeQuestion(sections, 0, 2);
    assert.equal(sections[0].questions.length, 2);
    assert.equal(sections[0].questions[0].text.includes('Photosynthesis'), true);

    const stats = computeStats(sections);
    assert.equal(stats.sectionCount, 1);
    assert.equal(stats.questionCount, 2);
    assert.equal(stats.typeCounts.mcq, 1);
    assert.equal(stats.typeCounts.long_answer, 1);
  });

  it('flags empty titles, empty question text, empty sections, and missing MCQ options', () => {
    let sections = addSection([], 'mcq');
    let errors = validateSections(sections);
    assert.equal(errors.some((e) => e.type === 'empty_section'), true);

    sections = addQuestion(sections, 0, 'mcq');
    errors = validateSections(sections);
    assert.equal(errors.some((e) => e.type === 'question_text'), true);
    assert.equal(errors.some((e) => e.type === 'mcq_options'), false);

    sections = updateQuestion(sections, 0, 0, 'text', 'A valid MCQ?');
    sections = updateQuestion(sections, 0, 0, 'options', ['', '  ']);
    errors = validateSections(sections);
    assert.equal(errors.some((e) => e.type === 'mcq_options'), true);

    sections = updateSection(sections, 0, 'title', '   ');
    errors = validateSections(sections);
    assert.equal(errors.some((e) => e.type === 'section_title'), true);

    assert.equal(validateSections([]).length, 1);
  });

  it('renumbers questions sequentially after reorder', () => {
    let sections = addSection([], 'short_answer');
    sections = addQuestion(sections, 0, 'short_answer');
    sections = addQuestion(sections, 0, 'short_answer');
    sections = addQuestion(sections, 0, 'short_answer');
    sections = moveQuestion(sections, 0, 0, 1);
    sections = renumberQuestions(sections);
    assert.deepEqual(
      sections[0].questions.map((q) => q.number),
      ['1', '2', '3']
    );
  });
});
