#!/usr/bin/env python

"""Tests for `configuration` sub-package."""
# pylint: disable=redefined-outer-name

import unittest
from jsonschema.exceptions import ValidationError
from typing import Dict
import logging
import os

from youbot import Configuration, validate_json_schema

logger = logging.getLogger('TestConfiguration')


class TestConfiguration(unittest.TestCase):

    def test_validation_library(self):
        """ Sanity Check unittest"""
        configuration_schema = Configuration.load_configuration_schema(
            os.path.join(self.test_data_path, 'simplest_yml_schema.json'))
        wrong_confs = [
            {"subproperty1": [123, 234],
             "subproperty2": 1},  # p1 is string

            {"subproperty1": "10",
             "subproperty2": 3},  # p2 is either 1 or 2

            {"subproperty2": 1},  # p1 is required

            {"subproperty1": "10",
             "subproperty2": 1,
             "subproperty3": {}},  # p4 is required in p3

            {"subproperty1": "10",
             "subproperty2": 1,
             "subproperty3": {"subproperty4": 15}}  # p4 is either 1 or 2
        ]
        for wrong_conf in wrong_confs:
            with self.assertRaises(ValidationError):
                # try:
                validate_json_schema(wrong_conf, configuration_schema)
            # except Exception as e:
            #     print(e)
        logger.info('YMLs failed to validate successfully.')

    def test_schema_validation(self):
        try:
            logger.info('Loading the correct Configuration..')
            Configuration(config_src=os.path.join(self.test_data_path, 'minimal_conf_correct.yml'),
                          config_schema_path=os.path.join(self.test_data_path,
                                                          'minimal_yml_schema.json'))
        except ValidationError as e:
            logger.error('Error validating the correct yml: %s', e)
            self.fail('Error validating the correct yml')
        except Exception as e:
            raise e
        else:
            logger.info('First yml validated successfully.')

        with self.assertRaises(ValidationError):
            logger.info('Loading the wrong Configuration..')
            Configuration(config_src=os.path.join(self.test_data_path, 'minimal_conf_wrong.yml'),
                          config_schema_path=os.path.join(self.test_data_path,
                                                          'minimal_yml_schema.json'))
        logger.info('Second yml failed to validate successfully.')

    def test_to_json(self):
        logger.info('Loading Configuration..')
        configuration = Configuration(config_src=os.path.join(self.test_data_path, 'minimal_conf_correct.yml'),
                                      config_schema_path=os.path.join(self.test_data_path,
                                                                      'minimal_yml_schema.json'))

        expected_json = {'datastore': 'test',
                         'cloudstore': [{
                             'subproperty1': 1,
                             'subproperty2': [123, 234]
                         }],
                         'tag': 'test_tag'}
        # Compare
        logger.info('Comparing the results..')
        self.assertDictEqual(self._sort_dict(expected_json), self._sort_dict(configuration.to_json()))

    def test_to_yaml(self):
        logger.info('Loading Configuration..')
        configuration = Configuration(config_src=os.path.join(self.test_data_path, 'minimal_conf_correct.yml'),
                                      config_schema_path=os.path.join(self.test_data_path,
                                                                      'minimal_yml_schema.json'))
        # Modify and export yml
        logger.info('Changed the host and the api_key..')
        configuration.config['cloudstore'][0]['subproperty1'] = 999
        configuration.tag = 'CHANGED VALUE'
        logger.info('Exporting to yaml..')
        configuration.to_yaml(os.path.join(self.test_data_path,
                                           'actual_output_to_yaml.yml'))
        # Load the modified yml
        logger.info('Loading the exported yaml..')
        modified_configuration = Configuration(
            config_src=os.path.join(self.test_data_path, 'actual_output_to_yaml.yml'))
        # Compare
        logger.info('Comparing the results..')
        expected_json = {'datastore': 'test',
                         'cloudstore': [{
                             'subproperty1': 999,
                             'subproperty2': [123, 234]
                         }],
                         'tag': 'CHANGED VALUE'}
        self.assertDictEqual(self._sort_dict(expected_json), self._sort_dict(modified_configuration.to_json()))

    def test_get_config(self):
        logger.info('Loading Configuration..')
        configuration = Configuration(config_src=os.path.join(self.test_data_path, 'minimal_conf_correct.yml'),
                                      config_schema_path=os.path.join(self.test_data_path,
                                                                      'minimal_yml_schema.json'))
        cloudstore_config = configuration.get_config(config_name='cloudstore')
        expected_json = [{
            'subproperty1': 1,
            'subproperty2': [123, 234]
        }]
        # Compare
        logger.info('Comparing the results..')
        self.assertListEqual(expected_json, cloudstore_config)

    @classmethod
    def _sort_dict(cls, dictionary: Dict) -> Dict:
        return {k: cls._sort_dict(v) if isinstance(v, dict) else v
                for k, v in sorted(dictionary.items())}

    @staticmethod
    def _setup_log() -> None:
        # noinspection PyArgumentList
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            handlers=[logging.StreamHandler()
                                      ]
                            )

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    @classmethod
    def setUpClass(cls):
        cls._setup_log()
        cls.tests_abs_path = os.path.abspath(os.path.dirname(__file__))
        cls.test_data_path: str = os.path.join(cls.tests_abs_path, 'test_data', 'test_configuration')

    @classmethod
    def tearDownClass(cls):
        pass


if __name__ == '__main__':
    unittest.main()
