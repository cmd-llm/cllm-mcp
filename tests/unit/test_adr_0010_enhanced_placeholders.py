"""Unit tests for ADR-0010: Enhanced Placeholders with Type and Description."""  # noqa: B101

import json

import pytest

from cllm_mcp.client import generate_json_example, generate_placeholder


class TestEnhancedPlaceholder:
    """Tests for enhanced placeholder generation with descriptions."""

    @pytest.mark.unit
    def test_placeholder_string_with_description(self):
        """Test that string type with description generates enhanced placeholder."""
        prop_info = {"type": "string", "description": "User name"}
        result = generate_placeholder(prop_info)
        assert result == "<type:string|desc:User name>"

    @pytest.mark.unit
    def test_placeholder_string_without_description(self):
        """Test that string type without description uses fallback."""
        prop_info = {"type": "string"}
        result = generate_placeholder(prop_info)
        assert result == "<type:string|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_number_with_description(self):
        """Test that number type with description generates enhanced placeholder."""
        prop_info = {"type": "number", "description": "Price value"}
        result = generate_placeholder(prop_info)
        assert result == "<type:number|desc:Price value>"

    @pytest.mark.unit
    def test_placeholder_integer_with_description(self):
        """Test that integer type with description generates enhanced placeholder."""
        prop_info = {"type": "integer", "description": "Count of items"}
        result = generate_placeholder(prop_info)
        assert result == "<type:integer|desc:Count of items>"

    @pytest.mark.unit
    def test_placeholder_boolean_with_description(self):
        """Test that boolean type returns string placeholder (not True/False)."""
        prop_info = {"type": "boolean", "description": "Is active flag"}
        result = generate_placeholder(prop_info)
        assert result == "<type:boolean|desc:Is active flag>"

    @pytest.mark.unit
    def test_placeholder_description_truncation(self):
        """Test that long descriptions are truncated to 80 chars."""
        long_desc = "a" * 100
        prop_info = {"type": "string", "description": long_desc}
        result = generate_placeholder(prop_info)
        # Should truncate to 80 chars + "..."
        assert "..." in result
        assert len(result) < len(f"<type:string|desc:{long_desc}>")
        assert len(result) <= 100  # Reasonable upper bound

    @pytest.mark.unit
    def test_placeholder_array_with_string_items(self):
        """Test that array of strings generates array structure with enhanced placeholders."""
        prop_info = {
            "type": "array",
            "items": {"type": "string", "description": "Tag value"},
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == "<type:string|desc:Tag value>"
        assert result[1] == "<type:string|desc:Tag value>"

    @pytest.mark.unit
    def test_placeholder_array_without_item_description(self):
        """Test array items without descriptions use fallback."""
        prop_info = {"type": "array", "items": {"type": "integer"}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert result[0] == "<type:integer|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_object_with_properties_and_descriptions(self):
        """Test that nested objects generate structure with enhanced placeholders."""
        prop_info = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User full name"},
                "age": {"type": "integer", "description": "User age in years"},
            },
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result["name"] == "<type:string|desc:User full name>"
        assert result["age"] == "<type:integer|desc:User age in years>"

    @pytest.mark.unit
    def test_placeholder_object_empty_properties(self):
        """Test object with no properties generates default structure."""
        prop_info = {"type": "object", "properties": {}}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result == {"<type:string|desc:No description available>": "<type:string|desc:No description available>"}

    @pytest.mark.unit
    def test_placeholder_object_missing_properties_key(self):
        """Test object without properties key generates default structure."""
        prop_info = {"type": "object"}
        result = generate_placeholder(prop_info)
        assert isinstance(result, dict)
        assert result == {"<type:string|desc:No description available>": "<type:string|desc:No description available>"}

    @pytest.mark.unit
    def test_placeholder_default_type_with_description(self):
        """Test that missing type defaults to string with description."""
        prop_info = {"description": "Some value"}
        result = generate_placeholder(prop_info)
        assert result == "<type:string|desc:Some value>"

    @pytest.mark.unit
    def test_placeholder_unknown_type_with_description(self):
        """Test that unknown type is preserved in placeholder."""
        prop_info = {"type": "custom", "description": "Custom type value"}
        result = generate_placeholder(prop_info)
        assert result == "<type:custom|desc:Custom type value>"

    @pytest.mark.unit
    def test_placeholder_nested_array_of_objects(self):
        """Test array of objects with descriptions."""
        prop_info = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Unique identifier"},
                    "name": {"type": "string", "description": "Item name"},
                },
            },
        }
        result = generate_placeholder(prop_info)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], dict)
        assert result[0]["id"] == "<type:integer|desc:Unique identifier>"
        assert result[0]["name"] == "<type:string|desc:Item name>"

    @pytest.mark.unit
    def test_placeholder_empty_description_string(self):
        """Test that empty description string uses fallback."""
        prop_info = {"type": "string", "description": ""}
        result = generate_placeholder(prop_info)
        # Empty string is falsy, so should use fallback
        assert result == "<type:string|desc:No description available>"

    @pytest.mark.unit
    def test_placeholder_special_characters_in_description(self):
        """Test that special characters in descriptions are preserved."""
        prop_info = {"type": "string", "description": "Email (format: user@example.com)"}
        result = generate_placeholder(prop_info)
        assert "Email (format: user@example.com)" in result
        assert result == "<type:string|desc:Email (format: user@example.com)>"


class TestPhase2SpecialCases:
    """Tests for Phase 2: Enum and constraint support."""

    @pytest.mark.unit
    def test_placeholder_with_enum(self):
        """Test that enum values are included in description."""
        prop_info = {
            "type": "string",
            "description": "Status",
            "enum": ["active", "inactive", "pending"],
        }
        result = generate_placeholder(prop_info)
        assert "enum: active, inactive, pending" in result
        assert result == "<type:string|desc:Status (enum: active, inactive, pending)>"

    @pytest.mark.unit
    def test_placeholder_enum_truncation(self):
        """Test that many enum values are truncated."""
        prop_info = {
            "type": "string",
            "description": "Priority",
            "enum": ["low", "medium", "high", "critical", "blocker", "enhancement", "bug"],
        }
        result = generate_placeholder(prop_info)
        # Should truncate to first 5 with "..."
        assert "enum: low, medium, high, critical, blocker, ..." in result

    @pytest.mark.unit
    def test_placeholder_with_min_max(self):
        """Test that min/max constraints are included."""
        prop_info = {
            "type": "integer",
            "description": "Count",
            "minimum": 1,
            "maximum": 100,
        }
        result = generate_placeholder(prop_info)
        assert "range: 1-100" in result
        assert result == "<type:integer|desc:Count (range: 1-100)>"

    @pytest.mark.unit
    def test_placeholder_with_minimum_only(self):
        """Test that minimum constraint alone is included."""
        prop_info = {
            "type": "integer",
            "description": "Page number",
            "minimum": 1,
        }
        result = generate_placeholder(prop_info)
        assert "min: 1" in result
        assert result == "<type:integer|desc:Page number (min: 1)>"

    @pytest.mark.unit
    def test_placeholder_with_maximum_only(self):
        """Test that maximum constraint alone is included."""
        prop_info = {
            "type": "integer",
            "description": "Items per page",
            "maximum": 100,
        }
        result = generate_placeholder(prop_info)
        assert "max: 100" in result
        assert result == "<type:integer|desc:Items per page (max: 100)>"

    @pytest.mark.unit
    def test_placeholder_with_format(self):
        """Test that format constraint is included."""
        prop_info = {
            "type": "string",
            "description": "Birthday",
            "format": "date",
        }
        result = generate_placeholder(prop_info)
        assert "format: date" in result
        assert result == "<type:string|desc:Birthday (format: date)>"

    @pytest.mark.unit
    def test_placeholder_with_pattern(self):
        """Test that pattern constraint is included."""
        prop_info = {
            "type": "string",
            "description": "Email",
            "pattern": "^[a-zA-Z0-9+._-]+@[a-zA-Z0-9.-]+$",
        }
        result = generate_placeholder(prop_info)
        # Pattern should be truncated
        assert "pattern:" in result
        assert "..." in result or len(result) <= 100

    @pytest.mark.unit
    def test_placeholder_with_multiple_constraints(self):
        """Test that multiple constraints are all included."""
        prop_info = {
            "type": "integer",
            "description": "Retry count",
            "minimum": 0,
            "maximum": 10,
        }
        result = generate_placeholder(prop_info)
        # All constraints should be present
        assert "range: 0-10" in result
        assert result == "<type:integer|desc:Retry count (range: 0-10)>"

    @pytest.mark.unit
    def test_placeholder_enum_with_numbers(self):
        """Test enum with numeric values."""
        prop_info = {
            "type": "integer",
            "description": "HTTP status category",
            "enum": [200, 201, 204, 301, 302, 400, 401, 403, 404, 500],
        }
        result = generate_placeholder(prop_info)
        assert "enum:" in result
        # Should show first 5 values with ...
        assert "200, 201, 204, 301, 302, ..." in result

    @pytest.mark.unit
    def test_placeholder_constraints_with_truncation(self):
        """Test that very long constraint descriptions are still truncated to 80 chars."""
        prop_info = {
            "type": "string",
            "description": "A very long description that explains everything about this field in great detail",
            "enum": ["value1", "value2"],
        }
        result = generate_placeholder(prop_info)
        # Total should be truncated to 80 chars
        # Extract the description part
        desc_part = result.split("|desc:")[1].rstrip(">")
        assert len(desc_part) <= 80
        # Should end with ...
        assert desc_part.endswith("...")

    @pytest.mark.unit
    def test_placeholder_with_all_constraints(self):
        """Test placeholder with multiple types of constraints."""
        prop_info = {
            "type": "string",
            "description": "Username",
            "pattern": "^[a-zA-Z0-9_-]{3,20}$",
            "format": "username",
        }
        result = generate_placeholder(prop_info)
        # Should contain format at minimum
        assert "format: username" in result
        # Pattern should be included but may be truncated
        assert "pattern:" in result

    @pytest.mark.unit
    def test_json_example_with_enums(self):
        """Test JSON example generation with enum values in schema."""
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status",
                    "enum": ["draft", "published", "archived"],
                }
            },
        }
        result = generate_json_example(schema)
        assert "status" in result
        assert "enum: draft, published, archived" in result["status"]

    @pytest.mark.unit
    def test_json_example_with_numeric_constraints(self):
        """Test JSON example with numeric constraints."""
        schema = {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "description": "User age",
                    "minimum": 0,
                    "maximum": 150,
                },
                "score": {
                    "type": "number",
                    "description": "Test score",
                    "minimum": 0.0,
                    "maximum": 100.0,
                },
            },
        }
        result = generate_json_example(schema)
        assert "range: 0-150" in result["age"]
        assert "range: 0.0-100.0" in result["score"]

    @pytest.mark.unit
    def test_json_example_with_format_constraints(self):
        """Test JSON example with format constraints."""
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address",
                    "format": "email",
                },
                "created_at": {
                    "type": "string",
                    "description": "Creation timestamp",
                    "format": "date-time",
                },
            },
        }
        result = generate_json_example(schema)
        assert "format: email" in result["email"]
        assert "format: date-time" in result["created_at"]


class TestEnhancedJsonExample:
    """Tests for enhanced JSON example generation."""

    @pytest.mark.unit
    def test_simple_string_property_with_description(self):
        """Test example generation for simple string property with description."""
        schema = {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name",
                }
            },
        }
        result = generate_json_example(schema)
        assert result == {"timezone": "<type:string|desc:IANA timezone name>"}

    @pytest.mark.unit
    def test_multiple_properties_with_descriptions(self):
        """Test example generation for multiple properties with descriptions."""
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"},
                "overwrite": {"type": "boolean", "description": "Overwrite existing file"},
            },
        }
        result = generate_json_example(schema)
        assert result == {
            "path": "<type:string|desc:File path>",
            "content": "<type:string|desc:File content>",
            "overwrite": "<type:boolean|desc:Overwrite existing file>",
        }

    @pytest.mark.unit
    def test_mixed_types_with_descriptions(self):
        """Test example generation with mixed property types and descriptions."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer", "description": "User age"},
                "score": {"type": "number", "description": "Score value"},
                "active": {"type": "boolean", "description": "Is active"},
            },
        }
        result = generate_json_example(schema)
        assert result == {
            "name": "<type:string|desc:User name>",
            "age": "<type:integer|desc:User age>",
            "score": "<type:number|desc:Score value>",
            "active": "<type:boolean|desc:Is active>",
        }

    @pytest.mark.unit
    def test_array_property_with_descriptions(self):
        """Test example generation for array property."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "description": "Tag string"},
                }
            },
        }
        result = generate_json_example(schema)
        assert "tags" in result
        assert isinstance(result["tags"], list)
        assert all(item == "<type:string|desc:Tag string>" for item in result["tags"])

    @pytest.mark.unit
    def test_nested_object_property_with_descriptions(self):
        """Test example generation for nested object property with descriptions."""
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "author": {"type": "string", "description": "Author name"},
                        "version": {"type": "integer", "description": "Version number"},
                    },
                }
            },
        }
        result = generate_json_example(schema)
        assert isinstance(result["metadata"], dict)
        assert result["metadata"]["author"] == "<type:string|desc:Author name>"
        assert result["metadata"]["version"] == "<type:integer|desc:Version number>"

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
    def test_complex_nested_structure_with_descriptions(self):
        """Test example generation for complex nested structure with descriptions."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "filters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Filter type"},
                        "limit": {"type": "integer", "description": "Result limit"},
                    },
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string", "description": "Option value"},
                },
            },
        }
        result = generate_json_example(schema)
        assert result["query"] == "<type:string|desc:Search query>"
        assert isinstance(result["filters"], dict)
        assert result["filters"]["type"] == "<type:string|desc:Filter type>"
        assert result["filters"]["limit"] == "<type:integer|desc:Result limit>"
        assert isinstance(result["options"], list)
        assert all(item == "<type:string|desc:Option value>" for item in result["options"])

    @pytest.mark.unit
    def test_example_json_serializable_with_descriptions(self):
        """Test that generated examples with descriptions are JSON serializable."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "count": {"type": "integer", "description": "Item count"},
                "active": {"type": "boolean", "description": "Is active"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "description": "Tag"},
                },
            },
        }
        result = generate_json_example(schema)
        # Should not raise an exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        # Should be able to parse it back
        parsed = json.loads(json_str)
        assert parsed["name"] == "<type:string|desc:User name>"

    @pytest.mark.unit
    def test_perplexity_like_messages_schema(self):
        """Test with real-world schema similar to perplexity messages parameter."""
        schema = {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Role of the message sender (user or assistant)",
                            },
                            "content": {
                                "type": "string",
                                "description": "Content of the message",
                            },
                        },
                    },
                    "description": "Array of messages for the conversation",
                }
            },
        }
        result = generate_json_example(schema)
        assert "messages" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][0], dict)
        assert (
            result["messages"][0]["role"]
            == "<type:string|desc:Role of the message sender (user or assistant)>"
        )
        assert (
            result["messages"][0]["content"]
            == "<type:string|desc:Content of the message>"
        )

    @pytest.mark.unit
    def test_properties_without_descriptions(self):
        """Test that properties without descriptions use fallback."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        result = generate_json_example(schema)
        assert result["name"] == "<type:string|desc:No description available>"
        assert result["age"] == "<type:integer|desc:No description available>"

    @pytest.mark.unit
    def test_mixed_properties_with_and_without_descriptions(self):
        """Test mixing properties with and without descriptions."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer"},
                "active": {"type": "boolean", "description": "Is active"},
            },
        }
        result = generate_json_example(schema)
        assert result["name"] == "<type:string|desc:User name>"
        assert result["age"] == "<type:integer|desc:No description available>"
        assert result["active"] == "<type:boolean|desc:Is active>"
