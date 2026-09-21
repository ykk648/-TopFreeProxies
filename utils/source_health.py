#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'sub' / 'sub_list.json'
REPORT_FILE = ROOT / 'sub' / 'source_health.json'
URI_PATTERN = re.compile(r'\b(?:ss|ssr|vmess|vless|trojan|hysteria2?|tuic)://')


def session_create():
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=1,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=('GET',),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers['User-Agent'] = 'TopFreeProxies source-health/2026.09'
    return session


def decode_subscription(text):
    compact = re.sub(r'\s+', '', text)
    if not compact or not re.fullmatch(r'[A-Za-z0-9+/=_-]+', compact):
        return ''
    try:
        payload = compact.replace('-', '+').replace('_', '/')
        payload += '=' * (-len(payload) % 4)
        return base64.b64decode(payload).decode('utf-8', 'replace')
    except Exception:
        return ''


def content_is_subscription(content):
    text = content.decode('utf-8', 'replace').strip()
    if not text:
        return False, 'empty response'
    if 'proxies:' in text or URI_PATTERN.search(text):
        return True, 'plain subscription'
    decoded = decode_subscription(text)
    if decoded and ('proxies:' in decoded or URI_PATTERN.search(decoded)):
        return True, 'base64 subscription'
    return False, 'unsupported content format'


def check_url(session, url):
    result = {'url': url, 'ok': False}
    try:
        response = session.get(url, timeout=(8, 30))
        content = response.content
        valid, detail = content_is_subscription(content)
        result.update({
            'status': response.status_code,
            'bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest(),
            'content_type': response.headers.get('content-type', ''),
            'ok': response.status_code == 200 and valid,
            'detail': detail,
        })
    except requests.RequestException as error:
        result['detail'] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description='Check enabled subscription sources.')
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail when any enabled source has no valid URL.',
    )
    args = parser.parse_args()

    sources = json.loads(SOURCE_FILE.read_text(encoding='utf-8'))
    session = session_create()
    report = {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'sources': [],
    }

    for source in sources:
        if not source.get('enabled'):
            continue
        checks = [check_url(session, url.strip()) for url in source['url'].split('|')]
        source_ok = any(check['ok'] for check in checks)
        report['sources'].append({
            'id': source['id'],
            'remarks': source['remarks'],
            'ok': source_ok,
            'checks': checks,
        })
        state = 'OK' if source_ok else 'FAILED'
        details = ', '.join(
            f"{check.get('status', '-')} {check.get('bytes', 0)}B {check['detail']}"
            for check in checks
        )
        print(f"[{state}] {source['remarks']}: {details}")

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    valid_count = sum(source['ok'] for source in report['sources'])
    if valid_count == 0:
        raise SystemExit('No enabled subscription source is currently valid.')
    if args.strict and valid_count != len(report['sources']):
        raise SystemExit('At least one enabled subscription source failed validation.')


if __name__ == '__main__':
    main()
