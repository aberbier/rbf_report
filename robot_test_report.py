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
        # Only process top-level and second level suites here
        if suite.parent:
            if not suite.parent.parent:  # This is a second-level suite (child of top-level)
                suite_info = {
                    'id': suite.id,
                    'name': suite.name,
                    'source': suite.source,
                    'status': suite.status,
                    'tests': [],
                    'parent': suite.parent.name,
                    'setup': None,
                    'teardown': None
                }

                # Check for suite setup
                if hasattr(suite, 'setup') and suite.setup is not None:
                    suite_info['setup'] = self._process_suite_keyword(suite.setup, 'SUITE SETUP')

                # Check for suite teardown
                if hasattr(suite, 'teardown') and suite.teardown is not None:
                    suite_info['teardown'] = self._process_suite_keyword(suite.teardown, 'SUITE TEARDOWN')

                self.current_suite = suite_info
                self.suite_data.append(suite_info)
        else:  # Top level suite
            self.current_parent_suite = suite.name

        # Continue visiting test cases and child suites
        suite.tests.visit(self)
        suite.suites.visit(self)

    def _process_suite_keyword(self, keyword, keyword_type):
        """Process a suite setup or teardown keyword"""
        if keyword is None:
            return None

        kw_info = {
            'name': keyword.name,
            'status': keyword.status,
            'type': keyword_type,
            'children': []
        }

        # Process child keywords if any
        if hasattr(keyword, 'body'):
            for child_item in keyword.body:
                if hasattr(child_item, 'name'):
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

            # Check for test setup
            if hasattr(test, 'setup') and test.setup is not None:
                setup_info = {
                    'name': test.setup.name,
                    'status': test.setup.status,
                    'type': 'TEST SETUP',
                    'level': 0,
                    'children': []
                }

                # Process child keywords in setup if any
                if hasattr(test.setup, 'body'):
                    for child_item in test.setup.body:
                        if hasattr(child_item, 'name'):
                            self._process_keyword(child_item, setup_info['children'], 1)

                test_info['setup'] = setup_info

            # Process all body items in this test
            # In Robot Framework 7.x, 'keywords' was renamed to 'body'
            for item in test.body:
                # Check if this is a keyword
                if hasattr(item, 'name'):
                    self._process_keyword(item, test_info['keywords'], 0)

            # Check for test teardown
            if hasattr(test, 'teardown') and test.teardown is not None:
                teardown_info = {
                    'name': test.teardown.name,
                    'status': test.teardown.status,
                    'type': 'TEST TEARDOWN',
                    'level': 0,
                    'children': []
                }

                # Process child keywords in teardown if any
                if hasattr(test.teardown, 'body'):
                    for child_item in test.teardown.body:
                        if hasattr(child_item, 'name'):
                            self._process_keyword(child_item, teardown_info['children'], 1)

                test_info['teardown'] = teardown_info

            self.current_suite['tests'].append(test_info)

    def _process_keyword(self, keyword, keywords_list, level):
        """Process a keyword and its children recursively"""
        kw_info = {
            'name': keyword.name,
            'status': keyword.status,
            'type': getattr(keyword, 'type', ''),
            'level': level,
            'children': []
        }

        # Process child keywords recursively
        # In Robot Framework 7.x, child keywords are in 'body'
        if hasattr(keyword, 'body'):
            for child_item in keyword.body:
                # Check if this is a keyword
                if hasattr(child_item, 'name'):
                    self._process_keyword(child_item, kw_info['children'], level + 1)

        keywords_list.append(kw_info)

def generate_html_report(output_xml, html_output="interactive_report.html"):
    # Parse the output.xml using Robot Framework's API
    result = ExecutionResult(output_xml)

    # Create and use the visitor
    visitor = TestCaseKeywordVisitor()
    result.visit(visitor)

    # Calculate statistics
    suite_count = len(visitor.suite_data)
    test_count = sum(len(suite['tests']) for suite in visitor.suite_data)
    keyword_count = sum(sum(len(test['keywords']) for test in suite['tests']) for suite in visitor.suite_data)

    # Create HTML content with Apple-like design, focused on test cases organized by suite
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Robot Framework Test Suite Overview</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Apple-like design system */
        :root {{
            --background: #ffffff;
            --surface: #f5f5f7;
            --primary: #0071e3;
            --accent: #5e5ce6;
            --success: #34c759;
            --error: #ff3b30;
            --warning: #ff9500;
            --text-primary: #1d1d1f;
            --text-secondary: #86868b;
            --border: #d2d2d7;
            --shadow: rgba(0, 0, 0, 0.1);
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --background: #1d1d1f;
                --surface: #2c2c2e;
                --primary: #0a84ff;
                --accent: #5e5ce6;
                --success: #30d158;
                --error: #ff453a;
                --warning: #ff9f0a;
                --text-primary: #f5f5f7;
                --text-secondary: #98989d;
                --border: #444;
                --shadow: rgba(0, 0, 0, 0.3);
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "San Francisco", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background-color: var(--background);
            color: var(--text-primary);
            line-height: 1.5;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            padding: 20px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        h1 {{
            font-weight: 500;
            font-size: 32px;
            letter-spacing: -0.5px;
            color: var(--text-primary);
        }}

        .intro {{
            margin-bottom: 30px;
            color: var(--text-secondary);
            font-size: 16px;
            line-height: 1.6;
        }}

        .test-summary {{
            display: flex;
            gap: 16px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .summary-card {{
            flex: 1;
            min-width: 180px;
            background-color: var(--surface);
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px var(--shadow);
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: transform 0.2s ease;
        }}

        .summary-card:hover {{
            transform: translateY(-4px);
        }}

        .summary-value {{
            font-size: 36px;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--primary);
        }}

        .summary-label {{
            font-size: 14px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .test-suite {{
            margin-bottom: 40px;
        }}

        .suite-header {{
            cursor: pointer;
            background-color: var(--surface);
            padding: 20px 24px;
            margin: 12px 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px var(--shadow);
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid var(--accent);
        }}

        .suite-header:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px var(--shadow);
        }}

        .suite-name {{
            font-weight: 600;
            font-size: 18px;
            flex: 1;
        }}

        .suite-meta {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        .suite-tests {{
            display: none;
            margin: 8px 0 24px 24px;
            opacity: 0;
            max-height: 0;
            transition: opacity 0.3s ease, max-height 0.3s ease;
        }}

        .suite-tests.visible {{
            display: block;
            opacity: 1;
            max-height: 5000px;
        }}

        .suite-setup {{
            background-color: var(--surface);
            padding: 16px 24px;
            margin: 12px 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px var(--shadow);
            border-left: 4px solid var(--success);
            cursor: pointer;
        }}

        .suite-teardown {{
            background-color: var(--surface);
            padding: 16px 24px;
            margin: 12px 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px var(--shadow);
            border-left: 4px solid var(--warning);
            cursor: pointer;
        }}

        .test-case {{
            cursor: pointer;
            background-color: var(--surface);
            padding: 16px 24px;
            margin: 12px 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px var(--shadow);
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid var(--primary);
        }}

        .test-case:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px var(--shadow);
        }}

        .setup-keyword {{
            border-left: 4px solid var(--success) !important;
        }}

        .teardown-keyword {{
            border-left: 4px solid var(--warning) !important;
        }}

        .test-name {{
            font-weight: 500;
            flex: 1;
        }}

        .chevron {{
            color: var(--text-secondary);
            transition: transform 0.3s ease;
        }}

        .test-case[aria-expanded="true"] .chevron,
        .suite-header[aria-expanded="true"] .chevron,
        .suite-setup[aria-expanded="true"] .chevron,
        .suite-teardown[aria-expanded="true"] .chevron {{
            transform: rotate(90deg);
        }}

        .keywords {{
            display: none;
            margin: 8px 0 24px 24px;
            border-left: 2px solid var(--border);
            padding-left: 24px;
            overflow: hidden;
            opacity: 0;
            max-height: 0;
            transition: opacity 0.3s ease, max-height 0.3s ease;
        }}

        .keywords.visible {{
            display: block;
            opacity: 1;
            max-height: 2000px;
        }}

        .keyword {{
            padding: 12px;
            margin: 8px 0;
            background-color: var(--surface);
            border-radius: 8px;
            box-shadow: 0 1px 4px var(--shadow);
            position: relative;
            border-left: 4px solid var(--accent);
        }}

        .keyword-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .keyword .type-badge {{
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            background-color: var(--border);
            color: var(--text-secondary);
            margin-left: 8px;
        }}

        .child-keywords {{
            margin-left: 24px;
            margin-top: 8px;
        }}

        .section-title {{
            margin: 40px 0 20px 0;
            font-size: 24px;
            font-weight: 500;
            color: var(--text-primary);
        }}

        footer {{
            text-align: center;
            padding: 24px 0;
            margin-top: 48px;
            color: var(--text-secondary);
            font-size: 14px;
            border-top: 1px solid var(--border);
        }}
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Event handlers for test suites
            const suiteHeaders = document.querySelectorAll('.suite-header');

            suiteHeaders.forEach(suiteHeader => {{
                suiteHeader.addEventListener('click', function() {{
                    const suiteId = this.getAttribute('data-target');
                    const suiteElement = document.getElementById(suiteId);
                    const isExpanded = this.getAttribute('aria-expanded') === 'true';

                    // Update aria-expanded attribute
                    this.setAttribute('aria-expanded', !isExpanded);

                    if (suiteElement.classList.contains('visible')) {{
                        suiteElement.classList.remove('visible');
                        setTimeout(() => {{
                            suiteElement.style.display = 'none';
                        }}, 300);
                    }} else {{
                        suiteElement.style.display = 'block';
                        setTimeout(() => {{
                            suiteElement.classList.add('visible');
                        }}, 10);
                    }}
                }});
            }});

            // Event handlers for test cases and setup/teardown elements
            const expandableElements = document.querySelectorAll('.test-case, .suite-setup, .suite-teardown');

            expandableElements.forEach(element => {{
                element.addEventListener('click', function() {{
                    const targetId = this.getAttribute('data-target');
                    const targetElement = document.getElementById(targetId);
                    const isExpanded = this.getAttribute('aria-expanded') === 'true';

                    // Update aria-expanded attribute
                    this.setAttribute('aria-expanded', !isExpanded);

                    if (targetElement.classList.contains('visible')) {{
                        targetElement.classList.remove('visible');
                        setTimeout(() => {{
                            targetElement.style.display = 'none';
                        }}, 300);
                    }} else {{
                        targetElement.style.display = 'block';
                        setTimeout(() => {{
                            targetElement.classList.add('visible');
                        }}, 10);
                    }}
                }});
            }});
        }});
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>Test Automation Overview</h1>
        </header>

        <div class="intro">
            <p>This report shows all automated test cases organized by test suite. Click on each suite to see its test cases, then click on a test case to see the detailed steps.</p>
        </div>

        <div class="test-summary">
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
    for i, suite in enumerate(visitor.suite_data):
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

        # Add suite setup if exists
        if suite['setup']:
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

            # Add test setup if exists
            if test['setup']:
                html_content += _render_keyword_special(test['setup'], 'setup-keyword')

            # Add regular keywords
            for kw in test['keywords']:
                html_content += _render_keyword_overview(kw)

            # Add test teardown if exists
            if test['teardown']:
                html_content += _render_keyword_special(test['teardown'], 'teardown-keyword')

            html_content += "                </div>\n"

        # Add suite teardown if exists
        if suite['teardown']:
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
