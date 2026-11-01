const API_BASE = '/api';

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
}

export async function analyzeReferencePdf(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/reference/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
    throw new Error(err.detail || 'Failed to analyze reference PDF');
  }

  return await res.json();
}

export async function parseQuestions(rawText) {
  const res = await fetch(`${API_BASE}/questions/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_text: rawText }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Parsing failed' }));
    throw new Error(err.detail || 'Failed to parse questions');
  }

  return await res.json();
}

export async function importQuestionsFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/questions/import`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(err.detail || 'Failed to import questions file');
  }

  return await res.json();
}

function formatApiError(err, fallback = 'Operation failed') {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (err.detail) {
    if (typeof err.detail === 'string') return err.detail;
    if (err.detail.validation_errors && Array.isArray(err.detail.validation_errors)) {
      return err.detail.validation_errors.join('\n');
    }
    if (err.detail.message) return err.detail.message;
    if (Array.isArray(err.detail)) {
      return err.detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join(', ');
    }
    try {
      return JSON.stringify(err.detail);
    } catch {
      return fallback;
    }
  }
  if (err.message) return err.message;
  return fallback;
}

export async function fetchPaperPreviewBlob(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Preview generation failed' }));
    throw new Error(formatApiError(err, 'Failed to generate PDF preview'));
  }

  return await res.blob();
}

export async function downloadPaperPdf(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Download failed' }));
    throw new Error(formatApiError(err, 'Failed to generate question paper PDF'));
  }

  const blob = await res.blob();
  const filename = `${config.subject_name.replace(/[^a-zA-Z0-9_-]/g, '_') || 'Question_Paper'}.pdf`;
  triggerDownload(blob, filename);
}

export async function fetchPaperOverview(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/overview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Overview calculation failed' }));
    throw new Error(err.detail || 'Failed to fetch paper overview');
  }

  return await res.json();
}

export async function downloadOverviewPdf(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/overview?download_pdf=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Overview PDF download failed' }));
    throw new Error(err.detail || 'Failed to download overview report PDF');
  }

  const blob = await res.blob();
  triggerDownload(blob, 'Question_Paper_Overview.pdf');
}

export async function fetchPaperReview(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Visual review failed' }));
    throw new Error(err.detail || 'Failed to perform visual comparison and review');
  }

  return await res.json();
}

export async function fetchPaperComparison(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Visual comparison failed' }));
    throw new Error(err.detail || 'Failed to run visual PDF comparison');
  }

  return await res.json();
}

export async function fetchQualityCheck(sections, config, referenceStyle) {
  const res = await fetch(`${API_BASE}/paper/quality-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sections,
      config,
      reference_style: referenceStyle,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Quality check failed' }));
    throw new Error(err.detail || 'Failed to run pre-export quality check');
  }

  return await res.json();
}

// ----------------- QUESTION BANK APIs -----------------

export async function fetchBankQuestions(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      query.append(k, v);
    }
  });

  const res = await fetch(`${API_BASE}/bank/questions?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch questions' }));
    throw new Error(err.detail || 'Failed to load questions from Question Bank');
  }
  return await res.json();
}

export async function fetchBankSubjects() {
  const res = await fetch(`${API_BASE}/bank/questions/subjects`);
  if (!res.ok) return { subjects: [] };
  return await res.json();
}

export async function createBankQuestion(questionData) {
  const res = await fetch(`${API_BASE}/bank/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(questionData),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Creation failed' }));
    throw new Error(err.detail || 'Failed to save question to bank');
  }
  return await res.json();
}

export async function updateBankQuestion(id, questionData) {
  const res = await fetch(`${API_BASE}/bank/questions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(questionData),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Update failed' }));
    throw new Error(err.detail || 'Failed to update question');
  }
  return await res.json();
}

export async function deleteBankQuestion(id) {
  const res = await fetch(`${API_BASE}/bank/questions/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Deletion failed' }));
    throw new Error(err.detail || 'Failed to delete question');
  }
  return await res.json();
}

export async function getBankQuestionSnapshot(id, number = '') {
  const res = await fetch(`${API_BASE}/bank/questions/${id}/snapshot?number=${encodeURIComponent(number)}`, {
    method: 'POST',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Snapshot failed' }));
    throw new Error(err.detail || 'Failed to clone question snapshot');
  }
  return await res.json();
}



function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }, 100);
}
