import { Card, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { api } from '../api';
import { PageTitle } from '../components/Shell';
import type { AuditEvent } from '../types';

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  useEffect(() => { api<AuditEvent[]>('/audit-events').then(setEvents); }, []);
  return <><PageTitle title="审计记录" subtitle="关键操作只追加、不通过业务接口修改" />
    <Card className="panel-card"><Table rowKey="id" dataSource={events} pagination={{ pageSize: 15 }} columns={[
      { title: '时间', dataIndex: 'occurred_at', width: 180, render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm:ss') },
      { title: '动作', dataIndex: 'action', render: (value: string) => <Tag>{value}</Tag> },
      { title: '资源', render: (_, row) => `${row.resource_type} / ${row.resource_id?.slice(0, 8) ?? '-'}` },
      { title: '操作者', dataIndex: 'actor_id', render: (value?: string) => value?.slice(0, 8) ?? 'system' },
      { title: '请求ID', dataIndex: 'request_id', render: (value?: string) => value?.slice(0, 12) ?? '-' },
    ]} /></Card></>;
}
