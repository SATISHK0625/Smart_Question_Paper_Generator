from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FontDetail(BaseModel):
    name: str
    size: float
    is_bold: bool = False
    is_italic: bool = False
    count: int = 1

class HeaderLine(BaseModel):
    text: str
    font_size: float = 12.0
    is_bold: bool = True
    alignment: str = "center" # "center", "left", "right"
    y_offset: float = 0.0

class ReferenceAnalysis(BaseModel):
    page_count: int = 0
    page_size: str = "A4"
    page_width_pt: float = 595.28
    page_height_pt: float = 841.89
    margins: Dict[str, float] = Field(default_factory=lambda: {"top": 35.0, "bottom": 35.0, "left": 40.0, "right": 40.0})
    detected_fonts: List[FontDetail] = Field(default_factory=list)
    primary_font: str = "Helvetica"
    primary_font_size: float = 10.0
    heading_font_size: float = 12.0
    has_header: bool = False
    header_text: Optional[str] = None
    has_footer: bool = False
    footer_text: Optional[str] = None
    has_page_numbers: bool = False
    is_scanned: bool = False
    text_density: float = 0.0
    columns_detected: int = 1
    warnings: List[str] = Field(default_factory=list)
    raw_summary: str = ""

    # Rich Layout Structure Engine properties
    document_type: str = "worksheet" # "worksheet", "exam_paper", "minimal"
    has_page_border: bool = False
    border_inset_pt: float = 25.0
    border_width_pt: float = 1.2
    border_color_hex: str = "#000000"
    header_lines: List[HeaderLine] = Field(default_factory=list)
    has_header_divider: bool = False
    header_logo_base64: Optional[str] = None
    header_logo_width: float = 70.0
    header_logo_height: float = 40.0
    has_metadata_box: bool = False
    section_style: Dict[str, Any] = Field(default_factory=lambda: {
        "has_background": False,
        "font_size": 11.0,
        "is_bold": True,
        "alignment": "left",
        "space_before": 8.0,
        "space_after": 4.0
    })
    question_style: Dict[str, Any] = Field(default_factory=lambda: {
        "font_size": 10.0,
        "line_spacing": 14.0,
        "option_layout": "inline", # "inline", "vertical", "grid"
        "indent_pt": 0.0
    })
    matching_columns_detected: bool = False
    footer_has_line: bool = False
    reference_id: Optional[str] = None
    reference_pdf_path: Optional[str] = None
    structural_capacity: Optional[Dict[str, Any]] = None

class SubQuestion(BaseModel):
    id: str
    label: str
    text: str
    marks: Optional[float] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None

class DiagramMarker(BaseModel):
    id: str
    number: int
    x: float # Normalized coordinate 0.0 to 1.0
    y: float # Normalized coordinate 0.0 to 1.0
    label: Optional[str] = None # Correct answer part name (answer key)

class Question(BaseModel):
    id: str
    number: str
    text: str
    marks: Optional[float] = None
    options: List[str] = Field(default_factory=list) # e.g. ["a) Rock", "b) Soil", "c) Water", "d) Air"]
    subquestions: List[SubQuestion] = Field(default_factory=list)
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    is_optional: bool = False
    or_group: Optional[str] = None
    is_matching: bool = False
    matching_col_a: Optional[str] = None
    matching_col_b: Optional[str] = None
    question_type: Optional[str] = None # "mcq", "short_answer", "long_answer", "fill_in_the_blanks", "true_false", "matching", "image_based", "diagram_identify", "mixed"

    # Feature A: Match the Following
    matching_left: List[str] = Field(default_factory=list) # e.g. ["A. Left 1", "B. Left 2"]
    matching_right: List[str] = Field(default_factory=list) # e.g. ["1. Right 1", "2. Right 2"]
    shuffle_right: bool = False
    matching_answers: Optional[Dict[str, str]] = None # Answer mapping e.g. {"A": "2", "B": "1"}

    # Feature B: Image-Based Questions
    image_base64: Optional[str] = None # data:image/png;base64,...
    image_caption: Optional[str] = None
    image_width_ratio: Optional[float] = 0.65 # Fraction of printable width (0.2 to 1.0)

    # Feature C: Identify the Parts of a Diagram
    diagram_mode: Optional[str] = "numbered_markers" # "numbered_markers" or "blank_lines"
    diagram_markers: List[DiagramMarker] = Field(default_factory=list)

    # Question Bank & Blueprint Traceability
    bank_question_id: Optional[str] = None
    difficulty: Optional[str] = None
    topic: Optional[str] = None
    chapter: Optional[str] = None
    is_locked: bool = False
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    rubric: Optional[str] = None
    alternative_answers: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)

class Section(BaseModel):
    id: str
    title: str
    instructions: Optional[str] = None
    questions: List[Question] = Field(default_factory=list)
    total_marks_available: Optional[float] = 0.0
    expected_marks: Optional[float] = None
    required_count: Optional[int] = None
    question_type: Optional[str] = "mixed" # "mcq", "short_answer", "long_answer", "fill_in_the_blanks", "true_false", "mixed"

class PaperConfig(BaseModel):
    institution_name: str = ""
    department: Optional[str] = ""
    exam_name: str = ""
    subject_name: str = ""
    subject_code: Optional[str] = ""
    semester_class: Optional[str] = ""
    date_str: Optional[str] = ""
    duration: Optional[str] = ""
    maximum_marks: Optional[float] = None
    general_instructions: List[str] = Field(default_factory=list)
    page_size: str = "A4" # "A4" or "Letter"
    header_style: str = "auto" # "auto", "reference", "boxed", "underlined", "minimal"
    use_reference_header: bool = True
    show_page_numbers: bool = False # Follows reference; worksheets typically do not have page footers
    overview_placement: str = "none" # "separate", "end_of_paper", "start_of_paper", "none"
    reference_id: Optional[str] = None
    reference_pdf_path: Optional[str] = None
    adaptation_mode: str = "extend_template" # "extend_template", "adapt_content", "preserve_blocks"

    # User Interactive Layout Overrides
    override_font_size: Optional[float] = None
    override_margins: Optional[Dict[str, float]] = None
    override_line_spacing: Optional[float] = None
    override_page_border: Optional[bool] = None
    override_heading_align: Optional[str] = None
    override_section_spacing: Optional[float] = None

class QualityFindingLocation(BaseModel):
    section: Optional[str] = None
    section_id: Optional[str] = None
    question_number: Optional[str] = None
    question_id: Optional[str] = None
    page_number: Optional[int] = None

class QualityFinding(BaseModel):
    code: str
    severity: str # "error", "warning", "info"
    message: str
    location: QualityFindingLocation = Field(default_factory=QualityFindingLocation)
    suggested_action: str

class QualityReport(BaseModel):
    status: str # "passed", "has_warnings", "blocked"
    can_export: bool
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    total_questions: int = 0
    total_sections: int = 0
    total_marks: float = 0.0
    configured_max_marks: Optional[float] = None
    page_count: int = 0
    reference_comparison_status: str = "not_compared" # "passed", "review", "mismatch", "not_compared"
    findings: List[QualityFinding] = Field(default_factory=list)

class ValidationIssue(BaseModel):
    severity: str # "error", "warning", "info"
    message: str
    location: Optional[str] = None


class SectionSummary(BaseModel):
    section_id: str
    section_title: str
    question_count: int
    total_marks_available: float
    expected_marks: Optional[float] = None
    required_count: Optional[int] = None
    instructions: Optional[str] = None

class OverviewData(BaseModel):
    total_questions_count: int
    total_sections_count: int
    section_summaries: List[SectionSummary]
    total_marks_sum: float
    calculated_student_marks: float
    configured_max_marks: Optional[float] = None
    marks_match: bool
    optional_questions_detected: bool
    missing_marks_count: int
    duplicate_numbers: List[str]
    numbering_gaps: List[str]
    validation_issues: List[ValidationIssue]
    page_count: int = 1
    page_size: str = "A4"

class ParseQuestionsRequest(BaseModel):
    raw_text: str

class ParseQuestionsResponse(BaseModel):
    sections: List[Section]
    extracted_instructions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    uncertain_items_count: int = 0

class GeneratePaperRequest(BaseModel):
    sections: List[Section]
    config: PaperConfig
    reference_style: Optional[ReferenceAnalysis] = None

class DifferenceItem(BaseModel):
    category: str # "layout_difference", "content_error", "expected_content_change"
    severity: str # "verified", "uncertain", "info"
    title: str
    description: str
    page_number: Optional[int] = None

class VisualPageComparison(BaseModel):
    page_number: int
    status: str = "passed" # "passed", "review", "mismatch", "extra_page", "missing_page"
    status_label: Optional[str] = None
    dimensions_match: bool = True
    difference_percentage: float = 0.0
    layout_difference_percentage: float = 0.0
    content_difference_percentage: float = 0.0
    similarity_score: float = 100.0
    mean_abs_difference: float = 0.0
    reference_image_data: Optional[str] = None
    generated_image_data: Optional[str] = None
    side_by_side_data: Optional[str] = None
    diff_overlay_data: Optional[str] = None
    heatmap_data: Optional[str] = None
    notes: Optional[str] = None

class DifferenceReport(BaseModel):
    status: str = "success" # "success", "warning", "error"
    validation_status: str = "PASS" # "PASS", "WARNING", "FAIL"
    fidelity_score: int = 100
    reference_pages: int = 1
    generated_pages: int = 1
    passes: List[str] = Field(default_factory=list)
    layout_differences: List[DifferenceItem] = Field(default_factory=list)
    content_errors: List[DifferenceItem] = Field(default_factory=list)
    expected_content_changes: List[str] = Field(default_factory=list)
    page_comparisons: List[VisualPageComparison] = Field(default_factory=list)
    auto_fixable_actions: List[str] = Field(default_factory=list)
    side_by_side_images: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    comparison_summary: Optional[Dict[str, Any]] = None


# ==========================================
# Feature 4: Exam Blueprint Schemas
# ==========================================

class DifficultyDistribution(BaseModel):
    easy: float = 30.0
    medium: float = 50.0
    hard: float = 20.0

class BlueprintConfig(BaseModel):
    id: Optional[str] = None
    name: str = "Exam Blueprint"
    subject: str = ""
    class_level: str = ""
    chapter: Optional[str] = ""
    topic: Optional[str] = ""
    total_marks: float = 100.0
    target_question_count: Optional[int] = None
    distribution_basis: str = "marks" # "marks" or "count"
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)
    question_types: List[str] = Field(default_factory=list) # e.g. ["mcq", "short_answer", "long_answer"]
    allow_approximate: bool = False
    section_structure: str = "by_type" # "by_type", "by_difficulty", "single_section"
    reuse_questions: bool = True
    random_seed: Optional[int] = None
    locked_question_ids: List[str] = Field(default_factory=list)

class BlueprintShortfall(BaseModel):
    category: str # "easy", "medium", "hard", "total_marks", "question_count"
    required: float
    available: float
    shortfall: float
    message: str

class AchievedCategoryDistribution(BaseModel):
    target_marks: float = 0.0
    achieved_marks: float = 0.0
    target_percentage: float = 0.0
    achieved_percentage: float = 0.0
    question_count: int = 0

class AchievedDistributionReport(BaseModel):
    distribution_basis: str = "marks"
    total_marks: float = 0.0
    total_questions: int = 0
    easy: AchievedCategoryDistribution = Field(default_factory=AchievedCategoryDistribution)
    medium: AchievedCategoryDistribution = Field(default_factory=AchievedCategoryDistribution)
    hard: AchievedCategoryDistribution = Field(default_factory=AchievedCategoryDistribution)
    unlabeled_count: int = 0
    rounding_note: Optional[str] = None

class BlueprintGenerationResult(BaseModel):
    blueprint_id: Optional[str] = None
    name: str
    config: BlueprintConfig
    sections: List[Section]
    selected_question_ids: List[str]
    total_marks: float
    total_questions: int
    achieved_distribution: AchievedDistributionReport
    is_exact_match: bool
    is_approximate: bool = False
    shortfalls: List[BlueprintShortfall] = Field(default_factory=list)
    unmet_requirements: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    unlabeled_questions_found: int = 0
    locked_question_count: int = 0

class BlueprintReplaceRequest(BaseModel):
    blueprint_id: Optional[str] = None
    current_question_id: str
    replacement_question_id: str
    sections: List[Section]

# ==========================================
# Feature 5: Teacher Answer Key Schemas
# ==========================================

class AnswerKeyItem(BaseModel):
    question_id: str
    bank_question_id: Optional[str] = None
    number: str
    section_title: str
    question_text: str
    question_type: str
    marks: float
    has_answer: bool
    status: str # "available", "not_provided"
    correct_answer: Optional[str] = None
    alternative_answers: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    rubric: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    matching_pairs: Optional[Dict[str, str]] = None
    diagram_mode: Optional[str] = None
    diagram_markers: List[DiagramMarker] = Field(default_factory=list)
    image_base64: Optional[str] = None
    image_caption: Optional[str] = None

class TeacherAnswerKeySummary(BaseModel):
    total_questions: int = 0
    total_marks: float = 0.0
    questions_with_answers: int = 0
    questions_missing_answers: int = 0
    questions_with_rubrics: int = 0
    inconsistencies: List[str] = Field(default_factory=list)
    items: List[AnswerKeyItem] = Field(default_factory=list)

class GenerateAnswerKeyRequest(BaseModel):
    sections: List[Section]
    config: PaperConfig
    reference_style: Optional[ReferenceAnalysis] = None


