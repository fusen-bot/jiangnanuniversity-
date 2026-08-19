import { CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined, FileDoneOutlined } from '@ant-design/icons';
import { Card, Col, List, Progress, Row, Skeleton, Statistic, Tag, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { PageTitle } from '../components/Shell';
import type { Batch, WorkflowTask } from '../types';
import { businessLabel, statusColor, statusLabel } from '../utils/labels';

export function DashboardPage() {
  const { hasRole } = useAuth();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      api<Batch[]>('/batches'),
      hasRole('admin', 'operator', 'approver') ? api<WorkflowTask[]>('/tasks') : Promise.resolve([]),
    ])
      .then(([batchData, taskData]) => { setBatches(batchData); setTasks(taskData); })
      .finally(() => setLoading(false));
  }, [hasRole]);
  const metrics = useMemo(() => ({
    pendingReview: batches.filter((b) => b.status === 'pending_review').length,
    pendingApproval: batches.filter((b) => b.status === 'pending_approval').length,
    issues: batches.reduce((sum, b) => sum + b.issue_count, 0),
    completed: batches.filter((b) => b.status === 'exported').length,
  }), [batches]);

  if (loading) return <Skeleton active />;
  return (
    <>
      <PageTitle title="运营总览" subtitle="聚焦今天需要处理的财务批次与异常" />
      <Row gutter={[16, 16]}>
        <Metric title="待复核" value={metrics.pendingReview} icon={<ClockCircleOutlined />} tone="blue" />
        <Metric title="待审批" value={metrics.pendingApproval} icon={<FileDoneOutlined />} tone="gold" />
        <Metric title="异常记录" value={metrics.issues} icon={<ExclamationCircleOutlined />} tone="red" />
        <Metric title="已归档" value={metrics.completed} icon={<CheckCircleOutlined />} tone="green" />
      </Row>
      <Row gutter={[16, 16]} className="dashboard-grid">
        <Col xs={24} xl={15}>
          <Card title="最近批次" className="panel-card">
            <List dataSource={batches.slice(0, 6)} locale={{ emptyText: '暂无批次' }} renderItem={(batch) => (
              <List.Item extra={<Tag color={statusColor[batch.status]}>{statusLabel[batch.status]}</Tag>}>
                <List.Item.Meta title={batch.name} description={`${businessLabel[batch.business_type]} · ${batch.row_count} 条 · v${batch.version}`} />
              </List.Item>
            )} />
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card title="流程健康度" className="panel-card">
            <Typography.Paragraph type="secondary">已处理异常占当前异常总量</Typography.Paragraph>
            <Progress type="dashboard" percent={metrics.issues ? 0 : 100} strokeColor="#0f766e" />
            <Typography.Title level={5}>我的待办</Typography.Title>
            <List size="small" dataSource={tasks.filter((t) => t.status !== 'done').slice(0, 4)} renderItem={(task) => <List.Item>{task.title}</List.Item>} />
          </Card>
        </Col>
      </Row>
    </>
  );
}

function Metric({ title, value, icon, tone }: { title: string; value: number; icon: React.ReactNode; tone: string }) {
  return <Col xs={12} xl={6}><Card className={`metric-card ${tone}`}><Statistic title={title} value={value} prefix={icon} /></Card></Col>;
}
