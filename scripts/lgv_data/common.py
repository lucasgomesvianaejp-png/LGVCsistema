from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


USER_AGENT = 'LGV-Capital-Research/3.0 (+official-public-sources; firebase)'


def env(name: str, required: bool = True, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f'Variável de ambiente ausente: {name}')
    return value


def http_bytes(url: str, timeout: int = 180, headers: dict[str, str] | None = None) -> bytes:
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
    if value is None or value == '': return None
    if isinstance(value, (int, float, Decimal)): return float(value)
    text = str(value).strip().replace('\xa0','')
    if not text or text in {'-','N/A','null','None'}: return None
    try:
        if ',' in text and '.' in text: text = text.replace('.','').replace(',','.')
        elif ',' in text: text = text.replace(',','.')
        return float(Decimal(text))
    except (InvalidOperation, ValueError): return None


def parse_date(value: Any) -> str | None:
    if value is None or value == '': return None
    text = str(value).strip()
    if not text: return None
    if 'T' in text: text = text.split('T',1)[0]
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%Y%m%d'):
        try: return datetime.strptime(text,fmt).date().isoformat()
        except ValueError: pass
    return None


def date_after(date_com: Any) -> str | None:
    parsed=parse_date(date_com)
    return (date.fromisoformat(parsed)+timedelta(days=1)).isoformat() if parsed else None


def b64_params(payload: dict[str, Any]) -> str:
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_doc_id(value: Any) -> str:
    return str(value).strip().replace('/','_')


class FirestoreRepo:
    """Camada mínima de persistência.

    O banco guarda dados normalizados por ativo/emissor, não cada observação diária.
    Isso mantém a LGV confortavelmente dentro da cota gratuita do Firestore.
    """
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore
        raw = env('FIREBASE_SERVICE_ACCOUNT_LGV_INVEST')
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError('FIREBASE_SERVICE_ACCOUNT_LGV_INVEST não contém JSON válido') from exc
        project_id = os.getenv('FIREBASE_PROJECT_ID') or info.get('project_id') or 'lvg-invest'
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(credentials.Certificate(info), {'projectId': project_id})
        self.db = firestore.client()
        self.project_id = project_id

    def get(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        snap=self.db.collection(collection).document(safe_doc_id(doc_id)).get()
        return ({'id':snap.id, **(snap.to_dict() or {})}) if snap.exists else None

    def all(self, collection: str) -> list[dict[str, Any]]:
        return [{'id':s.id, **(s.to_dict() or {})} for s in self.db.collection(collection).stream()]

    def set(self, collection: str, doc_id: str, values: dict[str, Any], merge: bool=True) -> None:
        self.db.collection(collection).document(safe_doc_id(doc_id)).set(values, merge=merge)

    def batch_set(self, collection: str, rows: Iterable[tuple[str,dict[str,Any]]], merge: bool=True, batch_size: int=400) -> int:
        rows=list(rows); written=0
        for i in range(0,len(rows),batch_size):
            batch=self.db.batch()
            for doc_id, values in rows[i:i+batch_size]:
                ref=self.db.collection(collection).document(safe_doc_id(doc_id))
                batch.set(ref, values, merge=merge); written += 1
            batch.commit()
        return written

    def delete_collection(self, collection: str, batch_size: int=400) -> int:
        refs=[s.reference for s in self.db.collection(collection).stream()]
        deleted=0
        for i in range(0,len(refs),batch_size):
            batch=self.db.batch()
            for ref in refs[i:i+batch_size]: batch.delete(ref); deleted += 1
            batch.commit()
        return deleted


class IngestionRun:
    def __init__(self, db: FirestoreRepo, source: str, source_url: str='', run_key: str='', metadata: dict[str,Any]|None=None):
        self.db=db; self.source=source; self.rows_read=0; self.rows_written=0
        self.id=f'{source}_{run_key or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}'.replace('/','_')
        self.base={'source':source,'sourceUrl':source_url or None,'runKey':run_key or None,'status':'RUNNING','startedAt':utc_now_iso(),'metadata':metadata or {}}
        db.set('researchIngestionRuns', self.id, self.base, merge=False)

    def success(self, source_hash: str|None=None, metadata: dict[str,Any]|None=None):
        values={'status':'SUCCESS','finishedAt':utc_now_iso(),'rowsRead':self.rows_read,'rowsWritten':self.rows_written,'sourceHash':source_hash}
        if metadata is not None: values['metadata']=metadata
        self.db.set('researchIngestionRuns',self.id,values)
        self.db.set('researchMeta','status',{'lastSuccessAt':values['finishedAt'],'lastSource':self.source,'updatedAt':utc_now_iso()})

    def fail(self, exc: Exception):
        self.db.set('researchIngestionRuns',self.id,{'status':'FAILED','finishedAt':utc_now_iso(),'rowsRead':self.rows_read,'rowsWritten':self.rows_written,'errorMessage':str(exc)[:3000]})
