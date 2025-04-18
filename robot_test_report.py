#!/usr/bin/env python3

import os
import sys
import argparse
from robot.api import ExecutionResult, ResultVisitor

# Updated visitor class for Robot Framework 7.x with suite support and setup/teardown handling
class TestCaseKeywordVisitor(ResultVisitor):
    def __init__(self):
        self.suite_data = []
        self.current_suite = None
        self.current_parent_suite = None

    def visit_suite(self, suite):
        # Process all suites
        suite_info = {
            'id': suite.id,
            'name': suite.name,
            'source': suite.source,
            'status': suite.status,
            'tests': [],
            'parent': suite.parent.name if suite.parent else None,
            'setup': None,
            'teardown': None
        }

        # Check for suite setup - only add if it has keywords
        if hasattr(suite, 'setup') and suite.setup is not None and suite.setup.name != 'None' and hasattr(suite.setup, 'body') and len(suite.setup.body) > 0:
            suite_info['setup'] = self._process_suite_keyword(suite.setup)

        # Check for suite teardown - only add if it has keywords
        if hasattr(suite, 'teardown') and suite.teardown is not None and suite.teardown.name != 'None' and hasattr(suite.teardown, 'body') and len(suite.teardown.body) > 0:
            suite_info['teardown'] = self._process_suite_keyword(suite.teardown)

        self.current_suite = suite_info
        self.suite_data.append(suite_info)

        # Continue visiting test cases and child suites
        suite.tests.visit(self)
        suite.suites.visit(self)

    def _process_suite_keyword(self, keyword):
        """Process a suite-level keyword."""
        if keyword is None:
            return None

        # Get the keyword name safely
        keyword_name = str(keyword)
        if '.' in keyword_name:
            keyword_name = keyword_name.split('.')[-1]

        kw_info = {
            'name': keyword_name,
            'status': keyword.status,
            'type': getattr(keyword, 'type', ''),
            'children': []
        }

        # Skip control structures and iterations but process their body
        if kw_info['type'] in ['IF', 'WHILE', 'FOR', 'IFBRANCH', 'ELSE', 'ELSEIF', 'FORITERATION', 'ITERATION'] or str(keyword).startswith('${'):
            if hasattr(keyword, 'body'):
                for child_item in keyword.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, kw_info['children'], 0)
            return None

        # Process child keywords
        if hasattr(keyword, 'body'):
            for child_item in keyword.body:
                if hasattr(child_item, 'body'):  # It's a keyword
                    self._process_keyword(child_item, kw_info['children'], 0)

        return kw_info

    def visit_test(self, test):
        if self.current_suite:
            test_info = {
                'id': test.id,
                'name': test.name,
                'status': test.status,
                'keywords': [],
                'setup': None,
                'teardown': None
            }

            # Check for test setup - only add if it has keywords
            if hasattr(test, 'setup') and test.setup is not None and test.setup.name != 'None' and hasattr(test.setup, 'body') and len(test.setup.body) > 0:
                setup_info = {
                    'name': str(test.setup),
                    'status': test.setup.status,
                    'type': 'TEST SETUP',
                    'level': 0,
                    'children': []
                }

                # Process child keywords in setup if any
                for child_item in test.setup.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, setup_info['children'], 1)

                test_info['setup'] = setup_info

            # Process all body items in this test
            for item in test.body:
                if hasattr(item, 'body'):  # It's a keyword
                    self._process_keyword(item, test_info['keywords'], 0)

            # Check for test teardown - only add if it has keywords
            if hasattr(test, 'teardown') and test.teardown is not None and test.teardown.name != 'None' and hasattr(test.teardown, 'body') and len(test.teardown.body) > 0:
                teardown_info = {
                    'name': str(test.teardown),
                    'status': test.teardown.status,
                    'type': 'TEST TEARDOWN',
                    'level': 0,
                    'children': []
                }

                # Process child keywords in teardown if any
                for child_item in test.teardown.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, teardown_info['children'], 1)

                test_info['teardown'] = teardown_info

            self.current_suite['tests'].append(test_info)

    def _process_keyword(self, keyword, keywords_list, level):
        """Process a keyword and its children recursively"""
        # Skip control structures and iterations but process their body
        if (hasattr(keyword, 'type') and
            keyword.type in ['IF', 'WHILE', 'FOR', 'IFBRANCH', 'ELSE', 'ELSEIF', 'FORITERATION', 'ITERATION', 'IF/ELSE ROOT']):
            if hasattr(keyword, 'body'):
                for child_item in keyword.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, keywords_list, level)
            return

        # Skip iter tags but process their body
        if str(keyword).startswith('${') or hasattr(keyword, 'type') and keyword.type == 'ITERATION':
            if hasattr(keyword, 'body'):
                for child_item in keyword.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, keywords_list, level)
            return

        # Get the keyword name safely
        keyword_name = str(keyword)
        if '.' in keyword_name:
            keyword_name = keyword_name.split('.')[-1]

        # Skip IF/ELSE structures and their branches even if they don't have a type attribute
        if (keyword_name.startswith('IF') or
            keyword_name.startswith('ELSE') or
            keyword_name.startswith('ELSE IF') or
            keyword_name.startswith('IFBRANCH') or
            keyword_name.startswith('IF ROOT') or
            keyword_name.startswith('ELSE ROOT') or
            'IF/ELSE ROOT' in keyword_name or
            'ROOT' in keyword_name and ('IF' in keyword_name or 'ELSE' in keyword_name)):
            if hasattr(keyword, 'body'):
                for child_item in keyword.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, keywords_list, level)
            return

        # Skip any keyword that contains "IF" or "ELSE" in its name
        if ('IF' in keyword_name or 'ELSE' in keyword_name or
            (hasattr(keyword, 'libname') and ('IF' in str(keyword.libname) or 'ELSE' in str(keyword.libname)))):
            if hasattr(keyword, 'body'):
                for child_item in keyword.body:
                    if hasattr(child_item, 'body'):  # It's a keyword
                        self._process_keyword(child_item, keywords_list, level)
            return

        # Get arguments and return values
        args = []
        if hasattr(keyword, 'args'):
            args = [str(arg) for arg in keyword.args]

        returns = []
        if hasattr(keyword, 'assign'):
            returns = [str(assign) for assign in keyword.assign]

        # Get variable values
        variables = {}
        if hasattr(keyword, 'body'):
            for item in keyword.body:
                if hasattr(item, 'type') and item.type == 'VARIABLE':
                    var_name = str(item.name)
                    var_value = str(item.value) if hasattr(item, 'value') else ''
                    variables[var_name] = var_value

        kw_info = {
            'name': keyword_name,
            'status': keyword.status,
            'type': getattr(keyword, 'type', ''),
            'level': level,
            'args': args,
            'returns': returns,
            'variables': variables,
            'children': []
        }

        # Process child keywords recursively
        if hasattr(keyword, 'body'):
            for child_item in keyword.body:
                if hasattr(child_item, 'body'):  # It's a keyword
                    self._process_keyword(child_item, kw_info['children'], level + 1)

        keywords_list.append(kw_info)

    def _format_keyword_children(self, keyword):
        """Format keyword children for display"""
        if not keyword['children']:
            return ''

        children_html = '<ul class="keyword-children">'
        for child in keyword['children']:
            children_html += '<li>'

            # Add argument information
            if child.get('args'):
                args_text = ', '.join(child['args'])
                children_html += f'<span class="keyword-args">Arguments: [{args_text}]</span><br>'

            # Add return information
            if child.get('returns'):
                returns_text = ', '.join(child['returns'])
                children_html += f'<span class="keyword-returns">Returns: [{returns_text}]</span><br>'

            # Add variable information
            if child.get('variables'):
                for var_name, var_value in child['variables'].items():
                    children_html += f'<span class="keyword-variable">{var_name} = {var_value}</span><br>'

            # Add the keyword name and status
            children_html += f'<span class="keyword-name">{child["name"]}</span>'
            if child.get('type'):
                children_html += f' <span class="keyword-type">({child["type"]})</span>'
            children_html += f' <span class="keyword-status {child["status"].lower()}">{child["status"]}</span>'

            # Add duration if available
            if child.get('duration'):
                children_html += f' <span class="keyword-duration">({child["duration"]})</span>'

            # Recursively process children
            children_html += self._format_keyword_children(child)
            children_html += '</li>'

        children_html += '</ul>'
        return children_html

def generate_html_report(output_xml, html_output="interactive_report.html"):
    # Parse the output.xml using Robot Framework's API
    result = ExecutionResult(output_xml)
    visitor = TestCaseKeywordVisitor()
    result.visit(visitor)

    # Get statistics - only count suites that have tests
    actual_suites = [suite for suite in visitor.suite_data if suite['tests']]
    suite_count = len(actual_suites)
    test_count = sum(len(suite['tests']) for suite in actual_suites)
    keyword_count = sum(len(test['keywords']) for suite in actual_suites for test in suite['tests'])

    # Start generating HTML content
    html_content = _get_html_header()

    # Add summary section
    html_content += f"""
    <div class="container">
        <h1 class="main-title">Robot Framework Test Overview</h1>
        <div class="summary-section">
            <div class="summary-card">
                <div class="summary-value">{suite_count}</div>
                <div class="summary-label">Test Suites</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{test_count}</div>
                <div class="summary-label">Test Cases</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{keyword_count}</div>
                <div class="summary-label">Keywords</div>
            </div>
        </div>

        <h2 class="section-title">Available Test Suites</h2>
"""

    # Add test suites to HTML
    for i, suite in enumerate(actual_suites):
        # Skip suites with no test cases
        if not suite['tests']:
            continue

        test_count = len(suite['tests'])
        html_content += f"""
        <div class="test-suite">
            <div class="suite-header" data-target="suite-{i}" aria-expanded="false">
                <div>
                    <div class="suite-name">{suite['name']}</div>
                    <div class="suite-meta">{test_count} test case{'s' if test_count != 1 else ''}</div>
                </div>
                <div class="chevron">›</div>
            </div>
            <div id="suite-{i}" class="suite-tests">
"""

        # Add suite setup if exists and is not None
        if suite.get('setup') and suite['setup'].get('name') != 'None':
            setup_id = f"suite-setup-{i}"
            html_content += f"""
                <div class="suite-setup" data-target="{setup_id}" aria-expanded="false">
                    <div class="keyword-content">
                        <span><strong>{suite['setup']['name']}</strong> (Suite Setup)</span>
                        <div class="chevron">›</div>
                    </div>
                </div>
                <div id="{setup_id}" class="keywords">
                    {_render_suite_keyword(suite['setup'])}
                </div>
"""

        # Add tests for this suite
        for j, test in enumerate(suite['tests']):
            test_id = f"{i}-{j}"
            html_content += f"""
                <div class="test-case" data-target="keywords-{test_id}" aria-expanded="false">
                    <div class="test-name">{test['name']}</div>
                    <div class="chevron">›</div>
                </div>
                <div id="keywords-{test_id}" class="keywords">
"""

            # Add test setup if exists and is not None
            if test.get('setup') and test['setup'].get('name') != 'None':
                html_content += _render_keyword_special(test['setup'], 'setup-keyword')

            # Add regular keywords
            for kw in test['keywords']:
                html_content += _render_keyword_overview(kw)

            # Add test teardown if exists and is not None
            if test.get('teardown') and test['teardown'].get('name') != 'None':
                html_content += _render_keyword_special(test['teardown'], 'teardown-keyword')

            html_content += "                </div>\n"

        # Add suite teardown if exists and is not None
        if suite.get('teardown') and suite['teardown'].get('name') != 'None':
            teardown_id = f"suite-teardown-{i}"
            html_content += f"""
                <div class="suite-teardown" data-target="{teardown_id}" aria-expanded="false">
                    <div class="keyword-content">
                        <span><strong>{suite['teardown']['name']}</strong> (Suite Teardown)</span>
                        <div class="chevron">›</div>
                    </div>
                </div>
                <div id="{teardown_id}" class="keywords">
                    {_render_suite_keyword(suite['teardown'])}
                </div>
"""

        html_content += "            </div>\n        </div>\n"

    html_content += """
        <footer>
            <p>Generated with Robot Framework Test Overview Generator</p>
        </footer>
    </div>
</body>
</html>
"""

    # Write the HTML file
    with open(html_output, 'w') as f:
        f.write(html_content)

    return html_output

def _render_suite_keyword(keyword):
    """Render a suite setup or teardown keyword"""
    html = f"""
                    <div class="keyword">
                        <div class="keyword-content">
                            <span>{keyword['name']}</span>
                            <span class="type-badge">{keyword['type']}</span>
                        </div>
"""

    # Render children recursively
    if keyword['children']:
        html += '                        <div class="child-keywords">'
        for child in keyword['children']:
            html += _render_keyword_overview(child)
        html += '                        </div>'

    html += "                    </div>\n"

    return html

def _render_keyword_special(keyword, special_class):
    """Render a test setup or teardown keyword with special styling"""
    html = f"""
                    <div class="keyword {special_class}">
                        <div class="keyword-content">
                            <span>{keyword['name']}</span>
                            <span class="type-badge">{keyword['type']}</span>
                        </div>
"""

    # Render children recursively
    if keyword['children']:
        html += '                        <div class="child-keywords">'
        for child in keyword['children']:
            html += _render_keyword_overview(child)
        html += '                        </div>'

    html += "                    </div>\n"

    return html

def _render_keyword_overview(keyword, level=0):
    """Render a keyword and its children recursively with focus on steps rather than status"""
    indent_class = f"level-{level}"

    html = f"""
                    <div class="keyword {indent_class}" style="margin-left: {level * 12}px;">
                        <div class="keyword-content">
                            <span>{keyword['name']}</span>
                            {f'<span class="type-badge">{keyword["type"]}</span>' if keyword['type'] else ''}
                        </div>
"""

    # Render children recursively
    if keyword['children']:
        html += '                        <div class="child-keywords">'
        for child in keyword['children']:
            html += _render_keyword_overview(child, level + 1)
        html += '                        </div>'

    html += "                    </div>\n"
    return html

def _get_html_header():
    """Return the HTML header with styles and scripts."""
    return """<!DOCTYPE html>
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
            margin-bottom: 2rem;
            letter-spacing: -0.5px;
        }

        .summary-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .summary-card {
            background: var(--background-secondary);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 6px var(--shadow-color);
            transition: transform 0.2s ease;
        }

        .summary-card:hover {
            transform: translateY(-2px);
        }

        .summary-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
        }

        .summary-label {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 500;
        }

        .section-title {
            color: var(--text-primary);
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border-color);
        }

        .test-suite {
            background: var(--background-secondary);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px var(--shadow-color);
            overflow: hidden;
            transition: transform 0.2s ease;
        }

        .test-suite:hover {
            transform: translateY(-2px);
        }

        .suite-header {
            padding: 1.25rem;
            background: var(--background-secondary);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.2s ease;
        }

        .suite-header:hover {
            background-color: var(--background-primary);
        }

        .suite-name {
            font-weight: 600;
            color: var(--text-primary);
            font-size: 1.1rem;
        }

        .suite-meta {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .suite-tests {
            display: none;
            padding: 1.25rem;
        }

        .suite-tests.visible {
            display: block;
            animation: fadeIn 0.3s ease-in-out;
        }

        .test-case {
            padding: 1rem;
            margin: 0.5rem 0;
            background: var(--background-primary);
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background-color 0.2s ease;
        }

        .test-case:hover {
            background-color: var(--background-secondary);
        }

        .test-name {
            font-weight: 500;
            color: var(--text-primary);
        }

        .keywords {
            display: none;
            padding-left: 1.5rem;
            margin-top: 0.75rem;
        }

        .keywords.visible {
            display: block;
            animation: fadeIn 0.3s ease-in-out;
        }

        .keyword {
            margin: 0.5rem 0;
            padding: 0.75rem;
            background: var(--background-secondary);
            border-radius: 8px;
            border-left: 3px solid var(--border-color);
            transition: transform 0.2s ease;
        }

        .keyword:hover {
            transform: translateX(4px);
        }

        .keyword-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .type-badge {
            background: var(--background-primary);
            color: var(--text-secondary);
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .child-keywords {
            margin-left: 1.5rem;
            margin-top: 0.5rem;
        }

        .chevron {
            color: var(--text-secondary);
            transition: transform 0.3s ease;
            font-size: 1.2rem;
        }

        [aria-expanded="true"] .chevron {
            transform: rotate(90deg);
        }

        .setup-keyword {
            border-left-color: var(--success-color);
        }

        .teardown-keyword {
            border-left-color: var(--error-color);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        footer {
            text-align: center;
            margin-top: 3rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
            padding: 1rem;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .main-title {
                font-size: 2rem;
            }

            .summary-section {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Event handlers for test suites
            const suiteHeaders = document.querySelectorAll('.suite-header');

            suiteHeaders.forEach(suiteHeader => {
                suiteHeader.addEventListener('click', function() {
                    const suiteId = this.getAttribute('data-target');
                    const suiteElement = document.getElementById(suiteId);
                    const isExpanded = this.getAttribute('aria-expanded') === 'true';

                    this.setAttribute('aria-expanded', !isExpanded);

                    if (suiteElement.classList.contains('visible')) {
                        suiteElement.classList.remove('visible');
                        setTimeout(() => {
                            suiteElement.style.display = 'none';
                        }, 300);
                    } else {
                        suiteElement.style.display = 'block';
                        setTimeout(() => {
                            suiteElement.classList.add('visible');
                        }, 10);
                    }
                });
            });

            // Event handlers for test cases and setup/teardown elements
            const expandableElements = document.querySelectorAll('.test-case, .suite-setup, .suite-teardown');

            expandableElements.forEach(element => {
                element.addEventListener('click', function() {
                    const targetId = this.getAttribute('data-target');
                    const targetElement = document.getElementById(targetId);
                    const isExpanded = this.getAttribute('aria-expanded') === 'true';

                    this.setAttribute('aria-expanded', !isExpanded);

                    if (targetElement.classList.contains('visible')) {
                        targetElement.classList.remove('visible');
                        setTimeout(() => {
                            targetElement.style.display = 'none';
                        }, 300);
                    } else {
                        targetElement.style.display = 'block';
                        setTimeout(() => {
                            targetElement.classList.add('visible');
                        }, 10);
                    }
                });
            });
        });
    </script>
</head>
<body>"""

def main():
    parser = argparse.ArgumentParser(description='Generate interactive HTML report from Robot Framework output.xml')
    parser.add_argument('input_file', nargs='?', help='Path to the Robot Framework output.xml file')
    parser.add_argument('-o', '--output', default='interactive_report.html', help='Path to the output HTML file (default: interactive_report.html)')
    args = parser.parse_args()

    # Check if input file was provided
    if not args.input_file:
        print("Error: No input file specified.")
        print("Usage: python robot_test_report.py path/to/output.xml [--output report.html]")
        sys.exit(1)

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)

    # Generate the report
    print(f"Generating report from: {args.input_file}")
    html_file = generate_html_report(args.input_file, args.output)
    print(f"HTML report created at: {os.path.abspath(html_file)}")
    print(f"\nYou can open {html_file} in your browser to see the interactive report.")

if __name__ == "__main__":
    main()
