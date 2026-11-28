import asyncio
import threading
import time
import unittest
from unittest import mock

import arrow

import tap_bing_ads


class TestConcurrentReportCalls(unittest.TestCase):
    """Report calls run on worker threads: different accounts' calls overlap, one account's
    calls (one SOAP client) never do."""

    def setUp(self):
        tap_bing_ads.CONFIG.clear()
        tap_bing_ads.CONFIG.update({'max_parallel_requests': 8})
        tap_bing_ads.EXECUTOR = None
        tap_bing_ads.ACCOUNT_LOCKS.clear()
        self.lock = threading.Lock()
        self.active = {}
        self.most_total = 0
        self.most_per_account = 0

    def tearDown(self):
        tap_bing_ads.EXECUTOR = None
        tap_bing_ads.ACCOUNT_LOCKS.clear()

    def poll(self, client, request_id):
        account = client
        with self.lock:
            self.active[account] = self.active.get(account, 0) + 1
            self.most_per_account = max(self.most_per_account, self.active[account])
            self.most_total = max(self.most_total, sum(self.active.values()))
        time.sleep(0.05)
        with self.lock:
            self.active[account] -= 1
        return mock.Mock(Status='Success', ReportDownloadUrl='https://x/' + request_id)

    def test_accounts_poll_side_by_side_and_each_account_one_at_a_time(self):
        async def everything():
            calls = [
                tap_bing_ads.poll_report(account, account, 'CampaignPerformanceReport',
                                         arrow.get('2026-11-01'), arrow.get('2026-11-02'), f'{account}-{report}')
                for account in ('1', '2', '3', '4')
                for report in range(3)
            ]
            return await asyncio.gather(*calls)

        with mock.patch('tap_bing_ads.generate_poll_report', side_effect=self.poll):
            started = time.monotonic()
            results = asyncio.run(everything())
            took = time.monotonic() - started
        self.assertTrue(all(ok and url for ok, url in results))
        self.assertEqual(self.most_per_account, 1)
        self.assertGreater(self.most_total, 1)
        # 12 calls of 50 ms: one at a time that is 600 ms; 4 accounts side by side about 150 ms.
        self.assertLess(took, 0.45)

    @mock.patch('tap_bing_ads.singer.write_record')
    def test_a_report_is_written_from_its_downloaded_zip(self, write):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('r.csv', '﻿"TimePeriod","Clicks"\n"2026-11-01","3"\n')
        tap_bing_ads.write_report('campaign_performance_report', buf.getvalue(), 't')
        row = write.call_args[0][1]
        self.assertTrue(row['TimePeriod'].startswith('2026-11-01'))
        self.assertEqual(row['_sdc_report_datetime'], 't')


if __name__ == '__main__':
    unittest.main()
