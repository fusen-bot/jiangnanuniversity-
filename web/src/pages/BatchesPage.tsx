import { CheckOutlined, CloudUploadOutlined, EyeOutlined, FileExcelOutlined, PlusOutlined } from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Card,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Upload,
} from 'antd';
import type { UploadFile } from 'antd';
import { useEffect, useState } from 'react';
import { api, patch, post } from '../api';
import { useAuth } from '../auth';
import { PageTitle } from '../components/Shell';
import type { Batch, BusinessType, Issue } from '../types';
import { businessLabel, statusColor, statusLabel } from '../utils/labels';

export function BatchesPage() {
  const { message } = App.useApp();
  const { hasRole } = useAuth();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selected, setSelected] = useState<Batch | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [form] = Form.useForm();
  const [approvalForm] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try { setBatches(await api<Batch[]>('/batches')); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const openBatch = async (batch: Batch) => {
    setSelected(batch);
    setIssues(await api<Issue[]>(`/validation-issues?batch_id=${batch.id}`));
  };

  const upload = async (values: { name: string; businessType: BusinessType; sourceSheet?: string }) => {
    const raw = uploadFiles[0]?.originFileObj;
    if (!raw) return message.error('请选择数据文件');
    const data = new FormData();
    data.append('name', values.name);
    data.append('business_type', values.businessType);
    if (values.sourceSheet?.trim()) data.append('source_sheet', values.sourceSheet.trim());
    data.append('file', raw);
    await post<Batch>('/batches/import', data);
    message.success('已进入异步导入队列');
    setUploadOpen(false);
    setUploadFiles([]);
    form.resetFields();
    await load();
  };

  const resolve = async (issue: Issue, next: 'resolved' | 'ignored') => {
    await patch<Issue>(`/validation-issues/${issue.id}`, { status: next, resolution: next === 'resolved' ? '已人工核对并修正' : '经复核确认可忽略' });
    message.success('异常已复核');
    if (selected) await openBatch(selected);
  };

  const act = async (path: string, success: string) => {
    if (!selected) return;
    const updated = await post<Batch>(path);
    setSelected(updated);
    message.success(success);
    await load();
  };

  const approve = async (values: { decision: 'approve' | 'reject'; comment: string }) => {
    if (!selected) return;
    const updated = await post<Batch>(`/approvals/${selected.id}`, values);
    setSelected(updated);
    setApprovalOpen(false);
    approvalForm.resetFields();
    message.success(values.decision === 'approve' ? '批次已批准' : '批次已驳回');
    await load();
  };

  return (
    <>
      <PageTitle title="财务批次" subtitle="审稿费、版面费与作者稿费共用一套可审计流程" extra={
        hasRole('admin', 'operator') ? <Button type="primary" icon={<PlusOutlined />} onClick={() => setUploadOpen(true)}>导入批次</Button> : undefined
      } />
      <Card className="panel-card">
        <Table rowKey="id" dataSource={batches} loading={loading} pagination={{ pageSize: 10 }} columns={[
          { title: '批次', dataIndex: 'name', render: (name: string, row: Batch) => <Space><FileExcelOutlined className="table-icon" /><div><strong>{name}</strong><div className="muted">{businessLabel[row.business_type]}</div></div></Space> },
          { title: '状态', dataIndex: 'status', render: (value: Batch['status']) => <Tag color={statusColor[value]}>{statusLabel[value]}</Tag> },
          { title: '记录', dataIndex: 'row_count', width: 90 },
          { title: '异常', dataIndex: 'issue_count', width: 90, render: (value: number) => <span className={value ? 'danger-text' : ''}>{value}</span> },
          { title: '版本', dataIndex: 'version', width: 80, render: (value: number) => `v${value}` },
          { title: '操作', width: 100, render: (_, row) => <Button type="link" icon={<EyeOutlined />} onClick={() => void openBatch(row)}>查看</Button> },
        ]} />
      </Card>

      <Modal title="导入财务批次" open={uploadOpen} onCancel={() => setUploadOpen(false)} footer={null} destroyOnHidden>
        <Alert type="info" showIcon message="Excel/CSV 仅作为输入，导入后数据进入数据库并执行规则校验。" />
        <Form form={form} layout="vertical" onFinish={(values) => void upload(values)} className="spaced-form">
          <Form.Item name="name" label="批次名称" rules={[{ required: true, min: 2 }]}><Input placeholder="例如：2026年3月审稿费" /></Form.Item>
          <Form.Item name="businessType" label="业务类型" rules={[{ required: true }]}>
            <Select options={Object.entries(businessLabel).map(([value, label]) => ({ value, label }))} />
          </Form.Item>
          <Form.Item name="sourceSheet" label="工作表名（可选）" extra="多工作表文件建议填写；留空则由系统自动识别。">
            <Input placeholder="例如：Sheet1、详细数据、2025" maxLength={160} />
          </Form.Item>
          <Upload.Dragger fileList={uploadFiles} beforeUpload={() => false} onChange={({ fileList }) => setUploadFiles(fileList.slice(-1))} accept=".xlsx,.xls,.csv" maxCount={1}>
            <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p><p>拖入或点击选择 Excel / CSV</p>
          </Upload.Dragger>
          <Button htmlType="submit" type="primary" block>导入并校验</Button>
        </Form>
      </Modal>

      <Drawer title={selected?.name} width={720} open={Boolean(selected)} onClose={() => setSelected(null)} extra={selected && <Tag color={statusColor[selected.status]}>{statusLabel[selected.status]}</Tag>}>
        {selected && <>
          <Descriptions bordered size="small" column={2} items={[
            { key: 'type', label: '业务类型', children: businessLabel[selected.business_type] },
            { key: 'version', label: '数据版本', children: `v${selected.version}` },
            { key: 'rows', label: '记录数量', children: selected.row_count },
            { key: 'issues', label: '异常数量', children: selected.issue_count },
          ]} />
          <div className="drawer-actions">
            {selected.status === 'pending_review' && hasRole('admin', 'operator') &&
              <Button type="primary" disabled={issues.some((i) => i.status === 'open')} onClick={() => void act(`/batches/${selected.id}/submit`, '已提交审批')}>提交审批</Button>}
            {selected.status === 'pending_approval' && hasRole('admin', 'approver') &&
              <Button type="primary" icon={<CheckOutlined />} onClick={() => setApprovalOpen(true)}>审批</Button>}
            {selected.status === 'approved' && hasRole('admin', 'operator') &&
              <Popconfirm title="生成正式报表并归档？" onConfirm={() => void act(`/exports/${selected.id}`, '报表已生成')}><Button>生成报表</Button></Popconfirm>}
          </div>
          <h3>校验异常</h3>
          <Table rowKey="id" size="small" dataSource={issues} pagination={false} columns={[
            { title: '级别', dataIndex: 'severity', width: 80, render: (value: string) => <Tag color={value === 'error' ? 'red' : 'orange'}>{value}</Tag> },
            { title: '问题', dataIndex: 'message' },
            { title: '状态', dataIndex: 'status', width: 90 },
            { title: '复核', width: 150, render: (_, issue) => issue.status === 'open' && hasRole('admin', 'operator') ? <Space><Button size="small" onClick={() => void resolve(issue, 'resolved')}>解决</Button><Button size="small" onClick={() => void resolve(issue, 'ignored')}>忽略</Button></Space> : issue.resolution },
          ]} />
        </>}
      </Drawer>

      <Modal title="批次审批" open={approvalOpen} onCancel={() => setApprovalOpen(false)} footer={null}>
        <Form form={approvalForm} layout="vertical" onFinish={(values) => void approve(values)}>
          <Form.Item name="decision" label="审批结论" rules={[{ required: true }]}><Select options={[{ value: 'approve', label: '批准' }, { value: 'reject', label: '驳回' }]} /></Form.Item>
          <Form.Item name="comment" label="审批意见" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={4} /></Form.Item>
          <Button type="primary" htmlType="submit" block>确认审批</Button>
        </Form>
      </Modal>
    </>
  );
}
