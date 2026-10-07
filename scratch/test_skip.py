import re

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def parse_override_command(text):
    text = text.strip()
    if text.lower() in ['list', 'status', 'view', 'show']:
        return {'action': 'list'}
        
    skip_match = re.match(r'^(?P<day>' + '|'.join(DAYS) + r')\s+(?:skip|none|off|disabled)$', text, re.IGNORECASE)
    if skip_match:
        return {'action': 'skip', 'day': skip_match.group('day').lower()}
        
    clear_match = re.match(r'^(?P<day>' + '|'.join(DAYS) + r')\s+(?:clear|delete|remove|reset)$', text, re.IGNORECASE)
    if clear_match:
        return {'action': 'clear', 'day': clear_match.group('day').lower()}
        
    pattern = r'^(?P<day>' + '|'.join(DAYS) + r')\s+search\s+["\'`]?(.+?)["\'`]?\s+offset\s+([-+]?\d+)$'
    match = re.match(pattern, text, re.IGNORECASE)
    if match:
        day, query, offset = match.groups()
        return {'action': 'set', 'day': day.lower(), 'query': query.strip('"`\' '), 'offset': int(offset)}
        
    return None

test_cases = [
    'saturday skip',
    'sunday off',
    'wednesday disabled',
    'monday search "ny times" offset -1',
    'saturday clear'
]

for tc in test_cases:
    print(tc, '-->', parse_override_command(tc))
