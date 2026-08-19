import { DownloadOutlined, FileExcelOutlined, FilePdfOutlined, FileTextOutlined } from '@ant-design/icons';
import { Button, Card, Space, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { api } from '../api';
import { PageTitle } from '../components/Shell';
import type { StoredFile } from '../types';

const icon = (type: string) => type.includes('pdf') ? <FilePdfOutlined /> : type.includes('sheet') || type.includes('excel') ? <FileExcelOutlined /> : <FileTextOutlined />;

export function FilesPage() {
  const [files, setFiles] = useState<StoredFile[]>([]);
  useEffect(() => { api<StoredFile[]>('/files').then(setFiles); }, []);
  return <><PageTitle title="文件中心" subtitle="集中管理源文件、解析结果与正式导出版本" />
    <Card className="panel-card"><Table rowKey="id" dataSource={files} columns={[
      { title: '文件', dataIndex: 'original_name', render: (name: string, row: StoredFile) => <Space>{icon(row.media_type)}<strong>{name}</strong></Space> },
      { title: '类型', dataIndex: 'category', render: (value: string) => <Tag color={value === 'export' ? 'green' : 'blue'}>{value === 'export' ? '正式导出' : '源文件'}</Tag> },
      { title: '大小', dataIndex: 'size_bytes', render: (value: number) => `${(value / 1024).toFixed(1)} KB` },
      { title: 'SHA-256', dataIndex: 'sha256', render: (value: string) => <code>{value.slice(0, 12)}…</code> },
      { title: '创建时间', dataIndex: 'created_at', render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm') },
      { title: '操作', render: (_, row) => <Button type="link" icon={<DownloadOutlined />} href={`/api/v1/files/${row.id}/download`}>下载</Button> },
    ]} /></Card></>;
}
