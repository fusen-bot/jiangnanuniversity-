import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Form, Input, Modal, Row, Select, Tag } from 'antd';
import { useEffect, useState } from 'react';
import { api, patch, post } from '../api';
import { useAuth } from '../auth';
import { PageTitle } from '../components/Shell';
import type { WorkflowTask } from '../types';

const lanes = [
  { status: 'todo', label: '待处理', color: 'default' },
  { status: 'in_progress', label: '处理中', color: 'processing' },
  { status: 'done', label: '已完成', color: 'success' },
] as const;

export function TasksPage() {
  const { message } = App.useApp();
  const { hasRole } = useAuth();
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [open, setOpen] = useState(false);
  const load = () => api<WorkflowTask[]>('/tasks').then(setTasks);
  useEffect(() => { void load(); }, []);
  const create = async (values: { title: string; description?: string }) => {
    await post('/tasks', values); setOpen(false); message.success('任务已创建'); await load();
  };
  const move = async (task: WorkflowTask, status: WorkflowTask['status']) => {
    await patch(`/tasks/${task.id}`, { status }); await load();
  };
  return <>
    <PageTitle title="任务中心" subtitle="将待办关联到财务流程，而不是散落在个人浏览器里" extra={hasRole('admin', 'operator', 'approver') ? <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>新建任务</Button> : undefined} />
    <Row gutter={16}>{lanes.map((lane) => <Col xs={24} lg={8} key={lane.status}>
      <Card title={<>{lane.label} <Tag color={lane.color}>{tasks.filter((t) => t.status === lane.status).length}</Tag></>} className="task-lane">
        {tasks.filter((t) => t.status === lane.status).map((task) => <Card size="small" key={task.id} className="task-card">
          <strong>{task.title}</strong><p>{task.description || '暂无说明'}</p>
          {hasRole('admin', 'operator', 'approver') && <Select size="small" value={task.status} onChange={(value) => void move(task, value)} options={lanes.map((item) => ({ value: item.status, label: item.label }))} />}
        </Card>)}
      </Card>
    </Col>)}</Row>
    <Modal title="新建业务任务" open={open} onCancel={() => setOpen(false)} footer={null}>
      <Form layout="vertical" onFinish={(values) => void create(values)}><Form.Item name="title" label="任务标题" rules={[{ required: true, min: 2 }]}><Input /></Form.Item><Form.Item name="description" label="说明"><Input.TextArea rows={4} /></Form.Item><Button type="primary" htmlType="submit" block>创建</Button></Form>
    </Modal>
  </>;
}
