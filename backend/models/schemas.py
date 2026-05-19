from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


DailyIntakeCategory = Literal['vegetable', 'frozen', 'meat']
DailyIntakeSource = Literal['manual', 'voice']
DailyIntakeParseStatus = Literal['parsed', 'invalid']
InventoryDirection = Literal['IN', 'OUT', 'ADJUST']
InventorySourceType = Literal['daily_intake', 'manual_outbound', 'manual_adjust']


class ConfigResponse(BaseModel):
    config: dict


class ConfigUpdateRequest(BaseModel):
    updates: dict


class DetectRequest(BaseModel):
    folder_path: str
    date: str


class DetectResponse(BaseModel):
    files: list[str]
    count: int


class VarietiesRequest(BaseModel):
    table_paths: list[str]


class VarietiesResponse(BaseModel):
    varieties: list[str]
    count: int


class DedupRequest(BaseModel):
    veg_names: list[str]


class DedupResponse(BaseModel):
    original: list[str]
    deduplicated: list[str]
    removed_count: int


class TransferRequest(BaseModel):
    table_paths: list[str]
    small_template_path: str
    veg_names: list[str]
    output_dir: str
    small_type: str = '滨鲜'


class TransferDetail(BaseModel):
    variety: str
    rate: str
    result: str


class TransferResponse(BaseModel):
    success: bool
    processed_files: int
    matched_count: int
    written_count: int
    output_file: str | None = None
    message: str
    details: list[TransferDetail] = []


class BrowseRequest(BaseModel):
    path: str = ''


class BrowseResponse(BaseModel):
    path: str
    subdirs: list[str]
    files: list[str] = []


class GenerateRatesRequest(BaseModel):
    veg_text: str


class GenerateRatesItem(BaseModel):
    variety: str
    rate: str


class GenerateRatesResponse(BaseModel):
    data: list[GenerateRatesItem]
    count: int


class DedupJsonRequest(BaseModel):
    json_text: str


class DedupJsonResponse(BaseModel):
    data: list[GenerateRatesItem]
    removed_count: int


class FormatJsonRequest(BaseModel):
    json_text: str


class FormatJsonResponse(BaseModel):
    json_text: str


class FindFilesRequest(BaseModel):
    big_dir: str
    small_dir: str
    year: str
    month: str
    day: str


class FindFilesResponse(BaseModel):
    big_file: str
    small_file: str
    big_exists: bool
    small_exists: bool


class ExecuteTaskRequest(BaseModel):
    big_path: str
    small_path: str
    json_text: str
    date_label: str
    output_dir: str
    inspector_name: str = '朱林初'


class ExecuteTaskResponse(BaseModel):
    success: bool
    message: str
    data_count: int
    output_dir: str


class WeeklyPricePreviewRequest(BaseModel):
    update_path: str
    reference_path: str


class WeeklyPriceExecuteRequest(BaseModel):
    update_path: str
    reference_path: str
    output_path: str


class WeeklyPriceMatchedItem(BaseModel):
    name: str
    old_price: float | None = None
    new_price: float
    changed: bool
    match_type: Literal['exact', 'alias'] = 'exact'


class WeeklyPriceSuggestionCandidate(BaseModel):
    target_name: str
    score: float


class WeeklyPriceSuggestedMatch(BaseModel):
    source_name: str
    candidates: list[WeeklyPriceSuggestionCandidate] = []
    preselected_target_name: str | None = None


class WeeklyPricePreviewResponse(BaseModel):
    success: bool
    message: str
    matched_count: int
    updated_count: int
    matched_items: list[WeeklyPriceMatchedItem] = []
    not_matched: list[str] = []
    not_matched_count: int = 0
    not_matched_unique_count: int = 0
    suggested_matches: list[WeeklyPriceSuggestedMatch] = []
    alias_hit_count: int = 0
    warnings: list[str] = []
    update_start_row: int = 0
    reference_start_row: int = 0


class WeeklyPriceAliasItem(BaseModel):
    source_name: str
    target_name: str


class WeeklyPriceAliasListResponse(BaseModel):
    aliases: list[WeeklyPriceAliasItem] = []
    total: int = 0


class WeeklyPriceAliasUpsertRequest(BaseModel):
    mappings: dict[str, str]


class WeeklyPriceAliasDeleteRequest(BaseModel):
    source_name: str


class WeeklyPriceExecuteResponse(BaseModel):
    success: bool
    message: str
    matched_count: int
    updated_count: int
    matched_items: list[WeeklyPriceMatchedItem] = []
    not_matched: list[str] = []
    not_matched_count: int = 0
    not_matched_unique_count: int = 0
    alias_hit_count: int = 0
    warnings: list[str] = []
    output_path: str
    backup_path: str | None = None


class WeeklyQuoteEntryInput(BaseModel):
    name: str
    unit: str = "斤"
    price: float = Field(gt=0)


class WeeklyQuoteBatchInput(BaseModel):
    supplier: str
    quote_date: str
    entries: list[WeeklyQuoteEntryInput] = []


class WeeklyQuoteImportRequest(BaseModel):
    supplier: str
    quote_date: str
    source_path: str


class WeeklyQuoteSummaryItem(BaseModel):
    name: str
    unit: str
    summary_price: float
    average_price: float | None = None


class WeeklyQuoteUnitSummary(BaseModel):
    supplier: str
    batch_count: int = 0
    entry_count: int = 0
    summary_items: list[WeeklyQuoteSummaryItem] = []


class WeeklyQuoteImportResponse(BaseModel):
    success: bool
    message: str
    batch: WeeklyQuoteBatchInput


class WeeklyQuotePreviewRequest(BaseModel):
    batches: list[WeeklyQuoteBatchInput] = []


class WeeklyQuotePreviewResponse(BaseModel):
    success: bool
    message: str
    unit_summaries: list[WeeklyQuoteUnitSummary] = []
    total_batches: int = 0
    total_entries: int = 0
    total_summary_items: int = 0
    issue_messages: list[str] = []


class WeeklyQuoteExportRequest(BaseModel):
    workbook_path: str
    batches: list[WeeklyQuoteBatchInput] = []


class WeeklyQuoteExportResponse(BaseModel):
    success: bool
    message: str
    workbook_path: str
    sheet_names: list[str] = []
    unit_summaries: list[WeeklyQuoteUnitSummary] = []
    total_batches: int = 0
    total_entries: int = 0
    total_summary_items: int = 0


class WeeklyQuoteSupplierOption(BaseModel):
    id: int | None = None
    name: str
    weekly_batch_limit: int = 7
    summary_rule: Literal['highest', 'average'] = 'highest'
    is_builtin: bool = False
    sort_order: int = 1000


class WeeklyQuoteMeasureUnitOption(BaseModel):
    id: int | None = None
    name: str
    sort_order: int = 1000


class WeeklyQuoteSummaryOptionsResponse(BaseModel):
    success: bool
    suppliers: list[WeeklyQuoteSupplierOption] = []
    measure_units: list[WeeklyQuoteMeasureUnitOption] = []


class WeeklyQuoteSupplierCreateRequest(BaseModel):
    name: str
    weekly_batch_limit: int = Field(default=7, ge=1, le=7)
    summary_rule: Literal['highest', 'average'] = 'highest'


class WeeklyQuoteSupplierCreateResponse(BaseModel):
    success: bool
    message: str
    supplier: WeeklyQuoteSupplierOption


class WeeklyQuoteMeasureUnitCreateRequest(BaseModel):
    name: str


class WeeklyQuoteMeasureUnitCreateResponse(BaseModel):
    success: bool
    message: str
    measure_unit: WeeklyQuoteMeasureUnitOption


class DailyIntakeItemUpsertRequest(BaseModel):
    intake_date: str
    name: str
    category: Literal['vegetable', 'frozen', 'meat']
    quantity: float
    unit: str
    source: Literal['manual', 'voice'] | None = 'manual'
    transcript: str | None = ''


class DailyIntakeItemUpdateRequest(BaseModel):
    name: str
    category: Literal['vegetable', 'frozen', 'meat']
    quantity: float
    unit: str
    source: Literal['manual', 'voice'] | None = 'manual'
    transcript: str | None = ''


class DailyIntakeItemResponse(BaseModel):
    id: int
    sheet_id: int
    veg_id: int | None = None
    raw_name: str
    normalized_name: str
    category: Literal['vegetable', 'frozen', 'meat']
    quantity: float
    source: Literal['manual', 'voice']
    transcript: str = ''
    last_source: Literal['manual', 'voice']
    last_transcript: str = ''
    merge_count: int = 1
    last_confirmed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    unit_id: int
    unit_name: str


class DailyIntakeSheetData(BaseModel):
    id: int
    intake_date: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    item_count: int = 0
    total_quantity: float = 0
    quantity_by_unit: dict[str, float] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    items: list[DailyIntakeItemResponse] = Field(default_factory=list)


class DailyIntakeSheetResponse(BaseModel):
    success: bool
    message: str
    sheet: DailyIntakeSheetData


class DailyIntakeItemMutationResponse(BaseModel):
    success: bool
    message: str
    item: DailyIntakeItemResponse | None = None
    sheet: DailyIntakeSheetData
    merged: bool = False


class DailyIntakeDeleteResponse(BaseModel):
    success: bool
    message: str
    sheet: DailyIntakeSheetData


class DailyIntakeHistoryEntry(BaseModel):
    id: int
    intake_date: str
    status: str
    item_count: int = 0
    total_quantity: float = 0
    created_at: str | None = None
    updated_at: str | None = None


class DailyIntakeHistoryResponse(BaseModel):
    success: bool
    message: str
    sheets: list[DailyIntakeHistoryEntry] = Field(default_factory=list)
    total: int = 0


class DailyIntakeSpeechCapabilitiesResponse(BaseModel):
    success: bool
    stable_transcription_enabled: bool = False
    provider: str | None = None
    model: str | None = None
    requested_device: str | None = None
    requested_compute_type: str | None = None
    device: str | None = None
    compute_type: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    primary_provider: str | None = None
    backup_provider: str | None = None
    failover_enabled: bool = False
    shadow_compare_enabled: bool = False
    providers: list[dict] = Field(default_factory=list)
    message: str


class DailyIntakeSpeechDiagnosticsResponse(BaseModel):
    success: bool
    dependency_available: bool = False
    provider: str | None = None
    model: str | None = None
    requested_device: str | None = None
    requested_compute_type: str | None = None
    resolved_device: str | None = None
    resolved_compute_type: str | None = None
    effective_device: str | None = None
    effective_compute_type: str | None = None
    cuda_device_count: int = 0
    supported_compute_types_cpu: list[str] = Field(default_factory=list)
    supported_compute_types_cuda: list[str] = Field(default_factory=list)
    missing_cuda_runtime_dlls: list[str] = Field(default_factory=list)
    model_loaded: bool = False
    runtime_checked: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None
    suggested_fix: str | None = None
    primary_provider: str | None = None
    backup_provider: str | None = None
    failover_enabled: bool = False
    shadow_compare_enabled: bool = False
    providers: list[dict] = Field(default_factory=list)
    message: str


class DailyIntakeParseRequest(BaseModel):
    intake_date: str
    transcript: str
    category: Literal['vegetable', 'frozen', 'meat'] | None = None


class DailyIntakeMergePreview(BaseModel):
    item_id: int
    current_quantity: float
    next_quantity: float
    unit_name: str
    merge_count: int


class DailyIntakeParseResponse(BaseModel):
    success: bool
    message: str
    raw_transcript: str
    draft_name: str | None = None
    normalized_name: str | None = None
    quantity: float | None = None
    unit: str | None = None
    category_hint: Literal['vegetable', 'frozen', 'meat'] | None = None
    warnings: list[str] = Field(default_factory=list)
    parse_status: Literal['parsed', 'invalid']
    requires_confirmation: bool = True
    merge_preview: DailyIntakeMergePreview | None = None
    asr_provider: str | None = None
    asr_model: str | None = None
    asr_fallback_used: bool = False
    asr_fallback_reason: str | None = None
    asr_duration_ms: int | None = None
    asr_warnings: list[str] = Field(default_factory=list)
    asr_shadow_recorded: bool = False


class InventoryBalanceItem(BaseModel):
    display_name: str
    normalized_name: str
    veg_id: int | None = None
    unit_id: int
    unit_name: str
    available_quantity: float
    transaction_count: int
    last_business_date: str | None = None
    updated_at: str | None = None


class InventoryBalanceListResponse(BaseModel):
    success: bool
    message: str
    items: list[InventoryBalanceItem] = Field(default_factory=list)
    total: int = 0


class InventoryTransactionResponse(BaseModel):
    id: int
    display_name: str
    normalized_name: str
    veg_id: int | None = None
    unit_id: int
    unit_name: str
    direction: Literal['IN', 'OUT', 'ADJUST']
    quantity: float
    quantity_delta: float
    business_date: str
    source_type: Literal['daily_intake', 'manual_outbound', 'manual_adjust']
    source_ref_id: int | None = None
    target_quantity: float | None = None
    note: str = ''
    created_at: str | None = None
    updated_at: str | None = None


class InventoryTransactionListResponse(BaseModel):
    success: bool
    message: str
    items: list[InventoryTransactionResponse] = Field(default_factory=list)
    total: int = 0


class InventoryOutboundRequest(BaseModel):
    business_date: str
    name: str
    unit: str
    quantity: float
    note: str | None = ''


class InventoryAdjustmentRequest(BaseModel):
    business_date: str
    name: str
    unit: str
    target_quantity: float
    note: str | None = ''


class InventoryTransactionMutationResponse(BaseModel):
    success: bool
    message: str
    transaction: InventoryTransactionResponse


class InventoryDeleteResponse(BaseModel):
    success: bool
    message: str

class MonthlyListEntryItem(BaseModel):
    date: str
    names: list[str] = Field(default_factory=list)


class MonthlyListParseError(BaseModel):
    line: int
    message: str
    raw: str = ''


class MonthlyListParseResponse(BaseModel):
    success: bool
    entries: list[MonthlyListEntryItem] = Field(default_factory=list)
    errors: list[MonthlyListParseError] = Field(default_factory=list)
    detected_month: str = ''
    total_dates: int = 0
    total_names: int = 0
    message: str = ''


class PesticideTemplateInfo(BaseModel):
    configured: bool = False
    path: str = ''
    filename: str = ''
    updated_at: str = ''


class PesticideTemplateStatusResponse(BaseModel):
    big_template: PesticideTemplateInfo
    small_template: PesticideTemplateInfo


class TransferTemplateInfo(BaseModel):
    configured: bool = False
    path: str = ''
    filename: str = ''
    updated_at: str = ''


class TransferTemplateStatusResponse(BaseModel):
    templates: dict[str, TransferTemplateInfo] = Field(default_factory=dict)


class MonthlyTransferGroup(BaseModel):
    date: str
    files: list[str] = Field(default_factory=list)
    count: int = 0


class MonthlyTransferPreviewResponse(BaseModel):
    success: bool = False
    groups: list[MonthlyTransferGroup] = Field(default_factory=list)
    unrecognized_files: list[str] = Field(default_factory=list)
    total_files: int = 0
    message: str = ''


class WeeklyQuoteSaveRequest(BaseModel):
    supplier: str
    quote_date: str
    entries: list[WeeklyQuoteEntryInput]
    source_label: str = "手动录入"


class WeeklyQuoteDeleteRequest(BaseModel):
    supplier: str
    quote_date: str


class WeeklyQuoteWeekSummaryRequest(BaseModel):
    supplier: str
    date: str


class WeeklyQuoteWeekSummaryResponse(BaseModel):
    success: bool
    supplier: str
    batch_count: int = 0
    entry_count: int = 0
    summary_items: list[WeeklyQuoteSummaryItem] = []
    total_summary_items: int = 0


class WeeklyQuoteSavedBatchResponse(BaseModel):
    id: int
    supplier: str
    quote_date: str
    entry_count: int = 0
    entries: list[WeeklyQuoteEntryInput] = []
    source_label: str = ''
    source_path: str = ''
    created_at: str = ''


class WeeklyQuoteSupplierWeekOverview(BaseModel):
    supplier: str
    limit: int
    summary_rule: Literal['highest', 'average'] = 'highest'
    batches: list[WeeklyQuoteSavedBatchResponse] = []
    batch_count: int = 0
    entry_count: int = 0
    summary_items: list[WeeklyQuoteSummaryItem] = []


class WeeklyQuoteWeekOverviewResponse(BaseModel):
    success: bool
    week_start: str
    week_end: str
    suppliers: list[WeeklyQuoteSupplierWeekOverview] = []
    total_batches: int = 0
    total_entries: int = 0
    total_summary_items: int = 0
    issue_messages: list[str] = []


# ==================== Smart Detection ====================

from typing import Optional


class SmartRecommendResponse(BaseModel):
    today_intake: list[dict] = []
    yesterday_inventory: list[dict] = []
    missing_dates: list[str] = []


class SmartExecuteRequest(BaseModel):
    selected_varieties: list[str] = Field(default_factory=list)
    date: str = ""
    big_template: str = ""
    small_template: str = ""
    output_dir: str = ""
    inspector_name: str = "检测员"
    manual_additions: list[str] = Field(default_factory=list)
    export_format: str = "docx"


class SmartExecuteResponse(BaseModel):
    success: bool = False
    error: Optional[str] = None
    output_paths: dict = Field(default_factory=dict)
    pdf_files: list[str] = Field(default_factory=list)
    low_stock_alerts: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class BackfillRequest(BaseModel):
    start_date: str
    end_date: str
    inspector_name: str = "检测员"


class BackfillResponse(BaseModel):
    success: bool = False
    results: list[dict] = Field(default_factory=list)


class GapResponse(BaseModel):
    missing_dates: list[str] = Field(default_factory=list)
    last_detection_date: Optional[str] = None
    total_missing: int = 0


class PrepareResponse(BaseModel):
    big_template: str = ""
    small_template: str = ""
    output_dir: str = ""
    inspector_name: str = ""
