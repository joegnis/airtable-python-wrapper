""" Airtable Python Wrapper  """

__author__ = 'Gui Talarico'
__version__ = '0.1.0'

import os
import json
import requests
import posixpath
import time

from airtable.auth import AirtableAuth
from airtable.models import Records

from urllib.parse import urlencode
from configparser import ConfigParser


class Airtable():

    _VERSION = 'v0'
    _API_BASE_URL = 'https://api.airtable.com/'

    API_URL = posixpath.join(_API_BASE_URL, _VERSION)
    ALLOWED_PARAMS = ['view', 'maxRecords', 'offset', 'sort']

    def __init__(self, base_key, table_name):
        session = requests.Session()
        session.auth = AirtableAuth()
        self.session = session
        self.url_table = posixpath.join(self.API_URL, base_key, table_name)
        self.is_authenticated = self.validate_authentication(self.url_table)

    def validate_authentication(self, url):
        response = self.session.get(url, params={'maxRecords': 1})
        if response.ok:
            return True
        else:
            raise ValueError('Authentication failed. Check your API Key')

    def if_ok(self, response):
        response.raise_for_status()
        return response

    def _get(self, url, **params):
        if any([True for option in params.keys() if option not in self.ALLOWED_PARAMS]):
            raise ValueError('invalid url param: {}'.format(params.keys()))
        return self.if_ok(self.session.get(url, params=params))

    def _post(self, url, json_data):
        return self.if_ok(self.session.post(url, json=json_data))

    def _patch(self, url, json_data):
        return self.if_ok(self.session.patch(url, json=json_data))

    def get_records(self, **options):
        """
        Get records

        Kwargs:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve
            sort (``dict``): {'field': 'COLUMND_ID', 'direction':'desc'} | 'asc'

        Returns:
            records (``list``): List of Records

        >>> records = get_records(maxRecords=3, view='All')
        """
        records = []
        offset = None
        while True:
            response = self._get(self.url_table, offset=offset, **options)
            response_data = response.json()
            records.extend(response_data.get('records', []))
            offset = response_data.get('offset')
            if not response.ok or 'offset' not in response_data:
                break
        return records

    def get_match(self, field_name, field_value, **options):
        """
        Returns First match

        Args:
            field_name (``str``)
            field_value (``str``)

        Returns:
            record (``dict``)
        """
        for record in self.get_records(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                return record

    def get_search(self, field_name, field_value, **options):
        records = []
        for record in self.get_records(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                records.append(record)
        return records

    def insert(self, fields):
        """
        Inserts a record

        Args:
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key
        Returns:
            response
        """
        return self._post(self.url_table, json_data={"fields": fields})

    def batch_insert(self, rows):
        """ Batch Insert without breaking API Rate Limit (5/sec) """
        for row in rows:
            self.insert(row)
            time.sleept(0.21)

    def update(self, record_id, fields, **options):
        record_url = posixpath.join(self.url_table, record_id)
        return self._patch(record_url, json_data={"fields": fields})

    def update_by_field(self, field_name, field_value, fields, view=''):
        record = self.get_match(field_name, field_value, view=view)
        if record:
            record_url = posixpath.join(self.url_table, record['id'])
            return self._patch(record_url, json_data={"fields": fields})