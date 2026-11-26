import asyncio
import unittest
from unittest import mock

import arrow

import tap_bing_ads


class Stream:
    stream = 'campaign_performance_report'


class TestReportWindowAttempts(unittest.TestCase):
    def setUp(self):
        tap_bing_ads.CONFIG.clear()
        tap_bing_ads.STATE.clear()
        tap_bing_ads.CONFIG.update({'start_date': '2026-11-01', 'end_date': '2026-11-03'})

    @mock.patch('tap_bing_ads.sync_report_interval')
    def test_a_window_bing_keeps_failing_fails_the_run(self, interval):
        async def failed(*args, **kwargs):
            return False
        interval.side_effect = failed
        with self.assertRaises(Exception) as raised:
            asyncio.run(tap_bing_ads.sync_report(None, 123, Stream()))
        self.assertIn('after 3 attempts', str(raised.exception))
        self.assertEqual(interval.call_count, tap_bing_ads.MAX_REPORT_WINDOW_ATTEMPTS)

    @mock.patch('tap_bing_ads.sync_report_interval')
    def test_a_failed_window_is_retried(self, interval):
        results = iter([False, True])

        async def flaky(*args, **kwargs):
            return next(results, True)
        interval.side_effect = flaky
        asyncio.run(tap_bing_ads.sync_report(None, 123, Stream()))
        self.assertGreaterEqual(interval.call_count, 2)


class TestPollTimeout(unittest.TestCase):
    @mock.patch('tap_bing_ads.MAX_NUM_REPORT_POLLS', 2)
    @mock.patch('tap_bing_ads.REPORT_POLL_SLEEP', 0)
    @mock.patch('tap_bing_ads.generate_poll_report')
    def test_a_report_still_pending_is_not_read_as_no_data(self, poll):
        poll.return_value = mock.Mock(Status='Pending', ReportDownloadUrl=None)
        success, url = asyncio.run(tap_bing_ads.poll_report(None, 1, 'CampaignPerformanceReport',
                                                            arrow.get('2026-11-01'), arrow.get('2026-11-02'), 'r'))
        self.assertFalse(success)
        self.assertIsNone(url)


class TestAccountsStream(unittest.TestCase):
    @mock.patch('tap_bing_ads.singer.write_records')
    @mock.patch('tap_bing_ads.singer.write_schema')
    @mock.patch('tap_bing_ads.get_core_schema', return_value={})
    @mock.patch('tap_bing_ads.CustomServiceClient')
    @mock.patch('tap_bing_ads.create_sdk_client')
    @mock.patch('tap_bing_ads.sobject_to_dict')
    def test_every_account_is_sent_whatever_the_bookmark(self, to_dict, create, *_):
        tap_bing_ads.STATE.clear()
        tap_bing_ads.STATE.update({'bookmarks': {'accounts': {'last_record': '2030-01-01T00:00:00'}}})
        to_dict.side_effect = [{'Id': 1, 'LastModifiedTime': '2026-01-01T00:00:00'},
                               {'Id': 2, 'LastModifiedTime': '2026-02-01T00:00:00'}]
        catalog_item = mock.Mock(metadata=None)
        tap_bing_ads.sync_accounts_stream(['1', '2'], catalog_item)
        sent = tap_bing_ads.singer.write_records.call_args[0][1]
        self.assertEqual([a['Id'] for a in sent], [1, 2])


if __name__ == '__main__':
    unittest.main()
