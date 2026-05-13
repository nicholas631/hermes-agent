---
title: "Testing Scenarios"
description: "Practical testing scenarios for validating Hermes Agent with local models"
revision: 0.1.0
last_updated: 2026-05-12
---

# Testing Scenarios

This guide provides practical testing scenarios for validating Hermes Agent capabilities with local models, based on the Qwen 3.6 27B testing guide.

## Code Generation Tests

### Scenario 1: REST API Endpoint Creation

**Purpose**: Validate model's ability to generate functional, production-ready code.

**Test prompt:**
```
Create a Python Flask REST API endpoint that:
1. Accepts POST requests at /api/users
2. Validates required fields: name (string), email (string), age (integer)
3. Returns 400 for invalid data, 201 for success
4. Includes input validation and error handling
5. Uses type hints and docstrings
```

**Expected behavior:**
- Generates syntactically correct Python code
- Includes all required validation
- Proper HTTP status codes
- Type hints present
- Docstrings included

**Validation:**
```python
def test_rest_api_generation():
    response = agent.chat(prompt)
    
    # Check code is present
    assert "def" in response or "class" in response
    
    # Check for required elements
    assert "@app.route" in response or "@blueprint.route" in response
    assert "POST" in response
    assert "400" in response or "Bad Request" in response
    assert "201" in response or "Created" in response
    
    # Extract and attempt to parse Python code
    code_blocks = extract_code_blocks(response)
    assert len(code_blocks) > 0
    
    try:
        compile(code_blocks[0], '<string>', 'exec')
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax errors: {e}")
```

### Scenario 2: Unit Test Generation

**Purpose**: Test model's understanding of testing best practices.

**Test prompt:**
```
Write pytest unit tests for this function:

def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

Include:
- Test for n=0
- Test for n=1
- Test for normal cases
- Test for edge cases
- Test for invalid input
```

**Expected behavior:**
- Valid pytest syntax
- Multiple test cases
- Edge case coverage
- Proper assertions
- Clear test names

**Validation:**
```python
def test_unit_test_generation():
    response = agent.chat(prompt)
    
    # Check for pytest patterns
    assert "def test_" in response
    assert "assert" in response
    
    # Should have multiple test cases
    test_count = response.count("def test_")
    assert test_count >= 4, f"Expected at least 4 tests, got {test_count}"
    
    # Check for edge cases mentioned
    assert "0" in response or "zero" in response.lower()
    assert "1" in response or "one" in response.lower()
```

### Scenario 3: Data Structure Implementation

**Purpose**: Validate implementation of complex data structures.

**Test prompt:**
```
Implement a binary search tree in Python with:
- insert() method
- search() method
- in_order_traversal() method
- delete() method
- Include type hints
- Add comprehensive docstrings
```

**Expected behavior:**
- Complete class definition
- All required methods implemented
- Type hints for parameters and returns
- Docstrings with descriptions
- Handling of edge cases

---

## Code Explanation & Documentation

### Scenario 4: Algorithm Explanation

**Purpose**: Test model's ability to explain complex code.

**Test prompt:**
```
Explain this quicksort implementation in detail:

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

Include:
- How it works
- Time complexity
- Space complexity
- Edge cases handled
```

**Expected behavior:**
- Clear explanation of algorithm steps
- Mentions divide-and-conquer approach
- Discusses complexity (O(n log n) average)
- Identifies edge cases (empty array, single element)

**Validation:**
```python
def test_algorithm_explanation():
    response = agent.chat(prompt)
    
    # Should mention key concepts
    assert "pivot" in response.lower()
    assert "partition" in response.lower() or "divide" in response.lower()
    
    # Should discuss complexity
    assert "complexity" in response.lower() or "O(n" in response
    
    # Should be detailed (not just a one-liner)
    assert len(response.split()) > 50, "Explanation too brief"
```

### Scenario 5: Docstring Generation

**Purpose**: Test ability to generate comprehensive documentation.

**Test prompt:**
```
Add complete docstrings to this function:

def process_user_data(data, normalize=True, validate=True):
    if validate:
        if not isinstance(data, dict):
            raise ValueError("Data must be dict")
        if 'name' not in data:
            raise ValueError("Missing required field: name")
    
    result = data.copy()
    if normalize:
        result['name'] = result['name'].strip().lower()
    
    return result

Use Google-style docstrings.
```

**Expected behavior:**
- Function description
- Args section with parameter descriptions
- Returns section
- Raises section with exception descriptions
- Usage example (optional but good)

---

## Long Context Handling

### Scenario 6: Multi-File Project Analysis

**Purpose**: Test ability to handle large codebases across multiple files.

**Test prompt:**
```
Analyze this Django project structure and identify all API endpoints:

[Paste contents of 5-10 Python files totaling ~30k tokens]

List all API endpoints with:
- HTTP method
- URL pattern
- View function name
- Required parameters
- Authentication requirements
```

**Expected behavior:**
- Correctly processes large context
- Identifies all endpoints across files
- Extracts accurate details
- Maintains coherence across files
- References specific files when listing endpoints

**Validation:**
```python
@pytest.mark.slow
def test_large_codebase_analysis():
    # Generate large context (30k tokens ≈ 120k chars)
    large_codebase = generate_test_codebase(file_count=10, lines_per_file=400)
    
    response = agent.chat(f"Analyze this codebase:\n\n{large_codebase}\n\nList all functions.")
    
    # Should handle large context without error
    assert response is not None
    assert len(response) > 100, "Response too short for large codebase"
    
    # Should reference multiple files
    assert response.count("file") > 5 or response.count(".py") > 5
```

### Scenario 7: Log File Summarization

**Purpose**: Test summarization of large structured data.

**Test prompt:**
```
Summarize these application logs (5000 lines) and identify:
- Most common errors
- Error frequency
- Affected components
- Time patterns
- Recommended actions

[Large log file content]
```

**Expected behavior:**
- Processes large log context
- Groups similar errors
- Provides frequency statistics
- Identifies patterns
- Makes actionable recommendations

---

## Tool Usage Validation

### Scenario 8: File Operations

**Purpose**: Test integration of terminal/file tools with code understanding.

**Test prompt:**
```
Find all Python files in the current directory that import 'requests',
then list what endpoints they're calling.
```

**Expected behavior:**
- Uses file system tools to search
- Reads relevant files
- Analyzes code for requests usage
- Extracts and lists endpoints
- Provides organized summary

**Validation:**
```python
def test_file_operation_with_analysis():
    # Create test files
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    
    (test_dir / "api.py").write_text("""
import requests

def get_users():
    return requests.get("https://api.example.com/users")

def get_posts():
    return requests.get("https://api.example.com/posts")
""")
    
    response = agent.chat(
        f"In {test_dir}, find files importing requests and list endpoints they call"
    )
    
    # Should identify the file
    assert "api.py" in response
    
    # Should extract endpoints
    assert "users" in response.lower()
    assert "posts" in response.lower()
    
    # Should have called terminal/file tools
    assert any(call["tool"] == "terminal" for call in agent.last_tool_calls)
```

### Scenario 9: Web Search Integration

**Purpose**: Test combining web search with code generation.

**Test prompt:**
```
Search for the current best practices for Python async/await error handling,
then show me a code example implementing those best practices.
```

**Expected behavior:**
- Uses web search tool
- Synthesizes findings
- Generates relevant code example
- Cites modern best practices
- Code reflects current patterns

### Scenario 10: Multi-Step Workflow

**Purpose**: Test complex multi-tool workflows.

**Test prompt:**
```
1. Check what Python version is installed
2. Create a virtual environment
3. Create a requirements.txt with Flask and pytest
4. Generate a simple Flask app with one endpoint
5. Generate a pytest test for that endpoint
```

**Expected behavior:**
- Executes steps sequentially
- Uses terminal tool multiple times
- Generates appropriate files
- Validates each step before proceeding
- Handles any errors gracefully

**Validation:**
```python
def test_multi_step_workflow():
    response = agent.chat(prompt)
    
    # Should have used terminal tool
    terminal_calls = [c for c in agent.last_tool_calls if c["tool"] == "terminal"]
    assert len(terminal_calls) >= 3, "Should make multiple terminal calls"
    
    # Should mention each step
    assert "python" in response.lower()
    assert "virtual environment" in response.lower() or "venv" in response.lower()
    assert "flask" in response.lower()
    assert "test" in response.lower()
```

---

## Instruction Following

### Scenario 11: Format Conversion

**Purpose**: Test precise adherence to format specifications.

**Test prompt:**
```
Convert this JSON to YAML format:
- Use 2-space indentation
- Add comments for each top-level key
- Ensure all keys use snake_case

{
  "appName": "MyApp",
  "version": "1.0",
  "database": {
    "host": "localhost",
    "port": 5432
  }
}
```

**Expected behavior:**
- Correct YAML syntax
- 2-space indentation used
- Comments added
- Keys converted to snake_case
- Maintains data structure

**Validation:**
```python
def test_format_conversion():
    response = agent.chat(prompt)
    
    # Extract YAML content
    yaml_content = extract_code_blocks(response)[0]
    
    # Verify it's valid YAML
    import yaml
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML: {e}")
    
    # Check snake_case
    assert "app_name" in yaml_content or "app_name" in str(data)
    
    # Check comments exist
    assert "#" in yaml_content
```

### Scenario 12: Style Enforcement

**Purpose**: Test adherence to coding style requirements.

**Test prompt:**
```
Refactor this code to follow PEP 8:
- Maximum line length 88 characters
- Use type hints
- Add docstrings
- Fix all naming conventions

def getData(UserId, IncludeMetadata=True):
    result=[]
    for i in range(100):
        if IncludeMetadata:result.append({'id':i,'user':UserId,'meta':'data'})
        else:result.append({'id':i,'user':UserId})
    return result
```

**Expected behavior:**
- Proper naming (snake_case)
- Lines under 88 chars
- Type hints added
- Docstring present
- Proper spacing
- Clear formatting

---

## Reasoning & Problem Solving

### Scenario 13: Debugging

**Purpose**: Test analytical debugging capabilities.

**Test prompt:**
```
This function is supposed to find the first duplicate in a list,
but it's not working correctly. Find and fix the bug:

def find_first_duplicate(arr):
    seen = []
    for item in arr:
        if item in seen:
            return item
        seen = []  # Bug is here
    return None

Test case that fails:
find_first_duplicate([1, 2, 3, 2, 4])  # Should return 2, returns None
```

**Expected behavior:**
- Identifies the bug (resetting seen list)
- Explains why it causes the failure
- Provides correct fix
- Optionally suggests improvements

**Validation:**
```python
def test_debugging_capability():
    response = agent.chat(prompt)
    
    # Should identify the problem line
    assert "seen = []" in response or "resetting" in response.lower()
    
    # Should provide a fix
    assert "seen.append" in response or "fix" in response.lower()
    
    # Extract fixed code and test it
    fixed_code = extract_code_blocks(response)[0]
    # Verify fix works (would need exec() and testing)
```

### Scenario 14: Algorithm Optimization

**Purpose**: Test ability to identify and improve performance issues.

**Test prompt:**
```
This function is running slowly on large datasets.
Analyze the time complexity and suggest optimizations:

def has_duplicates(arr):
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j]:
                return True
    return False

Current performance: 30 seconds for 10,000 items
```

**Expected behavior:**
- Identifies O(n²) complexity
- Suggests O(n) solution using set
- Provides optimized code
- Explains performance improvement

---

## Performance Benchmarking

### Scenario 15: Response Time Measurement

**Purpose**: Establish baseline performance metrics.

```python
def test_response_time_benchmark():
    """Measure and record response times for different prompt types."""
    
    test_cases = [
        ("simple", "What is 2+2?", 50),
        ("code_gen", "Write a Python function to reverse a string", 150),
        ("explanation", "Explain how quicksort works", 200),
        ("analysis", "Analyze this code: [100 lines]", 300),
    ]
    
    results = []
    
    for name, prompt, max_tokens in test_cases:
        start = time.time()
        response = agent.chat(prompt, max_tokens=max_tokens)
        latency = time.time() - start
        
        results.append({
            "scenario": name,
            "latency_ms": latency * 1000,
            "response_length": len(response),
            "tokens": estimate_tokens(response),
        })
        
        # Basic assertions
        assert latency < 60, f"{name} took too long: {latency:.1f}s"
        assert len(response) > 10, f"{name} response too short"
    
    # Log results for tracking
    print("\nBenchmark Results:")
    for r in results:
        print(f"  {r['scenario']}: {r['latency_ms']:.0f}ms")
```

---

## Running Testing Scenarios

### Manual Execution

```powershell
# Configure for local model
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b

# Test each scenario interactively
hermes

# Then paste test prompts and validate responses
```

### Automated Execution

```python
# tests/scenarios/test_code_generation_scenarios.py
import pytest
from agent import AIAgent

@pytest.mark.integration
class TestCodeGenerationScenarios:
    
    @pytest.fixture
    def agent(self):
        return AIAgent(
            model="qwen36_27b",
            provider="custom",
            base_url="http://localhost:8085/v1",
        )
    
    def test_rest_api_generation(self, agent):
        prompt = """Create a Python Flask REST API endpoint..."""
        response = agent.chat(prompt)
        
        # Validations as shown in scenarios
        assert "def" in response
        # ... more assertions
```

---

## Additional Resources

- **Benchmark Script**: [`scripts/benchmark_local_model.py`](../../scripts/benchmark_local_model.py)
- **Integration Tests**: [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py)
- **Testing Best Practices**: [`testing-best-practices.md`](testing-best-practices.md)
- **LLM Service Testing Guide**: `d:\Python_Projects\LLM_Local_Model_Service\docs\QWEN36_TESTING_GUIDE.md`
