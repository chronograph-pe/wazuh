import pytest

from pathlib import Path

from wazuh_testing.constants.paths.logs import WAZUH_LOG_PATH, ACTIVE_RESPONSE_LOG_PATH
from wazuh_testing.modules.active_response import patterns
from wazuh_testing.modules.execd import EXECD_DEBUG_CONFIG
from wazuh_testing.modules.execd.patterns import EXECD_EXECUTING_COMMAND
from wazuh_testing.tools.file_monitor import FileMonitor
from wazuh_testing.utils.callbacks import generate_callback
from wazuh_testing.utils.configuration import get_test_cases_data, load_configuration_template
from wazuh_testing.utils.services import control_service

from . import CONFIGS_PATH, TEST_CASES_PATH


# Set pytest marks.
pytestmark = [pytest.mark.agent, pytest.mark.tier(level=1)]

# Configuration and cases data.
configs_path = Path(CONFIGS_PATH, 'config_execd.yaml')
cases_path = Path(TEST_CASES_PATH, 'cases_execd_firewall_drop.yaml')

# Test configurations.
test_configuration, test_metadata, cases_ids = get_test_cases_data(cases_path)
test_configuration = load_configuration_template(configs_path, test_configuration, test_metadata)

# Test internal options.
local_internal_options = EXECD_DEBUG_CONFIG
# Test daemons to restart.
daemons_handler_configuration = {'all_daemons': True}
# Test Active Response configuration
active_response_configuration = 'restart-wazuh0 - restart-wazuh - 0\n' \
                                'restart-wazuh0 - restart-wazuh.exe - 0\n' \
                                'firewall-drop0 - firewall-drop - 0\n' \
                                'firewall-drop5 - firewall-drop - 5'


# Test function.

@pytest.mark.parametrize('test_configuration, test_metadata', zip(test_configuration, test_metadata), ids=cases_ids)
def test_execd_firewall_drop(test_configuration, test_metadata, set_wazuh_configuration, configure_local_internal_options,
                             truncate_monitored_files, active_response_configuration, send_execd_message):
    '''
    description: Check if 'firewall-drop' command of 'active response' is executed correctly.
                 For this purpose, a simulated agent is used and the 'active response'
                 is sent to it. This response includes an IP address that must be added
                 and removed from 'iptables', the Linux firewall.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - set_debug_mode:
            type: fixture
            brief: Set the 'wazuh-execd' daemon in debug mode.
        - get_configuration:
            type: fixture
            brief: Get configurations from the module.
        - test_version:
            type: fixture
            brief: Validate the Wazuh version.
        - configure_environment:
            type: fixture
            brief: Configure a custom environment for testing.
        - remove_ip_from_iptables:
            type: fixture
            brief: Remove the testing IP address from 'iptables' if it exists.
        - start_agent:
            type: fixture
            brief: Create 'wazuh-remoted' and 'wazuh-authd' simulators, register agent and start it.
        - set_ar_conf_mode:
            type: fixture
            brief: Configure the 'active responses' used in the test.

    assertions:
        - Verify that the testing IP address is added to 'iptables'.
        - Verify that the testing IP address is removed from 'iptables'.

    input_description: Different use cases are found in the test module and include
                       parameters for 'firewall-drop' command and the expected result.

    expected_output:
        - r'DEBUG: Received message'
        - r'Starting'
        - r'active-response/bin/firewall-drop'
        - r'Ended'
        - r'Cannot read 'srcip' from data' (If the 'active response' fails)

    tags:
        - simulator
    '''
    # Instantiate the monitors.
    ar_monitor = FileMonitor(ACTIVE_RESPONSE_LOG_PATH)
    wazuh_log_monitor = FileMonitor(WAZUH_LOG_PATH)

    # If the command is invalid, check it raised the warning.
    if not test_metadata['success']:
        callback = generate_callback(patterns.ACTIVE_RESPONSE_CANNOT_READ_SRCIP)
        ar_monitor.start(callback=callback)
        assert ar_monitor.callback_result, 'AR `firewall-drop` did not fail.'
        return

    # Wait for the firewall drop command to be executed.
    wazuh_log_monitor.start(callback=generate_callback(EXECD_EXECUTING_COMMAND))
    assert wazuh_log_monitor.callback_result, 'Execd `executing` command log not raised.'

    # Wait and check the add command to be executed.
    ar_monitor.start(callback=generate_callback(patterns.ACTIVE_RESPONSE_ADD_COMMAND))
    assert '"command":"add"' in ar_monitor.callback_result, 'AR `add` command not executed.'

    # Wait and check the delete command to be executed.
    ar_monitor.start(callback=generate_callback(patterns.ACTIVE_RESPONSE_DELETE_COMMAND))
    assert '"command":"delete"' in ar_monitor.callback_result, 'AR `delete` command not executed.'
