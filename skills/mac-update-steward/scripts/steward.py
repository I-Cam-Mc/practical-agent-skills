#!/usr/bin/env python3
"""Plan and journal agent-operated updates. Never installs software or runs a shell."""
import datetime as dt
import argparse
import hashlib
import json
import re
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def decide(c, policy):
    if c.get('device') not in policy.get('devices', []):
        return 'skip', 'device_out_of_scope'
    if c.get('present') is not True:
        return 'skip', 'not_installed'
    if c.get('protected') is not False or c['id'] in policy.get('protected_ids', []):
        return 'defer', 'protected_access_or_work'
    if c.get('pinned') is not False:
        return 'review', 'explicit_pin'
    if c.get('channel') != 'stable':
        return 'defer', 'stable_channel_required'
    source = urlsplit(c.get('source_url', ''))
    if source.scheme != 'https' or not source.hostname or source.username or source.password:
        return 'defer', 'official_https_source_required'
    before, target = version(c.get('before')), version(c.get('target'))
    if before is None or target is None:
        return 'review', 'version_order_unknown'
    order_before, order_target = before, target
    if target == before and ('before_build' in c or 'target_build' in c):
        order_before, order_target = version(c.get('before_build')), version(c.get('target_build'))
        if order_before is None or order_target is None:
            return 'review', 'version_order_unknown'
    if order_target <= order_before:
        return 'skip', 'downgrade_or_equal'
    if (c.get('change') not in ('patch', 'minor') or target[0] != before[0]
            or (before[0] == 0 and target[1] != before[1])):
        if approval_target(c) not in policy.get('approvals', []):
            return 'review', 'migration_decision_required'
    if policy.get('install_authorized') is not True:
        return 'review', 'installation_authority_missing'
    for field in ('source_verified', 'compatible', 'eligible', 'idle', 'rollback_ready'):
        if c.get(field) is not True:
            return 'defer', field + '_unverified'
    return 'ready', 'preconditions_met'


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:\.\d+){0,7}', value):
        return None
    parts = tuple(int(x) for x in value.split('.'))
    return parts + (0,) * (8 - len(parts))


def approval_target(c):
    """An approval is bound to this version, source and change, never a wildcard."""
    return {k: c.get(k) for k in ('device', 'id', 'before', 'target', 'before_build',
                                 'target_build', 'source_url', 'change', 'owner')}


def validate(candidates, policy):
    if not isinstance(candidates, list) or not isinstance(policy, dict):
        raise ValueError('expected candidate array and policy object')
    for key in ('devices', 'protected_ids', 'approvals'):
        if not isinstance(policy.get(key, []), list):
            raise ValueError('policy ' + key + ' must be an array')
    if any(not isinstance(v, str) for v in policy.get('devices', []) + policy.get('protected_ids', [])):
        raise ValueError('policy device and protected ids must be strings')
    seen = set()
    for c in candidates:
        if not isinstance(c, dict):
            raise ValueError('candidate must be an object')
        for key in ('device', 'id', 'name', 'before', 'target', 'owner', 'source_url', 'change'):
            value = c.get(key)
            if not isinstance(value, str) or not value or len(value) > 2048 or any(ord(x) < 32 for x in value):
                raise ValueError('invalid candidate field: ' + key)
        identity = (c['device'], c['id'])
        if c['id'].startswith('coverage:'):
            raise ValueError('coverage: prefix is reserved for source coverage')
        if identity in seen:
            raise ValueError('duplicate device and installation identity')
        seen.add(identity)
        for key in ('present', 'source_verified', 'compatible', 'eligible', 'idle', 'rollback_ready',
                    'protected', 'pinned', 'activation_required'):
            if c.get(key) is not None and type(c[key]) is not bool:
                raise ValueError(key + ' must be boolean or null')


def make_plan(candidates, policy):
    validate(candidates, policy)
    items = []
    for c in candidates:
        decision, reason = decide(c, policy)
        items.append(dict(candidate=c, decision=decision, reason=reason))
    plan = dict(schema_version=1, created_at=utcnow(), policy=policy, items=items)
    plan['plan_id'] = digest(plan)
    return plan


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp needs a timezone')
    return parsed


def check_plan(plan, current_candidates=None):
    if plan.get('schema_version') != 1:
        raise ValueError('unsupported plan schema')
    if plan.get('plan_id') != digest({k: v for k, v in plan.items() if k != 'plan_id'}):
        raise ValueError('plan changed, generate it again')
    age = (timestamp(utcnow()) - timestamp(plan['created_at'])).total_seconds()
    if not 0 <= age <= 86400:
        raise ValueError('plan expired or future-dated, collect fresh evidence')
    candidates = [i['candidate'] for i in plan['items']]
    validate(candidates, plan['policy'])
    for item in plan['items']:
        if (item['decision'], item['reason']) != decide(item['candidate'], plan['policy']):
            raise ValueError('decision does not match policy')
    if current_candidates is not None and candidates != current_candidates:
        raise ValueError('preconditions changed, generate a fresh plan')
    return True


def evidence_receipts(paths):
    receipts = []
    if not isinstance(paths, list):
        raise ValueError('evidence must be a list of files')
    for name in paths:
        path = Path(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError('evidence file unavailable or empty')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        receipts.append({'path': str(path.resolve()), 'sha256': h.hexdigest()})
    return receipts


def outcome(c, result, receipts):
    if result.get('before') != c['before'] or result.get('before_build') != c.get('before_build'):
        return 'stale_plan', 'installation_changed_before_attempt'
    phase = result.get('phase')
    if phase in ('failed', 'blocked', 'unavailable'):
        return phase, result.get('reason', 'updater_' + phase)
    if phase in ('downloaded', 'staged'):
        return phase, 'activation_unverified'
    if phase != 'installed':
        raise ValueError('unknown result phase')
    if result.get('identity_matches') is not True or not receipts:
        return 'verification_failed', 'installed_identity_or_version_unverified'
    if result.get('restart_required') is True:
        return 'pending_restart', 'restart_required'
    if (result.get('installed_version') != c['target']
            or result.get('installed_build') != c.get('target_build')
            or result.get('identity_matches') is not True or not receipts):
        return 'verification_failed', 'installed_identity_or_version_unverified'
    if c.get('activation_required') is not False:
        if (result.get('running_version') != c['target']
                or result.get('running_build') != c.get('target_build')):
            return 'pending_relaunch', 'running_version_unverified'
    if result.get('functional_ok') is not True:
        return 'verification_failed', 'functional_check_unverified'
    return 'verified', 'installed_and_verified'


def reconcile(plan, results):
    check_plan(plan)
    if not isinstance(results, list):
        raise ValueError('results must be an array')
    keyed = {}
    allowed = {(i['candidate']['device'], i['candidate']['id']) for i in plan['items']}
    for result in results:
        key = (result['device'], result['id'])
        if key not in allowed or key in keyed:
            raise ValueError('duplicate or unplanned result')
        if not re.fullmatch('[a-z][a-z0-9_]{0,63}', result.get('reason', 'unspecified')):
            raise ValueError('reason must be a short machine code, not raw output')
        for field in ('identity_matches', 'functional_ok', 'restart_required'):
            if result.get(field) is not None and type(result[field]) is not bool:
                raise ValueError('result evidence flags must be boolean or null')
        observed = timestamp(result['observed_at'])
        if not timestamp(plan['created_at']) <= observed <= timestamp(utcnow()):
            raise ValueError('result time is outside this plan')
        keyed[key] = result
    entries = []
    for item in plan['items']:
        c = item['candidate']
        result = keyed.get((c['device'], c['id']))
        receipts = []
        if item['decision'] != 'ready':
            if result is not None:
                raise ValueError('result supplied for a held or skipped item')
            state, reason = item['decision'], item['reason']
        elif result is None:
            state, reason = 'coverage_gap', 'no_result_received'
        else:
            receipts = evidence_receipts(result.get('evidence', []))
            state, reason = outcome(c, result, receipts)
        entries.append(dict(device=c['device'], id=c['id'], name=c['name'],
                            before=c['before'], before_build=c.get('before_build'),
                            target=c['target'], target_build=c.get('target_build'),
                            observed_at=result['observed_at'] if result else None,
                            state=state, reason=reason, evidence=receipts, plan_id=plan['plan_id']))
    return entries


def database(state_dir):
    directory = Path(state_dir)
    if directory.is_symlink():
        raise ValueError('state directory cannot be a symlink')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise ValueError('state directory must be private (mode 0700); choose a private directory')
    path = directory / 'journal.sqlite3'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError('existing journal must be a private regular file')
    con = sqlite3.connect(str(path), timeout=0)
    con.execute('CREATE TABLE IF NOT EXISTS findings (device TEXT, id TEXT, data TEXT, PRIMARY KEY(device,id))')
    con.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, digest TEXT, report TEXT)')
    return con


def coverage_findings(plan, coverage):
    if not isinstance(coverage, list):
        raise ValueError('coverage must be an array')
    entries, seen = [], set()
    for observation in coverage:
        device, source = observation['device'], observation['source']
        state, reason = observation['state'], observation['reason']
        if device not in plan['policy'].get('devices', []):
            raise ValueError('coverage device outside policy scope')
        if source not in ('device', 'macos', 'homebrew', 'app-store', 'runtimes', 'vendor'):
            raise ValueError('unknown coverage source')
        if state not in ('checked', 'partial', 'unavailable'):
            raise ValueError('unknown coverage state')
        if not re.fullmatch('[a-z][a-z0-9_]{0,63}', reason):
            raise ValueError('coverage reason must be a short machine code')
        observed = timestamp(observation['observed_at'])
        # Discovery usually precedes the plan; still require observations within 24 hours.
        if not 0 <= (timestamp(utcnow()) - observed).total_seconds() <= 86400:
            raise ValueError('coverage observation is stale or future-dated')
        key = (device, source)
        if key in seen:
            raise ValueError('duplicate coverage observation')
        seen.add(key)
        entries.append(dict(device=device, id='coverage:' + source, name=source,
                            before=None, before_build=None, target=None, target_build=None,
                            state='coverage_' + state, reason=reason, evidence=[],
                            observed_at=observation['observed_at'], plan_id=plan['plan_id']))
    return entries


def record_run(plan, results, state_dir, coverage=None):
    entries = reconcile(plan, results) + coverage_findings(plan, [] if coverage is None else coverage)
    con = database(state_dir)
    try:
        con.execute('BEGIN IMMEDIATE')
        previous_run = con.execute('SELECT digest,report FROM runs WHERE id=?', (plan['plan_id'],)).fetchone()
        receipt_digest = digest(entries)
        if previous_run:
            if previous_run[0] != receipt_digest:
                raise ValueError('run already recorded with different evidence; make a fresh plan')
            report = json.loads(previous_run[1])
            report.update(changes=[], newly_verified=0, replayed=True)
            con.rollback()
            return report
        changes = []
        for entry in entries:
            key = (entry['device'], entry['id'])
            old = con.execute('SELECT data FROM findings WHERE device=? AND id=?', key).fetchone()
            old = json.loads(old[0]) if old else None
            semantic = ('target', 'target_build', 'state', 'reason')
            first_healthy_check = old is None and entry['state'] == 'coverage_checked'
            if entry['state'] != 'skip' and not first_healthy_check and (old is None or any(old[k] != entry[k] for k in semantic)):
                changes.append(entry)
            saved = dict(entry, first_recorded_at=old['first_recorded_at'] if old else utcnow(),
                         last_recorded_at=utcnow())
            con.execute('INSERT OR REPLACE INTO findings VALUES (?,?,?)', (*key, json.dumps(saved)))
        report = dict(schema_version=1, plan_id=plan['plan_id'], recorded_at=utcnow(),
                      findings=entries, changes=changes,
                      newly_verified=sum(e['state'] == 'verified' for e in changes), replayed=False)
        con.execute('INSERT INTO runs VALUES (?,?,?)', (plan['plan_id'], receipt_digest, json.dumps(report)))
        con.commit()
        return report
    finally:
        con.close()


def read_state(state_dir):
    con = database(state_dir)
    try:
        return [json.loads(row[0]) for row in con.execute('SELECT data FROM findings ORDER BY device,id')]
    finally:
        con.close()


def load(path):
    if Path(path).stat().st_size > 4 * 1024 * 1024:
        raise ValueError('input exceeds 4 MiB limit')
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan', help='Create a reviewable plan; performs no installations')
    plan.add_argument('--candidates', required=True)
    plan.add_argument('--policy', required=True)
    plan.add_argument('--output', required=True)
    check = commands.add_parser('check', help='Reject changed or stale preconditions before an agent acts')
    check.add_argument('--plan', required=True)
    check.add_argument('--candidates', required=True)
    record = commands.add_parser('record', help='Reconcile observations into private durable state')
    record.add_argument('--plan', required=True)
    record.add_argument('--results', required=True)
    record.add_argument('--state-dir', required=True)
    record.add_argument('--coverage', help='Device/source observations, including unreachable devices with no candidates')
    record.add_argument('--all', action='store_true', help='Print even when nothing materially changed')
    status = commands.add_parser('status', help='Read the local pending/completed journal')
    status.add_argument('--state-dir', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'plan':
            value = make_plan(load(args.candidates), load(args.policy))
            fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(value, f, indent=2)
                f.write('\n')
            print(json.dumps({'plan_id': value['plan_id'], 'items': len(value['items'])}))
        elif args.command == 'check':
            check_plan(load(args.plan), load(args.candidates))
            print(json.dumps({'preconditions_unchanged': True}))
        elif args.command == 'record':
            coverage = load(args.coverage) if args.coverage else []
            if not isinstance(coverage, list):
                raise ValueError('coverage must be an array')
            value = record_run(load(args.plan), load(args.results), args.state_dir,
                               coverage)
            if args.all or value['changes']:
                print(json.dumps(value, indent=2))
        else:
            print(json.dumps(read_state(args.state_dir), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        print('steward: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
