import type { BatchStatus, BusinessType } from '../types';

export const businessLabel: Record<BusinessType, string> = {
  review_fee: '审稿费', page_fee: '版面费', royalty: '作者稿费',
};

export const statusLabel: Record<BatchStatus, string> = {
  draft: '草稿', validating: '校验中', pending_review: '待复核', pending_approval: '待审批',
  approved: '已批准', exported: '已导出', rejected: '已驳回', validation_failed: '校验失败', task_failed: '任务失败',
};

export const statusColor: Record<BatchStatus, string> = {
  draft: 'default', validating: 'processing', pending_review: 'warning', pending_approval: 'gold',
  approved: 'success', exported: 'cyan', rejected: 'error', validation_failed: 'error', task_failed: 'error',
};
