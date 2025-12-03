"""Unit tests for ADR-0006: Tool invocation example generation.

Note: Tests updated for ADR-0010 enhanced placeholders with type and description.
Enhanced placeholders follow format: <type:TYPE|desc:DESCRIPTION>
"""  # noqa: B101

import json

import pytest

from cllm_mcp.client import generate_json_example, generate_placeholder


class TestGeneratePlaceholder:
    """Tests for generate_placeholder function (ADR-0006/ADR-0010)."""

    @pytest.mark.unit
    def test_placeholder_string_type(self):
        """Test that string type generates enhanced placeholder with description."""
        prop_info = {"type": "string"}
        result = generate_placeholder(prop_info)
        # ADR-0010: Enhanced placeholders include type and description
        assert result == "<type:string|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_number_type(self):
        """Test that number type generates enhanced placeholder."""
        prop_info = {"type": "number"}
        result = generate_placeholder(prop_info)
        assert result == "<type:number|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_integer_type(self):
        """Test that integer type generates enhanced placeholder."""
        prop_info = {"type": "integer"}
        result = generate_placeholder(prop_info)
        assert result == "<type:integer|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_boolean_type(self):
        """Test that boolean type generates enhanced placeholder (not True/False)."""
        prop_info = {"type": "boolean"}
        result = generate_placeholder(prop_info)
        # ADR-0010: Changed from True to enhanced string placeholder
        assert result == "<type:boolean|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_array_of_strings(self):
        """Test that array of strings generates list with enhanced placeholders."""
        prop_info = {"type": "array", "items": {"type": "string"}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        # ADR-0010: Array items use enhanced placeholders
        assert all(item == "<type:string|desc:No description available>" for item in result)

    @pytest.mark.unit
    def test_placeholder_array_of_numbers(self):
        """Test that array of numbers generates list with enhanced placeholders."""
        prop_info = {"type": "array", "items": {"type": "number"}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(item == "<type:number|desc:No description available>" for item in result)

    @pytest.mark.unit
    def test_placeholder_simple_object(self):
        """Test that simple object generates nested structure with enhanced placeholders."""
        prop_info = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result["name"] == "<type:string|desc:No description available>"
        assert result["age"] == "<type:integer|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_empty_object(self):
        """Test that empty object properties returns default structure."""
        prop_info = {"type": "object", "properties": {}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        # Empty dict {} is falsy in Python, so it returns default structure
        # ADR-0010: Default uses enhanced placeholder format
        default_placeholder = "<type:string|desc:No description available>"
        assert result == {default_placeholder: default_placeholder}

    @pytest.mark.unit
    def test_placeholder_object_without_properties(self):
        """Test that object without properties generates default structure."""
        prop_info = {"type": "object"}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        default_placeholder = "<type:string|desc:No description available>"
        assert result == {default_placeholder: default_placeholder}

    @pytest.mark.unit
    def test_placeholder_default_type(self):
        """Test that missing type defaults to string with enhanced format."""
        prop_info = {}
        result = generate_placeholder(prop_info)
        assert result == "<type:string|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_unknown_type(self):
        """Test that unknown type generates enhanced placeholder with type preserved."""
        prop_info = {"type": "custom"}
        result = generate_placeholder(prop_info)
        assert result == "<type:custom|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_nested_array(self):
        """Test that nested array of objects works correctly with enhanced placeholders."""
        prop_info = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            },
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], dict)
        # ADR-0010: Nested structures use enhanced placeholders
        assert result[0]["id"] == "<type:integer|desc:No description available>"
        assert result[0]["name"] == "<type:string|desc:No description available>"


class TestGenerateJsonExample:
    """Tests for generate_json_example function (ADR-0006/ADR-0010)."""

    @pytest.mark.unit
    def test_simple_string_property(self):
        """Test example generation for simple string property with description."""
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        }
        result = generate_json_example(schema)
        # ADR-0010: Enhanced placeholders include description
        assert result == {"path": "<type:string|desc:File path>"}

    @pytest.mark.unit
    def test_multiple_properties(self):
        """Test example generation for multiple properties with enhanced placeholders."""
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
            "required": ["path", "content"],
        }
        result = generate_json_example(schema)
        # ADR-0010: All placeholders are enhanced format now
        assert result == {
            "path": "<type:string|desc:No description available>",
            "content": "<type:string|desc:No description available>",
            "overwrite": "<type:boolean|desc:No description available>",
        }

    @pytest.mark.unit
    def test_mixed_types(self):
        """Test example generation with mixed property types."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
        }
        result = generate_json_example(schema)
        # ADR-0010: Enhanced placeholders for all types
        assert result == {
            "name": "<type:string|desc:No description available>",
            "age": "<type:integer|desc:No description available>",
            "score": "<type:number|desc:No description available>",
            "active": "<type:boolean|desc:No description available>",
        }

    @pytest.mark.unit
    def test_array_property(self):
        """Test example generation for array property."""
        schema = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        }
        result = generate_json_example(schema)
        assert "tags" in result
        assert isinstance(result["tags"], list)
        # ADR-0010: Array items use enhanced placeholders
        assert all(item == "<type:string|desc:No description available>" for item in result["tags"])

    @pytest.mark.unit
    def test_nested_object_property(self):
        """Test example generation for nested object property."""
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "author": {"type": "string"},
                        "version": {"type": "integer"},
                    },
                }
            },
        }
        result = generate_json_example(schema)
        assert isinstance(result["metadata"], dict)
        # ADR-0010: Nested properties use enhanced placeholders
        assert result["metadata"]["author"] == "<type:string|desc:No description available>"
        assert result["metadata"]["version"] == "<type:integer|desc:No description available>"

    @pytest.mark.unit
    def test_empty_schema(self):
        """Test example generation for empty schema."""
        schema = {}
        result = generate_json_example(schema)
        assert result == {}

    @pytest.mark.unit
    def test_schema_with_no_properties(self):
        """Test example generation for schema with no properties."""
        schema = {"type": "object"}
        result = generate_json_example(schema)
        assert result == {}

    @pytest.mark.unit
    def test_complex_nested_structure(self):
        """Test example generation for complex nested structure."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "filters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
                "options": {"type": "array", "items": {"type": "string"}},
            },
        }
        result = generate_json_example(schema)
        # ADR-0010: Enhanced placeholders throughout
        assert result["query"] == "<type:string|desc:No description available>"
        assert isinstance(result["filters"], dict)
        assert result["filters"]["type"] == "<type:string|desc:No description available>"
        assert result["filters"]["limit"] == "<type:integer|desc:No description available>"
        assert isinstance(result["options"], list)
        assert all(item == "<type:string|desc:No description available>" for item in result["options"])

    @pytest.mark.unit
    def test_example_json_serializable(self):
        """Test that generated examples with enhanced placeholders are JSON serializable."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }
        result = generate_json_example(schema)
        # Should not raise an exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

    @pytest.mark.unit
    def test_single_required_string_property(self):
        """Test example for tool with single required string parameter."""
        schema = {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "IANA timezone name"}
            },
            "required": ["timezone"],
        }
        result = generate_json_example(schema)
        # ADR-0010: Enhanced placeholder includes description from schema
        assert result == {"timezone": "<type:string|desc:IANA timezone name>"}

    @pytest.mark.unit
    def test_multiple_required_strings(self):
        """Test example for tool with multiple required string parameters."""
        schema = {
            "type": "object",
            "properties": {
                "source_timezone": {"type": "string"},
                "time": {"type": "string"},
                "target_timezone": {"type": "string"},
            },
            "required": ["source_timezone", "time", "target_timezone"],
        }
        result = generate_json_example(schema)
        # ADR-0010: Enhanced placeholders for all properties
        assert result == {
            "source_timezone": "<type:string|desc:No description available>",
            "time": "<type:string|desc:No description available>",
            "target_timezone": "<type:string|desc:No description available>",
        }
