import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import { useState } from 'react';
import { ApiError } from '../api';
import { useAuth } from '../auth';

export function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (values: { username: string; password: string }) => {
    setSubmitting(true);
    setError('');
    try { await login(values.username, values.password); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : '登录失败'); }
    finally { setSubmitting(false); }
  };

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="eyebrow"><SafetyCertificateOutlined /> 企业财务流程 · 人机协同</div>
        <Typography.Title>让期刊财务从文件流转<br />升级为可审计的业务闭环</Typography.Title>
        <Typography.Paragraph>统一处理审稿费、版面费与作者稿费，异常有复核、操作有依据、审批有留痕。</Typography.Paragraph>
        <div className="flow-line"><span>数据导入</span><i /><span>规则校验</span><i /><span>人工复核</span><i /><span>审批导出</span></div>
      </section>
      <Card className="login-card" variant="borderless">
        <Typography.Title level={3}>登录工作台</Typography.Title>
        <Typography.Paragraph type="secondary">使用分配给你的机构账号继续</Typography.Paragraph>
        {error && <Alert type="error" showIcon message={error} />}
        <Form layout="vertical" onFinish={(values) => void submit(values)} initialValues={{ username: 'admin', password: 'Admin123!' }}>
          <Form.Item name="username" label="账号" rules={[{ required: true }]}><Input prefix={<UserOutlined />} size="large" autoComplete="username" /></Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password prefix={<LockOutlined />} size="large" autoComplete="current-password" /></Form.Item>
          <Button type="primary" htmlType="submit" size="large" block loading={submitting}>安全登录</Button>
        </Form>
        <Typography.Text type="secondary" className="demo-hint">演示账号已预填；其他角色账号见 README。</Typography.Text>
      </Card>
    </main>
  );
}
