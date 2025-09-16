from flask import Flask, Blueprint, render_template, request
import json
import xml.dom.minidom as minidom

app = Blueprint("json_to_xml", __name__, template_folder="templates")

def convert_json_to_xml(json_data, root_tag="root", namespace=None, element_order=None):
    xml_data = minidom.Document()
    root_element = xml_data.createElement(root_tag)
    if namespace:
        root_element.setAttribute("xmlns", namespace)
    xml_data.appendChild(root_element)

    vpn_site_element = xml_data.createElement("VPN_SITE")
    vpn_site_element.setAttribute("xmlns", "http://com.cisco/tbs/vpn/rfs/site")
    root_element.appendChild(vpn_site_element)

    _json_to_xml(json_data, vpn_site_element, element_order)
    return xml_data.toprettyxml(indent="  ")[23:]


def _json_to_xml(json_data, parent, element_order=None):
    if isinstance(json_data, dict):
        if element_order:
            sorted_keys = sorted(
                json_data,
                key=lambda k: element_order.index(k) if k in element_order else float('inf')
            )
        else:
            sorted_keys = json_data.keys()

        for tag_name in sorted_keys:
            value = json_data[tag_name]

            if isinstance(value, dict):
                element = parent.ownerDocument.createElement(tag_name)
                parent.appendChild(element)
                _json_to_xml(value, element, element_order)
            elif isinstance(value, list):
                for item in value:
                    element = parent.ownerDocument.createElement(tag_name)
                    parent.appendChild(element)
                    _json_to_xml(item, element, element_order)
            else:
                element = parent.ownerDocument.createElement(tag_name)
                element.appendChild(parent.ownerDocument.createTextNode(str(value)))
                parent.appendChild(element)

    elif isinstance(json_data, list):
        for item in json_data:
            _json_to_xml(item, parent, element_order)


@app.route("/", methods=["GET", "POST"])
def index():
    xml_output = ""
    json_input = ""
    if request.method == "POST":
        json_input = request.form["json_input"]
        try:
            json_data = json.loads(json_input)

            # Lista completa de element_order
            element_order = [
                "MPLS_VPN_SITE", "ADMINISTRATIVE_NUMBER_SITE", "SITE_TOPOLOGY",
                "MULTIVRF", "MANAGEMENT_ENTITY_SITE", "CUSTOMER_NAME", "CUST_SHORT_NAME",
                "PERFORMANCE_REPORTING", "SHARED_SERVICE_OPTIONS_MPLS", "OB_MANAGEMENT_NC_ID",
                "Technical_Functional_Unit", "TECHNICAL_FUNCTIONAL_UNIT_NC_ID", "VPN_REFERENCE",
                "VPN_Customer_Devices_And_Features", "NAT_OPTIONS", "CDF_BACKTOBACK",
                "Access_Security", "VTY_PASSWORD", "CONSOLE_PASSWORD", "Access", "MPLS_Access",
                "MPLS_ACCESS_NC_ID", "ASSOCIATED_LINK_MPLS", "Access_Features", "Routing",
                "ROUTING_ROLE", "ROUTING_TYPE", "Routing_BGP", "BGP_MAX_PREFIX", "HOLDTIME",
                "KEEPALIVE", "Routing_BGP_WAN", "AS_CE", "AS_OVERRIDE_SITE", "AS_PE",
                "ID_SITE_COMMUNITY", "BGP_MD5", "QoS_Profile", "BRONZE_DOWN_BANDWIDTH",
                "BRONZE_UP_BANDWIDTH", "GOLD_DOWN_BANDWIDTH", "GOLD_UP_BANDWIDTH",
                "PLATINUM_DOWN_BANDWIDTH", "PLATINUM_UP_BANDWIDTH", "SILVER_DOWN_BANDWIDTH",
                "SILVER_UP_BANDWIDTH", "VIDEO_DOWN_BANDWIDTH", "VIDEO_UP_BANDWIDTH",
                "VOICE_DOWN_BANDWIDTH", "VOICE_UP_BANDWIDTH", "TOTAL_DOWN_BANDWIDTH",
                "TOTAL_UP_BANDWIDTH", "IPP_DSCP", "VOICE_TOS", "VIDEO_TOS", "PLATINUM_TOS",
                "GOLD_TOS", "MGMT_TOS", "SILVER_TOS", "BRONZE_TOS", "PE_Endpoint", "Direct",
                "PE_VCConfig", "QINQ", "C_TAG_PE", "SUBINTERFACE_ID_PE", "PE_IP_Config",
                "IP_WAN_PE", "MASK_WAN_PE", "IP_MTU_PE", "Provider_Edge_Port", "INTERFACE_ID_PE",
                "IP_LOOPBACK_PE", "PE_ACCESS_OR_NNIL2", "Route_Aggregation", "ROUTE_AGGREGATION",
                "CE_Endpoint", "Physical", "CE_IP_Config", "IP_WAN_CE", "MPLS_Access_ServicePoint",
                "STATE_SITE_TFU_ACCESS", "Commercial_Functional_Unit", "Physical_Link",
                "MPLS_Link", "MPLS_LINK_NC_ID", "COUNTRY_LINK", "CITY_LINK", "LINK_TECHNOLOGY",
                "SHARED_LINK", "Link_Technology", "Fixed", "Ethernet_Link", "TBS_PE_ACCESS_MODE",
                "CONFIGURE_BFD", "JUMBOFRAMES"
            ]

            updated_json_data = {k: json_data[k] for k in element_order if k in json_data}

            xml_output = convert_json_to_xml(
                updated_json_data,
                root_tag="config",
                namespace="http://tail-f.com/ns/config/1.0",
                element_order=element_order
            )
        except Exception as e:
            xml_output = f"Error: {e}"

    return render_template("json_to_xml.html", json_input=json_input, xml_output=xml_output)


if __name__ == "__main__":
    app.run(debug=True)
