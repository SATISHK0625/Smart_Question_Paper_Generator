# Smart Question Paper Generator 📄✨

A production-ready, full-stack web application that allows educators and institutions to upload a reference question-paper PDF, author or import questions, generate a publication-ready examination paper conforming faithfully to the reference layout, and run automated quality assurance and visual difference audits before export—**built with 100% private local processing and zero paid API dependencies**.

---

## 🚀 Core Features

### 1. Template Layout Preservation Engine
- **PyMuPDF Canvas Re-Use**: Preserves reference PDF geometry, dimensions (A4, Letter), vector page borders, header dividing rules, embedded school emblems/logos, and running headers.
- **Dynamic Reference Typography**: Accurately aligns section headers, multi-line questions, and right-aligned mark brackets.
- **Non-Destructive**: Replaces text content within detected content boundaries while keeping template headers, borders, and margins intact.

### 2. Feature 1 — Visual PDF Comparison
- **Tri-Mode Visual Diff Workspace**:
  - **Side-by-Side View**: High-resolution comparative view with synchronized page navigation and zoom controls (60% to 175%).
  - **Difference Overlay**: Dual-color overlay distinguishing unwanted layout shifts in borders/margins (vivid magenta) from intended question content replacement (cyan).
  - **Thermal Difference Heatmap**: 256-color thermal gradient mapping pixel divergence with a color legend (Navy: No diff $\to$ Cyan: Minor text $\to$ Yellow: Moderate shift $\to$ Hot Magenta: High layout variance).
- **Pixel Difference Metrics**:
  - Mean Absolute Difference (MAD).
  - Overall Difference Percentage above noise threshold.
  - Layout Variance Percentage (outside content zone) vs Content Difference Percentage.
  - Diagnostic Similarity Score (0 to 100%).
- **Multi-Page & Page Deviation Detection**:
  - Handles mismatched page counts cleanly, flagging `extra_page` or `missing_page`.
  - Distinguishes expected question substitutions from structural template defects.

### 3. Feature 2 — Pre-Export Quality Assurance Checker
- **Two-Pass Validation Architecture**:
  - **Pass 1 (Pre-Generation)**: Validates structured question paper data:
    - Empty section titles and empty question text.
    - Multiple-Choice Questions: Enforces minimum 2 options, checks for blank or duplicated option values, verifies valid answer keys.
    - Match the Following: Enforces minimum 2 pairs, validates equal item counts in Column A and Column B.
    - Image & Diagram Questions: Validates image base64 decoding, file format (PNG, JPEG, WebP), 5MB size limit, and coordinate bounds ($0.0 \le x, y \le 1.0$) for diagram markers.
    - Blueprint & Marks: Sum of question marks vs configured Maximum Marks.
  - **Pass 2 (Post-Generation)**: Validates rendered PDF document:
    - Unexpected blank pages (zero text blocks and zero drawings).
    - Text block collisions and overlapping text.
    - Content overflow into margins or footer boundaries.
    - Content integrity verification ensuring no requested question text is dropped.
- **Export Blocker Gate**:
  - Export is strictly blocked if any `error` severity findings are present.
  - UI displays an interactive dashboard with severity counters (Errors, Warnings, Info), grouped findings, location markers, and actionable suggestions.

### 4. Feature 3 — Reusable Question Bank
- **Persistent Local Storage (SQLite)**:
  - Local-first single-user repository with automated versioned migrations (`schema_version` table) and WAL mode for reliability.
  - Stored in `backend/data/question_bank.db`.
- **Search & Multi-Facet Filtering**:
  - Full-text search across question prompt, topic, chapter, and subject.
  - Filter by Subject, Class/Grade, Chapter, Difficulty (`easy`, `medium`, `hard`), and Question Type.
  - Server-side pagination and sorting (`created_at`, `marks`, `difficulty`, `text`).
- **Answer-Key Isolation (Student PDF Protection)**:
  - Correct answers and step-by-step explanations are preserved in the bank repository for teacher grading.
  - Strictly stripped and excluded from student-facing examination PDF generation.
- **Independent Paper Snapshots**:
  - Adding bank questions into a paper section creates deep-copy snapshots with fresh IDs. Editing bank records later never mutates already generated or drafted exam papers.
- **Duplicate Question Detection**:
  - Real-time heuristic check for near-duplicate questions upon creation.

---

## 📁 System Architecture

```
Pdf_Formatter/
├── frontend/                     # React 19 + Vite + Tailwind CSS Single-Page Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx              # Navigation sidebar with status & health indicators
│   │   │   ├── TopNav.jsx               # Workspace title bar & quick actions
│   │   │   ├── ReferenceSection.jsx     # Stage 1: Reference PDF upload & layout analysis
│   │   │   ├── QuestionWorkspace.jsx    # Stage 2: Section & question authoring suite
│   │   │   ├── ManualSectionBuilder.jsx # Drag-and-drop sections, MCQ, diagram editors
│   │   │   ├── AdvancedQuestionEditors.jsx # Matching columns & interactive diagram markers
│   │   │   ├── QuestionBankSection.jsx  # Feature 3: Question bank browser, filters & authoring
│   │   │   ├── PreviewExportSection.jsx # Stage 3: Live PDF preview & Feature 2 Quality Checker
│   │   │   └── ComparisonWorkspace.jsx  # Feature 1: Visual diff, heatmaps & side-by-side audit
│   │   ├── services/
│   │   │   └── api.js                   # Unified REST API client
│   │   ├── App.jsx                      # App root state & workflow coordinator
│   │   └── index.css                    # Tailwind design system
│   ├── package.json
│   └── vite.config.js                   # Dev server & API proxy
│
├── backend/                      # Python 3.12 FastAPI Modular Backend
│   ├── app/
│   │   ├── main.py                      # FastAPI app entry point, CORS, lifespan temp cleanup
│   │   ├── db/
│   │   │   └── question_bank_db.py      # SQLite repository, schema migration, parameterized SQL
│   │   ├── api/
│   │   │   ├── health.py                # Health check endpoint
│   │   │   ├── reference.py             # Reference PDF upload & analysis
│   │   │   ├── questions.py             # Regex parser & file importer
│   │   │   ├── paper.py                 # PDF preview, generate, overview, review & compare
│   │   │   └── question_bank.py         # Question Bank CRUD, search, filter & snapshots
│   │   ├── services/
│   │   │   ├── pdf_analyzer.py          # PyMuPDF geometry, font & border extraction
│   │   │   ├── pdf_template_modifier.py # Direct reference template canvas preservation
│   │   │   ├── pdf_generator.py         # Dispatcher & ReportLab fallback generation
│   │   │   ├── pdf_comparison_service.py # Feature 1: Pixel metrics, overlay & thermal heatmap
│   │   │   ├── quality_checker.py       # Feature 2: Two-pass pre-export quality checker
│   │   │   ├── question_bank_service.py # Feature 3: Snapshot cloning & answer isolation
│   │   │   ├── pdf_review_service.py    # Fidelity auditing & text overlap/overflow checks
│   │   │   └── question_parser.py       # Deterministic rule-based text parser
│   │   ├── models/
│   │   │   └── schemas.py               # Pydantic data models
│   │   └── utils/
│   │       └── file_utils.py            # Temporary storage, cleanup & path sanitation
│   ├── tests/
│   │   ├── test_visual_comparison.py    # Feature 1: Visual comparison & heatmap tests
│   │   ├── test_quality_checker.py      # Feature 2: Pre-export quality gate tests
│   │   ├── test_question_bank.py        # Feature 3: SQLite persistence & snapshot tests
│   │   ├── test_advanced_question_types.py
│   │   ├── test_dynamic_reference_preservation.py
│   │   ├── test_dynamic_content_validation.py
│   │   ├── test_template_preservation.py
│   │   └── test_visual_regression.py
│   └── requirements.txt
│
└── README.md
```

---

## 🛠️ Setup & Run Instructions (Windows PowerShell)

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ (tested on Node.js 20+)

### 1. Backend Setup & Startup
```powershell
# Navigate to the backend directory
cd D:\Pdf_Formatter\backend

# Activate virtual environment (if using .venv)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup & Startup
```powershell
# In a separate terminal, navigate to the frontend directory
cd D:\Pdf_Formatter\frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Verification

### Running All Backend Tests
```powershell
cd D:\Pdf_Formatter\backend
python -m pytest -v
```
*Current test suite: **62 passed**, 0 failures.*

### Running Frontend Checks
```powershell
cd D:\Pdf_Formatter\frontend
npm run build
npm run lint
```
*Vite production build succeeds cleanly.*

---

## 📊 Endpoints & API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health and service readiness check |
| `POST` | `/api/reference/analyze` | Analyze reference PDF layout, dimensions, fonts, logos |
| `POST` | `/api/questions/parse` | Parse raw text into structured sections and questions |
| `POST` | `/api/paper/preview` | Generate live preview PDF |
| `POST` | `/api/paper/generate` | Generate final PDF (enforces pre-export quality gate) |
| `POST` | `/api/paper/quality-check` | Run Feature 2 pre-export quality assurance audit |
| `POST` | `/api/paper/compare` | Run Feature 1 visual comparison with heatmap & metrics |
| `POST` | `/api/paper/review` | Run visual fidelity review against reference template |
| `POST` | `/api/paper/overview` | Compute marks distribution & blueprint calculations |
| `GET` | `/api/bank/questions` | List, search, filter and paginate bank questions |
| `POST` | `/api/bank/questions` | Author and store a new question with answer keys |
| `GET` | `/api/bank/questions/{id}` | Retrieve question by ID |
| `PUT` | `/api/bank/questions/{id}` | Update question metadata |
| `DELETE` | `/api/bank/questions/{id}` | Delete question from repository |
| `POST` | `/api/bank/questions/{id}/snapshot` | Generate isolated Question snapshot for exam paper |
| `POST` | `/api/bank/questions/bulk` | Bulk import questions |

---

## 🔬 PDF Comparison Methodology & Limitations

1. **Pixel Differences vs Quality Assessment**:
   - A newly generated question paper contains completely different text from the uploaded reference template. A standard pixel-difference count would erroneously report ~20-30% difference even for a perfect template clone.
   - Our methodology divides the page into **Stable Regions** (outer page border, institution header lines, logos, divider rules, margins, running footers) and **Dynamic Content Zones** (question text, options, blanks).
   - Differences in Stable Regions are penalized heavily (3.5x weight) as potential layout shifts, whereas differences in Content Zones reflect intended question substitutions (0.4x weight).
2. **Thermal Heatmap Interpretation**:
   - The thermal heatmap highlights exact divergence coordinates. A dark navy border and header banner indicate complete template preservation.
3. **Scanned & Flattened PDFs**:
   - If the uploaded reference is a scanned bitmap without vector elements or selectable text, the system detects this via text density heuristics and applies fallback positioning. Exact font matching on scanned documents requires manual layout fine-tuning via the interactive controls.

---

## 🔒 Security & Reliability

- **Path Traversal Protection**: All temporary files are generated with UUID filenames within sandboxed directories.
- **Image Validation**: Base64 images are verified for format (PNG, JPEG, WebP), byte length ($\le$ 5MB), and dimensions ($\le$ 6000px).
- **Parameterized SQL**: All database operations in `question_bank_db.py` use SQLite parameter placeholders (`?`) to prevent SQL injection.
- **Resource Cleanup**: Temporary comparison PNGs and generated preview PDFs are registered with FastAPI `BackgroundTasks` for automatic cleanup.
