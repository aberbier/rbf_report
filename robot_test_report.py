#!/usr/bin/env python3

import sys
from robot.api import ExecutionResult

def extract_keywords(item, html_lines, indent=0, is_setup=False, is_teardown=False):
    """Extract keywords from an item, handling nested structures."""
    # Skip items marked as NOT RUN
    if hasattr(item, 'status') and item.status == 'NOT RUN':
        return

    # Handle different types of items
    if hasattr(item, 'type'):
        if item.type == 'FOR':
            # Process FOR loop body without showing the FOR structure
            if hasattr(item, 'body'):
                for iteration in item.body:
                    if hasattr(iteration, 'status') and iteration.status == 'NOT RUN':
                        continue
                    if hasattr(iteration, 'body'):
                        for nested_item in iteration.body:
                            extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)

        elif item.type == 'IF/ELSE ROOT':
            # Process IF/ELSE branches without showing the IF/ELSE structure
            if hasattr(item, 'body'):
                for branch in item.body:
                    if hasattr(branch, 'status') and branch.status == 'NOT RUN':
                        continue
                    if hasattr(branch, 'body'):
                        for nested_item in branch.body:
                            extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)

        elif item.type in ['KEYWORD', 'SETUP', 'TEARDOWN']:
            # Handle all keywords, including setup and teardown
            keyword_name = getattr(item, 'kwname', '')
            if not keyword_name or keyword_name.startswith('$'):
                return

            if hasattr(item, 'body') and item.body:
                # If keyword has nested keywords, make it foldable
                keyword_class = ""
                if is_setup:
                    keyword_class = "setup-keyword"
                elif is_teardown:
                    keyword_class = "teardown-keyword"
                html_lines.append(f"<li class='{keyword_class}'>{keyword_name.split('  ')[0]}")
                html_lines.append("<ul>")
                for nested_item in item.body:
                    extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)
                html_lines.append("</ul>")
                html_lines.append("</li>")
            else:
                # If no nested keywords, display as simple list item
                keyword_class = ""
                if is_setup:
                    keyword_class = "setup-keyword"
                elif is_teardown:
                    keyword_class = "teardown-keyword"
                html_lines.append(f"<li class='{keyword_class}'>{keyword_name.split('  ')[0]}</li>")

    elif hasattr(item, 'body') and item.body:
        # Handle named items (like user keywords)
        keyword_name = getattr(item, 'kwname', '')
        if not keyword_name or keyword_name.startswith('$'):
            return

        keyword_class = ""
        if is_setup:
            keyword_class = "setup-keyword"
        elif is_teardown:
            keyword_class = "teardown-keyword"
        html_lines.append(f"<li class='{keyword_class}'>{keyword_name.split('  ')[0]}")
        html_lines.append("<ul>")
        for nested_item in item.body:
            extract_keywords(nested_item, html_lines, indent + 1, is_setup, is_teardown)
        html_lines.append("</ul>")
        html_lines.append("</li>")
    else:
        # If no nested keywords, display as simple list item
        keyword_name = getattr(item, 'kwname', '')
        if not keyword_name or keyword_name.startswith('$'):
            return

        keyword_class = ""
        if is_setup:
            keyword_class = "setup-keyword"
        elif is_teardown:
            keyword_class = "teardown-keyword"
        html_lines.append(f"<li class='{keyword_class}'>{keyword_name.split('  ')[0]}</li>")

def process_suite(suite, html_lines):
    """Process a test suite and its contents."""
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
        process_suite(subsuite, html_lines)

    # Process test cases
    for test in suite.tests:
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
        if hasattr(item, 'type'):
            if item.type in ['FOR', 'IF/ELSE ROOT', 'RETURN', 'FOR ITERATION', 'IF BRANCH']:
                if hasattr(item, 'body'):
                    for nested_item in item.body:
                        count_in_item(nested_item)
                return

        # Only count actual keywords
        if hasattr(item, 'type') and item.type in ['KEYWORD', 'SETUP', 'TEARDOWN']:
            if hasattr(item, 'kwname'):
                keyword_name = item.kwname.split('  ')[0]
                # Skip keywords that start with $
                if not keyword_name.startswith('$'):
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

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_suite_overview.py <output.xml>")
        sys.exit(1)

    output_file = sys.argv[1]
    result = ExecutionResult(output_file)

    # Count total test cases and keywords
    total_test_cases, total_keywords = count_test_cases_and_keywords(result.suite)

    # Count keyword occurrences
    keyword_counts = count_keyword_occurrences(result.suite)

    html_lines = []
    html_lines.append("""<!DOCTYPE html>
<html>
<head>
    <title>Robot Framework Test Suite Overview</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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

        .keyword {
            margin: 0.5rem 0;
            padding: 0.75rem;
            background: var(--background-secondary);
            border-radius: 8px;
            border-left: 3px solid var(--border-color);
        }

        /* Remove bullet points from lists */
        ul {
            list-style-type: none;
            padding-left: 2rem;
        }

        li {
            list-style-type: none;
        }

        .setup-keyword {
            border-left-color: var(--success-color);
        }

        .teardown-keyword {
            border-left-color: var(--error-color);
        }

        .chevron {
            color: var(--text-secondary);
            transition: transform 0.3s ease;
            font-size: 1.2rem;
        }

        [aria-expanded="true"] .chevron {
            transform: rotate(90deg);
        }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Add click handlers to all suite headers
            document.querySelectorAll('.suite-header').forEach(function(element) {
                element.addEventListener('click', function(event) {
                    event.stopPropagation();
                    const content = this.nextElementSibling;
                    const isExpanded = content.classList.contains('visible');

                    // Toggle visibility
                    content.classList.toggle('visible');

                    // Update aria-expanded attribute
                    this.setAttribute('aria-expanded', !isExpanded);
                });
            });

            // Add click handlers to all test cases
            document.querySelectorAll('.test-case').forEach(function(element) {
                element.addEventListener('click', function(event) {
                    event.stopPropagation();
                    const keywords = this.querySelector('.keywords');
                    if (keywords) {
                        keywords.classList.toggle('visible');
                    }
                });
            });

            // Add click handler for keyword statistics
            document.querySelector('.keyword-stats').addEventListener('click', function() {
                const statsList = this.nextElementSibling;
                statsList.classList.toggle('visible');
            });
        });
    </script>
</head>
<body>
    <div class="container">
        <h1 class="main-title">Test Suite Overview</h1>
        <div class="statistics">
            Total Test Cases: <span>%d</span> | Total Executed Keywords: <span>%d</span>
        </div>
        <div class="keyword-stats">Statistics per keyword</div>
        <div class="keyword-stats-list">
            %s
        </div>""" % (total_test_cases, total_keywords,
            "\n".join([f'<div class="keyword-stat-item"><span class="keyword-name">{keyword}</span><span class="keyword-count">{count}</span></div>'
                      for keyword, count in sorted(keyword_counts.items())])))

    # Process the test suite
    process_suite(result.suite, html_lines)

    html_lines.append("""
    </div>
</body>
</html>""")

    with open("test_suite_overview.html", "w") as f:
        f.write("\n".join(html_lines))

    print("HTML file generated: test_suite_overview.html")

if __name__ == "__main__":
    main()
