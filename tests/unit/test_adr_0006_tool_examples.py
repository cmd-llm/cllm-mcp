"""Unit tests for ADR-0006: Tool invocation example generation."""

import json

import pytest
from mcp_cli import generate_json_example, generate_placeholder


class TestGeneratePlaceholder:
    """Tests for generate_placeholder function."""

    @pytest.mark.unit
    def test_placeholder_string_type(self):
        """Test that string type generates <string> placeholder."""
        prop_info = {"type": "string"}
        result = generate_placeholder(prop_info)
        assert result == "<string>"

    @pytest.mark.unit
    def test_placeholder_number_type(self):
        """Test that number type generates <number> placeholder."""
        prop_info = {"type": "number"}
        result = generate_placeholder(prop_info)
        assert result == "<number>"

    @pytest.mark.unit
    def test_placeholder_integer_type(self):
        """Test that integer type generates <integer> placeholder."""
        prop_info = {"type": "integer"}
        result = generate_placeholder(prop_info)
        assert result == "<integer>"

    @pytest.mark.unit
    def test_placeholder_boolean_type(self):
        """Test that boolean type generates True placeholder."""
        prop_info = {"type": "boolean"}
        result = generate_placeholder(prop_info)
        assert result is True

    @pytest.mark.unit
    def test_placeholder_array_of_strings(self):
        """Test that array of strings generates list with string placeholders."""
        prop_info = {"type": "array", "items": {"type": "string"}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(item == "<string>" for item in result)

    @pytest.mark.unit
    def test_placeholder_array_of_numbers(self):
        """Test that array of numbers generates list with number placeholders."""
        prop_info = {"type": "array", "items": {"type": "number"}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(item == "<number>" for item in result)

    @pytest.mark.unit
    def test_placeholder_simple_object(self):
        """Test that simple object generates nested structure with placeholders."""
        prop_info = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result["name"] == "<string>"
        assert result["age"] == "<integer>"

    @pytest.mark.unit
    def test_placeholder_empty_object(self):
        """Test that empty object properties returns default structure."""
        prop_info = {"type": "object", "properties": {}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        # Empty dict {} is falsy in Python, so it returns default structure
        assert result == {"<string>": "<string>"}

    @pytest.mark.unit
    def test_placeholder_object_without_properties(self):
        """Test that object without properties generates default structure."""
        prop_info = {"type": "object"}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result == {"<string>": "<string>"}

    @pytest.mark.unit
    def test_placeholder_default_type(self):
        """Test that missing type defaults to string."""
        prop_info = {}
        result = generate_placeholder(prop_info)
        assert result == "<string>"

    @pytest.mark.unit
    def test_placeholder_unknown_type(self):
        """Test that unknown type generates <type> placeholder."""
        prop_info = {"type": "custom"}
        result = generate_placeholder(prop_info)
        assert result == "<custom>"

    @pytest.mark.unit
    def test_placeholder_nested_array(self):
        """Test that nested array of objects works correctly."""
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
        assert result[0] == {"id": "<integer>", "name": "<string>"}


class TestGenerateJsonExample:
    """Tests for generate_json_example function."""

    @pytest.mark.unit
    def test_simple_string_property(self):
        """Test example generation for simple string property."""
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        }
        result = generate_json_example(schema)
        assert result == {"path": "<string>"}

    @pytest.mark.unit
    def test_multiple_properties(self):
        """Test example generation for multiple properties."""
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
        assert result == {"path": "<string>", "content": "<string>", "overwrite": True}

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
        assert result == {
            "name": "<string>",
            "age": "<integer>",
            "score": "<number>",
            "active": True,
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
        assert all(item == "<string>" for item in result["tags"])

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
        assert result["metadata"]["author"] == "<string>"
        assert result["metadata"]["version"] == "<integer>"

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
        assert result["query"] == "<string>"
        assert isinstance(result["filters"], dict)
        assert result["filters"]["type"] == "<string>"
        assert result["filters"]["limit"] == "<integer>"
        assert isinstance(result["options"], list)
        assert all(item == "<string>" for item in result["options"])

    @pytest.mark.unit
    def test_example_json_serializable(self):
        """Test that generated examples are JSON serializable."""
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
        assert result == {"timezone": "<string>"}

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
        assert result == {
            "source_timezone": "<string>",
            "time": "<string>",
            "target_timezone": "<string>",
        }
