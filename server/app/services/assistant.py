from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.enums import BatchStatus, IssueStatus, RoleCode
from app.models import AIInteraction, KnowledgeDocument, ProcessingBatch, ToolCall, User, ValidationIssue

PROMPT_VERSION = "business-copilot-v1"
INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"忽略.{0,8}(之前|以上|系统).{0,8}(指令|提示)",
    r"输出.{0,8}(系统提示|system prompt)",
    r"直接.{0,8}(执行sql|修改数据库|绕过审批)",
)


class AIClient(Protocol):
    def complete(self, *, system: str, user: str) -> tuple[str, dict[str, int]]: ...


class DeepSeekClient:
    def complete(self, *, system: str, user: str) -> tuple[str, dict[str, int]]:
        settings = get_settings()
        if not settings.deepseek_api_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="未配置 DeepSeek API Key")
        response = httpx.post(
            f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "temperature": 0.1,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"], body.get("usage", {})


class FakeAIClient:
    def complete(self, *, system: str, user: str) -> tuple[str, dict[str, int]]:
        del system
        return f"这是基于当前授权数据生成的测试建议：{user[:120]}", {"prompt_tokens": 20, "completion_tokens": 20}


@dataclass
class AssistantResult:
    interaction: AIInteraction
    warning: str | None = None


def detect_injection(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def retrieve_knowledge(db: Session, query: str, limit: int = 4) -> list[KnowledgeDocument]:
    segments = [term for term in re.split(r"\s+|[，。；、？！]", query) if len(term) >= 2]
    terms = segments + [segment[index : index + 2] for segment in segments for index in range(len(segment) - 1)]
    terms = list(dict.fromkeys(terms))[:16]
    if not terms:
        return []
    conditions = [
        or_(KnowledgeDocument.title.contains(term), KnowledgeDocument.content.contains(term)) for term in terms
    ]
    return list(
        db.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.is_active.is_(True), or_(*conditions)).limit(limit)
        )
    )


def batch_summary(db: Session, batch_id: str, user: User) -> dict[str, Any]:
    batch = db.get(ProcessingBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    if RoleCode.VIEWER.value in {role.code for role in user.roles} and batch.status not in {
        BatchStatus.APPROVED,
        BatchStatus.EXPORTED,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只读角色只能查询已批准结果")
    open_issues = (
        db.scalar(
            select(func.count())
            .select_from(ValidationIssue)
            .where(ValidationIssue.batch_id == batch_id, ValidationIssue.status == IssueStatus.OPEN)
        )
        or 0
    )
    return {
        "id": batch.id,
        "name": batch.name,
        "business_type": batch.business_type.value,
        "status": batch.status.value,
        "row_count": batch.row_count,
        "open_issues": open_issues,
    }


def ask_assistant(
    db: Session,
    user: User,
    question: str,
    batch_id: str | None,
    client: AIClient | None = None,
) -> AssistantResult:
    settings = get_settings()
    model = "fake" if settings.use_fake_ai else settings.deepseek_model
    if detect_injection(question):
        interaction = AIInteraction(
            user_id=user.id,
            question=question,
            answer="该请求试图改变助手安全边界，已拒绝处理。",
            sources=[],
            model=model,
            prompt_version=PROMPT_VERSION,
        )
        db.add(interaction)
        db.flush()
        return AssistantResult(interaction=interaction, warning="检测到提示注入风险")

    documents = retrieve_knowledge(db, question)
    sources = [{"id": document.id, "title": document.title, "source": document.source} for document in documents]
    context = "\n\n".join(f"[{doc.title}]\n{doc.content[:2000]}" for doc in documents)
    tool_result: dict[str, Any] | None = batch_summary(db, batch_id, user) if batch_id else None
    system = (
        "你是期刊财务业务副驾，只能依据提供的制度和授权业务摘要回答。"
        "不得声称已经修改数据或完成审批；证据不足时明确说明。所有写操作只能生成待确认建议。"
    )
    user_prompt = json.dumps(
        {"question": question, "knowledge": context, "authorized_batch_summary": tool_result},
        ensure_ascii=False,
    )
    selected_client = client or (FakeAIClient() if settings.use_fake_ai else DeepSeekClient())
    started = time.perf_counter()
    answer, usage = selected_client.complete(system=system, user=user_prompt)
    proposed_action = None
    if "任务" in question and batch_id:
        proposed_action = {"type": "create_task", "batch_id": batch_id, "title": f"AI建议：{question[:80]}"}
    interaction = AIInteraction(
        user_id=user.id,
        question=question,
        answer=answer,
        sources=sources,
        proposed_action=proposed_action,
        model=model,
        prompt_version=PROMPT_VERSION,
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        completion_tokens=int(usage.get("completion_tokens", 0)),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    db.add(interaction)
    db.flush()
    if tool_result:
        db.add(
            ToolCall(
                interaction_id=interaction.id,
                tool_name="get_batch_summary",
                arguments={"batch_id": batch_id},
                result_summary=json.dumps(tool_result, ensure_ascii=False),
            )
        )
    return AssistantResult(interaction=interaction)
