from flask import Flask, render_template
from config_parser.app import app as config_parser_blueprint
from json_to_xml.app import app as json_to_xml_blueprint
from qos.app import app as qos_blueprint
from simplicity.app import app as simplicity_blueprint

app = Flask(__name__)

# Registrar cada mini-app
app.register_blueprint(config_parser_blueprint, url_prefix="/config_parser")
app.register_blueprint(json_to_xml_blueprint, url_prefix="/json_to_xml")
app.register_blueprint(qos_blueprint, url_prefix="/qos")
app.register_blueprint(simplicity_blueprint, url_prefix="/simplicity")

@app.route("/")
def index():
    return render_template("index.html")  # página principal

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)