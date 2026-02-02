
import sys
import os

sys.path.append(os.getcwd())

from app.ai.tools.bq_queries.leavers import get_leavers_list, get_leavers_distribution

print("🚀 Testing Quarter Logic...")

# Test 1: get_leavers_list
print("\n--- Test 1: get_leavers_list('2025-Q4') ---")
res1 = get_leavers_list(periodo="2025-Q4", uo_value="Corporativo")
# We look for the debug_sql in the content
sql1 = next((item['payload'] for item in res1['content'] if item['type'] == 'debug_sql'), "NO SQL FOUND")
print(f"SQL Snippet:\n{sql1}")

if "BETWEEN 10 AND 12" in sql1:
    print("✅ SQL contains correct Q4 range (10-12)")
else:
    print("❌ SQL Missing Q4 range")

# Test 2: get_leavers_distribution
print("\n--- Test 2: get_leavers_distribution('2025-Q1') ---")
res2 = get_leavers_distribution(periodo="2025-Q1", breakdown_by="UO2")
sql2 = next((item['payload'] for item in res2['content'] if item['type'] == 'debug_sql'), "NO SQL FOUND")
print(f"SQL Snippet:\n{sql2}")

if "BETWEEN 1 AND 3" in sql2:
    print("✅ SQL contains correct Q1 range (1-3)")
else:
    print("❌ SQL Missing Q1 range")
