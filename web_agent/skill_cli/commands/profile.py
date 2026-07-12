"""Profile management command handlers.

Local Chrome profile management. Cloud profile management (browser-use-sdk)
has been removed from this project.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


ProfileMode = Literal['real', 'remote']


class ProfileModeError(Exception):
	"""Raised when profile mode cannot be determined or is invalid."""

	pass


def get_profile_mode(args: argparse.Namespace) -> ProfileMode:
	"""Determine profile mode from -b flag or install config.

	Args:
		args: Parsed command-line arguments with browser attribute

	Returns:
		'real' for local Chrome profiles, 'remote' for cloud profiles (removed)

	Raises:
		ProfileModeError: If mode cannot be determined or chromium mode is used
	"""
	from web_agent.skill_cli.install_config import is_mode_available

	browser_mode = getattr(args, 'browser', None)

	# Explicit mode specified
	if browser_mode == 'real':
		return 'real'
	elif browser_mode == 'remote':
		return 'remote'
	elif browser_mode == 'chromium':
		raise ProfileModeError(
			'Profile commands are not supported in chromium mode.\nUse -b real for local Chrome profiles.'
		)

	# No explicit mode - try to infer from install config
	local_available = is_mode_available('real')
	remote_available = is_mode_available('remote')

	if local_available and not remote_available:
		return 'real'
	elif remote_available and not local_available:
		return 'remote'
	elif local_available and remote_available:
		raise ProfileModeError('Both local and remote modes are available.\nSpecify -b real for local Chrome profiles.')
	else:
		raise ProfileModeError('No profile modes available. Run web-agent setup first.')


def handle_profile_command(args: argparse.Namespace) -> int:
	"""Handle profile subcommands (local Chrome profiles only)."""
	command = args.profile_command

	if command is None:
		_print_usage()
		return 1

	if command == 'sync':
		print('Error: Cloud profile sync has been removed from this project.', file=sys.stderr)
		return 1

	try:
		mode = get_profile_mode(args)
	except ProfileModeError as e:
		print(f'Error: {e}', file=sys.stderr)
		return 1

	if mode == 'remote':
		print('Error: Cloud profile management has been removed from this project. Use -b real.', file=sys.stderr)
		return 1

	if command == 'list':
		return _list_local_profiles(args)
	elif command == 'get':
		return _get_local_profile(args)
	elif command == 'create':
		print('Error: Cannot create local Chrome profiles via CLI.', file=sys.stderr)
		print('Use Chrome browser to create new profiles.', file=sys.stderr)
		return 1
	elif command == 'update':
		print('Error: Cannot update local Chrome profiles via CLI.', file=sys.stderr)
		print('Use Chrome browser settings to update profiles.', file=sys.stderr)
		return 1
	elif command == 'delete':
		print('Error: Cannot delete local Chrome profiles via CLI.', file=sys.stderr)
		print('Use Chrome browser settings to remove profiles.', file=sys.stderr)
		return 1
	elif command == 'cookies':
		return _list_profile_cookies(args)
	else:
		_print_usage()
		return 1


def _print_usage() -> None:
	"""Print profile command usage."""
	print('Usage: web-agent -b real profile <command>')
	print()
	print('Commands:')
	print('  list              List local Chrome profiles')
	print('  get <id>          Get profile details')
	print('  cookies <id>      Show cookies by domain')


# -----------------------------------------------------------------------------
# List profiles
# -----------------------------------------------------------------------------


def _list_local_profiles(args: argparse.Namespace) -> int:
	"""List local Chrome profiles."""
	profiles = list_local_chrome_profiles()

	if getattr(args, 'json', False):
		print(json.dumps({'profiles': profiles}))
	else:
		if profiles:
			print('Local Chrome profiles:')
			for p in profiles:
				print(f'  {p["id"]}: {p["name"]} ({p["email"]})')
		else:
			print('No Chrome profiles found')

	return 0


# -----------------------------------------------------------------------------
# Get profile
# -----------------------------------------------------------------------------


def _get_local_profile(args: argparse.Namespace) -> int:
	"""Get local Chrome profile details."""
	profiles = list_local_chrome_profiles()
	profile_id = args.id

	for p in profiles:
		if p['id'] == profile_id or p['name'] == profile_id:
			if getattr(args, 'json', False):
				print(json.dumps(p))
			else:
				print(f'Profile: {p["id"]}')
				print(f'  Name: {p["name"]}')
				print(f'  Email: {p["email"]}')
			return 0

	print(f'Error: Profile "{profile_id}" not found', file=sys.stderr)
	return 1


# -----------------------------------------------------------------------------
# Cookies (local only)
# -----------------------------------------------------------------------------


def _list_profile_cookies(args: argparse.Namespace) -> int:
	"""List cookies by domain in a local Chrome profile."""
	import asyncio

	from web_agent.skill_cli.sessions import create_browser_session

	# Get local profiles
	local_profiles = list_local_chrome_profiles()
	if not local_profiles:
		print('Error: No local Chrome profiles found', file=sys.stderr)
		return 1

	# Find the matching profile
	profile_arg = args.id
	selected_profile = None
	for p in local_profiles:
		if p['id'] == profile_arg or p['name'] == profile_arg:
			selected_profile = p
			break

	if not selected_profile:
		print(f'Error: Profile "{profile_arg}" not found', file=sys.stderr)
		print('Available profiles:')
		for p in local_profiles:
			print(f'  {p["id"]}: {p["name"]}')
		return 1

	profile_id = selected_profile['id']
	print(f'Loading cookies from: {selected_profile["name"]} ({selected_profile["email"]})')

	async def get_cookies():
		local_session = await create_browser_session('real', headed=False, profile=profile_id)
		await local_session.start()
		try:
			cookies = await local_session._cdp_get_cookies()
			return cookies
		finally:
			await local_session.kill()

	try:
		cookies = asyncio.get_event_loop().run_until_complete(get_cookies())
	except RuntimeError:
		cookies = asyncio.run(get_cookies())

	# Group cookies by domain
	domains: dict[str, int] = {}
	for cookie in cookies:
		domain = cookie.get('domain', 'unknown')
		# Normalize domain (remove leading dot)
		if domain.startswith('.'):
			domain = domain[1:]
		domains[domain] = domains.get(domain, 0) + 1

	# Sort by count descending
	sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)

	if getattr(args, 'json', False):
		print(json.dumps({'domains': dict(sorted_domains), 'total_cookies': len(cookies)}))
	else:
		print(f'\nCookies by domain ({len(cookies)} total):')
		for domain, count in sorted_domains[:20]:  # Show top 20
			print(f'  {domain}: {count}')
		if len(sorted_domains) > 20:
			print(f'  ... and {len(sorted_domains) - 20} more domains')

	return 0


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def list_local_chrome_profiles() -> list[dict[str, Any]]:
	"""List local Chrome profiles from the Local State file."""
	import platform

	# Find Chrome Local State file
	system = platform.system()
	if system == 'Darwin':
		local_state = Path.home() / 'Library/Application Support/Google/Chrome/Local State'
	elif system == 'Windows':
		local_state = Path.home() / 'AppData/Local/Google/Chrome/User Data/Local State'
	else:
		local_state = Path.home() / '.config/google-chrome/Local State'

	if not local_state.exists():
		return []

	try:
		data = json.loads(local_state.read_text())
		profiles_info = data.get('profile', {}).get('info_cache', {})

		profiles = []
		for profile_id, info in profiles_info.items():
			profiles.append(
				{
					'id': profile_id,
					'name': info.get('name', profile_id),
					'email': info.get('user_name', ''),
				}
			)
		return profiles
	except Exception:
		return []
