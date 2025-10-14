# Python Template Escaping Issues with Markdown for LLM Usage

## The Problem

Your code encountered template escaping issues due to a conflict between Python's string formatting syntax and the natural use of curly braces in markdown content intended for LLM consumption.

### Root Cause Analysis

1. **Python's `.format()` Method Behavior**
   - Python's `.format()` method treats `{` and `}` as special formatting characters
   - Any `{` or `}` in the template string is interpreted as a format placeholder
   - This includes JSON examples, code snippets, and other legitimate uses of braces in markdown

2. **Your Specific Issues**
   ```python
   # In code_generation.md - This caused problems:
   ```json
   {{
     "code": "# Your complete Python code here",
     "explanation": "..."
   }}
   ```
   
   # In system_instructions.py - This was the trigger:
   base_instructions.format(
       preprocessing_result=preprocessing_str,
       nlp_plan=nlp_plan_str
   )
   ```

3. **Why It Failed**
   - The `{{` and `}}` in your JSON example were interpreted as escaped braces
   - Other single `{` and `}` characters in code examples caused format errors
   - Python couldn't parse the template due to malformed format placeholders

## The Solution Applied

### 1. **Switched from `.format()` to `.replace()`**
```python
# Old (problematic):
formatted_instructions = base_instructions.format(
    preprocessing_result=preprocessing_str,
    nlp_plan=nlp_plan_str
)

# New (solution):
formatted_instructions = base_instructions.replace(
    '{preprocessing_result}', preprocessing_str
).replace(
    '{nlp_plan}', nlp_plan_str
)
```

### 2. **Normalized Markdown Content**
- Removed double braces `{{` `}}` from JSON examples
- Fixed escape sequences (`\\n` → `\n`)
- Used natural markdown syntax without Python-specific escaping

## Guidelines for Future Prevention

### 1. **Choose the Right Template Strategy**

**For Simple Placeholder Replacement (Recommended for LLM markdown):**
```python
# Use string replacement - treats content as literal text
template.replace('{placeholder}', value)
```

**For Complex Formatting (Only when you control all content):**
```python
# Use .format() only when template is completely controlled
template.format(placeholder=value)
```

### 2. **Design Template-Friendly Markdown**

**✅ DO - Use simple placeholders:**
```markdown
## Given Data
### Preprocessing Result
{preprocessing_result}

### NLP Plan
{nlp_plan}
```

**❌ AVOID - Complex nested braces in examples:**
```markdown
Example format:
```json
{{
  "nested": {{"key": "value"}}
}}
```
```

### 3. **LLM Markdown Best Practices**

**Use Literal Code Blocks:**
```markdown
Your output should be formatted as a JSON object:
```json
{
  "code": "# Your complete Python code here",
  "explanation": "Brief explanation"
}
```
```

**Avoid Python String Escaping in Markdown:**
```markdown
# ❌ DON'T - Python-style escaping in markdown
f.write('='*50 + '\\n')

# ✅ DO - Natural representation
f.write('='*50 + '\n')
```

### 4. **Template Architecture Patterns**

**Pattern 1: Simple String Replacement (Recommended)**
```python
class TemplateManager:
    def render(self, template: str, **kwargs) -> str:
        result = template
        for key, value in kwargs.items():
            placeholder = f'{{{key}}}'
            result = result.replace(placeholder, str(value))
        return result
```

**Pattern 2: Safe Format with Validation**
```python
import string

class SafeTemplateManager:
    def render(self, template: str, **kwargs) -> str:
        # Validate template has only expected placeholders
        formatter = string.Formatter()
        try:
            # This will raise KeyError if unexpected placeholders exist
            return template.format(**kwargs)
        except (KeyError, ValueError) as e:
            # Fall back to string replacement
            result = template
            for key, value in kwargs.items():
                result = result.replace(f'{{{key}}}', str(value))
            return result
```

### 5. **Testing Strategy**

**Always Test Templates with Real Content:**
```python
def test_template_rendering():
    # Include braces, JSON, code examples in test markdown
    test_template = """
    Example JSON:
    ```json
    {
      "key": "value",
      "nested": {"inner": true}
    }
    ```
    
    Placeholder: {my_placeholder}
    """
    
    rendered = template_manager.render(test_template, my_placeholder="test_value")
    assert "{" in rendered  # Should preserve JSON braces
    assert "test_value" in rendered  # Should replace placeholder
```

### 6. **Documentation Standards**

**Always Document Template Expectations:**
```python
def get_instructions(self, **kwargs) -> str:
    """
    Render instruction template with dynamic content.
    
    Template Placeholders:
        {preprocessing_result} - JSON string of preprocessing output
        {nlp_plan} - JSON string of NLP plan
        
    Note: Template uses simple string replacement to avoid 
    conflicts with JSON/code examples containing braces.
    """
```

## Key Takeaways

1. **LLM markdown templates often contain natural braces** (JSON, code examples)
2. **Python's `.format()` conflicts with this natural syntax**
3. **Simple string replacement is safer** for LLM template scenarios
4. **Test templates with realistic content** including braces and special characters
5. **Design placeholders to be unique** and unlikely to appear naturally in content
6. **Document your template strategy** for future maintainers

This approach ensures your templates work reliably with LLM-focused content while maintaining readability and maintainability.