export const TaskStatus = {
  PENDING: "PENDING",
  DOWNLOADING: "DOWNLOADING",
  UPLOADING: "UPLOADING",
  TRANSCRIBING: "TRANSCRIBING",
  SUMMARIZING: "SUMMARIZING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED"
} as const;

export type TaskStatus = typeof TaskStatus[keyof typeof TaskStatus];
export type SummaryMode = 'standard' | 'agent' | 'auto';

export interface Task {
  id: string;
  video_url: string;
  status: TaskStatus;
  created_at: string;
  latest_modified_at?: string;
  progress: number;
  title?: string;
  topic?: string;
  transcript?: string;
  summary?: string;
  error_message?: string;
  transcription_time?: number;
  audio_duration?: number;
  author_name?: string;
  author_url?: string;
  summary_mode?: SummaryMode;
  summary_chunk_total?: number;
  summary_chunk_done?: number;
  summary_meta?: string;
  folder_id?: string | null;
  source_type?: 'video' | 'wechat_article' | string;
  source_url?: string | null;
  source_meta?: string | null;
  library_visible?: boolean;
}

export interface CreateTaskRequest {
  video_url: string;
  quality: string;
  summary_mode?: Exclude<SummaryMode, 'auto'> | SummaryMode;
}

export interface CreateWechatArticleRequest {
  url: string;
  folder_id?: string | null;
  summary_mode?: SummaryMode;
}

export interface MarkdownHeadingItem {
  id: string;
  text: string;
  level: number;
}

export interface LLMProvider {
  id: string;
  label: string;
  default_base_url: string;
  default_model_id: string;
  description: string;
}

export interface LLMProfile {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model_id: string;
  temperature: number;
  context_window_size: number;
  has_api_key: boolean;
  api_key_hint: string;
}

export interface LLMSettings {
  active_profile_id: string;
  profiles: LLMProfile[];
}

export interface CreateProfileRequest {
  name: string;
  provider: string;
  base_url?: string;
  api_key?: string;
  model_id?: string;
  temperature?: number;
}

export interface UpdateProfileRequest {
  profile_id: string;
  name?: string;
  provider?: string;
  base_url?: string;
  api_key?: string;
  model_id?: string;
  temperature?: number;
  context_window_size?: number;
}

export interface SwitchActiveProfileRequest {
  profile_id: string;
}

export interface TranscriptionSettings {
  device: "cpu" | "cuda";
  model_source: "auto_download" | "manual_path";
  model_size: "tiny" | "base" | "small" | "medium" | "large";
  model_path: string;
  model_path_valid: boolean;
  model_path_message: string;
  model_path_resolved: string;
  required_model_files: string[];
  cuda_available: boolean;
  available_devices: string[];
  has_nvidia_gpu: boolean;
  torch_installed: boolean;
  torch_cuda_built: boolean;
  ctranslate2_installed: boolean;
  ctranslate2_cuda_device_count: number;
  cuda_reason: string;
  cuda_message: string;
  enable_bilibili_subtitle_fetch: boolean;
  has_bilibili_sessdata: boolean;
  bilibili_cookie_source: string;
  bilibili_sessdata_masked: string;
}

export interface UpdateTranscriptionSettingsRequest {
  device?: "cpu" | "cuda";
  model_source?: "auto_download" | "manual_path";
  model_size?: "tiny" | "base" | "small" | "medium" | "large";
  model_path?: string;
  enable_bilibili_subtitle_fetch?: boolean;
  bilibili_sessdata?: string;
  clear_bilibili_sessdata?: boolean;
}

export interface SummarizationSettings {
  mode: SummaryMode;
  auto_chunk_min_audio_duration_sec: number;
  auto_chunk_min_transcript_lines: number;
  chunk_target_duration_sec: number;
  chunk_min_duration_sec: number;
  chunk_max_duration_sec: number;
  boundary_jump_sec: number;
  prev_tail_timestamp_lines_m: number;
  prev_summary_tail_chars_j: number;
  llm_call_retry_max: number;
  max_agent_value_chars: number;
  fallback_to_standard_on_agent_error: boolean;
}

export interface UpdateSummarizationSettingsRequest {
  mode?: SummaryMode;
  auto_chunk_min_audio_duration_sec?: number;
  auto_chunk_min_transcript_lines?: number;
  chunk_target_duration_sec?: number;
  chunk_min_duration_sec?: number;
  chunk_max_duration_sec?: number;
  boundary_jump_sec?: number;
  prev_tail_timestamp_lines_m?: number;
  prev_summary_tail_chars_j?: number;
  llm_call_retry_max?: number;
  max_agent_value_chars?: number;
  fallback_to_standard_on_agent_error?: boolean;
}

export interface BilibiliCookieFromBrowserResult {
  success: boolean;
  sessdata?: string;
  sessdata_masked?: string;
  source_browser?: string;
  error?: string;
}

export interface CaptureProviderInfo {
  id: string;
  name: string;
  credential_types: string[];
  supports_validate: boolean;
}

export interface ConnectedAccount {
  id: string;
  user_id: string;
  provider: string;
  display_name?: string | null;
  credential_type: string;
  secret_masked?: string | null;
  domain_scope?: string | null;
  status: string;
  last_verified_at?: string | null;
  last_used_at?: string | null;
  last_error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ConnectedAccountUpsertRequest {
  account_id?: string;
  credential_type: string;
  payload: Record<string, string>;
  display_name?: string;
  domain_scope?: string;
}

export interface ConnectedAccountBrowserImportRequest {
  source_url?: string;
  domain_scope?: string;
  display_name?: string;
}

export interface ConnectedAccountBrowserImportResult {
  success: boolean;
  source_browser?: string | null;
  account: ConnectedAccount;
}

export interface BilibiliVideoPartInfo {
  index: number;
  cid: number;
  title: string;
  duration: number;
}

export interface BilibiliVideoInfo {
  is_multi_part: boolean;
  title: string;
  bvid: string;
  duration: number;
  parts?: BilibiliVideoPartInfo[];
}

export interface BilibiliPartsConfig {
  mode: 'merge' | 'separate';
  indices: number[];
}

export interface CollectionPreviewItem {
  provider: string;
  source_url: string;
  title: string;
  part_index?: number | null;
  duration?: number | null;
}

export interface CollectionPreview {
  provider: string;
  source_type: string;
  source_url?: string | null;
  title: string;
  total_items: number;
  items: CollectionPreviewItem[];
}

export interface CreateCollectionRequest {
  provider: string;
  source_type: string;
  source_url?: string | null;
  title: string;
  quality?: string;
  summary_mode?: SummaryMode;
  items: CollectionPreviewItem[];
}

export interface CollectionItem {
  id: string;
  job_id: string;
  sort_order: number;
  provider: string;
  source_url: string;
  title: string;
  part_index?: number | null;
  duration?: number | null;
  task_id?: string | null;
  status: string;
  task?: Task | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CollectionJob {
  id: string;
  provider: string;
  source_type: string;
  source_url?: string | null;
  title: string;
  folder_id?: string | null;
  status: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  running_items?: number;
  aggregate_markdown?: string | null;
  error_message?: string | null;
  items?: CollectionItem[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LocalFolderFile {
  name: string;
  path: string;
  size: number;
}

export interface LocalFolderScanResult {
  folder_path: string;
  files: LocalFolderFile[];
  total: number;
}

export interface LocalPathCheckResult {
  type: 'file' | 'folder' | 'not_found';
  path: string;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  folder_type: 'auto' | 'manual';
  source_video_url: string | null;
  sort_order: number;
  created_at: string;
  task_ids?: string[];
}

export interface FolderTreeNode extends Folder {
  children: FolderTreeNode[];
}

export type FolderNode = FolderTreeNode

export interface GitSettings {
  configured: boolean;
  repository_url: string;
  branch: string;
  root_path: string;
  author_name: string;
  author_email: string;
  include_transcript: boolean;
  auto_sync: boolean;
  has_private_key: boolean;
  public_key: string;
  status: 'not_configured' | 'connected' | 'error' | string;
  last_verified_at?: string | null;
  last_used_at?: string | null;
  last_error?: string | null;
}

export interface GitSettingsUpdate {
  repository_url: string;
  branch: string;
  root_path: string;
  author_name: string;
  author_email: string;
  include_transcript: boolean;
  auto_sync: boolean;
  private_key?: string;
}

export interface GitSyncResult {
  success: boolean;
  document_count: number;
  committed: boolean;
  commit_sha: string;
  created: number;
  updated: number;
  adopted: number;
  removed: number;
  conflicts: string[];
}

export type SettingsModalTab = 'llm' | 'transcription' | 'accounts' | 'summarization' | 'git';

export type ContentSubscriptionStatus = 'ACTIVE' | 'PAUSED' | 'AUTH_REQUIRED' | 'DEGRADED' | 'ERROR';
export type ContentSubscriptionInitialSyncMode = 'from_now' | 'today' | 'last_7_days';

export interface ContentSubscriptionPreview {
  provider: 'homeway';
  source_type: 'homeway_lecturer';
  external_source_id: string;
  display_name: string;
  source_url: string;
  avatar_url?: string;
  intro?: string;
  text_menu_name: string;
  menu: Array<Record<string, unknown>>;
  account_required: boolean;
  connected_account?: ConnectedAccount | null;
}

export interface ContentSubscription {
  id: string;
  user_id: string;
  provider: 'homeway' | string;
  source_type: 'homeway_lecturer' | string;
  source_url: string;
  external_source_id: string;
  display_name: string;
  connected_account_id: string;
  folder_id?: string | null;
  status: ContentSubscriptionStatus;
  poll_interval_minutes: number;
  active_window_start: string;
  active_window_end: string;
  digest_time: string;
  timezone: string;
  initial_sync_mode: ContentSubscriptionInitialSyncMode;
  last_cursor?: string | null;
  last_polled_at?: string | null;
  last_success_at?: string | null;
  next_poll_at?: string | null;
  last_digest_date?: string | null;
  last_digest_at?: string | null;
  last_error?: string | null;
  consecutive_failures: number;
  today_item_count: number;
  locked_item_count: number;
  captured_item_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ContentSubscriptionCreateRequest {
  source_url: string;
  connected_account_id: string;
  initial_sync_mode: ContentSubscriptionInitialSyncMode;
  poll_interval_minutes?: number;
  active_window_start?: string;
  active_window_end?: string;
  digest_time?: string;
  timezone?: string;
}

export interface SubscriptionRun {
  id: string;
  subscription_id: string;
  trigger: 'scheduled' | 'manual' | 'reconciliation' | string;
  status: 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED' | string;
  started_at: string;
  finished_at?: string | null;
  discovered_count: number;
  captured_count: number;
  updated_count: number;
  locked_count: number;
  failed_count: number;
  error_code?: string | null;
  error_detail?: string | null;
}

export interface LibraryDocumentPayload {
  title: string;
  content: string;
  folder_id: string | null;
}
