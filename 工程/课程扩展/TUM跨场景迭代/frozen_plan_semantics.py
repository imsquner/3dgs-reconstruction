"""Compare frozen JSON meaning; no coercion of budgets, hashes or IDs."""
import json
def assert_same_plan(saved,expected):
 assert saved==json.loads(json.dumps(expected,allow_nan=False)), 'Frozen plan differs semantically'
 return True
