import { CheckCircleOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons';
import { Alert, App, Button, Card, Empty, Input, List, Select, Space, Spin, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { api, post } from '../api';
import { PageTitle } from '../components/Shell';
import type { AssistantAnswer, Batch } from '../types';

export function AssistantPage() {
  const { message } = App.useApp();
  const [question, setQuestion] = useState('');
  const [batchId, setBatchId] = useState<string>();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [answers, setAnswers] = useState<AssistantAnswer[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => { api<Batch[]>('/batches').then(setBatches); }, []);
  const ask = async () => {
    if (question.trim().length < 2) return;
    setLoading(true);
    try {
      const answer = await post<AssistantAnswer>('/assistant/query', { question, batch_id: batchId });
      setAnswers((current) => [answer, ...current]); setQuestion('');
    } finally { setLoading(false); }
  };
  const confirm = async (answer: AssistantAnswer) => {
    await post('/assistant/confirm', { interaction_id: answer.interaction_id });
    message.success('已由你确认并创建业务任务');
  };
  return <>
    <PageTitle title="AI 业务副驾" subtitle="基于制度与授权数据提供建议；不代替人工审批" />
    <Alert type="info" showIcon message="AI 只能查询授权摘要和制度知识。任何写操作都会先生成建议，确认后才执行。" />
    <Card className="assistant-composer">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Select allowClear value={batchId} onChange={setBatchId} placeholder="可选：关联一个财务批次" options={batches.map((batch) => ({ value: batch.id, label: batch.name }))} />
        <Input.TextArea value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} maxLength={2000} placeholder="例如：总结这个批次的异常，并给出复核顺序建议" />
        <Button type="primary" icon={<SendOutlined />} loading={loading} onClick={() => void ask()}>发送给副驾</Button>
      </Space>
    </Card>
    {loading && <div className="centered"><Space><Spin /><span>正在检索制度与业务摘要</span></Space></div>}
    {!loading && answers.length === 0 && <Empty description="尚无对话" />}
    <List dataSource={answers} renderItem={(answer) => <Card className="assistant-answer">
      <Typography.Title level={5}><RobotOutlined /> 业务副驾建议</Typography.Title>
      {answer.warning && <Alert type="warning" showIcon message={answer.warning} />}
      <Typography.Paragraph className="answer-text">{answer.answer}</Typography.Paragraph>
      <Space wrap>{answer.sources.map((source) => <Tag key={source.id}>{source.title} · {source.source}</Tag>)}</Space>
      {answer.proposed_action && <div className="proposed-action"><strong>待确认操作：</strong>{answer.proposed_action.title}<Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => void confirm(answer)}>确认创建任务</Button></div>}
    </Card>} />
  </>;
}
