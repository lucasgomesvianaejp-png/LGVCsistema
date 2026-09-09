from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

USER_AGENT = 'LGV-Capital-Research/1.0 (+data-ingestion; official-public-sources)'


def env(name: str, required: bool = True, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f'Variável de ambiente ausente: {name}')
    return value


def http_bytes(url: str, timeout: int = 120, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 90) -> Any:
    data = None
    method = 'GET'
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        method = 'POST'
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_decimal(value: Any) -> float | None:
    if value is None or value == '':
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    text = str(value).strip().replace('\xa0', '')
    if not text or text in {'-', 'N/A', 'null', 'None'}:
        return None
    try:
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.')
        elif ',' in text:
            text = text.replace(',', '.')
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: Any) -> str | None:
    if value is None or value == '':
        return None
    text = str(value).strip()
    if not text:
        return None
    if 'T' in text:
        text = text.split('T', 1)[0]
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y%m%d'):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def date_after(date_com: Any) -> str | None:
    parsed = parse_date(date_com)
    if not parsed:
        return None
    return (date.fromisoformat(parsed) + timedelta(days=1)).isoformat()


def b64_params(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


@dataclass
class RestResponse:
    data: Any
    content_range: str = ''


class SupabaseRest:
    def __init__(self) -> None:
        self.url = str(env('SUPABASE_URL')).rstrip('/')
        self.key = str(env('SUPABASE_SERVICE_ROLE_KEY'))

    def _request(self, method: str, path: str, body: Any = None, prefer: str | None = None) -> RestResponse:
        url = f'{self.url}/rest/v1/{path.lstrip("/")}'
        headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Accept': 'application/json',
            'User-Agent': USER_AGENT,
        }
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, default=str).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if prefer:
            headers['Prefer'] = prefer
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read().decode('utf-8')
                parsed = json.loads(raw) if raw else []
                return RestResponse(parsed, response.headers.get('Content-Range', ''))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Supabase {method} {path}: HTTP {exc.code}: {text[:800]}') from exc

    def select(self, table: str, query: str = 'select=*') -> list[dict[str, Any]]:
        return self._request('GET', f'{table}?{query}').data

    def select_all(self, table: str, query: str = 'select=*', page_size: int = 1000) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            sep = '&' if query else ''
            chunk = self._request('GET', f'{table}?{query}{sep}limit={page_size}&offset={offset}').data
            if not isinstance(chunk, list):
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            offset += page_size
        return rows

    def upsert(self, table: str, rows: Iterable[dict[str, Any]], on_conflict: str, batch_size: int = 500) -> int:
        rows = list(rows)
        written = 0
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            if not chunk:
                continue
            conflict = urllib.parse.quote(on_conflict, safe=',')
            self._request(
                'POST', f'{table}?on_conflict={conflict}', chunk,
                prefer='resolution=merge-duplicates,return=minimal'
            )
            written += len(chunk)
        return written

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        result = self._request('POST', table, row, prefer='return=representation').data
        return result[0] if isinstance(result, list) and result else {}

    def patch(self, table: str, filter_query: str, values: dict[str, Any]) -> None:
        self._request('PATCH', f'{table}?{filter_query}', values, prefer='return=minimal')


class IngestionRun:
    def __init__(self, db: SupabaseRest, source: str, source_url: str = '', run_key: str = '', metadata: dict[str, Any] | None = None):
        self.db = db
        self.source = source
        self.rows_read = 0
        self.rows_written = 0
        row = db.insert('lgv_ingestion_runs', {
            'source': source,
            'source_url': source_url or None,
            'run_key': run_key or None,
            'status': 'RUNNING',
            'metadata': metadata or {},
        })
        self.id = row.get('id')

    def success(self, source_hash: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        if not self.id:
            return
        values = {
            'status': 'SUCCESS', 'finished_at': datetime.utcnow().isoformat() + 'Z',
            'rows_read': self.rows_read, 'rows_written': self.rows_written,
            'source_hash': source_hash,
        }
        if metadata is not None:
            values['metadata'] = metadata
        self.db.patch('lgv_ingestion_runs', f'id=eq.{self.id}', values)

    def fail(self, exc: Exception) -> None:
        if not self.id:
            return
        self.db.patch('lgv_ingestion_runs', f'id=eq.{self.id}', {
            'status': 'FAILED', 'finished_at': datetime.utcnow().isoformat() + 'Z',
            'rows_read': self.rows_read, 'rows_written': self.rows_written,
            'error_message': str(exc)[:3000],
        })
