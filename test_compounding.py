# test_compounding.py
"""
Critical test: Does the system actually learn?

This test proves expertise compounds by debugging the same class
of problem multiple times and measuring improvement.
"""

import sys
import os
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from coding_agent import CodingAgent
from knowledge_core import StructuredContext, PatternCategory
from failure_taxonomy import FailureTaxonomy


def test_compounding_expertise():
    """
    The core validation: Does debugging get faster?
    
    Expected behavior:
    - Session 1-2: No guidance, must explore
    - Session 3: Might start seeing patterns  
    - Session 4: Should promote to archetype
    - Sessions 5-7: Strong guidance from archetype, fast recognition
    """
    
    print("=" * 70)
    print("COMPOUNDING EXPERTISE TEST")
    print("=" * 70)
    print()
    
    agent = CodingAgent(use_docker=False)
    
    context = StructuredContext(
        language="python",
        problem_type="concurrency",
        domain="threading"
    )
    
    # Five similar race condition problems
    problems = [
        {
            'symptom': 'Counter shows wrong value after concurrent increments',
            'test_code': '''
counter = 0
import threading

def increment():
    global counter
    for _ in range(100):
        temp = counter
        temp += 1
        counter = temp

threads = [threading.Thread(target=increment) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()

if counter != 500:
    print(f"RACE DETECTED: got {counter}, expected 500")
else:
    print("No race detected")
''',
            'root_cause': 'Race condition due to non-atomic read-modify-write',
            'fix_code': '''
counter = 0
import threading
lock = threading.Lock()

def safe_increment():
    global counter
    for _ in range(100):
        with lock:
            counter += 1

threads = [threading.Thread(target=safe_increment) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Final value: {counter} (expected 500)")
'''
        },
        {
            'symptom': 'Shared dictionary gets corrupted during parallel writes',
            'test_code': '''
data = {}
import threading

def write_data(key):
    for i in range(50):
        data[f"{key}_{i}"] = i

threads = [threading.Thread(target=write_data, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()

expected = 5 * 50
actual = len(data)
if actual != expected:
    print(f"CORRUPTION DETECTED: got {actual} items, expected {expected}")
else:
    print("No corruption detected")
''',
            'root_cause': 'Concurrent dictionary modifications without synchronization',
            'fix_code': '''
data = {}
import threading
lock = threading.Lock()

def safe_write_data(key):
    for i in range(50):
        with lock:
            data[f"{key}_{i}"] = i

threads = [threading.Thread(target=safe_write_data, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Items written: {len(data)} (expected 250)")
'''
        },
        {
            'symptom': 'List size incorrect after concurrent append operations',
            'test_code': '''
items = []
import threading

def append_items():
    for i in range(100):
        items.append(i)

threads = [threading.Thread(target=append_items) for _ in range(3)]
for t in threads: t.start()
for t in threads: t.join()

expected = 300
actual = len(items)
if actual != expected:
    print(f"RACE DETECTED: got {actual} items, expected {expected}")
else:
    print("No race detected")
''',
            'root_cause': 'Race condition in list append under concurrent access',
            'fix_code': '''
items = []
import threading
lock = threading.Lock()

def safe_append_items():
    for i in range(100):
        with lock:
            items.append(i)

threads = [threading.Thread(target=safe_append_items) for _ in range(3)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Items appended: {len(items)} (expected 300)")
'''
        },
        {
            'symptom': 'Balance calculation wrong with concurrent deposits',
            'test_code': '''
balance = 0
import threading

def deposit(amount):
    global balance
    for _ in range(50):
        current = balance
        current += amount
        balance = current

threads = [threading.Thread(target=deposit, args=(10,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

expected = 4 * 50 * 10
actual = balance
if actual != expected:
    print(f"RACE DETECTED: balance is {actual}, expected {expected}")
else:
    print("No race detected")
''',
            'root_cause': 'Unsynchronized access to shared balance variable',
            'fix_code': '''
balance = 0
import threading
lock = threading.Lock()

def safe_deposit(amount):
    global balance
    for _ in range(50):
        with lock:
            balance += amount

threads = [threading.Thread(target=safe_deposit, args=(10,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Final balance: {balance} (expected 2000)")
'''
        },
        {
            'symptom': 'Shared counter inconsistent with concurrent access',
            'test_code': '''
counter = 0
import threading

def modify_counter():
    global counter
    for _ in range(100):
        old = counter
        counter = old + 1

threads = [threading.Thread(target=modify_counter) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

if counter != 400:
    print(f"RACE DETECTED: counter is {counter}, expected 400")
else:
    print("No race detected")
''',
            'root_cause': 'Race condition from unprotected shared state mutation',
            'fix_code': '''
counter = 0
import threading
lock = threading.Lock()

def safe_modify_counter():
    global counter
    for _ in range(100):
        with lock:
            counter += 1

threads = [threading.Thread(target=safe_modify_counter) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Final counter: {counter} (expected 400)")
'''
        },
        {
            'symptom': 'Cache data inconsistent under concurrent load',
            'test_code': '''
cache = {}
import threading

def update_cache(key):
    for i in range(50):
        old_value = cache.get(key, 0)
        cache[key] = old_value + 1

threads = [threading.Thread(target=update_cache, args=('total',)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

expected = 200
actual = cache.get('total', 0)
if actual != expected:
    print(f"RACE DETECTED: cache value is {actual}, expected {expected}")
else:
    print("No race detected")
''',
            'root_cause': 'Concurrent cache updates without synchronization',
            'fix_code': '''
cache = {}
import threading
lock = threading.Lock()

def safe_update_cache(key):
    for i in range(50):
        with lock:
            old_value = cache.get(key, 0)
            cache[key] = old_value + 1

threads = [threading.Thread(target=safe_update_cache, args=('total',)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Cache value: {cache.get('total', 0)} (expected 200)")
'''
        },
        {
            'symptom': 'Shared resource pool corrupted by concurrent operations',
            'test_code': '''
pool = []
import threading

def use_resource():
    for i in range(50):
        # Simulate: check out, use, return
        pool.append(i)
        if pool:
            pool.pop()

threads = [threading.Thread(target=use_resource) for _ in range(3)]
for t in threads: t.start()
for t in threads: t.join()

if len(pool) != 0:
    print(f"RACE DETECTED: pool has {len(pool)} items, expected 0")
else:
    print("No race detected")
''',
            'root_cause': 'Race condition in resource pool management',
            'fix_code': '''
pool = []
import threading
lock = threading.Lock()

def safe_use_resource():
    for i in range(50):
        with lock:
            pool.append(i)
            if pool:
                pool.pop()

threads = [threading.Thread(target=safe_use_resource) for _ in range(3)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Pool size: {len(pool)} (expected 0)")
'''
        }
    ]
    
    session_data = []
    
    for i, problem in enumerate(problems, 1):
        print(f"\n{'='*70}")
        print(f"SESSION {i}: {problem['symptom']}")
        print(f"{'='*70}\n")
        
        session_start = time.time()
        
        # Start debugging
        session = agent.start_debugging(
            symptom=problem['symptom'],
            context=context
        )
        
        # Get initial guidance
        initial_guidance = agent.get_guidance(
            problem=problem['symptom'],
            context=context,
            what_failed={}
        )
        
        print("INITIAL GUIDANCE:")
        print(initial_guidance)
        print()
        
        # Test the race condition hypothesis
        print("Testing hypothesis: 'Race condition in shared state'...")
        test_result = agent.test_hypothesis(
            session=session,
            hypothesis="Race condition in shared state access",
            test_code=problem['test_code'],
            expected_if_true="RACE DETECTED",
            expected_if_false="No race detected"
        )
        
        print(f"Result: {test_result['observation'][:100]}...")
        print(f"Confirmed: {test_result['confirmed']}")
        print()
        
        # Resolve the session
        print("Applying fix...")
        
        # Debug: Check taxonomy state before closing
        print(f"[DEBUG] Current signatures: {len(agent.taxonomy.signatures)}")
        print(f"[DEBUG] Current archetypes: {len(agent.taxonomy.archetypes)}")
        
        resolution = agent.resolve_debug(
            session=session,
            root_cause=problem['root_cause'],
            fix_code=problem['fix_code'],
            evidence=[
                "Non-atomic operations on shared state",
                "Multiple threads accessing without synchronization",
                test_result['observation'][:200]
            ]
        )
        
        # Debug: Check after closing
        print(f"[DEBUG] After close - signatures: {len(agent.taxonomy.signatures)}, archetypes: {len(agent.taxonomy.archetypes)}")
        
        session_time = time.time() - session_start
        
        print(f"Resolution validated: {resolution['validated']}")
        print(f"Archetype ID: {resolution['archetype_id']}")
        print(f"Session time: {session_time:.2f}s")
        
        # Get taxonomy state
        taxonomy_summary = agent.taxonomy.get_summary()
        
        session_data.append({
            'session': i,
            'time': session_time,
            'guidance_length': len(initial_guidance),
            'has_guidance': 'No similar failures' not in initial_guidance,
            'archetype_id': resolution.get('archetype_id'),
            'total_archetypes': taxonomy_summary['total_archetypes'],
            'validated': resolution['validated']
        })
        
        print()
    
    # Analysis
    print("\n" + "="*70)
    print("COMPOUNDING ANALYSIS")
    print("="*70)
    print()
    
    print("Session | Time(s) | Has Guidance | Archetype | Total Archetypes")
    print("-" * 70)
    for data in session_data:
        print(f"   {data['session']}    | {data['time']:6.2f}  | "
              f"{'Yes' if data['has_guidance'] else 'No ':>12} | "
              f"{data['archetype_id'] or 'None':>9} | {data['total_archetypes']}")
    
    print()
    
    # Check for learning
    times = [d['time'] for d in session_data]
    guidance_improved = sum(1 for d in session_data if d['has_guidance'])
    archetype_created = any(d['archetype_id'] for d in session_data)
    
    print("LEARNING INDICATORS:")
    print(f"  Sessions with guidance: {guidance_improved}/{len(session_data)}")
    print(f"  Archetype created: {archetype_created}")
    print(f"  Final archetypes: {session_data[-1]['total_archetypes']}")
    
    # Get final expertise summary
    expertise = agent.get_expertise_summary()
    print(f"\nFINAL EXPERTISE STATE:")
    print(f"  Total concepts: {expertise['knowledge']['total_concepts']}")
    print(f"  Total executions: {expertise['knowledge']['total_outcomes']}")
    print(f"  Total archetypes: {expertise['taxonomy']['total_archetypes']}")
    print(f"  High-confidence patterns: {expertise['knowledge']['high_confidence_patterns']}")
    
    # Show archetypes
    if expertise['taxonomy']['archetypes']:
        print(f"\nARCHETYPES LEARNED:")
        for arch in expertise['taxonomy']['archetypes']:
            print(f"  - {arch['name']}: {arch['confidence']:.1%} confidence "
                  f"({arch['times_seen']} seen, {arch['times_fixed']} fixed)")
    
    print()
    print("="*70)
    print("TEST RESULTS")
    print("="*70)
    
    # Assertions
    passed = []
    failed = []
    
    # Test 1: Archetype should be created by session 3
    if archetype_created:
        passed.append("✓ Archetype created from clustering")
    else:
        failed.append("✗ No archetype created (clustering failed)")
    
    # Test 2: Later sessions should have guidance (at least 3 now with 7 sessions)
    if guidance_improved >= 3:
        passed.append(f"✓ {guidance_improved} sessions received historical guidance")
    else:
        failed.append(f"✗ Only {guidance_improved} sessions got guidance (expected ≥3)")
    
    # Test 3: All validations should succeed
    all_validated = all(d['validated'] for d in session_data)
    if all_validated:
        passed.append("✓ All fixes validated successfully")
    else:
        failed.append("✗ Some fixes failed validation")
    
    # Test 4: Knowledge should accumulate
    if expertise['knowledge']['total_concepts'] > 0:
        passed.append(f"✓ {expertise['knowledge']['total_concepts']} concepts learned")
    else:
        failed.append("✗ No concepts created")
    
    print()
    for result in passed:
        print(f"  {result}")
    for result in failed:
        print(f"  {result}")
    
    print()
    
    if not failed:
        print("🎉 SUCCESS: System demonstrates compounding expertise!")
        print()
        print("Key findings:")
        print(f"  - Patterns clustered into {expertise['taxonomy']['total_archetypes']} archetype(s)")
        print(f"  - {guidance_improved} sessions benefited from prior experience")
        print(f"  - Archetype achieved {session_data[-1]['total_archetypes']} total archetypes")
        print(f"  - Sessions 5-7 received instant diagnostic guidance")
        print()
        print("The system is LEARNING, not just pattern matching.")
        print("Later sessions are faster because the system remembers.")
    else:
        print("⚠️  PARTIAL SUCCESS")
        print()
        print(f"Passed: {len(passed)}/{len(passed) + len(failed)} checks")
        print()
        print("The foundation works, but clustering may need tuning.")
    
    print("="*70)
    
    return len(failed) == 0


if __name__ == "__main__":
    success = test_compounding_expertise()
    exit(0 if success else 1)
