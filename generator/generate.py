#!/usr/bin/env python3
"""
WAHA Client Generator

Generates a Python client library and Typer CLI from the WAHA OpenAPI spec.
Based on openapi-python-client but extended with CLI generation.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


def snake_case(string: str) -> str:
    """Convert a string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", string)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return re.sub(r"[^\w]+", "_", s2).lower().strip("_")


def pascal_case(string: str) -> str:
    """Convert a string to PascalCase."""
    return "".join(word.capitalize() for word in re.split(r"[_\-\s]+", string))


def kebab_case(string: str) -> str:
    """Convert a string to kebab-case."""
    return snake_case(string).replace("_", "-")


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a Python identifier."""
    # Remove emojis and special chars from tag names
    name = re.sub(r"[^\w\s-]", "", name)
    name = name.strip()
    if not name:
        name = "default"
    return snake_case(name)


@dataclass
class PropertyInfo:
    """Information about a property/parameter."""
    name: str
    python_name: str
    type_hint: str
    required: bool
    default: Any = None
    description: str = ""
    enum_values: list[str] | None = None
    is_body: bool = False


@dataclass
class EndpointInfo:
    """Information about an API endpoint."""
    name: str
    python_name: str
    method: str
    path: str
    summary: str
    description: str
    tag: str
    parameters: list[PropertyInfo] = field(default_factory=list)
    body: PropertyInfo | None = None
    response_type: str = "Any"


@dataclass
class ModelInfo:
    """Information about a data model."""
    name: str
    python_name: str
    properties: list[PropertyInfo] = field(default_factory=list)
    description: str = ""


@dataclass
class EnumInfo:
    """Information about an enum."""
    name: str
    python_name: str
    values: list[tuple[str, Any]]  # (name, value) pairs
    description: str = ""


@dataclass
class EntityInfo:
    """Information about a high-level entity class.

    Derived from OpenAPI schemas marked with x-waha-entity extension.
    """
    name: str  # Python class name (e.g., "Group")
    schema_name: str  # OpenAPI schema name (e.g., "GroupInfo")
    properties: list[PropertyInfo] = field(default_factory=list)
    description: str = ""


class WAHAGenerator:
    """Generates WAHA client library and CLI from OpenAPI spec."""

    def __init__(self, spec_path: Path, output_dir: Path):
        self.spec_path = spec_path
        self.output_dir = output_dir
        self.template_dir = Path(__file__).parent / "templates"

        # Load spec
        with open(spec_path) as f:
            self.spec = json.load(f)

        # Parsed data
        self.endpoints: dict[str, list[EndpointInfo]] = {}  # tag -> endpoints
        self.models: list[ModelInfo] = []
        self.enums: list[EnumInfo] = []
        self.entities: list[EntityInfo] = []

        # Set up Jinja environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        self.env.filters["snake_case"] = snake_case
        self.env.filters["pascal_case"] = pascal_case
        self.env.filters["kebab_case"] = kebab_case

    def parse(self) -> None:
        """Parse the OpenAPI spec."""
        self._parse_schemas()
        self._parse_endpoints()
        self._parse_entities()

    def _get_type_hint(self, schema: dict, required: bool = True) -> str:
        """Convert OpenAPI schema to Python type hint."""
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            type_str = ref_name  # Keep original schema name for entity matching
        elif "allOf" in schema:
            # Take the first concrete type
            for item in schema["allOf"]:
                return self._get_type_hint(item, required)
            type_str = "Any"
        elif "oneOf" in schema or "anyOf" in schema:
            items = schema.get("oneOf") or schema.get("anyOf", [])
            types = [self._get_type_hint(item, True) for item in items]
            type_str = " | ".join(types)
        elif "type" not in schema:
            type_str = "Any"
        elif schema["type"] == "string":
            if "enum" in schema:
                type_str = "str"  # Will be converted to Literal later
            elif schema.get("format") == "date-time":
                type_str = "datetime"
            elif schema.get("format") == "date":
                type_str = "date"
            elif schema.get("format") == "binary":
                type_str = "bytes"
            else:
                type_str = "str"
        elif schema["type"] == "integer":
            type_str = "int"
        elif schema["type"] == "number":
            type_str = "float"
        elif schema["type"] == "boolean":
            type_str = "bool"
        elif schema["type"] == "array":
            items = schema.get("items", {})
            item_type = self._get_type_hint(items, True)
            type_str = f"list[{item_type}]"
        elif schema["type"] == "object":
            if "additionalProperties" in schema:
                value_type = self._get_type_hint(schema["additionalProperties"], True)
                type_str = f"dict[str, {value_type}]"
            else:
                type_str = "dict[str, Any]"
        else:
            type_str = "Any"

        if not required:
            type_str = f"{type_str} | None"
        return type_str

    def _parse_schemas(self) -> None:
        """Parse component schemas into models and enums."""
        schemas = self.spec.get("components", {}).get("schemas", {})

        for name, schema in schemas.items():
            # Use original schema name as Python class name (already PascalCase)
            python_name = name

            # Check if it's an enum
            if "enum" in schema:
                values = [(snake_case(str(v)).upper(), v) for v in schema["enum"]]
                self.enums.append(EnumInfo(
                    name=name,
                    python_name=python_name,
                    values=values,
                    description=schema.get("description", ""),
                ))
                continue

            # It's a model/object
            if schema.get("type") == "object" or "properties" in schema or "allOf" in schema:
                props = []
                required_fields = set(schema.get("required", []))

                # Handle allOf by merging properties
                if "allOf" in schema:
                    for item in schema["allOf"]:
                        if "properties" in item:
                            for prop_name, prop_schema in item["properties"].items():
                                props.append(self._parse_property(
                                    prop_name, prop_schema, prop_name in required_fields
                                ))
                        required_fields.update(item.get("required", []))

                # Regular properties
                for prop_name, prop_schema in schema.get("properties", {}).items():
                    props.append(self._parse_property(
                        prop_name, prop_schema, prop_name in required_fields
                    ))

                self.models.append(ModelInfo(
                    name=name,
                    python_name=python_name,
                    properties=props,
                    description=schema.get("description", ""),
                ))

    def _parse_property(self, name: str, schema: dict, required: bool) -> PropertyInfo:
        """Parse a property schema."""
        python_name = snake_case(name)
        # Handle Python keywords
        if python_name in ("from", "import", "class", "def", "return", "type"):
            python_name = f"{python_name}_"

        type_hint = self._get_type_hint(schema, required)
        default = schema.get("default")

        return PropertyInfo(
            name=name,
            python_name=python_name,
            type_hint=type_hint,
            required=required,
            default=default,
            description=schema.get("description", ""),
            enum_values=schema.get("enum"),
        )

    def _parse_endpoints(self) -> None:
        """Parse path operations into endpoints."""
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                tags = operation.get("tags", ["default"])
                tag = sanitize_name(tags[0])

                if tag not in self.endpoints:
                    self.endpoints[tag] = []

                endpoint = self._parse_endpoint(path, method, operation, tag)
                self.endpoints[tag].append(endpoint)

    def _parse_endpoint(self, path: str, method: str, operation: dict, tag: str) -> EndpointInfo:
        """Parse a single endpoint operation."""
        operation_id = operation.get("operationId", f"{method}_{path}")
        python_name = snake_case(operation_id)

        # Parse parameters
        parameters = []
        for param in operation.get("parameters", []):
            if "$ref" in param:
                # Resolve reference
                ref_path = param["$ref"].split("/")
                param = self.spec
                for part in ref_path[1:]:  # Skip '#'
                    param = param[part]

            schema = param.get("schema", {"type": "string"})
            required = param.get("required", False)

            # Path parameters are always required
            if param.get("in") == "path":
                required = True

            prop = PropertyInfo(
                name=param["name"],
                python_name=snake_case(param["name"]),
                type_hint=self._get_type_hint(schema, required),
                required=required,
                default=schema.get("default"),
                description=param.get("description", ""),
                enum_values=schema.get("enum"),
            )
            parameters.append(prop)

        # Parse request body
        body = None
        if "requestBody" in operation:
            req_body = operation["requestBody"]
            content = req_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                body = PropertyInfo(
                    name="body",
                    python_name="body",
                    type_hint=self._get_type_hint(schema, True),
                    required=req_body.get("required", True),
                    description=req_body.get("description", ""),
                    is_body=True,
                )

        # Parse response type
        response_type = "Any"
        responses = operation.get("responses", {})
        for status in ["200", "201", "default"]:
            if status in responses:
                resp = responses[status]
                content = resp.get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    response_type = self._get_type_hint(schema, True)
                    break

        return EndpointInfo(
            name=operation_id,
            python_name=python_name,
            method=method.upper(),
            path=path,
            summary=operation.get("summary", ""),
            description=operation.get("description", ""),
            tag=tag,
            parameters=parameters,
            body=body,
            response_type=response_type,
        )

    def _parse_entities(self) -> None:
        """Parse schemas marked with x-waha-entity into entity classes."""
        schemas = self.spec.get("components", {}).get("schemas", {})

        for schema_name, schema in schemas.items():
            entity_config = schema.get("x-waha-entity")
            if not entity_config:
                continue

            # Get the class name from the extension, or derive from schema name
            class_name = entity_config.get("class_name", pascal_case(schema_name))

            # Parse all properties from the schema
            properties = []
            required_fields = set(schema.get("required", []))

            for prop_name, prop_schema in schema.get("properties", {}).items():
                properties.append(self._parse_property(
                    prop_name, prop_schema, prop_name in required_fields
                ))

            self.entities.append(EntityInfo(
                name=class_name,
                schema_name=schema_name,
                properties=properties,
                description=schema.get("description", ""),
            ))

    def generate(self) -> None:
        """Generate the client library and CLI."""
        self.parse()

        # Create output directories
        src_dir = self.output_dir / "src" / "waha"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "api").mkdir(exist_ok=True)
        (src_dir / "models").mkdir(exist_ok=True)
        (src_dir / "_cli").mkdir(exist_ok=True)

        # Generate files
        self._generate_client(src_dir)
        self._generate_models(src_dir / "models")
        self._generate_api(src_dir / "api")
        self._generate_wrapper(src_dir)
        self._generate_cli(src_dir / "_cli")
        self._generate_cli_entry(src_dir)
        self._generate_package_init(src_dir)

        print(f"Generated WAHA client in {self.output_dir}")

    def _generate_client(self, output_dir: Path) -> None:
        """Generate the client module."""
        template = self.env.get_template("client.py.jinja")
        content = template.render(
            endpoints=self.endpoints,
            models=self.models,
        )
        (output_dir / "client.py").write_text(content)

        # Generate types.py
        template = self.env.get_template("types.py.jinja")
        content = template.render()
        (output_dir / "types.py").write_text(content)

        # Generate errors.py
        template = self.env.get_template("errors.py.jinja")
        content = template.render()
        (output_dir / "errors.py").write_text(content)

    def _generate_models(self, output_dir: Path) -> None:
        """Generate model files."""
        # Generate each model
        template = self.env.get_template("model.py.jinja")
        for model in self.models:
            content = template.render(model=model, all_models=self.models, enums=self.enums)
            filename = f"{snake_case(model.name)}.py"
            (output_dir / filename).write_text(content)

        # Generate enums
        template = self.env.get_template("enum.py.jinja")
        for enum in self.enums:
            content = template.render(enum=enum)
            filename = f"{snake_case(enum.name)}.py"
            (output_dir / filename).write_text(content)

        # Generate __init__.py
        template = self.env.get_template("models_init.py.jinja")
        content = template.render(models=self.models, enums=self.enums)
        (output_dir / "__init__.py").write_text(content)

    def _generate_api(self, output_dir: Path) -> None:
        """Generate API endpoint modules."""
        template = self.env.get_template("api_module.py.jinja")

        for tag, endpoints in self.endpoints.items():
            content = template.render(
                tag=tag,
                endpoints=endpoints,
                models=self.models,
                enums=self.enums,
            )
            filename = f"{tag}.py"
            (output_dir / filename).write_text(content)

        # Generate __init__.py
        template = self.env.get_template("api_init.py.jinja")
        content = template.render(tags=list(self.endpoints.keys()))
        (output_dir / "__init__.py").write_text(content)

    def _generate_wrapper(self, output_dir: Path) -> None:
        """Generate the high-level OO wrapper."""
        # Create mapping from schema name to entity class name
        schema_to_entity = {e.schema_name: e.name for e in self.entities}

        template = self.env.get_template("wrapper.py.jinja")
        content = template.render(
            tags=list(self.endpoints.keys()),
            endpoints_by_tag=self.endpoints,
            entities=self.entities,
            schema_to_entity=schema_to_entity,
        )
        (output_dir / "wrapper.py").write_text(content)

    def _generate_cli(self, output_dir: Path) -> None:
        """Generate CLI modules."""
        # Main CLI entry point
        template = self.env.get_template("cli_main.py.jinja")
        content = template.render(tags=list(self.endpoints.keys()))
        (output_dir / "__init__.py").write_text(content)

        # Generate CLI module for each tag
        template = self.env.get_template("cli_module.py.jinja")
        for tag, endpoints in self.endpoints.items():
            content = template.render(
                tag=tag,
                endpoints=endpoints,
            )
            filename = f"{tag}.py"
            (output_dir / filename).write_text(content)

    def _generate_cli_entry(self, output_dir: Path) -> None:
        """Generate CLI entry point at package level."""
        content = '''"""WAHA CLI entry point.

Usage:
    waha --help
    waha sessions
    waha send <chat_id> <text>
"""

from waha._cli import app

__all__ = ["app"]

if __name__ == "__main__":
    app()
'''
        (output_dir / "cli.py").write_text(content)

    def _generate_package_init(self, output_dir: Path) -> None:
        """Generate package __init__.py."""
        template = self.env.get_template("package_init.py.jinja")
        content = template.render(
            tags=list(self.endpoints.keys()),
            models=self.models,
            enums=self.enums,
            entities=self.entities,
        )
        (output_dir / "__init__.py").write_text(content)


def main():
    """Main entry point for the generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate WAHA client from OpenAPI spec")
    parser.add_argument("spec", type=Path, help="Path to OpenAPI spec file")
    parser.add_argument("-o", "--output", type=Path, default=Path("."), help="Output directory")

    args = parser.parse_args()

    generator = WAHAGenerator(args.spec, args.output)
    generator.generate()


if __name__ == "__main__":
    main()
