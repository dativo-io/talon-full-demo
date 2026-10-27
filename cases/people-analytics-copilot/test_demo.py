"""Local functional checks. Synthetic HR HTTP mock; Talon is NOT simulated as proof."""
import json
import os
import tempfile
from pathlib import Path
import warehouse
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import demo


class DemoSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.TemporaryDirectory()
        cls.old_db_env = os.environ.get("HR_DEMO_DB_PATH")
        os.environ["HR_DEMO_DB_PATH"] = str(Path(cls.db_dir.name) / "hr.duckdb")
        warehouse.seed()
        cls.service = ThreadingHTTPServer(('127.0.0.1', 0), demo.HRService)
        cls.thread = threading.Thread(target=cls.service.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.service.server_port)
        cls.dashboard = ThreadingHTTPServer(('127.0.0.1', 0), demo.DashboardService)
        cls.dashboard_thread = threading.Thread(target=cls.dashboard.serve_forever, daemon=True)
        cls.dashboard_thread.start()
        cls.dashboard_url = 'http://127.0.0.1:' + str(cls.dashboard.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.dashboard.shutdown()
        cls.dashboard.server_close()
        cls.dashboard_thread.join()
        cls.service.shutdown()
        cls.service.server_close()
        cls.thread.join()
        if cls.old_db_env is None:
            os.environ.pop("HR_DEMO_DB_PATH", None)
        else:
            os.environ["HR_DEMO_DB_PATH"] = cls.old_db_env
        cls.db_dir.cleanup()

    def test_mock_lists_both_safe_and_privileged_capabilities(self):
        status, out = demo.json_request(self.base + '/mcp',
            {'jsonrpc':'2.0', 'id':1, 'method':'tools/list', 'params':{'_meta':demo.META}})
        self.assertEqual(status, 200)
        self.assertEqual({t['name'] for t in out['result']['tools']},
                         {'hr_attrition_summary', 'hr_headcount_summary',
                          'hr_tenure_summary', 'hr_aggregate_sql', 'hr_employee_export'})

    def test_aggregate_tools_compute_real_synthetic_metrics(self):
        for name, arguments, field in [
            ('hr_attrition_summary', {'months':6}, 'cohorts'),
            ('hr_headcount_summary', {}, 'departments'),
            ('hr_tenure_summary', {}, 'bands'),
        ]:
            code, result = demo.json_request(self.base + '/mcp',
                {'jsonrpc':'2.0', 'id':1, 'method':'tools/call',
                 'params':{'_meta':demo.META, 'name':name, 'arguments':arguments}})
            self.assertEqual(code, 200)
            data = json.loads(result['result']['content'][0]['text'])
            self.assertIn(field, data)
            self.assertNotIn('employees', data)
            self.assertNotIn('full_name', json.dumps(data))

    def test_direct_bypass_would_expose_synthetic_employee_details(self):
        code, out = demo.json_request(self.base + '/mcp',
            {'jsonrpc':'2.0', 'id':1, 'method':'tools/call',
             'params':{'_meta':demo.META,'name':'hr_employee_export','arguments':{'scope':'all'}}})
        self.assertEqual(code, 200)
        data=json.loads(out['result']['content'][0]['text'])
        self.assertTrue(data['synthetic'])
        self.assertIn('employees', data)
        self.assertIn('monthly_salary_mxn', data['employees'][0])

    def test_browser_rejects_uncommitted_receipt(self):
        class TestBrowser(demo.Browser):
            pass
        TestBrowser.mock = self.base
        TestBrowser.dashboard = self.dashboard_url
        stub = ThreadingHTTPServer(('127.0.0.1', 0), TestBrowser)
        thread = threading.Thread(target=stub.serve_forever, daemon=True)
        thread.start()
        try:
            listing = (200, {'result': {'tools': [{'name': 'hr_attrition_summary'}]}})
            no_receipt = (200, {'result': {'content': [{'text': json.dumps(warehouse.attrition_summary())}]}})
            with patch.object(demo, 'mcp_call', side_effect=[listing, no_receipt]):
                req = Request(f'http://127.0.0.1:{stub.server_port}/api/query', method='POST',
                    data=json.dumps({'session':'hr-demo-test','query':'attrition'}).encode(),
                    headers={'Content-Type':'application/json'})
                with self.assertRaises(HTTPError) as ctx:
                    urlopen(req, timeout=5)
                self.assertEqual(ctx.exception.code, 502)
        finally:
            stub.shutdown()
            stub.server_close()
            thread.join()

    def test_dashboard_http_returns_actual_metrics_and_charts(self):
        class TestBrowser(demo.Browser):
            pass
        TestBrowser.mock = self.base
        TestBrowser.dashboard = self.dashboard_url
        app = ThreadingHTTPServer(('127.0.0.1', 0), TestBrowser)
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f'http://127.0.0.1:{app.server_port}/api/dashboard') as response:
                stats=json.load(response)
            self.assertGreater(stats['headcount'], 700)
            self.assertEqual(stats['data_period'], '2026-09')
            self.assertTrue(stats['synthetic'])
            with urlopen(f'http://127.0.0.1:{app.server_port}/charts') as response:
                page=response.read().decode()
            self.assertIn('12-month workforce attrition', page)
            self.assertIn('Active headcount', page)
        finally:
            app.shutdown()
            app.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
