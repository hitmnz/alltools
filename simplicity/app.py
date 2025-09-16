from flask import Flask, Blueprint, render_template, request, jsonify
from jinja2 import Environment, BaseLoader, meta, StrictUndefined, TemplateSyntaxError, nodes
import re

app = Blueprint("simplicity", __name__, template_folder="templates")

@app.route("/")
def index():
    return render_template("simplicity.html")

def extract_variables_with_order_and_conditions(parsed_content):
    condition_vars = []
    normal_vars = []
    conditional_vars = []
    if_blocks = []

    def recurse(node, inside_if=False):
        nonlocal condition_vars, normal_vars, conditional_vars, if_blocks

        if isinstance(node, list):
            for n in node:
                recurse(n, inside_if)
        elif isinstance(node, nodes.Output):
            for child in node.nodes:
                if isinstance(child, nodes.Name):
                    if inside_if:
                        if child.name not in conditional_vars:
                            conditional_vars.append(child.name)
                    else:
                        if child.name not in normal_vars:
                            normal_vars.append(child.name)
        elif isinstance(node, nodes.Name):
            if inside_if:
                if node.name not in conditional_vars:
                    conditional_vars.append(node.name)
            else:
                if node.name not in normal_vars:
                    normal_vars.append(node.name)
        elif isinstance(node, nodes.If):
            cond_names = [n.name for n in node.test.find_all(nodes.Name)]
            for name in cond_names:
                if name not in condition_vars:
                    condition_vars.append(name)
            if_blocks.append((cond_names, node))
            recurse(node.body, inside_if=True)
            if node.else_:
                recurse(node.else_, inside_if=True)
        elif hasattr(node, 'nodes'):
            recurse(node.nodes, inside_if)
        elif hasattr(node, 'body'):
            recurse(node.body, inside_if)
        elif hasattr(node, 'value'):
            recurse(node.value, inside_if)

    recurse(parsed_content.body)

    seen = set()
    all_vars = []
    for lst in [normal_vars, condition_vars]:
        for v in lst:
            if v not in seen:
                seen.add(v)
                all_vars.append(v)

    return all_vars, condition_vars, conditional_vars, if_blocks

@app.route("/variables", methods=["POST"])
def extract_variables():
    data = request.get_json()
    template_str = data.get("template", "")

    try:
        env = Environment(loader=BaseLoader())
        parsed_content = env.parse(template_str)
        all_vars, condition_vars, conditional_vars, if_blocks = extract_variables_with_order_and_conditions(parsed_content)

        # Asegúrate de incluir las variables dentro de los bloques if en la respuesta
        final_vars = all_vars + conditional_vars

        # Devolver las variables extraídas, junto con los bloques 'if' que contienen condiciones
        return jsonify({
            "variables": final_vars,
            "if_blocks": [(block[0], str(block[1].test)) for block in if_blocks]
        })
    except TemplateSyntaxError as e:
        return jsonify({"error": str(e), "variables": []}), 400

@app.route("/render", methods=["POST"])
def render_template_endpoint():
    data = request.get_json()
    template_str = data.get("template", "")
    groups = data.get("groups", [])

    results = []

    try:
        env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
        template_str = template_str.replace("\\", "\\\\")
        template = env.from_string(template_str)

        for group in groups:
            try:
                result = template.render(group)
                # Normalizar múltiples saltos de línea a uno solo
                result = re.sub(r'\n\s*\n+', '\n\n', result.strip())
                results.append(result)
            except Exception as e:
                results.append(f"[Error al renderizar: {e}]")
    except TemplateSyntaxError as e:
        results = [f"[Error de sintaxis en plantilla: {e}]"]

    return jsonify({"results": results})
