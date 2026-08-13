"""Observational audit of Notion mutations while Supabase is authoritative."""
from __future__ import annotations
import atexit, inspect, os, re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

VERSION = "supabase-authority-audit-v1.0.0"
_INSTALLED=False
_ENABLED=False
_EVENTS=[]

@dataclass
class AuditEvent:
    method:str; url:str; category:str; detail:str; caller:str

def _norm(v): return re.sub(r'[^0-9A-Za-z]','',str(v or '')).lower()
def _env(*names):
    for n in names:
        v=os.getenv(n,'').strip()
        if v: return _norm(v)
    return ''
def _task_db(): return _env('TASKS_DATABASE_ID','NOTION_TASKS_DATABASE_ID','NOTION_TASK_DATABASE_ID')
def _project_db(): return _env('PROJECTS_DATABASE_ID','PROJECT_DATABASE_ID','NOTION_PROJECTS_DATABASE_ID','NOTION_PROJECT_DATABASE_ID')
def _ai_log_db(): return _env('NOTION_AI_LOG_DATABASE_ID','AI_LOG_DATABASE_ID')
def _telemetry_db(): return _env('NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID','TOPOLOGY_TELEMETRY_DATABASE_ID')

def _caller():
    f=inspect.currentframe()
    try:
        f=f.f_back if f else None
        for _ in range(20):
            if not f: break
            mod=str(f.f_globals.get('__name__','')); name=f.f_code.co_name
            if mod != __name__ and not mod.startswith(('requests','urllib3')):
                return f'{mod}.{name}'
            f=f.f_back
    finally:
        try: del f
        except Exception: pass
    return ''

def _parent_db(payload):
    if not isinstance(payload,Mapping): return ''
    parent=payload.get('parent')
    return _norm(parent.get('database_id')) if isinstance(parent,Mapping) else ''

def classify_mutation(method,url,payload=None):
    method=str(method).upper(); url=str(url or '')
    if '/v1/blocks/' in url:
        return 'allowed_interface','Notion block presentation / interaction mutation'
    if method=='POST' and url.rstrip('/').endswith('/v1/pages'):
        pid=_parent_db(payload)
        if pid and pid==_ai_log_db(): return 'allowed_logging','AI Processing Log page creation'
        if pid and pid==_telemetry_db(): return 'allowed_telemetry','Project topology telemetry page creation'
        if pid and pid==_task_db(): return 'allowed_task_mirror','Transitional Notion task mirror page creation'
        if pid and pid==_project_db(): return 'unexpected_authoritative','Project database page creation in Supabase mode'
        return 'unclassified','Unrecognized Notion page creation'
    if '/v1/pages/' in url and method in {'PATCH','DELETE'}:
        return 'unexpected_authoritative',f'Notion page {method} in Supabase mode'
    return 'unclassified',f'Unclassified Notion mutation: {method}'

def _record(method,url,payload=None):
    if not _ENABLED or 'api.notion.com/v1/' not in str(url): return
    cat,detail=classify_mutation(method,url,payload)
    _EVENTS.append(AuditEvent(str(method).upper(),str(url),cat,detail,_caller()))

def install_supabase_authority_audit(datastore):
    global _INSTALLED,_ENABLED
    if str(datastore).strip().lower()!='supabase': return False
    if _INSTALLED:
        _ENABLED=True; return True
    import requests
    op,opa,od=requests.post,requests.patch,requests.delete
    def post(url,*a,**kw): _record('POST',url,kw.get('json')); return op(url,*a,**kw)
    def patch(url,*a,**kw): _record('PATCH',url,kw.get('json')); return opa(url,*a,**kw)
    def delete(url,*a,**kw): _record('DELETE',url,kw.get('json')); return od(url,*a,**kw)
    requests.post,requests.patch,requests.delete=post,patch,delete
    _INSTALLED=True; _ENABLED=True
    atexit.register(emit_report)
    print(f'[Supabase Authority Audit] Installed — {VERSION}')
    return True

def emit_report():
    if not _ENABLED: return
    c=Counter(e.category for e in _EVENTS)
    print('\n=== SUPABASE AUTHORITY AUDIT ===')
    print(f'[Supabase Authority Audit] Version: {VERSION}')
    print(f'[Supabase Authority Audit] Notion mutations observed: {len(_EVENTS)}')
    for key,label in [('allowed_interface','Allowed interface'),('allowed_logging','Allowed logging'),('allowed_telemetry','Allowed telemetry'),('allowed_task_mirror','Allowed task mirrors'),('unexpected_authoritative','Unexpected authoritative writes'),('unclassified','Unclassified mutations')]:
        print(f'[Supabase Authority Audit] {label}: {c[key]}')
    bad=[e for e in _EVENTS if e.category in {'unexpected_authoritative','unclassified'}]
    for e in bad[:20]:
        print(f'[Supabase Authority Audit] {e.category}: {e.method} {e.url} caller={e.caller or "unknown"} detail={e.detail}')
    print('RESULT: SUPABASE CORE PERSISTENCE AUTHORITY CLEAN' if not bad else 'RESULT: SUPABASE CORE PERSISTENCE AUTHORITY NEEDS REVIEW')
