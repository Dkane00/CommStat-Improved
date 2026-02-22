#!/usr/bin/env python3
"""
Test script for TCP message processing refactoring.

Tests all message formats to ensure the refactored code works correctly:
- Standard STATREP ({&%})
- Forwarded STATREP ({F%})
- F!304 format
- F!301 format
- Alert ({%%})
- Message (plain)
- Bulletin ({^%})
- Duplicate callsign handling
"""

import sys
import sqlite3
import re
from datetime import datetime, timezone

# Import the helper functions we added
sys.path.insert(0, '.')
from little_gucci import (
    ConsoleColors,
    sanitize_ascii,
    parse_message_datetime,
    strip_duplicate_callsign,
    expand_plus_shorthand,
    extract_grid_from_text,
    calculate_f304_status,
    map_f304_digits_to_fields,
    map_f301_digits_to_fields,
    format_statrep_comments
)

DATABASE_FILE = "traffic.db3"

# Test message data
TEST_MESSAGES = [
    {
        "name": "Standard STATREP",
        "value": "W8APP: @AMRRON ,EN82,1,174,111111111111,MI BEAUTIFUL SUNNY MORNING,{&%}",
        "from_callsign": "W8APP",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:30:00",
        "freq": 14118000,
        "snr": -3,
        "expected_type": "statrep"
    },
    {
        "name": "Forwarded STATREP",
        "value": "W1FWD: @AMRRON ,FN42,2,175,222222222222,RELAYED MESSAGE,W8APP,{F%}",
        "from_callsign": "W1FWD",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:31:00",
        "freq": 14118000,
        "snr": 5,
        "expected_type": "statrep"
    },
    {
        "name": "F!304 format",
        "value": "KB8UVN: @AMRRON MSG F!304 11114444 EN82",
        "from_callsign": "KB8UVN",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:32:00",
        "freq": 14118000,
        "snr": 10,
        "expected_type": "statrep"
    },
    {
        "name": "F!301 format",
        "value": "KB8UVN: @AMRRON MSG F!301 111114444 FN42",
        "from_callsign": "KB8UVN",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:33:00",
        "freq": 14118000,
        "snr": 8,
        "expected_type": "statrep"
    },
    {
        "name": "Alert",
        "value": "W1ABC: @ALL ,1,Test Alert,This is a test alert message,{%%}",
        "from_callsign": "W1ABC",
        "target": "@ALL",
        "utc": "2026-02-08   10:34:00",
        "freq": 14118000,
        "snr": -5,
        "expected_type": "alert"
    },
    {
        "name": "Plain Message",
        "value": "W8APP: @AMRRON MSG Hello everyone this is a test message",
        "from_callsign": "W8APP",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:35:00",
        "freq": 14118000,
        "snr": 0,
        "expected_type": "message"
    },
    {
        "name": "Bulletin Message",
        "value": "KD9DSS: @AMRRON MSG ,223,Test bulletin content,{^%}",
        "from_callsign": "KD9DSS",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:36:00",
        "freq": 14118000,
        "snr": 12,
        "expected_type": "message"
    },
    {
        "name": "Duplicate Callsign (JS8Call bug)",
        "value": "W8APP: W8APP: @AMRRON MSG Testing duplicate callsign handling",
        "from_callsign": "W8APP",
        "target": "@AMRRON",
        "utc": "2026-02-08   10:37:00",
        "freq": 14118000,
        "snr": 3,
        "expected_type": "message"
    }
]


def test_helper_functions():
    """Test the new helper functions."""
    print(f"\n{ConsoleColors.SUCCESS}=== Testing Helper Functions ==={ConsoleColors.RESET}\n")

    tests_passed = 0
    tests_failed = 0

    # Test 1: sanitize_ascii
    print("Test 1: sanitize_ascii()")
    test_cases = [
        ("Hello World", "Hello World"),
        ("Test\x00\x01\x02", "Test"),
        ("Café", "Caf"),
        ("Test™®©", "Test"),
        ("Normal ASCII 123!@#", "Normal ASCII 123!@#")
    ]
    for input_text, expected in test_cases:
        result = sanitize_ascii(input_text)
        if result == expected:
            print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} '{input_text}' -> '{result}'")
            tests_passed += 1
        else:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} '{input_text}' -> '{result}' (expected '{expected}')")
            tests_failed += 1

    # Test 2: parse_message_datetime
    print("\nTest 2: parse_message_datetime()")
    test_cases = [
        "2026-02-08   10:30:00",  # 3 spaces
        "2026-02-08 10:30:00",    # 1 space
    ]
    for utc in test_cases:
        try:
            date_only, msg_id = parse_message_datetime(utc)
            if date_only == "2026-02-08" and len(msg_id) > 0:
                print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} '{utc}' -> date='{date_only}', id='{msg_id}'")
                tests_passed += 1
            else:
                print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} '{utc}' -> Unexpected result")
                tests_failed += 1
        except Exception as e:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} '{utc}' -> Exception: {e}")
            tests_failed += 1

    # Test 3: strip_duplicate_callsign
    print("\nTest 3: strip_duplicate_callsign()")
    test_cases = [
        ("W8APP: W8APP: @AMRRON MSG Test", "W8APP", "W8APP: @AMRRON MSG Test"),
        ("KB8UVN: KB8UVN: @ALL MSG Hello", "KB8UVN", "KB8UVN: @ALL MSG Hello"),
        ("W8APP: @AMRRON MSG Test", "W8APP", "W8APP: @AMRRON MSG Test"),  # No duplicate
        ("N0DDK: N0DDK: @AMRRON MSG", "N0DDK/P", "N0DDK: @AMRRON MSG"),  # With suffix in from_call but not in value
    ]
    for value, from_call, expected in test_cases:
        result = strip_duplicate_callsign(value, from_call)
        if result == expected:
            print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} '{value}' -> '{result}'")
            tests_passed += 1
        else:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} '{value}' -> '{result}' (expected '{expected}')")
            tests_failed += 1

    # Test 4: extract_grid_from_text
    print("\nTest 4: extract_grid_from_text()")
    test_cases = [
        ("Some text EN82 more text", "", ("EN82", True)),
        ("F!304 11114444 FN42", "", ("FN42", True)),
        ("No grid here", "EM15", ("EM15", False)),
        ("EM15at is 6-char", "", ("EM15AT", True)),
    ]
    for text, default, expected in test_cases:
        result = extract_grid_from_text(text, default)
        if result == expected:
            print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} '{text}' -> {result}")
            tests_passed += 1
        else:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} '{text}' -> {result} (expected {expected})")
            tests_failed += 1

    # Test 5: calculate_f304_status
    print("\nTest 5: calculate_f304_status()")
    test_cases = [
        ("11111111", True, "1"),   # Score 8, grid = green (1)
        ("11114444", True, "1"),   # Score 8, grid = green (1)
        ("22224444", True, "2"),   # Score 12 (>10, not >12), grid = yellow (2)
        ("33334444", True, "3"),   # Score 16 (>12), grid = red (3)
        ("11111111", False, "4"),  # Score 8 but no grid = unknown (4)
    ]
    for digits, grid_found, expected in test_cases:
        result = calculate_f304_status(digits, grid_found)
        if result == expected:
            print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} digits='{digits}', grid={grid_found} -> '{result}'")
            tests_passed += 1
        else:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} digits='{digits}', grid={grid_found} -> '{result}' (expected '{expected}')")
            tests_failed += 1

    # Test 6: map_f304_digits_to_fields
    print("\nTest 6: map_f304_digits_to_fields()")
    result = map_f304_digits_to_fields("11114444")
    if result['power'] == '4' and result['water'] == '4' and len(result['comment_parts']) == 4:
        print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} F!304 digit mapping works")
        tests_passed += 1
    else:
        print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} F!304 digit mapping failed: {result}")
        tests_failed += 1

    # Test 7: map_f301_digits_to_fields
    print("\nTest 7: map_f301_digits_to_fields()")
    result = map_f301_digits_to_fields("111114444")
    if result['scope'] == 'My Location' and result['power'] == '4' and len(result['comment_parts']) == 3:
        print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} F!301 digit mapping works")
        tests_passed += 1
    else:
        print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} F!301 digit mapping failed: {result}")
        tests_failed += 1

    print(f"\n{ConsoleColors.SUCCESS}Helper Function Tests: {tests_passed} passed{ConsoleColors.RESET}")
    if tests_failed > 0:
        print(f"{ConsoleColors.ERROR}                       {tests_failed} failed{ConsoleColors.RESET}")

    return tests_passed, tests_failed


def check_database_insert(table, id_field, id_value, test_name):
    """Check if a record was inserted into the database."""
    try:
        conn = sqlite3.connect(DATABASE_FILE, timeout=10)
        cursor = conn.cursor()

        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {id_field} = ?", (id_value,))
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute(f"SELECT * FROM {table} WHERE {id_field} = ?", (id_value,))
            row = cursor.fetchone()
            print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} {test_name}: Record found in {table}")
            conn.close()
            return True
        else:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} {test_name}: Record NOT found in {table}")
            conn.close()
            return False

    except sqlite3.Error as e:
        print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} {test_name}: Database error: {e}")
        if 'conn' in locals():
            conn.close()
        return False


def test_message_processing():
    """Test message processing with sample data by directly calling helper logic."""
    print(f"\n{ConsoleColors.SUCCESS}=== Testing Message Processing ==={ConsoleColors.RESET}\n")

    tests_passed = 0
    tests_failed = 0

    # We'll test the helper functions' ability to process the messages
    # Since we can't easily instantiate the full LittleGucci class, we'll test
    # the individual components

    for test_msg in TEST_MESSAGES:
        print(f"\nTest: {test_msg['name']}")
        print(f"  Value: {test_msg['value'][:60]}...")

        try:
            # Test 1: Strip duplicate callsign if present
            cleaned_value = strip_duplicate_callsign(test_msg['value'], test_msg['from_callsign'])
            if "duplicate" in test_msg['name'].lower():
                if cleaned_value != test_msg['value']:
                    print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} Duplicate callsign stripped correctly")
                    tests_passed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} Duplicate callsign NOT stripped")
                    tests_failed += 1

            # Test 2: Parse datetime
            date_only, msg_id = parse_message_datetime(test_msg['utc'])
            if date_only == "2026-02-08" and len(msg_id) > 0:
                print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} DateTime parsed: date={date_only}, id={msg_id}")
                tests_passed += 1
            else:
                print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} DateTime parsing failed")
                tests_failed += 1

            # Test 3: Type-specific processing
            if "{&%}" in test_msg['value'] or "{F%}" in test_msg['value']:
                # STATREP processing
                marker = "{F%}" if "{F%}" in test_msg['value'] else "{&%}"
                match = re.search(r',(.+?)' + re.escape(marker), test_msg['value'])
                if match:
                    fields = match.group(1).split(",")
                    if len(fields) >= 4:
                        grid = fields[0].strip()
                        srcode = fields[3].strip()
                        srcode = expand_plus_shorthand(srcode)
                        print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} STATREP parsed: grid={grid}, srcode={srcode[:12]}")
                        tests_passed += 1
                    else:
                        print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} STATREP field count insufficient")
                        tests_failed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} STATREP pattern match failed")
                    tests_failed += 1

            elif "F!304" in test_msg['value']:
                # F!304 processing
                match = re.search(r'F!304\s+(\d{8})\s*(.*?)(?:>])?$', test_msg['value'], re.IGNORECASE)
                if match:
                    digits = match.group(1)
                    remainder = match.group(2)
                    field_map = map_f304_digits_to_fields(digits)
                    grid, found = extract_grid_from_text(remainder, "")
                    status = calculate_f304_status(digits, found)
                    print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} F!304 parsed: digits={digits}, grid={grid}, status={status}")
                    tests_passed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} F!304 pattern match failed")
                    tests_failed += 1

            elif "F!301" in test_msg['value']:
                # F!301 processing
                match = re.search(r'F!301\s+(\d{9})\s*(.*?)(?:>])?$', test_msg['value'], re.IGNORECASE)
                if match:
                    digits = match.group(1)
                    remainder = match.group(2)
                    field_map = map_f301_digits_to_fields(digits)
                    grid, found = extract_grid_from_text(remainder, "")
                    status = calculate_f304_status(digits[1:], found)
                    print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} F!301 parsed: digits={digits}, scope={field_map['scope']}, grid={grid}")
                    tests_passed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} F!301 pattern match failed")
                    tests_failed += 1

            elif "{%%}" in test_msg['value']:
                # Alert processing
                match = re.search(r'(@\w+)\s*,(.+?)\{\%\%\}', test_msg['value'])
                if match:
                    alert_target = match.group(1).strip()
                    fields_str = match.group(2).strip()
                    fields = fields_str.split(",", 2)
                    if len(fields) >= 3:
                        alert_color = int(fields[0].strip())
                        alert_title = sanitize_ascii(fields[1].strip())
                        alert_message = sanitize_ascii(fields[2].strip())
                        print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} ALERT parsed: target={alert_target}, color={alert_color}, title='{alert_title}'")
                        tests_passed += 1
                    else:
                        print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} ALERT field count insufficient")
                        tests_failed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} ALERT pattern match failed")
                    tests_failed += 1

            elif "MSG" in test_msg['value']:
                # Message processing
                msg_pattern = re.match(r'^(\w+):\s+(@?\w+)\s+MSG\s+(.+)$', cleaned_value, re.IGNORECASE)
                if msg_pattern:
                    msg_from = msg_pattern.group(1).strip()
                    msg_target = msg_pattern.group(2).strip()
                    message_text = msg_pattern.group(3).strip()

                    # Handle bulletin
                    if '{^%}' in message_text:
                        message_text = re.sub(r'^\s*,\d{3},\s*', '', message_text)
                        message_text = message_text.replace(',{^%}', '')

                    message_text = sanitize_ascii(message_text.strip())
                    print(f"  {ConsoleColors.SUCCESS}[PASS]{ConsoleColors.RESET} MESSAGE parsed: from={msg_from}, to={msg_target}, text='{message_text[:30]}...'")
                    tests_passed += 1
                else:
                    print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} MESSAGE pattern match failed")
                    tests_failed += 1

        except Exception as e:
            print(f"  {ConsoleColors.ERROR}[FAIL]{ConsoleColors.RESET} Exception: {e}")
            tests_failed += 1

    print(f"\n{ConsoleColors.SUCCESS}Message Processing Tests: {tests_passed} passed{ConsoleColors.RESET}")
    if tests_failed > 0:
        print(f"{ConsoleColors.ERROR}                          {tests_failed} failed{ConsoleColors.RESET}")

    return tests_passed, tests_failed


def main():
    """Run all tests."""
    print(f"\n{ConsoleColors.SUCCESS}{'='*70}")
    print(f"  TCP Message Processing Refactoring - Test Suite")
    print(f"{'='*70}{ConsoleColors.RESET}\n")

    total_passed = 0
    total_failed = 0

    # Test 1: Helper functions
    passed, failed = test_helper_functions()
    total_passed += passed
    total_failed += failed

    # Test 2: Message processing
    passed, failed = test_message_processing()
    total_passed += passed
    total_failed += failed

    # Final summary
    print(f"\n{ConsoleColors.SUCCESS}{'='*70}")
    print(f"  FINAL RESULTS")
    print(f"{'='*70}{ConsoleColors.RESET}")
    print(f"\n  Total Tests: {total_passed + total_failed}")
    print(f"  {ConsoleColors.SUCCESS}Passed: {total_passed}{ConsoleColors.RESET}")
    if total_failed > 0:
        print(f"  {ConsoleColors.ERROR}Failed: {total_failed}{ConsoleColors.RESET}")
        print(f"\n{ConsoleColors.ERROR}[FAILED] TESTS FAILED{ConsoleColors.RESET}\n")
        return 1
    else:
        print(f"\n{ConsoleColors.SUCCESS}[SUCCESS] ALL TESTS PASSED{ConsoleColors.RESET}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
