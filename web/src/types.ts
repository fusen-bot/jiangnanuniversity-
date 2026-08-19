export type RoleCode = 'admin' | 'operator' | 'approver' | 'viewer';
export type BusinessType = 'review_fee' | 'page_fee' | 'royalty';
export type BatchStatus =
  | 'draft'
  | 'validating'
  | 'pending_review'
  | 'pending_approval'
  | 'approved'
  | 'exported'
  | 'rejected'
  | 'validation_failed'
  | 'task_failed';

export interface Role { id: string; code: RoleCode; name: string }
export interface User {
  id: string;
  username: string;
  display_name: string;
  is_active: boolean;
  roles: Role[];
}

export interface Batch {
  id: string;
  name: string;
  business_type: BusinessType;
  status: BatchStatus;
  row_count: number;
  issue_count: number;
  version: number;
  source_file_id?: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: string;
  batch_id: string;
  record_type: BusinessType;
  record_id?: string;
  code: string;
  severity: string;
  message: string;
  status: 'open' | 'resolved' | 'ignored';
  resolution?: string;
  created_at: string;
}

export interface WorkflowTask {
  id: string;
  title: string;
  description?: string;
  status: 'todo' | 'in_progress' | 'done';
  batch_id?: string;
  assignee_id?: string;
  created_at: string;
}

export interface StoredFile {
  id: string;
  original_name: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
  category: string;
  uploaded_by_id: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details: Record<string, unknown>;
  request_id?: string;
}

export interface AssistantAnswer {
  interaction_id: string;
  answer: string;
  sources: Array<{ id: string; title: string; source: string }>;
  proposed_action?: { type: string; title: string; batch_id?: string };
  warning?: string;
}
