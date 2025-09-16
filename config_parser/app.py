from flask import Flask, Blueprint, render_template, request, jsonify, send_file
import csv
import io
import re
from .parse_configuration_cisco import parse_cisco_config
from .parse_configuration_juniper import parse_juniper_config

app = Blueprint("config_parser", __name__, template_folder="templates")

def detect_vendor(config_text):
    if re.search(r'(GigabitEthernet|TenGigE|HundredGigE|Bundle-Ether)', config_text, re.IGNORECASE):
        return "Cisco"
    elif re.search(r'(ge-|xe-|et-|ae\d+)', config_text, re.IGNORECASE):
        return "Juniper"
    return "Desconocido"

@app.route('/')
def index():
    return render_template('config_parser.html')

@app.route('/parse', methods=['POST'])
def parse():
    config_text = request.form['config']
    vendor = detect_vendor(config_text)

    if vendor == "Cisco":
        variables, fieldnames = parse_cisco_config(config_text)
    elif vendor == "Juniper":
        variables, fieldnames = parse_juniper_config(config_text)
    else:
        return jsonify({"error": "No se pudo detectar el tipo de equipo"}), 400

    return jsonify({"vendor": vendor, "variables": variables, "fieldnames": fieldnames})

@app.route('/download_csv', methods=['POST'])
def download_csv():
    data = request.json
    fieldnames = data['fieldnames']
    variables = data['variables']

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerow(variables)

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)

    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name="variables.csv")

if __name__ == "__main__":
    app.run(debug=True)
