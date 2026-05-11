"""Quick sanity check - verify imports and basic structure."""
import sys
sys.path.insert(0, '/mnt/d/Projects/pickaxes/seo-audit-mcp')

# Test imports
from collections import Counter
import re
import json
from urllib.parse import urlparse

# Test that server.py parses correctly
import importlib.util
spec = importlib.util.spec_from_file_location("server", "/mnt/d/Projects/pickaxes/seo-audit-mcp/server.py")
mod = importlib.util.module_from_spec(spec)
# Don't execute (avoids httpx dependency), just verify the spec loads
print(f"Module spec loaded: {spec is not None}")
print(f"Module name: {spec.name}")
print(f"Module origin: {spec.origin}")

# Check the source is valid Python
with open("/mnt/d/Projects/pickaxes/seo-audit-mcp/server.py") as f:
    source = f.read()
compile(source, "server.py", "exec")
print("Python source compiles successfully!")

# Check all 4 tool functions exist in source
tools = ["seo_analyze_url", "seo_check_headers", "seo_suggest_keywords", "seo_analyze_speed_factors"]
for tool in tools:
    assert tool in source, f"Missing tool: {tool}"
    print(f"  ✅ Found tool: {tool}")

# Check required patterns
assert "@server.list_tools()" in source
assert "@server.call_tool()" in source
assert "async def main():" in source
print("  ✅ MCP server structure verified")

# Check pricing in README
with open("/mnt/d/Projects/pickaxes/seo-audit-mcp/README.md") as f:
    readme = f.read()
assert "$19/month" in readme or "$19/mo" in readme
assert "buy.stripe.com" in readme
print("  ✅ Pricing and Stripe link in README")

print("\n✅ All checks passed!")
