import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

# Configuration
LOG_FILE = Path(".agent/logs/performance.jsonl")

def load_logs(limit=None):
    if not LOG_FILE.exists():
        print(f"❌ Log file not found at {LOG_FILE}")
        return []
    
    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    except Exception as e:
        print(f"❌ Error reading logs: {e}")
        return []

    return logs[-limit:] if limit else logs

def analyze(logs):
    stats = defaultdict(list)
    
    for entry in logs:
        tool = entry.get("tool", "unknown")
        duration = entry.get("duration_seconds", 0)
        stats[tool].append(duration)
        
    print(f"\n📊 PERFORMANCE REPORT (Last {len(logs)} entries)")
    print("=" * 65)
    print(f"{'TOOL':<30} | {'COUNT':<5} | {'AVG (s)':<8} | {'MAX (s)':<8} | {'P95 (s)':<8}")
    print("-" * 65)
    
    for tool, durations in stats.items():
        count = len(durations)
        avg_d = statistics.mean(durations)
        max_d = max(durations)
        # Simple P95
        durations.sort()
        p95_idx = int(len(durations) * 0.95)
        p95_d = durations[p95_idx]
        
        print(f"{tool:<30} | {count:<5} | {avg_d:<8.4f} | {max_d:<8.4f} | {p95_d:<8.4f}")
    
    print("=" * 65)
    print(f"📅 Generated at: {datetime.now().isoformat()}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze ADK Performance Logs")
    parser.add_argument("--limit", type=int, default=100, help="Number of last entries to analyze")
    args = parser.parse_args()
    
    data = load_logs(args.limit)
    if data:
        analyze(data)
    else:
        print("No data found.")
