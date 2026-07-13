"""Tests for lazy loading configuration system."""

import os

from web_agent.config import CONFIG


class TestLazyConfig:
	"""Test lazy loading of environment variables through CONFIG object."""

	def test_config_reads_env_vars_lazily(self):
		"""Test that CONFIG reads environment variables each time they're accessed."""
		# Set an env var
		original_value = os.environ.get('web_agent_LOGGING_LEVEL', '')
		try:
			os.environ['web_agent_LOGGING_LEVEL'] = 'debug'
			assert CONFIG.web_agent_LOGGING_LEVEL == 'debug'

			# Change the env var
			os.environ['web_agent_LOGGING_LEVEL'] = 'info'
			assert CONFIG.web_agent_LOGGING_LEVEL == 'info'

			# Delete the env var to test default
			del os.environ['web_agent_LOGGING_LEVEL']
			assert CONFIG.web_agent_LOGGING_LEVEL == 'info'  # default value
		finally:
			# Restore original value
			if original_value:
				os.environ['web_agent_LOGGING_LEVEL'] = original_value
			else:
				os.environ.pop('web_agent_LOGGING_LEVEL', None)

	def test_boolean_env_vars(self):
		"""Test boolean environment variables are parsed correctly."""
		original_value = os.environ.get('ANONYMIZED_TELEMETRY', '')
		try:
			# Test true values
			for true_val in ['true', 'True', 'TRUE', 'yes', 'Yes', '1']:
				os.environ['ANONYMIZED_TELEMETRY'] = true_val
				assert CONFIG.ANONYMIZED_TELEMETRY is True, f'Failed for value: {true_val}'

			# Test false values
			for false_val in ['false', 'False', 'FALSE', 'no', 'No', '0']:
				os.environ['ANONYMIZED_TELEMETRY'] = false_val
				assert CONFIG.ANONYMIZED_TELEMETRY is False, f'Failed for value: {false_val}'
		finally:
			if original_value:
				os.environ['ANONYMIZED_TELEMETRY'] = original_value
			else:
				os.environ.pop('ANONYMIZED_TELEMETRY', None)

	def test_api_keys_lazy_loading(self):
		"""Test API keys are loaded lazily."""
		original_value = os.environ.get('OPENAI_API_KEY', '')
		try:
			# Test empty default
			os.environ.pop('OPENAI_API_KEY', None)
			assert CONFIG.OPENAI_API_KEY == ''

			# Set a value
			os.environ['OPENAI_API_KEY'] = 'test-key-123'
			assert CONFIG.OPENAI_API_KEY == 'test-key-123'

			# Change the value
			os.environ['OPENAI_API_KEY'] = 'new-key-456'
			assert CONFIG.OPENAI_API_KEY == 'new-key-456'
		finally:
			if original_value:
				os.environ['OPENAI_API_KEY'] = original_value
			else:
				os.environ.pop('OPENAI_API_KEY', None)

	def test_path_configuration(self):
		"""Test path configuration variables."""
		original_value = os.environ.get('XDG_CACHE_HOME', '')
		try:
			# Test custom path
			test_path = '/tmp/test-cache'
			os.environ['XDG_CACHE_HOME'] = test_path
			# Use Path().resolve() to handle symlinks (e.g., /tmp -> /private/tmp on macOS)
			from pathlib import Path

			assert CONFIG.XDG_CACHE_HOME == Path(test_path).resolve()

			# Test default path expansion
			os.environ.pop('XDG_CACHE_HOME', None)
			assert '/.cache' in str(CONFIG.XDG_CACHE_HOME)
		finally:
			if original_value:
				os.environ['XDG_CACHE_HOME'] = original_value
			else:
				os.environ.pop('XDG_CACHE_HOME', None)

	def test_uppercase_env_var_is_read(self):
		"""WEB_AGENT_* (upper-snake) should work, not just the legacy mixed-case web_agent_*."""
		original = os.environ.get('web_agent_LOGGING_LEVEL', '')
		original_upper = os.environ.get('WEB_AGENT_LOGGING_LEVEL', '')
		try:
			os.environ.pop('web_agent_LOGGING_LEVEL', None)
			os.environ['WEB_AGENT_LOGGING_LEVEL'] = 'debug'
			assert CONFIG.web_agent_LOGGING_LEVEL == 'debug'
		finally:
			os.environ.pop('WEB_AGENT_LOGGING_LEVEL', None)
			if original:
				os.environ['web_agent_LOGGING_LEVEL'] = original
			if original_upper:
				os.environ['WEB_AGENT_LOGGING_LEVEL'] = original_upper

	def test_uppercase_env_var_takes_precedence_over_legacy(self):
		"""When both WEB_AGENT_* and legacy web_agent_* are set, the uppercase one wins."""
		original = os.environ.get('web_agent_LOGGING_LEVEL', '')
		original_upper = os.environ.get('WEB_AGENT_LOGGING_LEVEL', '')
		try:
			os.environ['web_agent_LOGGING_LEVEL'] = 'warning'
			os.environ['WEB_AGENT_LOGGING_LEVEL'] = 'debug'
			assert CONFIG.web_agent_LOGGING_LEVEL == 'debug'
		finally:
			if original:
				os.environ['web_agent_LOGGING_LEVEL'] = original
			else:
				os.environ.pop('web_agent_LOGGING_LEVEL', None)
			if original_upper:
				os.environ['WEB_AGENT_LOGGING_LEVEL'] = original_upper
			else:
				os.environ.pop('WEB_AGENT_LOGGING_LEVEL', None)

	def test_flat_env_config_proxy_url_uppercase(self):
		"""FlatEnvConfig-only fields (e.g. proxy URL) should also accept the uppercase name."""
		from web_agent.config import FlatEnvConfig

		original = os.environ.get('WEB_AGENT_PROXY_URL', '')
		try:
			os.environ['WEB_AGENT_PROXY_URL'] = 'http://proxy.example.com:8080'
			env_config = FlatEnvConfig()
			assert env_config.web_agent_PROXY_URL == 'http://proxy.example.com:8080'
		finally:
			if original:
				os.environ['WEB_AGENT_PROXY_URL'] = original
			else:
				os.environ.pop('WEB_AGENT_PROXY_URL', None)

	def test_cloud_sync_inherits_telemetry(self):
		"""Test web_agent_CLOUD_SYNC inherits from ANONYMIZED_TELEMETRY when not set."""
		telemetry_original = os.environ.get('ANONYMIZED_TELEMETRY', '')
		sync_original = os.environ.get('web_agent_CLOUD_SYNC', '')
		try:
			# When web_agent_CLOUD_SYNC is not set, it should inherit from ANONYMIZED_TELEMETRY
			os.environ['ANONYMIZED_TELEMETRY'] = 'true'
			os.environ.pop('web_agent_CLOUD_SYNC', None)
			assert CONFIG.web_agent_CLOUD_SYNC is True

			os.environ['ANONYMIZED_TELEMETRY'] = 'false'
			os.environ.pop('web_agent_CLOUD_SYNC', None)
			assert CONFIG.web_agent_CLOUD_SYNC is False

			# When explicitly set, it should use its own value
			os.environ['ANONYMIZED_TELEMETRY'] = 'false'
			os.environ['web_agent_CLOUD_SYNC'] = 'true'
			assert CONFIG.web_agent_CLOUD_SYNC is True
		finally:
			if telemetry_original:
				os.environ['ANONYMIZED_TELEMETRY'] = telemetry_original
			else:
				os.environ.pop('ANONYMIZED_TELEMETRY', None)
			if sync_original:
				os.environ['web_agent_CLOUD_SYNC'] = sync_original
			else:
				os.environ.pop('web_agent_CLOUD_SYNC', None)
