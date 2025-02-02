"""
 Copyright (C) 2015-2021, Wazuh Inc.
 Created by Wazuh, Inc. <info@wazuh.com>.
 This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
"""

import pytest

from pathlib import Path
from wazuh_testing.constants.paths.configurations import WAZUH_CONF_PATH
from wazuh_testing.tools.monitors.file_monitor import FileMonitor
from wazuh_testing.utils.callbacks import generate_callback
from wazuh_testing.utils.configuration import get_test_cases_data, load_configuration_template
from wazuh_testing.constants.paths.logs import WAZUH_LOG_PATH

from . import CONFIGS_PATH, TEST_CASES_PATH

from wazuh_testing.modules.remoted.configuration import REMOTED_DEBUG
from wazuh_testing.modules.remoted import patterns

# Set pytest marks.
pytestmark = [pytest.mark.server, pytest.mark.tier(level=1)]

# Cases metadata and its ids.
cases_path = Path(TEST_CASES_PATH, 'cases_syslog_invalid_denied_ips.yaml')
config_path = Path(CONFIGS_PATH, 'config_syslog_invalid_denied_ips.yaml')
test_configuration, test_metadata, cases_ids = get_test_cases_data(cases_path)
test_configuration = load_configuration_template(config_path, test_configuration, test_metadata)

daemons_handler_configuration = {'all_daemons': True}

local_internal_options = {REMOTED_DEBUG: '2'}

# Test function.
@pytest.mark.parametrize('test_configuration, test_metadata',  zip(test_configuration, test_metadata), ids=cases_ids)
def test_invalid_denied_ips_syslog(test_configuration, test_metadata, configure_local_internal_options, truncate_monitored_files,
                            set_wazuh_configuration, restart_wazuh_expect_error):

    '''
    description: Check that 'wazuh-remoted' fails when 'denied-ips' has invalid values.
                 For this purpose, it uses the configuration from test cases and check if the different errors are
                 logged correctly.

    parameters:
        - test_configuration
            type: dict
            brief: Configuration applied to ossec.conf.
        - test_metadata:
            type: dict
            brief: Test case metadata.
        - truncate_monitored_files:
            type: fixture
            brief: Truncate all the log files and json alerts files before and after the test execution.
        - configure_local_internal_options:
            type: fixture
            brief: Configure the Wazuh local internal options using the values from `local_internal_options`.
        - daemons_handler:
            type: fixture
            brief: Starts/Restarts the daemons indicated in `daemons_handler_configuration` before each test,
                   once the test finishes, stops the daemons.
        - restart_wazuh_expect_error
            type: fixture
            brief: Restart service when expected error is None, once the test finishes stops the daemons.
    '''

    log_monitor = FileMonitor(WAZUH_LOG_PATH)

    log_monitor.start(callback=generate_callback(patterns.ERROR_INVALID_IP,
                                                    replacement={
                                                    "ip": test_metadata['denied-ips']}))

    assert log_monitor.callback_result

    log_monitor.start(callback=generate_callback(patterns.ERROR_IN_CONFIGURATION,
                                                    replacement={
                                                    "severity": 'ERROR',
                                                    "conf_path": "etc/ossec.conf"}))
    assert log_monitor.callback_result

    log_monitor.start(callback=generate_callback(patterns.ERROR_IN_CONFIGURATION,
                                                    replacement={
                                                    "severity": 'CRITICAL',
                                                    "conf_path": "etc/ossec.conf"}))
    assert log_monitor.callback_result
