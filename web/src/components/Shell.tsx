import {
  AuditOutlined,
  BankOutlined,
  FileOutlined,
  LogoutOutlined,
  MessageOutlined,
  SearchOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Input, Layout, Menu, Space, Typography } from 'antd';
import { ReactNode, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

const { Header, Sider, Content } = Layout;

export function Shell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasRole } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const items = [
    { key: '/', icon: <BankOutlined />, label: '运营总览' },
    { key: '/batches', icon: <UnorderedListOutlined />, label: '财务批次' },
    ...(hasRole('admin', 'operator', 'approver') ? [{ key: '/tasks', icon: <TeamOutlined />, label: '任务中心' }] : []),
    { key: '/assistant', icon: <MessageOutlined />, label: 'AI 业务副驾' },
    { key: '/files', icon: <FileOutlined />, label: '文件中心' },
    ...(hasRole('admin', 'approver') ? [{ key: '/audit', icon: <AuditOutlined />, label: '审计记录' }] : []),
  ];

  return (
    <Layout className="app-shell">
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={232} className="app-sider">
        <div className="brand"><span>刊财</span>{!collapsed && <strong>智能运营平台</strong>}</div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={items} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索批次、稿件或人员"
            className="global-search"
            onPressEnter={(event) => navigate(`/batches?q=${encodeURIComponent(event.currentTarget.value)}`)}
          />
          <Space>
            <Avatar>{user?.display_name.slice(0, 1)}</Avatar>
            <div className="user-meta"><strong>{user?.display_name}</strong><span>{user?.roles.map((r) => r.name).join('、')}</span></div>
            <Button type="text" icon={<LogoutOutlined />} onClick={() => void logout()}>退出</Button>
          </Space>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}

export function PageTitle({ title, subtitle, extra }: { title: string; subtitle: string; extra?: ReactNode }) {
  return (
    <div className="page-title">
      <div><Typography.Title level={2}>{title}</Typography.Title><Typography.Text type="secondary">{subtitle}</Typography.Text></div>
      {extra}
    </div>
  );
}
