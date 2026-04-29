import unittest
from collections import OrderedDict
from datetime import date
from types import SimpleNamespace

import tap_bing_ads


REPORT_PROPERTIES = OrderedDict([
    ('AccountId', {'type': ['null', 'integer']}),
    ('TimePeriod', {'type': ['null', 'string'], 'format': 'date-time'}),
    ('CampaignId', {'type': ['null', 'integer']}),
    ('CampaignName', {'type': ['null', 'string']}),
    ('CampaignType', {'type': ['null', 'string']}),
    ('AdGroupId', {'type': ['null', 'integer']}),
    ('AdGroupName', {'type': ['null', 'string']}),
    ('Keyword', {'type': ['null', 'string']}),
    ('KeywordId', {'type': ['null', 'integer']}),
    ('Goal', {'type': ['null', 'string']}),
    ('GoalId', {'type': ['null', 'integer']}),
    ('GoalType', {'type': ['null', 'string']}),
    ('AllConversions', {'type': ['null', 'number']}),
    ('Assists', {'type': ['null', 'integer']}),
    ('AllConversionsQualified', {'type': ['null', 'number']}),
    ('_sdc_report_datetime', {'type': 'string', 'format': 'date-time'}),
    ('run_id', {'type': 'integer'}),
])


def build_metadata(automatic_fields, selected_fields=None):
    selected_fields = selected_fields or set()
    metadata = [{'breadcrumb': [], 'metadata': {'inclusion': 'available'}}]

    for field in REPORT_PROPERTIES:
        field_metadata = {'inclusion': 'available'}
        if field in automatic_fields:
            field_metadata['inclusion'] = 'automatic'
        if field in selected_fields:
            field_metadata['selected'] = True

        metadata.append({
            'breadcrumb': ['properties', field],
            'metadata': field_metadata,
        })

    return metadata


def build_catalog_item(metadata):
    return SimpleNamespace(
        key_properties=[],
        metadata=metadata,
        schema=SimpleNamespace(properties=REPORT_PROPERTIES),
    )


class FakeFactory:
    def create(self, name):
        if name == 'ArrayOfGoalsAndFunnelsReportColumn':
            return SimpleNamespace(GoalsAndFunnelsReportColumn=[])
        if name == 'ReportTimeZone':
            return SimpleNamespace(
                GreenwichMeanTimeDublinEdinburghLisbonLondon='GreenwichMeanTimeDublinEdinburghLisbonLondon'
            )
        return SimpleNamespace()


class FakeClient:
    factory = FakeFactory()


class TestCampaignGoalsReport(unittest.TestCase):
    def test_campaign_goals_stream_maps_to_goals_and_funnels_report(self):
        self.assertEqual(
            'GoalsAndFunnelsReport',
            tap_bing_ads.get_report_name_for_stream('campaign_goals_and_funnels_report'))

    def test_campaign_goals_metadata_defaults_to_campaign_level(self):
        report_schema = {
            'properties': REPORT_PROPERTIES,
            'additionalProperties': False,
            'type': 'object',
        }

        report_metadata = tap_bing_ads.get_report_metadata(
            'campaign_goals_and_funnels_report',
            report_schema)
        automatic_fields = {
            tuple(entry['breadcrumb'])[1]
            for entry in report_metadata
            if entry['breadcrumb'] and entry['metadata'].get('inclusion') == 'automatic'
        }

        self.assertTrue({
            'AccountId',
            'TimePeriod',
            'CampaignId',
            'CampaignName',
            'CampaignType',
            'Goal',
            'GoalId',
            'GoalType',
            'AllConversions',
            'Assists',
            'AllConversionsQualified',
            'run_id',
        }.issubset(automatic_fields))
        self.assertFalse({
            'AdGroupId',
            'AdGroupName',
            'Keyword',
            'KeywordId',
        } & automatic_fields)

    def test_existing_goals_report_can_request_campaign_level_columns(self):
        metadata = build_metadata(
            {'AccountId', 'TimePeriod', 'Goal', 'run_id', '_sdc_report_datetime'},
            {'CampaignId', 'CampaignName', 'CampaignType', 'GoalId', 'GoalType',
             'AllConversionsQualified'})
        catalog_item = build_catalog_item(metadata)

        selected_fields = tap_bing_ads.get_selected_fields(
            catalog_item,
            exclude=['_sdc_report_datetime', 'run_id'])

        self.assertTrue({
            'AccountId',
            'TimePeriod',
            'CampaignId',
            'CampaignName',
            'CampaignType',
            'Goal',
            'GoalId',
            'GoalType',
            'AllConversionsQualified',
        }.issubset(selected_fields))
        self.assertFalse({
            'AdGroupId',
            'AdGroupName',
            'Keyword',
            'KeywordId',
        } & set(selected_fields))

    def test_campaign_goals_request_excludes_ad_group_and_keyword_columns(self):
        metadata = build_metadata({
            'AccountId',
            'TimePeriod',
            'CampaignId',
            'CampaignName',
            'CampaignType',
            'Goal',
            'GoalId',
            'GoalType',
            'AllConversions',
            'Assists',
            'AllConversionsQualified',
            'run_id',
            '_sdc_report_datetime',
        })
        catalog_item = build_catalog_item(metadata)

        request = tap_bing_ads.build_report_request(
            FakeClient(),
            123,
            catalog_item,
            'GoalsAndFunnelsReport',
            date(2024, 1, 1),
            date(2024, 1, 2))
        requested_columns = request.Columns.GoalsAndFunnelsReportColumn[0]

        self.assertTrue({
            'AccountId',
            'TimePeriod',
            'CampaignId',
            'CampaignName',
            'CampaignType',
            'Goal',
            'GoalId',
            'GoalType',
            'AllConversions',
            'Assists',
            'AllConversionsQualified',
        }.issubset(requested_columns))
        self.assertFalse({
            'AdGroupId',
            'AdGroupName',
            'Keyword',
            'KeywordId',
        } & set(requested_columns))


if __name__ == '__main__':
    unittest.main()
