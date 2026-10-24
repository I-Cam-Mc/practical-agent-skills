"""Synthetic fixtures, exercised through the policy/journal public API."""
import copy
import datetime as dt
import json
import subprocess
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import steward


def candidate(**changes):
    value = dict(device='workstation', id='example.editor', name='Example Editor',
                 before='2.4.0', target='2.4.1', change='patch', owner='vendor',
                 source_url='https://example.com/releases/2.4.1',
                 channel='stable', present=True, source_verified=True,
                 compatible=True, eligible=True, idle=True, rollback_ready=True,
                 protected=False, pinned=False, activation_required=True)
    value.update(changes)
    return value


def policy():
    return dict(devices=['workstation'], install_authorized=True,
                protected_ids=[], approvals=[])


class PlanningTests(unittest.TestCase):
    def test_changed_preconditions_or_expired_plan_require_replanning(self):
        c = candidate()
        p = steward.make_plan([c], policy())
        self.assertTrue(steward.check_plan(p, [c]))
        with self.assertRaises(ValueError):
            steward.check_plan(p, [candidate(before='2.4.1')])
        p['items'][0]['candidate']['idle'] = False
        with self.assertRaises(ValueError):
            steward.check_plan(p, [c])
        expired = steward.make_plan([candidate()], policy())
        expired['created_at'] = '2020-01-01T00:00:00+00:00'
        expired['plan_id'] = steward.digest({k: v for k, v in expired.items() if k != 'plan_id'})
        with self.assertRaises(ValueError):
            steward.check_plan(expired, [candidate()])

    def test_build_updates_and_exact_migration_approval(self):
        build = candidate(before='2.4', target='2.4', before_build='140', target_build='141')
        self.assertEqual(steward.make_plan([build], policy())['items'][0]['decision'], 'ready')
        major = candidate(target='3.0', change='migration')
        p = policy()
        p['approvals'] = [steward.approval_target(major)]
        self.assertEqual(steward.make_plan([major], p)['items'][0]['decision'], 'ready')
        major['source_url'] = 'https://example.com/other'
        self.assertEqual(steward.make_plan([major], p)['items'][0]['decision'], 'review')
        self.assertEqual(steward.make_plan([candidate(source_url='http://example.com')], policy())['items'][0]['decision'], 'defer')

    def test_invalid_or_duplicate_identity_fails_closed(self):
        for entries in [[candidate(), candidate()], [candidate(id='')], [candidate(id=['x'])],
                        [candidate(id='x\ny')], [candidate(source_verified='yes')]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                steward.make_plan(entries, policy())
        with self.assertRaises(ValueError):
            steward.make_plan([candidate()], {'devices': 'workstation'})

    def test_receipts_protection_and_version_order_prevent_unsafe_plans(self):
        for changes, decision, reason in [
            ({'present': False}, 'skip', 'not_installed'),
            ({'device': 'other'}, 'skip', 'device_out_of_scope'),
            ({'protected': True}, 'defer', 'protected_access_or_work'),
            ({'pinned': True}, 'review', 'explicit_pin'),
            ({'before': '3.0.0'}, 'skip', 'downgrade_or_equal'),
            ({'before': '2.4.1'}, 'skip', 'downgrade_or_equal'),
            ({'target': 'latest'}, 'review', 'version_order_unknown'),
            ({'target': '3.0.0'}, 'review', 'migration_decision_required'),
            ({'before': '0.3.1', 'target': '0.4.0'}, 'review', 'migration_decision_required'),
            ({'channel': 'beta'}, 'defer', 'stable_channel_required'),
        ]:
            with self.subTest(changes=changes):
                item = steward.make_plan([candidate(**changes)], policy())['items'][0]
                self.assertEqual((item['decision'], item['reason']), (decision, reason))
        p = policy()
        p['protected_ids'] = ['example.editor']
        self.assertEqual(steward.make_plan([candidate()], p)['items'][0]['reason'], 'protected_access_or_work')

    def test_ready_requires_established_facts_and_existing_authority(self):
        self.assertEqual(steward.make_plan([candidate()], policy())['items'][0]['decision'], 'ready')
        for field in ['compatible', 'eligible', 'idle', 'rollback_ready', 'source_verified']:
            with self.subTest(field=field):
                item = steward.make_plan([candidate(**{field: None})], policy())['items'][0]
                self.assertEqual(item['decision'], 'defer')
        self.assertEqual(steward.make_plan([candidate()], {'devices': ['workstation']})['items'][0]['decision'], 'review')


class EvidenceTests(unittest.TestCase):
    def test_malformed_falsy_coverage_never_becomes_successful_empty_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ({}, False, 0, ''):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    steward.record_run(steward.make_plan([], policy()), [], tmp, coverage=value)
    def test_unreachable_device_without_app_candidates_has_durable_quiet_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = policy()
            p['devices'] = ['studio']
            plan = steward.make_plan([], p)
            gaps = [dict(device='studio', source='device', state='unavailable',
                         reason='connection_unavailable', observed_at=steward.utcnow())]
            first = steward.record_run(plan, [], tmp, coverage=gaps)
            self.assertEqual(first['changes'][0]['state'], 'coverage_unavailable')
            self.assertEqual(first['newly_verified'], 0)
            second = steward.record_run(steward.make_plan([], p), [], tmp, coverage=gaps)
            self.assertEqual(second['changes'], [])
            self.assertEqual(steward.read_state(tmp)[0]['device'], 'studio')

    def test_journal_preserves_build_before_after_and_observation_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = pathlib.Path(tmp) / 'receipt'
            receipt.write_text('Fictional build check')
            plan = steward.make_plan([candidate(before='2.4', target='2.4', before_build='140', target_build='141')], policy())
            observed = steward.utcnow()
            result = dict(device='workstation', id='example.editor', before='2.4', before_build='140',
                          phase='installed', installed_version='2.4', installed_build='141',
                          running_version='2.4', running_build='141', identity_matches=True,
                          functional_ok=True, observed_at=observed, evidence=[str(receipt)])
            steward.record_run(plan, [result], tmp)
            saved = steward.read_state(tmp)[0]
            self.assertEqual((saved['before_build'], saved['target_build']), ('140', '141'))
            self.assertEqual(saved['observed_at'], observed)
            self.assertIn('last_recorded_at', saved)

    def test_public_state_directory_is_rejected_without_changing_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            root.chmod(0o777)
            with self.assertRaises(ValueError):
                steward.record_run(steward.make_plan([candidate(idle=False)], policy()), [], tmp)
            self.assertFalse((root / 'journal.sqlite3').exists())
            self.assertEqual(root.stat().st_mode & 0o777, 0o777)

    def test_cli_plan_record_and_quiet_replay(self):
        script = pathlib.Path(steward.__file__)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name, value in [('candidates.json', [candidate(idle=False)]),
                                ('policy.json', policy()), ('results.json', [])]:
                (root / name).write_text(json.dumps(value))
            def cli(*args):
                return subprocess.run([sys.executable, str(script), *args], cwd=tmp,
                                      capture_output=True, text=True, timeout=10)
            first = cli('plan', '--candidates', 'candidates.json', '--policy', 'policy.json', '--output', 'plan.json')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((root / 'plan.json').is_file())
            self.assertEqual((root / 'plan.json').stat().st_mode & 0o777, 0o600)
            args = ('record', '--plan', 'plan.json', '--results', 'results.json', '--state-dir', 'state')
            self.assertEqual(len(json.loads(cli(*args).stdout)['changes']), 1)
            self.assertEqual(cli(*args).stdout, '')
            (root / 'bad-coverage.json').write_text('null')
            self.assertNotEqual(cli(*args, '--coverage', 'bad-coverage.json').returncode, 0)
            self.assertNotEqual(cli('plan', '--candidates', 'candidates.json', '--policy', 'policy.json', '--output', 'plan.json').returncode, 0)

    def test_journal_suppresses_unchanged_blockers_and_replayed_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = steward.make_plan([candidate(idle=False)], policy())
            first = steward.record_run(plan, [], tmp)
            self.assertEqual(len(first['changes']), 1)
            replay = steward.record_run(plan, [], tmp)
            self.assertEqual(replay['changes'], [])
            second = steward.record_run(steward.make_plan([candidate(idle=False)], policy()), [], tmp)
            self.assertEqual(second['changes'], [])
            changed = steward.record_run(steward.make_plan([candidate(compatible=False)], policy()), [], tmp)
            self.assertEqual(changed['changes'][0]['reason'], 'compatible_unverified')
            self.assertEqual(steward.read_state(tmp)[0]['reason'], 'compatible_unverified')
            self.assertEqual((pathlib.Path(tmp) / 'journal.sqlite3').stat().st_mode & 0o777, 0o600)

    def test_downloads_old_processes_and_restart_are_not_completed_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / 'receipt.txt'
            evidence.write_text('Synthetic bundle version and functional probe receipt')
            plan = steward.make_plan([candidate()], policy())
            observation = dict(device='workstation', id='example.editor', phase='installed',
                               observed_at=steward.utcnow(), before='2.4.0', installed_version='2.4.1',
                               running_version='2.4.1', identity_matches=True, functional_ok=True,
                               evidence=[str(evidence)])
            for changes, state in [({}, 'verified'), ({'phase': 'downloaded'}, 'downloaded'),
                                   ({'installed_version': '2.4.0'}, 'verification_failed'),
                                   ({'running_version': '2.4.0'}, 'pending_relaunch'),
                                   ({'restart_required': True}, 'pending_restart'),
                                   ({'restart_required': True, 'identity_matches': False}, 'verification_failed'),
                                   ({'restart_required': True, 'evidence': []}, 'verification_failed'),
                                   ({'before': '2.4.1'}, 'stale_plan'),
                                   ({'functional_ok': False}, 'verification_failed'),
                                   ({'evidence': []}, 'verification_failed')]:
                with self.subTest(changes=changes):
                    result = dict(observation, **changes)
                    self.assertEqual(steward.reconcile(plan, [result])[0]['state'], state)
            self.assertEqual(steward.reconcile(plan, [])[0]['state'], 'coverage_gap')


if __name__ == '__main__':
    unittest.main()
