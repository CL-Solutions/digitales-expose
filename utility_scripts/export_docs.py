#!/usr/bin/env python3
"""
API Documentation Export Script
Enterprise Multi-Tenant System

This script exports API documentation in various formats from your FastAPI application.

Usage:
    python export_docs.py --format openapi --output api-spec.json
    python export_docs.py --format html --output docs.html
    python export_docs.py --format pdf --output api-docs.pdf
    python export_docs.py --format markdown --output api-docs.md
"""

import json
import sys
import argparse
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIDocumentationExporter:
    """Export API documentation in various formats"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        
    def get_openapi_spec(self) -> Dict[str, Any]:
        """Fetch OpenAPI specification from the running API"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch OpenAPI spec: {e}")
            raise
    
    def export_openapi_json(self, output_path: str) -> None:
        """Export OpenAPI spec as JSON"""
        logger.info("Exporting OpenAPI specification as JSON...")
        
        spec = self.get_openapi_spec()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OpenAPI spec exported to: {output_path}")
    
    def export_openapi_yaml(self, output_path: str) -> None:
        """Export OpenAPI spec as YAML"""
        try:
            import yaml
        except ImportError:
            logger.error("PyYAML is required for YAML export. Install with: pip install PyYAML")
            return
        
        logger.info("Exporting OpenAPI specification as YAML...")
        
        spec = self.get_openapi_spec()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"OpenAPI spec exported to: {output_path}")
    
    def export_html_docs(self, output_path: str, template: str = "swagger") -> None:
        """Export documentation as HTML"""
        logger.info(f"Exporting HTML documentation using {template} template...")
        
        spec = self.get_openapi_spec()
        
        if template == "swagger":
            html_content = self._generate_swagger_html(spec)
        elif template == "redoc":
            html_content = self._generate_redoc_html(spec)
        else:
            raise ValueError(f"Unsupported template: {template}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML documentation exported to: {output_path}")
    
    def _generate_swagger_html(self, spec: Dict[str, Any]) -> str:
        """Generate Swagger UI HTML"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{spec.get('info', {}).get('title', 'API Documentation')}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin:0; background: #fafafa; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {json.dumps(spec)},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                tryItOutEnabled: true,
                filter: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch']
            }});
        }};
    </script>
</body>
</html>"""
    
    def _generate_redoc_html(self, spec: Dict[str, Any]) -> str:
        """Generate ReDoc HTML"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{spec.get('info', {}).get('title', 'API Documentation')}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='data:application/json,{json.dumps(spec).replace("'", "%27")}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>"""
    
    def export_markdown_docs(self, output_path: str) -> None:
        """Export documentation as Markdown"""
        logger.info("Exporting documentation as Markdown...")
        
        spec = self.get_openapi_spec()
        markdown_content = self._generate_markdown(spec)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown documentation exported to: {output_path}")
    
    def _resolve_schema_ref(self, spec: Dict[str, Any], schema_ref: str) -> Dict[str, Any]:
        """Resolve a schema reference to its actual definition"""
        try:
            # Remove '#/' prefix and split path
            ref_path = schema_ref.replace('#/', '').split('/')
            
            # Navigate to the schema definition
            schema_def = spec
            for path_part in ref_path:
                schema_def = schema_def.get(path_part, {})
            
            return schema_def
        except:
            return {}
    
    def _generate_markdown_schema(self, spec: Dict[str, Any], schema: Dict[str, Any], indent: int = 0) -> List[str]:
        """Generate markdown documentation for a schema"""
        lines = []
        indent_str = "  " * indent
        
        if '$ref' in schema:
            # Resolve schema reference
            schema_def = self._resolve_schema_ref(spec, schema['$ref'])
            if schema_def:
                return self._generate_markdown_schema(spec, schema_def, indent)
            else:
                schema_name = schema['$ref'].split('/')[-1]
                lines.append(f"{indent_str}**Schema:** `{schema_name}`")
                return lines
        
        schema_type = schema.get('type', 'object')
        lines.append(f"{indent_str}**Type:** `{schema_type}`")
        
        if schema_type == 'object':
            properties = schema.get('properties', {})
            required_fields = schema.get('required', [])
            
            if properties:
                lines.append(f"{indent_str}**Properties:**")
                
                for prop_name, prop_info in properties.items():
                    # Handle nested schema references
                    if '$ref' in prop_info:
                        prop_schema = self._resolve_schema_ref(spec, prop_info['$ref'])
                        prop_type = prop_schema.get('type', 'object')
                    else:
                        prop_type = prop_info.get('type', 'unknown')
                    
                    prop_desc = prop_info.get('description', '')
                    required_mark = " *(required)*" if prop_name in required_fields else ""
                    
                    # Handle enum values
                    enum_values = prop_info.get('enum')
                    enum_text = f" (options: {', '.join(map(str, enum_values))})" if enum_values else ""
                    
                    # Handle format
                    prop_format = prop_info.get('format', '')
                    format_text = f" (format: {prop_format})" if prop_format else ""
                    
                    # Handle min/max values
                    constraints = []
                    if prop_info.get('minimum') is not None:
                        constraints.append(f"min: {prop_info['minimum']}")
                    if prop_info.get('maximum') is not None:
                        constraints.append(f"max: {prop_info['maximum']}")
                    if prop_info.get('minLength') is not None:
                        constraints.append(f"minLength: {prop_info['minLength']}")
                    if prop_info.get('maxLength') is not None:
                        constraints.append(f"maxLength: {prop_info['maxLength']}")
                    
                    constraints_text = f" ({', '.join(constraints)})" if constraints else ""
                    
                    lines.append(f"{indent_str}  - `{prop_name}` ({prop_type}){format_text}{enum_text}{constraints_text}{required_mark}: {prop_desc}")
                    
                    # Handle nested objects
                    if prop_type == 'object' and '$ref' not in prop_info:
                        nested_lines = self._generate_markdown_schema(spec, prop_info, indent + 2)
                        lines.extend(nested_lines)
                    
                    # Handle arrays
                    elif prop_type == 'array':
                        items_schema = prop_info.get('items', {})
                        if items_schema:
                            lines.append(f"{indent_str}    **Array items:**")
                            nested_lines = self._generate_markdown_schema(spec, items_schema, indent + 3)
                            lines.extend(nested_lines)
        
        elif schema_type == 'array':
            items_schema = schema.get('items', {})
            if items_schema:
                lines.append(f"{indent_str}**Array items:**")
                nested_lines = self._generate_markdown_schema(spec, items_schema, indent + 1)
                lines.extend(nested_lines)
        
        return lines
        """Generate Markdown documentation"""
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        components = spec.get('components', {})
        
        md_content = []
        
        # Title and description
        md_content.append(f"# {info.get('title', 'API Documentation')}")
        md_content.append("")
        if info.get('description'):
            md_content.append(info['description'])
            md_content.append("")
        
        # Version and contact info
        if info.get('version'):
            md_content.append(f"**Version:** {info['version']}")
            md_content.append("")
        
        # Base URL
        servers = spec.get('servers', [])
        if servers:
            md_content.append("## Base URLs")
            for server in servers:
                md_content.append(f"- {server.get('url', '')}")
                if server.get('description'):
                    md_content.append(f"  - {server['description']}")
            md_content.append("")
        
        # Authentication
        security_schemes = components.get('securitySchemes', {})
        if security_schemes:
            md_content.append("## Authentication")
            for scheme_name, scheme in security_schemes.items():
                md_content.append(f"### {scheme_name}")
                md_content.append(f"- **Type:** {scheme.get('type', '')}")
                if scheme.get('scheme'):
                    md_content.append(f"- **Scheme:** {scheme['scheme']}")
                if scheme.get('description'):
                    md_content.append(f"- **Description:** {scheme['description']}")
                md_content.append("")
        
        # Endpoints
        md_content.append("## Endpoints")
        md_content.append("")
        
        # Group by tags
        tags_dict = {}
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    tags = operation.get('tags', ['Default'])
                    for tag in tags:
                        if tag not in tags_dict:
                            tags_dict[tag] = []
                        tags_dict[tag].append({
                            'path': path,
                            'method': method.upper(),
                            'operation': operation
                        })
        
        # Generate documentation for each tag
        for tag, endpoints in tags_dict.items():
            md_content.append(f"### {tag}")
            md_content.append("")
            
            for endpoint in endpoints:
                path = endpoint['path']
                method = endpoint['method']
                operation = endpoint['operation']
                
                # Endpoint title
                summary = operation.get('summary', f"{method} {path}")
                md_content.append(f"#### {summary}")
                md_content.append("")
                
                # Method and path
                md_content.append(f"**{method}** `{path}`")
                md_content.append("")
                
                # Description
                if operation.get('description'):
                    md_content.append(operation['description'])
                    md_content.append("")
                
                # Parameters
                parameters = operation.get('parameters', [])
                if parameters:
                    md_content.append("**Parameters:**")
                    md_content.append("")
                    for param in parameters:
                        param_name = param.get('name', '')
                        param_in = param.get('in', '')
                        param_required = " (required)" if param.get('required') else ""
                        param_desc = param.get('description', '')
                        md_content.append(f"- `{param_name}` ({param_in}){param_required}: {param_desc}")
                    md_content.append("")
                
    def _generate_markdown(self, spec: Dict[str, Any]) -> str:
        """Generate Markdown documentation"""
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        components = spec.get('components', {})
        
        md_content = []
        
        # Title and description
        md_content.append(f"# {info.get('title', 'API Documentation')}")
        md_content.append("")
        if info.get('description'):
            md_content.append(info['description'])
            md_content.append("")
        
        # Version and contact info
        if info.get('version'):
            md_content.append(f"**Version:** {info['version']}")
            md_content.append("")
        
        # Base URL
        servers = spec.get('servers', [])
        if servers:
            md_content.append("## Base URLs")
            for server in servers:
                md_content.append(f"- {server.get('url', '')}")
                if server.get('description'):
                    md_content.append(f"  - {server['description']}")
            md_content.append("")
        
        # Authentication
        security_schemes = components.get('securitySchemes', {})
        if security_schemes:
            md_content.append("## Authentication")
            for scheme_name, scheme in security_schemes.items():
                md_content.append(f"### {scheme_name}")
                md_content.append(f"- **Type:** {scheme.get('type', '')}")
                if scheme.get('scheme'):
                    md_content.append(f"- **Scheme:** {scheme['scheme']}")
                if scheme.get('description'):
                    md_content.append(f"- **Description:** {scheme['description']}")
                md_content.append("")
        
        # Endpoints
        md_content.append("## Endpoints")
        md_content.append("")
        
        # Group by tags
        tags_dict = {}
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    tags = operation.get('tags', ['Default'])
                    for tag in tags:
                        if tag not in tags_dict:
                            tags_dict[tag] = []
                        tags_dict[tag].append({
                            'path': path,
                            'method': method.upper(),
                            'operation': operation
                        })
        
        # Generate documentation for each tag
        for tag, endpoints in tags_dict.items():
            md_content.append(f"### {tag}")
            md_content.append("")
            
            for endpoint in endpoints:
                path = endpoint['path']
                method = endpoint['method']
                operation = endpoint['operation']
                
                # Endpoint title
                summary = operation.get('summary', f"{method} {path}")
                md_content.append(f"#### {summary}")
                md_content.append("")
                
                # Method and path
                md_content.append(f"**{method}** `{path}`")
                md_content.append("")
                
                # Description
                if operation.get('description'):
                    md_content.append(operation['description'])
                    md_content.append("")
                
                # Parameters
                parameters = operation.get('parameters', [])
                if parameters:
                    md_content.append("**Parameters:**")
                    md_content.append("")
                    for param in parameters:
                        param_name = param.get('name', '')
                        param_in = param.get('in', '')
                        param_required = " *(required)*" if param.get('required') else ""
                        param_desc = param.get('description', '')
                        
                        # Get parameter schema/type
                        param_schema = param.get('schema', {})
                        param_type = param_schema.get('type', 'string')
                        param_format = param_schema.get('format', '')
                        format_text = f" (format: {param_format})" if param_format else ""
                        
                        # Handle enum values in parameters
                        enum_values = param_schema.get('enum')
                        enum_text = f" (options: {', '.join(map(str, enum_values))})" if enum_values else ""
                        
                        md_content.append(f"- `{param_name}` ({param_in}) `{param_type}`{format_text}{enum_text}{param_required}: {param_desc}")
                    md_content.append("")
                
                # Request body
                request_body = operation.get('requestBody')
                if request_body:
                    md_content.append("**Request Body:**")
                    md_content.append("")
                    if request_body.get('description'):
                        md_content.append(request_body['description'])
                        md_content.append("")
                    
                    # Handle different content types
                    content = request_body.get('content', {})
                    for content_type, content_info in content.items():
                        md_content.append(f"**Content-Type:** `{content_type}`")
                        md_content.append("")
                        
                        # Schema information
                        schema = content_info.get('schema', {})
                        if schema:
                            # Use the enhanced schema documentation
                            schema_lines = self._generate_markdown_schema(spec, schema)
                            md_content.extend(schema_lines)
                            md_content.append("")
                        
                        # Example
                        example = content_info.get('example')
                        if example:
                            md_content.append("**Example:**")
                            md_content.append("```json")
                            md_content.append(json.dumps(example, indent=2))
                            md_content.append("```")
                            md_content.append("")
                        elif content_info.get('examples'):
                            examples = content_info['examples']
                            for example_name, example_info in examples.items():
                                md_content.append(f"**Example ({example_name}):**")
                                if example_info.get('description'):
                                    md_content.append(example_info['description'])
                                if example_info.get('value'):
                                    md_content.append("```json")
                                    md_content.append(json.dumps(example_info['value'], indent=2))
                                    md_content.append("```")
                                md_content.append("")
                        else:
                            # Generate example from schema if no explicit example
                            if schema:
                                generated_example = self._generate_example_from_schema(schema, spec)
                                if generated_example is not None:
                                    md_content.append("**Generated Example:**")
                                    md_content.append("```json")
                                    md_content.append(json.dumps(generated_example, indent=2))
                                    md_content.append("```")
                                    md_content.append("")
                
                # Responses
                responses = operation.get('responses', {})
                if responses:
                    md_content.append("**Responses:**")
                    md_content.append("")
                    for status_code, response in responses.items():
                        desc = response.get('description', '')
                        md_content.append(f"**{status_code}** - {desc}")
                        
                        # Response content/schema
                        response_content = response.get('content', {})
                        if response_content:
                            for content_type, content_info in response_content.items():
                                md_content.append(f"  - Content-Type: `{content_type}`")
                                
                                schema = content_info.get('schema', {})
                                if schema:
                                    if '$ref' in schema:
                                        schema_ref = schema['$ref'].split('/')[-1]
                                        md_content.append(f"  - Schema: `{schema_ref}`")
                                        
                                        # Try to resolve and show some properties
                                        resolved_schema = self._resolve_schema_ref(spec, schema['$ref'])
                                        if resolved_schema and resolved_schema.get('properties'):
                                            md_content.append("  - Key Properties:")
                                            properties = resolved_schema.get('properties', {})
                                            required = resolved_schema.get('required', [])
                                            
                                            # Show first 5 properties to avoid overwhelming
                                            for i, (prop_name, prop_info) in enumerate(list(properties.items())[:5]):
                                                prop_type = prop_info.get('type', 'unknown')
                                                required_mark = " *(required)*" if prop_name in required else ""
                                                prop_desc = prop_info.get('description', '')
                                                md_content.append(f"    - `{prop_name}` ({prop_type}){required_mark}: {prop_desc}")
                                            
                                            if len(properties) > 5:
                                                md_content.append(f"    - ... and {len(properties) - 5} more properties")
                                    else:
                                        schema_type = schema.get('type', 'object')
                                        md_content.append(f"  - Type: `{schema_type}`")
                                
                                # Response example
                                example = content_info.get('example')
                                if example:
                                    md_content.append("  - Example:")
                                    md_content.append("    ```json")
                                    example_json = json.dumps(example, indent=4)
                                    # Indent the JSON for proper markdown formatting
                                    indented_json = '\n'.join('    ' + line for line in example_json.split('\n'))
                                    md_content.append(indented_json)
                                    md_content.append("    ```")
                        
                        md_content.append("")
                
                md_content.append("---")
                md_content.append("")
        
        return "\n".join(md_content)
    
    def export_pdf_docs(self, output_path: str) -> None:
        """Export documentation as PDF (requires wkhtmltopdf)"""
        logger.info("Exporting documentation as PDF...")
        
        try:
            # First generate HTML
            html_path = output_path.replace('.pdf', '_temp.html')
            self.export_html_docs(html_path, template="redoc")
            
            # Convert HTML to PDF using wkhtmltopdf
            cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--margin-top', '0.75in',
                '--margin-right', '0.75in',
                '--margin-bottom', '0.75in',
                '--margin-left', '0.75in',
                '--encoding', 'UTF-8',
                '--no-stop-slow-scripts',
                '--javascript-delay', '5000',
                html_path,
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"PDF documentation exported to: {output_path}")
                # Clean up temporary HTML file
                Path(html_path).unlink()
            else:
                logger.error(f"Failed to generate PDF: {result.stderr}")
                logger.info("Make sure wkhtmltopdf is installed: https://wkhtmltopdf.org/downloads.html")
                
        except FileNotFoundError:
            logger.error("wkhtmltopdf not found. Please install it from: https://wkhtmltopdf.org/downloads.html")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
    
    def export_postman_collection(self, output_path: str) -> None:
        """Export Postman collection"""
        logger.info("Exporting Postman collection...")
        
        spec = self.get_openapi_spec()
        collection = self._convert_to_postman(spec)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Postman collection exported to: {output_path}")
    
    def _convert_to_postman(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAPI spec to Postman collection format"""
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        servers = spec.get('servers', [])
        
        base_url = servers[0].get('url', 'http://localhost:8000') if servers else 'http://localhost:8000'
        
        collection = {
            "info": {
                "name": info.get('title', 'API Documentation'),
                "description": info.get('description', ''),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "variable": [
                {
                    "key": "baseUrl",
                    "value": base_url,
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # Group by tags
        folders = {}
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    tags = operation.get('tags', ['Default'])
                    folder_name = tags[0] if tags else 'Default'
                    
                    if folder_name not in folders:
                        folders[folder_name] = {
                            "name": folder_name,
                            "item": []
                        }
                    
                    # Create request
                    request_item = {
                        "name": operation.get('summary', f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": f"{{{{baseUrl}}}}{path}",
                                "host": ["{{baseUrl}}"],
                                "path": path.strip('/').split('/')
                            }
                        }
                    }
                    
                    # Add authentication if required
                    if operation.get('security'):
                        request_item["request"]["auth"] = {
                            "type": "bearer",
                            "bearer": [
                                {
                                    "key": "token",
                                    "value": "{{authToken}}",
                                    "type": "string"
                                }
                            ]
                        }
                    
                    # Add request body for POST/PUT requests
                    request_body = operation.get('requestBody')
                    if request_body and method.upper() in ['POST', 'PUT', 'PATCH']:
                        content = request_body.get('content', {})
                        
                        # Try to get JSON content first
                        json_content = content.get('application/json')
                        if json_content:
                            schema = json_content.get('schema', {})
                            example = json_content.get('example')
                            
                            if example:
                                # Use provided example
                                request_item["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": json.dumps(example, indent=2),
                                    "options": {
                                        "raw": {
                                            "language": "json"
                                        }
                                    }
                                }
                            elif schema:
                                # Generate example from schema
                                example_body = self._generate_example_from_schema(schema, spec)
                                request_item["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": json.dumps(example_body, indent=2),
                                    "options": {
                                        "raw": {
                                            "language": "json"
                                        }
                                    }
                                }
                            else:
                                # Fallback empty JSON
                                request_item["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": "{\n  \n}",
                                    "options": {
                                        "raw": {
                                            "language": "json"
                                        }
                                    }
                                }
                        
                        # Handle form data
                        elif content.get('application/x-www-form-urlencoded'):
                            request_item["request"]["body"] = {
                                "mode": "urlencoded",
                                "urlencoded": []
                            }
                        
                        # Handle multipart form data
                        elif content.get('multipart/form-data'):
                            request_item["request"]["body"] = {
                                "mode": "formdata",
                                "formdata": []
                            }
                    
                    folders[folder_name]["item"].append(request_item)
        
        collection["item"] = list(folders.values())
        return collection
    
    def _generate_example_from_schema(self, schema: Dict[str, Any], spec: Dict[str, Any] = None) -> Any:
        """Generate example data from JSON schema"""
        # Handle schema references
        if '$ref' in schema and spec:
            resolved_schema = self._resolve_schema_ref(spec, schema['$ref'])
            if resolved_schema:
                return self._generate_example_from_schema(resolved_schema, spec)
        
        schema_type = schema.get('type', 'object')
        
        if schema_type == 'object':
            example = {}
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            for prop_name, prop_schema in properties.items():
                # Always include required fields, optionally include others
                if prop_name in required or len(properties) <= 5:  # Include all if few properties
                    example[prop_name] = self._generate_example_from_schema(prop_schema, spec)
            
            return example
        
        elif schema_type == 'array':
            items_schema = schema.get('items', {})
            return [self._generate_example_from_schema(items_schema, spec)]
        
        elif schema_type == 'string':
            enum_values = schema.get('enum')
            if enum_values:
                return enum_values[0]
            
            format_type = schema.get('format', '')
            if format_type == 'email':
                return "user@example.com"
            elif format_type == 'date':
                return "2024-01-01"
            elif format_type == 'date-time':
                return "2024-01-01T12:00:00Z"
            elif format_type == 'uuid':
                return "550e8400-e29b-41d4-a716-446655440000"
            elif format_type == 'password':
                return "••••••••"
            else:
                return "string"
        
        elif schema_type == 'integer':
            minimum = schema.get('minimum', 0)
            maximum = schema.get('maximum', 100)
            return minimum if minimum is not None else 0
        
        elif schema_type == 'number':
            minimum = schema.get('minimum', 0.0)
            maximum = schema.get('maximum', 100.0)
            return minimum if minimum is not None else 0.0
        
        elif schema_type == 'boolean':
            return True
        
        else:
            return None


def main():
    parser = argparse.ArgumentParser(description="Export API documentation in various formats")
    parser.add_argument(
        '--format', 
        choices=['openapi', 'openapi-yaml', 'html', 'html-redoc', 'markdown', 'pdf', 'postman'],
        required=True,
        help="Output format"
    )
    parser.add_argument(
        '--output', 
        required=True,
        help="Output file path"
    )
    parser.add_argument(
        '--base-url',
        default="http://localhost:8000",
        help="Base URL of the running API (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    exporter = APIDocumentationExporter(args.base_url)
    
    try:
        if args.format == 'openapi':
            exporter.export_openapi_json(args.output)
        elif args.format == 'openapi-yaml':
            exporter.export_openapi_yaml(args.output)
        elif args.format == 'html':
            exporter.export_html_docs(args.output, template="swagger")
        elif args.format == 'html-redoc':
            exporter.export_html_docs(args.output, template="redoc")
        elif args.format == 'markdown':
            exporter.export_markdown_docs(args.output)
        elif args.format == 'pdf':
            exporter.export_pdf_docs(args.output)
        elif args.format == 'postman':
            exporter.export_postman_collection(args.output)
        
        logger.info("Export completed successfully!")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()