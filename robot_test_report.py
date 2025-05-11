#!/usr/bin/env python3

import sys
import json
from robot.api import ExecutionResult

def extract_keywords(item, html_lines, indent=0, is_setup=False, is_teardown=False):
    """Extract keywords from an item, handling nested structures."""
    # Skip items marked as NOT RUN
    if hasattr(item, 'status') and item.status == 'NOT RUN':
        return

    # Handle different types of items
    if hasattr(item, 'type'):
        if item.type in ['KEYWORD', 'SETUP', 'TEARDOWN']:
            # Handle all keywords, including setup and teardown
            keyword_name = getattr(item, 'kwname', '')
            if not keyword_name or keyword_name.startswith('$'):
                return

            # Get tags for the keyword
            tags = []
            if hasattr(item, 'tags'):
                tags = item.tags

            # Check if the keyword has user_defined tag
            has_user_defined_tag = False
            for tag in tags:
                if tag.lower() == 'user_defined':
                    has_user_defined_tag = True
                    break

            if not has_user_defined_tag:
                return

            # Use the complete keyword name
            keyword_name = keyword_name.split('  ')[0]

            if hasattr(item, 'body') and item.body:
                # If keyword has nested keywords, make it foldable
                keyword_class = ""
                if is_setup:
                    keyword_class = "setup-keyword"
                elif is_teardown:
                    keyword_class = "teardown-keyword"

                html_lines.append(f"<li class='{keyword_class}' data-tags='{' '.join(tags)}'>{keyword_name}")
                html_lines.append("<ul>")
                for nested_item in item.body:
                    extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)
                html_lines.append("</ul>")
                html_lines.append("</li>")
            else:
                # If no nested keywords, display as a simple list item
                keyword_class = ""
                if is_setup:
                    keyword_class = "setup-keyword"
                elif is_teardown:
                    keyword_class = "teardown-keyword"

                html_lines.append(f"<li class='{keyword_class}' data-tags='{' '.join(tags)}'>{keyword_name}</li>")

    # Process nested items
    if hasattr(item, 'body'):
        for nested_item in item.body:
            extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)

def process_suite(suite, html_lines, processed_tests=None):
    """Process a test suite and its contents."""
    if processed_tests is None:
        processed_tests = set()

    html_lines.append(f"""
        <div class="test-suite">
            <div class="suite-header" aria-expanded="false">
                <div>
                    <div class="suite-name">Suite: {suite.name}</div>
                </div>
                <span class="chevron">▸</span>
            </div>
            <div class="suite-content">""")

    # Process suite setup
    if hasattr(suite, 'setup') and suite.setup:
        html_lines.append("""
                <div class="test-case">
                    <div class="test-name">Suite Setup</div>
                    <div class="keywords">""")
        extract_keywords(suite.setup, html_lines, is_setup=True)
        html_lines.append("""
                    </div>
                </div>""")

    # Process nested suites
    for subsuite in suite.suites:
        process_suite(subsuite, html_lines, processed_tests)

    # Process test cases
    for test in suite.tests:
        # Skip if we've already processed this test
        test_id = f"{suite.name}.{test.name}"
        if test_id in processed_tests:
            continue
        processed_tests.add(test_id)

        html_lines.append(f"""
                <div class="test-case">
                    <div class="test-name">Test Case: {test.name}</div>
                    <div class="keywords">""")

        # Process test setup
        if hasattr(test, 'setup') and test.setup:
            html_lines.append("""
                        <div class="test-case">
                            <div class="test-name">Test Setup</div>
                            <div class="keywords">""")
            extract_keywords(test.setup, html_lines, is_setup=True)
            html_lines.append("""
                            </div>
                        </div>""")

        # Process test keywords
        for keyword in test.body:
            if not (hasattr(keyword, 'type') and keyword.type in ['SETUP', 'TEARDOWN']):
                extract_keywords(keyword, html_lines)

        # Process test teardown
        if hasattr(test, 'teardown') and test.teardown:
            html_lines.append("""
                        <div class="test-case">
                            <div class="test-name">Test Teardown</div>
                            <div class="keywords">""")
            extract_keywords(test.teardown, html_lines, is_teardown=True)
            html_lines.append("""
                            </div>
                        </div>""")

        html_lines.append("""
                    </div>
                </div>""")

    # Process suite teardown
    if hasattr(suite, 'teardown') and suite.teardown:
        html_lines.append("""
                <div class="test-case">
                    <div class="test-name">Suite Teardown</div>
                    <div class="keywords">""")
        extract_keywords(suite.teardown, html_lines, is_teardown=True)
        html_lines.append("""
                    </div>
                </div>""")

    html_lines.append("""
            </div>
        </div>""")

def count_test_cases_and_keywords(suite):
    """Count total test cases and keywords in a suite and its subsuites."""
    total_test_cases = len(suite.tests)
    total_keywords = 0

    # Count keywords in suite setup
    if suite.setup:
        total_keywords += 1  # Count the setup itself
        total_keywords += count_keywords_in_item(suite.setup)

    # Count keywords in suite teardown
    if suite.teardown:
        total_keywords += 1  # Count the teardown itself
        total_keywords += count_keywords_in_item(suite.teardown)

    # Count keywords in test cases
    for test in suite.tests:
        # Count test setup
        if hasattr(test, 'setup') and test.setup:
            total_keywords += 1  # Count the setup itself
            total_keywords += count_keywords_in_item(test.setup)

        # Count test keywords
        for keyword in test.body:
            total_keywords += 1  # Count the keyword itself
            total_keywords += count_keywords_in_item(keyword)

        # Count test teardown
        if hasattr(test, 'teardown') and test.teardown:
            total_keywords += 1  # Count the teardown itself
            total_keywords += count_keywords_in_item(test.teardown)

    # Recursively count in subsuites
    for subsuite in suite.suites:
        subsuite_tests, subsuite_keywords = count_test_cases_and_keywords(subsuite)
        total_test_cases += subsuite_tests
        total_keywords += subsuite_keywords

    return total_test_cases, total_keywords

def count_keywords_in_item(item):
    """Count keywords in an item (keyword, setup, teardown, etc.)."""
    count = 0
    if hasattr(item, 'body'):
        for nested_item in item.body:
            count += 1  # Count the nested item itself
            count += count_keywords_in_item(nested_item)
    return count

def count_keyword_occurrences(suite):
    """Count how many times each keyword is executed in a suite and its subsuites."""
    keyword_counts = {}

    def count_in_item(item):
        # Skip special types that don't represent actual keywords
        if hasattr(item, 'type') and item.type in ['FOR', 'IF/ELSE ROOT', 'RETURN', 'FOR ITERATION', 'IF BRANCH']:
            if hasattr(item, 'body'):
                for nested_item in item.body:
                    count_in_item(nested_item)
            return

        # Only count keywords with user_defined tag
        if hasattr(item, 'type') and item.type in ['KEYWORD', 'SETUP', 'TEARDOWN']:
            if hasattr(item, 'kwname'):
                keyword_name = item.kwname.split('  ')[0]
                # Skip keywords that start with $
                if not keyword_name.startswith('$'):
                    # Check if the keyword has user_defined tag
                    has_user_defined_tag = False
                    if hasattr(item, 'tags'):
                        for tag in item.tags:
                            if tag.lower() == 'user_defined':
                                has_user_defined_tag = True
                                break

                    if has_user_defined_tag:
                        keyword_counts[keyword_name] = keyword_counts.get(keyword_name, 0) + 1

        # Process nested items
        if hasattr(item, 'body'):
            for nested_item in item.body:
                count_in_item(nested_item)

    # Count in suite setup
    if suite.setup:
        count_in_item(suite.setup)

    # Count in suite teardown
    if suite.teardown:
        count_in_item(suite.teardown)

    # Count in test cases
    for test in suite.tests:
        if hasattr(test, 'setup') and test.setup:
            count_in_item(test.setup)
        for keyword in test.body:
            count_in_item(keyword)
        if hasattr(test, 'teardown') and test.teardown:
            count_in_item(test.teardown)

    # Count in subsuites
    for subsuite in suite.suites:
        subsuite_counts = count_keyword_occurrences(subsuite)
        for keyword, count in subsuite_counts.items():
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + count

    return keyword_counts

def get_user_defined_keywords(suite):
    """Get all unique keywords that have the user_defined tag from executed test cases."""
    keywords = set()
    visited = set()

    def process_item(item):
        if id(item) in visited:
            return
        visited.add(id(item))

        if hasattr(item, 'type') and item.type in ['KEYWORD', 'SETUP', 'TEARDOWN']:
            if hasattr(item, 'kwname'):
                keyword_name = item.kwname.split('  ')[0]
                if not keyword_name.startswith('$'):
                    # Check if the keyword has user_defined tag
                    if hasattr(item, 'tags'):
                        for tag in item.tags:
                            if tag.lower() == 'user_defined':
                                keywords.add(keyword_name)
                                break
        # Process nested items (sub-keywords)
        if hasattr(item, 'body'):
            for nested_item in item.body:
                process_item(nested_item)

    # Process suite setup
    if suite.setup:
        process_item(suite.setup)

    # Process suite teardown
    if suite.teardown:
        process_item(suite.teardown)

    # Process test cases
    for test in suite.tests:
        if hasattr(test, 'setup') and test.setup:
            process_item(test.setup)
        for keyword in test.body:
            process_item(keyword)
        if hasattr(test, 'teardown') and test.teardown:
            process_item(test.teardown)

    # Process subsuites
    for subsuite in suite.suites:
        keywords.update(get_user_defined_keywords(subsuite))

    return sorted(list(keywords))

def create_html_report(suites, total_tests, total_keywords, keyword_stats):
    html_parts = []

    # Add header and styles
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <title>Test Suite Overview</title>
    <style>
        :root {
            --primary-color: #007AFF;
            --success-color: #34C759;
            --warning-color: #FF9500;
            --error-color: #FF3B30;
            --text-primary: #1C1C1E;
            --text-secondary: #3A3A3C;
            --background-primary: #F2F2F7;
            --background-secondary: #FFFFFF;
            --border-color: #E5E5EA;
            --shadow-color: rgba(0, 0, 0, 0.1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background-color: var(--background-primary);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .main-title {
            color: var(--text-primary);
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            letter-spacing: -0.5px;
        }

        .statistics {
            text-align: center;
            margin-bottom: 1rem;
            font-size: 1.1rem;
            color: var(--text-secondary);
        }

        .statistics span {
            font-weight: 600;
            color: var(--text-primary);
        }

        .feedback-section {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background-color: var(--background-secondary);
        }

        .feedback-section h3 {
            margin-top: 0;
            color: var(--text-primary);
        }

        .feedback-section textarea {
            width: 100%;
            min-height: 100px;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-family: inherit;
        }

        .button-group {
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }

        .button-group button {
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            font-size: 14px;
            font-weight: 500;
        }

        .button-group button:hover {
            background-color: #45a049;
        }

        .note {
            margin: 10px 0;
            padding: 10px;
            border-left: 4px solid #4CAF50;
            background-color: #f9f9f9;
        }

        .note.implemented {
            text-decoration: line-through;
            color: #999;
        }

        .note .timestamp {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }

        .test-suite {
            background: var(--background-secondary);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px var(--shadow-color);
            overflow: hidden;
        }

        .suite-header {
            padding: 1.25rem;
            background: var(--background-secondary);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }

        .suite-name {
            font-weight: 600;
            color: var(--text-primary);
            font-size: 1.1rem;
        }

        .suite-content {
            display: none;
            padding: 1.25rem;
        }

        .suite-content.visible {
            display: block;
        }

        .test-case {
            padding: 1rem;
            margin: 0.5rem 0;
            background: var(--background-primary);
            border-radius: 8px;
            cursor: pointer;
        }

        .test-name {
            font-weight: 500;
            color: var(--text-primary);
        }

        .keywords {
            display: none;
            margin-top: 0.75rem;
        }

        .keywords.visible {
            display: block;
        }

        .keywords ul {
            list-style-type: none;
            padding-left: 2rem;
        }

        .keywords li {
            margin: 0.5rem 0;
            padding: 0.75rem;
            background: var(--background-secondary);
            border-radius: 8px;
            border-left: 3px solid var(--border-color);
        }

        .setup-keyword {
            border-left-color: var(--success-color);
        }

        .teardown-keyword {
            border-left-color: var(--error-color);
        }

        .test-cases-filter {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background-color: var(--background-secondary);
        }

        .filter-header {
            margin-bottom: 15px;
        }

        .filter-header input {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            margin-top: 10px;
            font-family: inherit;
        }

        .test-cases-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }

        .test-case-item {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            font-family: monospace;
        }

        .test-case-item:last-child {
            border-bottom: none;
        }

        .test-case-item:hover {
            background-color: #f5f5f5;
        }

        .keyword-item {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            font-family: monospace;
            cursor: pointer;
        }

        .keyword-item:last-child {
            border-bottom: none;
        }

        .keyword-item:hover {
            background-color: #f5f5f5;
        }

        .keyword-stats {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.1rem;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .keyword-stats:hover {
            color: var(--primary-color);
        }

        .keyword-stats-list {
            display: none;
            margin-top: 1rem;
            background: var(--background-secondary);
            border-radius: 8px;
            padding: 1rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }

        .keyword-stats-list.visible {
            display: block;
            margin-bottom: 3rem;
        }

        .keyword-stat-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .keyword-stat-item:last-child {
            border-bottom: none;
        }

        .keyword-name {
            font-weight: 500;
        }

        .keyword-count {
            font-weight: 600;
            color: var(--primary-color);
        }
    </style>
</head>
<body>
    <h1>Test Suite Overview</h1>
    <p>Total Test Cases: {total_tests} | Total Executed Keywords: {total_keywords}</p>""".format(
        total_tests=total_tests,
        total_keywords=total_keywords
    ))

    # Add feedback section
    html_parts.append("""
    <div class="feedback-section">
        <h2>Feedback Notes</h2>
        <textarea id="feedbackText" class="feedback-textarea" placeholder="Enter your feedback note here..."></textarea>
        <button onclick="saveFeedback()" class="feedback-button">Save Note</button>
        <div id="feedbackNotes" class="feedback-notes"></div>
    </div>""")

    # Add keyword statistics
    html_parts.append("""
    <div class="keyword-stats">
        <h2>Statistics per Keyword</h2>
        <button onclick="toggleKeywordStats()" class="toggle-button">Show/Hide Statistics</button>
        <div id="keywordStats" style="display: none;">
            <ul>""")

    for keyword, count in keyword_stats.items():
        html_parts.append(f"                <li>{keyword}: {count} occurrences</li>")

    html_parts.append("""            </ul>
        </div>
    </div>""")

    # Add suites and test cases
    html_parts.append("""
    <div class="suites">""")

    for suite in suites:
        html_parts.append(f"""
        <div class="suite">
            <h2>{suite['name']}</h2>
            <p>{suite['doc']}</p>
            <div class="test-cases">""")

        for test in suite['tests']:
            html_parts.append(f"""
                <div class="test-case">
                    <h3>{test['name']}</h3>
                    <p>{test['doc']}</p>
                    <div class="keywords">""")

            for keyword in test['keywords']:
                html_parts.append(f"                        {keyword}")

            html_parts.append("""                    </div>
                </div>""")

        html_parts.append("""            </div>
        </div>""")

    # Add closing tags and JavaScript
    html_parts.append(r"""    </div>
    <script>
        function toggleKeywordStats() {
            const stats = document.getElementById('keywordStats');
            stats.style.display = stats.style.display === 'none' ? 'block' : 'none';
        }

        function saveFeedback() {
            const textarea = document.getElementById('feedbackText');
            const note = textarea.value.trim();
            if (!note) return;

            // Get existing notes from localStorage or initialize empty array
            let notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');

            // Add new note with timestamp
            notes.push({
                text: note,
                timestamp: new Date().toLocaleString()
            });

            // Save back to localStorage
            localStorage.setItem('feedbackNotes', JSON.stringify(notes));

            // Clear textarea
            textarea.value = '';

            // Update displayed notes
            displayNotes();
        }

        function displayNotes() {
            const notesContainer = document.getElementById('feedbackNotes');
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');

            notesContainer.innerHTML = notes.map(note => `
                <div class="feedback-note">
                    <div class="feedback-text">${note.text}</div>
                    <div class="feedback-timestamp">${note.timestamp}</div>
                </div>
            `).join('');
        }

        // Display existing notes when page loads
        displayNotes();
    </script>
</body>
</html>""")

    return ''.join(html_parts)

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_suite_overview.py <output.xml>")
        sys.exit(1)

    output_file = sys.argv[1]
    result = ExecutionResult(output_file)

    # Count total test cases and keywords
    total_test_cases, total_keywords = count_test_cases_and_keywords(result.suite)

    # Get unique user-defined keywords
    user_defined_keywords = get_user_defined_keywords(result.suite)

    # Count keyword occurrences
    keyword_counts = count_keyword_occurrences(result.suite)

    html_lines = []

    # CSS styles
    styles = """
        :root {
            --primary-color: #007AFF;
            --success-color: #34C759;
            --warning-color: #FF9500;
            --error-color: #FF3B30;
            --text-primary: #1C1C1E;
            --text-secondary: #3A3A3C;
            --background-primary: #F2F2F7;
            --background-secondary: #FFFFFF;
            --border-color: #E5E5EA;
            --shadow-color: rgba(0, 0, 0, 0.1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background-color: var(--background-primary);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .main-title {
            color: var(--text-primary);
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            letter-spacing: -0.5px;
        }

        .statistics {
            text-align: center;
            margin-bottom: 1rem;
            font-size: 1.1rem;
            color: var(--text-secondary);
        }

        .statistics span {
            font-weight: 600;
            color: var(--text-primary);
        }

        .feedback-section {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background-color: var(--background-secondary);
        }

        .feedback-section h3 {
            margin-top: 0;
            color: var(--text-primary);
        }

        .feedback-section textarea {
            width: 100%;
            min-height: 100px;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-family: inherit;
        }

        .button-group {
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }

        .button-group button {
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            font-size: 14px;
            font-weight: 500;
        }

        .button-group button:hover {
            background-color: #45a049;
        }

        .note {
            margin: 10px 0;
            padding: 10px;
            border-left: 4px solid #4CAF50;
            background-color: #f9f9f9;
        }

        .note.implemented {
            text-decoration: line-through;
            color: #999;
        }

        .note .timestamp {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }

        .test-suite {
            background: var(--background-secondary);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px var(--shadow-color);
            overflow: hidden;
        }

        .suite-header {
            padding: 1.25rem;
            background: var(--background-secondary);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }

        .suite-name {
            font-weight: 600;
            color: var(--text-primary);
            font-size: 1.1rem;
        }

        .suite-content {
            display: none;
            padding: 1.25rem;
        }

        .suite-content.visible {
            display: block;
        }

        .test-case {
            padding: 1rem;
            margin: 0.5rem 0;
            background: var(--background-primary);
            border-radius: 8px;
            cursor: pointer;
        }

        .test-name {
            font-weight: 500;
            color: var(--text-primary);
        }

        .keywords {
            display: none;
            margin-top: 0.75rem;
        }

        .keywords.visible {
            display: block;
        }

        .keywords ul {
            list-style-type: none;
            padding-left: 2rem;
        }

        .keywords li {
            margin: 0.5rem 0;
            padding: 0.75rem;
            background: var(--background-secondary);
            border-radius: 8px;
            border-left: 3px solid var(--border-color);
        }

        .setup-keyword {
            border-left-color: var(--success-color);
        }

        .teardown-keyword {
            border-left-color: var(--error-color);
        }

        .test-cases-filter {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background-color: var(--background-secondary);
        }

        .filter-header {
            margin-bottom: 15px;
        }

        .filter-header input {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            margin-top: 10px;
            font-family: inherit;
        }

        .test-cases-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }

        .test-case-item {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            font-family: monospace;
        }

        .test-case-item:last-child {
            border-bottom: none;
        }

        .test-case-item:hover {
            background-color: #f5f5f5;
        }

        .keyword-item {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            font-family: monospace;
            cursor: pointer;
        }

        .keyword-item:last-child {
            border-bottom: none;
        }

        .keyword-item:hover {
            background-color: #f5f5f5;
        }

        .keyword-stats {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.1rem;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .keyword-stats:hover {
            color: var(--primary-color);
        }

        .keyword-stats-list {
            display: none;
            margin-top: 1rem;
            background: var(--background-secondary);
            border-radius: 8px;
            padding: 1rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }

        .keyword-stats-list.visible {
            display: block;
            margin-bottom: 3rem;
        }

        .keyword-stat-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .keyword-stat-item:last-child {
            border-bottom: none;
        }

        .keyword-name {
            font-weight: 500;
        }

        .keyword-count {
            font-weight: 600;
            color: var(--primary-color);
        }
    """

    # Add header and HTML structure
    html_lines.append(f"""<!DOCTYPE html>
<html>
<head>
    <title>Robot Framework Test Suite Overview</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
{styles}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="main-title">Robot Framework Test Suite Overview</h1>
        <div class="statistics">
            Total Test Cases: <span>{total_test_cases}</span> | Total Keywords: <span>{total_keywords}</span>
        </div>

        <!-- Feedback Section -->
        <div class="feedback-section">
            <h3>Feedback Notes</h3>
            <textarea id="feedbackText" placeholder="Enter your feedback note here..."></textarea>
            <div class="button-group">
                <button onclick="saveFeedback()">Save Note</button>
                <button onclick="backupNotes()">Backup Notes</button>
                <button onclick="restoreNotes()">Restore Notes</button>
                <button onclick="toggleTestCasesFilter()">Filter Test Cases</button>
                <button onclick="toggleKeywordsFilter()">Filter Keywords</button>
            </div>
            <div id="savedNotes"></div>
        </div>

        <!-- Test Cases Filter Section -->
        <div id="testCasesFilter" class="test-cases-filter" style="display: none;">
            <div class="filter-header">
                <h3>Filter Test Cases</h3>
                <input type="text" id="testCaseSearch" placeholder="Search test cases..." onkeyup="filterTestCases()">
            </div>
            <div id="testCasesList" class="test-cases-list"></div>
        </div>

        <!-- Keywords Filter Section -->
        <div id="keywordsFilter" class="test-cases-filter" style="display: none;">
            <div class="filter-header">
                <h3>Filter Keywords</h3>
                <input type="text" id="keywordSearch" placeholder="Search keywords..." onkeyup="filterKeywords()">
            </div>
            <div id="keywordsList" class="test-cases-list"></div>
        </div>

        <div class="keyword-stats" onclick="toggleKeywordStats()">
            Click to Show/Hide Keyword Statistics
            <div class="keyword-stats-list" id="keywordStatsList">
                {
                    ''.join(
                        f'<div class="keyword-stat-item"><span class="keyword-name">{keyword}</span><span class="keyword-count">{count}</span></div>'
                        for keyword, count in sorted(keyword_counts.items())
                    )
                }
            </div>
        </div>
        <div class="test-suites">""")

    # Process suites
    process_suite(result.suite, html_lines)

    # Add closing tags and JavaScript
    html_lines.append(f"""
        </div>
    </div>
    <script>
        // Store the user-defined keywords
        const userDefinedKeywords = {json.dumps(user_defined_keywords)};

        function toggleKeywordStats() {{
            const statsList = document.getElementById('keywordStatsList');
            statsList.classList.toggle('visible');
        }}

        function saveFeedback() {{
            const textarea = document.getElementById('feedbackText');
            const note = textarea.value.trim();
            if (!note) return;

            // Get existing notes from localStorage or initialize empty array
            let notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');

            // Add new note with timestamp and implementation status
            notes.push({{
                text: note,
                timestamp: new Date().toLocaleString(),
                implemented: false
            }});

            // Save back to localStorage
            localStorage.setItem('feedbackNotes', JSON.stringify(notes));

            // Clear textarea
            textarea.value = '';

            // Update displayed notes
            displayNotes();
        }}

        function toggleImplementation(index) {{
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');
            notes[index].implemented = !notes[index].implemented;
            localStorage.setItem('feedbackNotes', JSON.stringify(notes));
            displayNotes();
        }}

        function editNote(index) {{
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');
            const note = notes[index];
            const noteElement = document.querySelector(`.note:nth-child(${{index + 1}})`);

            // Create edit form
            const editForm = document.createElement('div');
            editForm.className = 'note-edit';
            editForm.innerHTML = `
                <textarea class="edit-textarea">${{note.text}}</textarea>
                <div class="edit-buttons">
                    <button onclick="saveEdit(${{index}})">Save</button>
                    <button onclick="cancelEdit(${{index}})">Cancel</button>
                </div>
            `;

            // Replace note content with edit form
            noteElement.querySelector('.note-content').style.display = 'none';
            noteElement.appendChild(editForm);
        }}

        function saveEdit(index) {{
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');
            const noteElement = document.querySelector(`.note:nth-child(${{index + 1}})`);
            const editTextarea = noteElement.querySelector('.edit-textarea');

            // Update note text
            notes[index].text = editTextarea.value.trim();
            localStorage.setItem('feedbackNotes', JSON.stringify(notes));

            // Refresh display
            displayNotes();
        }}

        function cancelEdit(index) {{
            displayNotes();
        }}

        function displayNotes() {{
            const notesContainer = document.getElementById('savedNotes');
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');

            notesContainer.innerHTML = notes.map((note, index) => `
                <div class="note ${{note.implemented ? 'implemented' : ''}}">
                    <input type="checkbox"
                           ${{note.implemented ? 'checked' : ''}}
                           onchange="toggleImplementation(${{index}})">
                    <div class="note-content">
                        <div class="note-text">${{note.text}}</div>
                        <div class="note-actions">
                            <button onclick="editNote(${{index}})" class="edit-button">Edit</button>
                        </div>
                        <div class="timestamp">${{note.timestamp}}</div>
                    </div>
                </div>
            `).join('');
        }}

        function backupNotes() {{
            const notes = JSON.parse(localStorage.getItem('feedbackNotes') || '[]');
            const blob = new Blob([JSON.stringify(notes, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'feedback_notes_backup.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        function restoreNotes() {{
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = function(e) {{
                const file = e.target.files[0];
                if (file) {{
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        try {{
                            const notes = JSON.parse(e.target.result);
                            localStorage.setItem('feedbackNotes', JSON.stringify(notes));
                            displayNotes();
                            alert('Notes restored successfully!');
                        }} catch (error) {{
                            alert('Error restoring notes: Invalid JSON file');
                        }}
                    }};
                    reader.readAsText(file);
                }}
            }};
            input.click();
        }}

        function toggleTestCasesFilter() {{
            const filterSection = document.getElementById('testCasesFilter');
            if (filterSection.style.display === 'none') {{
                filterSection.style.display = 'block';
                populateTestCasesList();
            }} else {{
                filterSection.style.display = 'none';
            }}
        }}

        function populateTestCasesList() {{
            const testCasesList = document.getElementById('testCasesList');
            const testCasesSet = new Set(); // Use Set to ensure uniqueness

            // Collect all test cases with their full paths
            document.querySelectorAll('.test-suite').forEach(suite => {{
                // Only process leaf suites (those that contain test cases directly)
                const hasDirectTestCases = suite.querySelector('.test-case') !== null;
                const hasSubSuites = suite.querySelector('.test-suite') !== null;

                if (hasDirectTestCases && !hasSubSuites) {{
                    const suitePath = getFullSuitePath(suite);
                    suite.querySelectorAll('.test-case').forEach(testCase => {{
                        const testName = testCase.querySelector('.test-name').textContent.replace('Test Case: ', '');
                        // Skip setup and teardown entries
                        if (!testName.toLowerCase().includes('setup') && !testName.toLowerCase().includes('teardown')) {{
                            const fullPath = `${{suitePath}}.${{testName}}`;
                            testCasesSet.add(fullPath); // Set automatically handles duplicates
                        }}
                    }});
                }}
            }});

            // Convert Set to Array and sort
            const sortedTestCases = Array.from(testCasesSet).sort();

            // Store test cases in a global variable for filtering
            window.allTestCases = sortedTestCases;

            // Display all test cases initially
            displayFilteredTestCases(sortedTestCases);
        }}

        function getFullSuitePath(suiteElement) {{
            const pathParts = [];
            let currentElement = suiteElement;

            // Traverse up to build the full path
            while (currentElement) {{
                const suiteName = currentElement.querySelector('.suite-name');
                if (suiteName) {{
                    pathParts.unshift(suiteName.textContent.replace('Suite: ', ''));
                }}
                // Move up to parent suite if it exists
                currentElement = currentElement.closest('.test-suite')?.parentElement?.closest('.test-suite');
            }}

            return pathParts.join('.');
        }}

        function filterTestCases() {{
            const searchText = document.getElementById('testCaseSearch').value.toLowerCase();
            const filteredCases = Array.from(window.allTestCases).filter(testCase =>
                testCase.toLowerCase().includes(searchText)
            );
            displayFilteredTestCases(filteredCases);
        }}

        function displayFilteredTestCases(testCases) {{
            const testCasesList = document.getElementById('testCasesList');
            testCasesList.innerHTML = testCases.map(testCase => `
                <div class="test-case-item" onclick="scrollToTestCase('${{testCase}}')">
                    ${{testCase}}
                </div>
            `).join('');
        }}

        function scrollToTestCase(testCasePath) {{
            const pathParts = testCasePath.split('.');
            const testName = pathParts.pop(); // Last part is the test name
            const suitePath = pathParts.join('.'); // Rest is the suite path

            // Find the suite by matching the full path
            const suite = Array.from(document.querySelectorAll('.test-suite')).find(s =>
                getFullSuitePath(s) === suitePath
            );

            if (suite) {{
                const testCase = Array.from(suite.querySelectorAll('.test-case')).find(t =>
                    t.querySelector('.test-name').textContent.includes(testName)
                );
                if (testCase) {{
                    // Expand the suite if it's collapsed
                    suite.querySelector('.suite-content').classList.add('visible');
                    // Scroll to the test case
                    testCase.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    // Highlight the test case briefly
                    testCase.style.backgroundColor = '#fff3cd';
                    setTimeout(() => {{
                        testCase.style.backgroundColor = '';
                    }}, 2000);
                }}
            }}
        }}

        function toggleKeywordsFilter() {{
            const filterSection = document.getElementById('keywordsFilter');
            if (filterSection.style.display === 'none') {{
                filterSection.style.display = 'block';
                populateKeywordsList();
            }} else {{
                filterSection.style.display = 'none';
            }}
        }}

        function populateKeywordsList() {{
            const keywordsList = document.getElementById('keywordsList');

            // Store keywords in a global variable for filtering
            window.allKeywords = userDefinedKeywords;

            // Display all keywords initially
            displayFilteredKeywords(userDefinedKeywords);
        }}

        function filterKeywords() {{
            const searchText = document.getElementById('keywordSearch').value.toLowerCase();
            const filteredKeywords = window.allKeywords.filter(keyword =>
                keyword.toLowerCase().includes(searchText)
            );
            displayFilteredKeywords(filteredKeywords);
        }}

        function displayFilteredKeywords(keywords) {{
            const keywordsList = document.getElementById('keywordsList');
            keywordsList.innerHTML = keywords.map(keyword => `
                <div class="keyword-item" onclick="scrollToKeyword('${{keyword}}')">
                    ${{keyword}}
                </div>
            `).join('');
        }}

        function scrollToKeyword(keywordName) {{
            // Find the first occurrence of the keyword
            const keywordElement = Array.from(document.querySelectorAll('.keywords li')).find(
                li => li.textContent.trim() === keywordName
            );

            if (keywordElement) {{
                // Find the parent test case
                const testCase = keywordElement.closest('.test-case');
                if (testCase) {{
                    // Find the parent suite
                    const suite = testCase.closest('.test-suite');
                    if (suite) {{
                        // Expand the suite if it's collapsed
                        suite.querySelector('.suite-content').classList.add('visible');
                        // Expand the test case if it's collapsed
                        testCase.querySelector('.keywords').classList.add('visible');
                        // Scroll to the keyword
                        keywordElement.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        // Highlight the keyword briefly
                        keywordElement.style.backgroundColor = '#fff3cd';
                        setTimeout(() => {{
                            keywordElement.style.backgroundColor = '';
                        }}, 2000);
                    }}
                }}
            }}
        }}

        document.querySelectorAll('.test-suite').forEach(suite => {{
            suite.querySelector('.suite-header').addEventListener('click', () => {{
                suite.querySelector('.suite-content').classList.toggle('visible');
            }});
        }});

        document.querySelectorAll('.test-case').forEach(testCase => {{
            testCase.addEventListener('click', () => {{
                testCase.querySelector('.keywords').classList.toggle('visible');
            }});
        }});

        // Display existing notes when page loads
        displayNotes();
    </script>
</body>
</html>""")

    # Write the HTML file
    with open('test_suite_overview.html', 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))

if __name__ == "__main__":
    main()
