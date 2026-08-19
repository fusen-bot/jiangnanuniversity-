import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from app.config import get_settings


@dataclass
class AuthorRecord:
    manuscript_no: str
    author_name: str
    article_title: str = ""
    institution: str = ""
    email: str = ""


def extract_authors_from_pdf(path: Path) -> list[AuthorRecord]:
    records: list[AuthorRecord] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            manuscript_match = re.search(r"DOI[：:]\s*[\w./-]*?\.(\d{8,})", text, re.IGNORECASE)
            author_match = re.search(r"通[讯信]作者[：:]\s*([一-龥·]{2,30})", text)
            if not author_match:
                continue
            email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            institution_match = re.search(r"[（(]([^）)]*(?:大学|学院|研究院|研究所)[^）)]*)[）)]", text)
            records.append(
                AuthorRecord(
                    manuscript_no=manuscript_match.group(1) if manuscript_match else "",
                    author_name=author_match.group(1),
                    institution=institution_match.group(1) if institution_match else "",
                    email=email_match.group(0) if email_match else "",
                )
            )
    return records


class JournalGateway:
    def __init__(self, base_url: str | None = None):
        configured_url = base_url or get_settings().journal_base_url
        parsed = urlparse(configured_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Journal base URL must use HTTPS and include a hostname")
        self.base_url = configured_url.rstrip("/") + "/"
        self.allowed_host = parsed.hostname

    def issue_url(self, year: int, issue: int) -> str:
        return urljoin(self.base_url, f"issues/{year}/{issue}")

    def fetch_issue(self, year: int, issue: int) -> list[AuthorRecord]:
        target = self.issue_url(year, issue)
        if urlparse(target).hostname != self.allowed_host:
            raise ValueError("Refusing request outside configured journal host")
        response = httpx.get(target, timeout=20, follow_redirects=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        records: list[AuthorRecord] = []
        for article in soup.select("article[data-manuscript-no]"):
            title = article.select_one(".title")
            author = article.select_one(".author")
            institution = article.select_one(".institution")
            email = article.select_one(".email")
            records.append(
                AuthorRecord(
                    manuscript_no=str(article.get("data-manuscript-no", "")),
                    article_title=title.get_text(strip=True) if title else "",
                    author_name=author.get_text(strip=True) if author else "",
                    institution=institution.get_text(strip=True) if institution else "",
                    email=email.get_text(strip=True) if email else "",
                )
            )
        return records
