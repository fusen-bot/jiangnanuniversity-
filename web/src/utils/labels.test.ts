import { describe, expect, it } from 'vitest';
import { businessLabel, statusLabel } from './labels';

describe('labels', () => {
  it('contains user-facing labels for every core workflow state', () => {
    expect(businessLabel.review_fee).toBe('审稿费');
    expect(statusLabel.pending_review).toBe('待复核');
    expect(statusLabel.pending_approval).toBe('待审批');
    expect(statusLabel.exported).toBe('已导出');
  });
});
