# API与权限

所有业务接口使用 `/api/v1` 前缀，OpenAPI 是接口契约的事实来源。登录令牌存放在 HttpOnly、SameSite Cookie；非只读请求还必须提交双重Cookie CSRF Header。

| 能力 | 管理员 | 经办人 | 审批人 | 只读 |
|---|---:|---:|---:|---:|
| 用户/角色管理 | ✓ |  |  |  |
| 导入、修订、复核 | ✓ | ✓ |  |  |
| 提交审批 | ✓ | ✓ |  |  |
| 批准/驳回 | ✓ |  | ✓ |  |
| 导出报表 | ✓ | ✓ |  |  |
| 查询批准结果 | ✓ | ✓ | ✓ | ✓（脱敏） |
| 查看审计 | ✓ |  | ✓ |  |
| AI建议 | ✓ | ✓ | ✓ | ✓ |

主要资源：`auth`、`users`、`roles`、`batches`、`review-fees`、`page-fees`、`royalties`、`validation-issues`、`approvals`、`exports`、`tasks`、`comments`、`files`、`knowledge`、`assistant`、`audit-events`、`search`。

错误语义：`400` 输入错误、`401` 未登录、`403` 越权/CSRF失败、`404` 资源不存在、`409` 状态或版本冲突、`413/415` 上传限制、`503` AI供应商未配置。
