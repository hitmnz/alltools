from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from jinja2 import Environment, BaseLoader, StrictUndefined, TemplateSyntaxError
import re

app = Blueprint("qos", __name__, template_folder="templates")

def restar_en_cascada(adjusted_values, diff, order, bronze_min):
    values = {n: int(v) for n, v in adjusted_values}
    remaining = int(diff)
    for cname in order:
        if remaining <= 0:
            break
        cur = values.get(cname, 0)
        if cname == "Data-Bronze":
            max_reducible = max(cur - bronze_min, 0)
        else:
            max_reducible = cur
        take = min(max_reducible, remaining)
        values[cname] = cur - take
        remaining -= take
    return [(c, int(values.get(c, 0))) for c in order]

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    status = None
    form = request.form
    defaults = {k: form.get(k, "") for k in [
        "total_download", "voice_download", "video_download", "data_platinum_download",
        "data_gold_download", "data_silver_download", "data_bronze_download",
        "gestion", "tipo_acceso"
    ]}

    if request.method == "POST":
        if "clear" in form:
            return redirect(url_for("index"))
        try:
            voice = float(form.get("voice_download", 0) or 0)
            video = float(form.get("video_download", 0) or 0)
            platinum = float(form.get("data_platinum_download", 0) or 0)
            gold = float(form.get("data_gold_download", 0) or 0)
            silver = float(form.get("data_silver_download", 0) or 0)
            bronze = float(form.get("data_bronze_download", 0) or 0)
            total = float(form.get("total_download", 0) or 0)
            if total == 0:
                total = voice + video + platinum + gold + silver + bronze

            gestion = form.get("gestion")
            tipo_acceso = form.get("tipo_acceso")

            raw = [
                ("Voice", voice),
                ("Video", video),
                ("Data-Platinum", platinum),
                ("Data-Gold", gold),
                ("Data-Silver", silver),
                ("Data-Bronze", bronze)
            ]

            CLASSES_ORDER = ["Data-Bronze", "Data-Silver", "Data-Gold", "Data-Platinum", "Video", "Voice"]

            adjusted_values = [(name, int(max(0, round(kbps)))) for name, kbps in raw]

            if gestion == "gestionado":
                if tipo_acceso == "indirecto":
                    management_kbps = 16
                    bronze_min = 80
                else:
                    management_kbps = 64
                    bronze_min = 128
            elif gestion == "no_gestionado":
                management_kbps = 64
                bronze_min = 128
            else:
                management_kbps = 64
                bronze_min = 64

            # Restar management primero en Bronze y cascada si sobra
            bronze_actual = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
            max_reducible_bronze = max(bronze_actual - bronze_min, 0)
            if management_kbps <= max_reducible_bronze:
                adjusted_values = [(n, v - management_kbps if n == "Data-Bronze" else v) for n, v in adjusted_values]
            else:
                # Restar lo máximo en Bronze y el resto en cascada
                restante_management = management_kbps - max_reducible_bronze
                temp_values = [(n, v - max_reducible_bronze if n == "Data-Bronze" else v) for n, v in adjusted_values]
                adjusted_values = restar_en_cascada(temp_values, restante_management, CLASSES_ORDER, bronze_min)

            # Ajuste para que suma clases + management == total (sin granularidad)
            suma_valores = sum(v for _, v in adjusted_values)
            total_esperado = int(total) - management_kbps
            diff = suma_valores - total_esperado
            if diff > 0:
                adjusted_values = restar_en_cascada(adjusted_values, diff, CLASSES_ORDER, bronze_min)

            def calc_perc(val):
                return int(round((val / total * 100) if total else 0))

            # Construcción datos para template
            suma_clases = sum(v for _, v in adjusted_values) + management_kbps
            classes = []
            for name, adj in adjusted_values:
                percent = calc_perc(adj)
                classes.append({
                    "name": name,
                    "kbps": int(adj),
                    "percent": percent,
                    "burst_size": round(adj * 0.1875 * 1000),
                    "peak_burst": round(adj * 0.375 * 1000)
                })

            classes.append({
                "name": "Management",
                "kbps": int(management_kbps),
                "percent": calc_perc(management_kbps),
                "burst_size": round(management_kbps * 0.1875 * 1000),
                "peak_burst": round(management_kbps * 0.375 * 1000)
            })

            bronze_final = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
            if gestion == "gestionado" and tipo_acceso == "indirecto" and bronze_final < 80:
                status = "error: Bronze en indirecto gestionado debe ser >= 80 Kbps"
            elif gestion == "gestionado" and tipo_acceso != "indirecto" and bronze_final < 128:
                status = "error: Bronze en directo gestionado debe ser >= 128 Kbps"
            elif gestion == "no_gestionado" and bronze_final < 128:
                status = "error: Bronze en no gestionado debe ser >= 128 Kbps"
            elif (not gestion or gestion == "") and bronze_final < 64:
                status = "error: Bronze en estándar debe ser >= 64 Kbps"

            total_burst = round(total * 0.1875 * 1000)
            total_peak = round(total * 0.375 * 1000)

            # Cálculo de 4 colas (Calculadora QoS_4 colas)
            voice_adj = next((v for n, v in adjusted_values if n == "Voice"), 0)
            video_adj = next((v for n, v in adjusted_values if n == "Video"), 0)
            platinum_adj = next((v for n, v in adjusted_values if n == "Data-Platinum"), 0)
            gold_adj = next((v for n, v in adjusted_values if n == "Data-Gold"), 0)
            silver_adj = next((v for n, v in adjusted_values if n == "Data-Silver"), 0)
            bronze_adj = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
            manage_adj = int(management_kbps)

            ef_kbps = int(voice_adj)
            nc_kbps = int(manage_adj + video_adj)
            af_kbps = int(platinum_adj + gold_adj)
            be_kbps = int(silver_adj + bronze_adj)

            def clean_num(v):
                if isinstance(v, float) and v.is_integer():
                    return int(v)
                return v

            qos_4_colas = [
                {
                    "name": "TOTAL",
                    "description": "Capacidad Total",
                    "kbps": int(total),
                    "percent": 100,
                    "burst_size": total_burst,
                    "peak_burst": total_peak
                },
                {
                    "name": "clase_ef",
                    "description": "Voz",
                    "kbps": ef_kbps,
                    "percent": calc_perc(ef_kbps),
                    "burst_size": round(ef_kbps * 0.1875 * 1000),
                    "peak_burst": round(ef_kbps * 0.375 * 1000)
                },
                {
                    "name": "clase_nc",
                    "description": "Management + Video",
                    "kbps": nc_kbps,
                    "percent": calc_perc(nc_kbps),
                    "burst_size": round(nc_kbps * 0.1875 * 1000),
                    "peak_burst": round(nc_kbps * 0.375 * 1000)
                },
                {
                    "name": "clase_af",
                    "description": "Platinum + Gold",
                    "kbps": af_kbps,
                    "percent": calc_perc(af_kbps),
                    "burst_size": round(af_kbps * 0.1875 * 1000),
                    "peak_burst": round(af_kbps * 0.375 * 1000)
                },
                {
                    "name": "clase_be",
                    "description": "Silver + Bronze",
                    "kbps": be_kbps,
                    "percent": calc_perc(be_kbps),
                    "burst_size": round(be_kbps * 0.1875 * 1000),
                    "peak_burst": round(be_kbps * 0.375 * 1000)
                }
            ]

            # Construcción de variables para Plantilla Jinja
            jinja_vars = {
                # bps (bits por segundo)
                "TOTAL_DOWN_BANDWIDTH_B": int(total * 1000),
                "TOTAL_BURST": int(total_burst),
                "TOTAL_PEAK": int(total_peak),
                "VOICE_DOWN_BANDWIDTH_B": int(voice_adj * 1000),
                "VIDEO_DOWN_BANDWIDTH_B": int(video_adj * 1000),
                "PLATINUM_DOWN_BANDWIDTH_B": int(platinum_adj * 1000),
                "GOLD_DOWN_BANDWIDTH_B": int(gold_adj * 1000),
                "SILVER_DOWN_BANDWIDTH_B": int(silver_adj * 1000),
                "BRONZE_DOWN_BANDWIDTH_B": int(bronze_adj * 1000),
                "MANAGE_BANDWIDTH_B": int(manage_adj * 1000),
                "MANAGEMENT_DOWN_BANDWIDTH_B": int(manage_adj * 1000),
                "VOICE_B": int(voice_adj * 1000),
                "VIDEO_B": int(video_adj * 1000),
                "PLATINUM_B": int(platinum_adj * 1000),
                "GOLD_B": int(gold_adj * 1000),
                "SILVER_B": int(silver_adj * 1000),
                "BRONZE_B": int(bronze_adj * 1000),
                "MANAGE_B": int(manage_adj * 1000),
                "TOTAL_B": int(total * 1000),
                
                # Burst y Peak
                "VOICE_BURST": int(round(voice_adj * 0.1875 * 1000)),
                "VOICE_PEAK": int(round(voice_adj * 0.375 * 1000)),
                "VIDEO_BURST": int(round(video_adj * 0.1875 * 1000)),
                "VIDEO_PEAK": int(round(video_adj * 0.375 * 1000)),
                "PLATINUM_BURST": int(round(platinum_adj * 0.1875 * 1000)),
                "PLATINUM_PEAK": int(round(platinum_adj * 0.375 * 1000)),
                "GOLD_BURST": int(round(gold_adj * 0.1875 * 1000)),
                "GOLD_PEAK": int(round(gold_adj * 0.375 * 1000)),
                "SILVER_BURST": int(round(silver_adj * 0.1875 * 1000)),
                "SILVER_PEAK": int(round(silver_adj * 0.375 * 1000)),
                "BRONZE_BURST": int(round(bronze_adj * 0.1875 * 1000)),
                "BRONZE_PEAK": int(round(bronze_adj * 0.375 * 1000)),
                "MANAGE_BURST": int(round(manage_adj * 0.1875 * 1000)),
                "MANAGE_PEAK": int(round(manage_adj * 0.375 * 1000)),

                # Porcentajes
                "VOICE_BW_PERC": calc_perc(voice_adj),
                "VIDEO_BW_PERC": calc_perc(video_adj),
                "PLATINUM_BW_PERC": calc_perc(platinum_adj),
                "GOLD_BW_PERC": calc_perc(gold_adj),
                "SILVER_BW_PERC": calc_perc(silver_adj),
                "BRONZE_BW_PERC": calc_perc(bronze_adj),
                "MANAGE_BW_PERC": calc_perc(manage_adj),

                # Kbps
                "TOTAL_KBPS": int(total),
                "VOICE_KBPS": int(voice_adj),
                "VIDEO_KBPS": int(video_adj),
                "PLATINUM_KBPS": int(platinum_adj),
                "GOLD_KBPS": int(gold_adj),
                "SILVER_KBPS": int(silver_adj),
                "BRONZE_KBPS": int(bronze_adj),
                "MANAGE_KBPS": int(manage_adj),

                # 4 colas (ef, nc, af, be)
                "CLASE_EF_B": int(ef_kbps * 1000),
                "CLASE_EF_KBPS": int(ef_kbps),
                "CLASE_EF_PERC": calc_perc(ef_kbps),
                "CLASE_EF_BURST": int(round(ef_kbps * 0.1875 * 1000)),
                "CLASE_EF_PEAK": int(round(ef_kbps * 0.375 * 1000)),
                "clase_ef": int(ef_kbps * 1000),
                "clase_ef_kbps": int(ef_kbps),
                "clase_ef_perc": calc_perc(ef_kbps),

                "CLASE_NC_B": int(nc_kbps * 1000),
                "CLASE_NC_KBPS": int(nc_kbps),
                "CLASE_NC_PERC": calc_perc(nc_kbps),
                "CLASE_NC_BURST": int(round(nc_kbps * 0.1875 * 1000)),
                "CLASE_NC_PEAK": int(round(nc_kbps * 0.375 * 1000)),
                "clase_nc": int(nc_kbps * 1000),
                "clase_nc_kbps": int(nc_kbps),
                "clase_nc_perc": calc_perc(nc_kbps),

                "CLASE_AF_B": int(af_kbps * 1000),
                "CLASE_AF_KBPS": int(af_kbps),
                "CLASE_AF_PERC": calc_perc(af_kbps),
                "CLASE_AF_BURST": int(round(af_kbps * 0.1875 * 1000)),
                "CLASE_AF_PEAK": int(round(af_kbps * 0.375 * 1000)),
                "clase_af": int(af_kbps * 1000),
                "clase_af_kbps": int(af_kbps),
                "clase_af_perc": calc_perc(af_kbps),

                "CLASE_BE_B": int(be_kbps * 1000),
                "CLASE_BE_KBPS": int(be_kbps),
                "CLASE_BE_PERC": calc_perc(be_kbps),
                "CLASE_BE_BURST": int(round(be_kbps * 0.1875 * 1000)),
                "CLASE_BE_PEAK": int(round(be_kbps * 0.375 * 1000)),
                "clase_be": int(be_kbps * 1000),
                "clase_be_kbps": int(be_kbps),
                "clase_be_perc": calc_perc(be_kbps),
            }

            for key in list(jinja_vars.keys()):
                jinja_vars[key.lower()] = jinja_vars[key]

            ui_var_names = [
                ("TOTAL_DOWN_BANDWIDTH_B", "Total Bandwidth (bps)"),
                ("TOTAL_BURST", "Total Burst (bytes)"),
                ("TOTAL_PEAK", "Total Peak (bytes)"),
                ("TOTAL_KBPS", "Total Bandwidth (Kbps)"),
                ("VOICE_DOWN_BANDWIDTH_B", "Voice Bandwidth (bps) / clase_ef"),
                ("VOICE_BURST", "Voice Burst (bytes)"),
                ("VOICE_PEAK", "Voice Peak (bytes)"),
                ("VOICE_BW_PERC", "Voice Porcentaje (%)"),
                ("VIDEO_DOWN_BANDWIDTH_B", "Video Bandwidth (bps)"),
                ("VIDEO_BURST", "Video Burst (bytes)"),
                ("VIDEO_PEAK", "Video Peak (bytes)"),
                ("VIDEO_BW_PERC", "Video Porcentaje (%)"),
                ("PLATINUM_DOWN_BANDWIDTH_B", "Platinum Bandwidth (bps)"),
                ("PLATINUM_BURST", "Platinum Burst (bytes)"),
                ("PLATINUM_PEAK", "Platinum Peak (bytes)"),
                ("PLATINUM_BW_PERC", "Platinum Porcentaje (%)"),
                ("GOLD_DOWN_BANDWIDTH_B", "Gold Bandwidth (bps)"),
                ("GOLD_BURST", "Gold Burst (bytes)"),
                ("GOLD_PEAK", "Gold Peak (bytes)"),
                ("GOLD_BW_PERC", "Gold Porcentaje (%)"),
                ("SILVER_DOWN_BANDWIDTH_B", "Silver Bandwidth (bps)"),
                ("SILVER_BURST", "Silver Burst (bytes)"),
                ("SILVER_PEAK", "Silver Peak (bytes)"),
                ("SILVER_BW_PERC", "Silver Porcentaje (%)"),
                ("BRONZE_DOWN_BANDWIDTH_B", "Bronze Bandwidth (bps)"),
                ("BRONZE_BURST", "Bronze Burst (bytes)"),
                ("BRONZE_PEAK", "Bronze Peak (bytes)"),
                ("BRONZE_BW_PERC", "Bronze Porcentaje (%)"),
                ("MANAGE_BANDWIDTH_B", "Management Bandwidth (bps)"),
                ("MANAGE_BURST", "Management Burst (bytes)"),
                ("MANAGE_PEAK", "Management Peak (bytes)"),
                ("MANAGE_BW_PERC", "Management Porcentaje (%)"),
                ("CLASE_EF_B", "clase_ef (Voz) en bps"),
                ("CLASE_EF_KBPS", "clase_ef (Voz) en Kbps"),
                ("CLASE_EF_PERC", "clase_ef Porcentaje (%)"),
                ("CLASE_NC_B", "clase_nc (Mgmt + Video) en bps"),
                ("CLASE_NC_KBPS", "clase_nc (Mgmt + Video) en Kbps"),
                ("CLASE_NC_PERC", "clase_nc Porcentaje (%)"),
                ("CLASE_AF_B", "clase_af (Plat + Gold) en bps"),
                ("CLASE_AF_KBPS", "clase_af (Plat + Gold) en Kbps"),
                ("CLASE_AF_PERC", "clase_af Porcentaje (%)"),
                ("CLASE_BE_B", "clase_be (Silv + Bronze) en bps"),
                ("CLASE_BE_KBPS", "clase_be (Silv + Bronze) en Kbps"),
                ("CLASE_BE_PERC", "clase_be Porcentaje (%)"),
            ]
            jinja_vars_list = [
                {"name": name, "label": label, "value": jinja_vars[name]}
                for name, label in ui_var_names if name in jinja_vars
            ]

            if not status:
                status = "correcto" if abs(suma_clases - total) < 1e-6 else "incorrecto"
                total_final = int(total)
                result = {
                    "total_ingresado": int(total),
                    "total": total_final,
                    "classes": classes,
                    "qos_4_colas": qos_4_colas,
                    "jinja_vars": jinja_vars,
                    "jinja_vars_list": jinja_vars_list,
                    "burst_size": total_burst,
                    "peak_burst": total_peak,
                    "suma": int(suma_clases),
                }

            for k in defaults:
                defaults[k] = form.get(k, defaults[k])

        except Exception as e:
            status = f"error: {e}"

    return render_template("qos.html", result=result, status=status, defaults=defaults)

@app.route("/compare", methods=["GET", "POST"])
def compare():
    comparison = None
    if request.method == "POST":
        def to_int(x):
            try:
                return int(x or 0)
            except:
                return 0
        keys = [("Total", "total"), ("Voice", "voice"), ("Video", "video"),
                ("Data-Platinum", "platinum"), ("Data-Gold", "gold"),
                ("Data-Silver", "silver"), ("Data-Bronze", "bronze")]
        a = {k[0]: to_int(request.form.get(f"{k[1]}_a", 0)) for k in keys}
        b = {k[0]: to_int(request.form.get(f"{k[1]}_b", 0)) for k in keys}
        comparison = []
        for name in a.keys():
            comparison.append({
                "name": name,
                "a": a[name],
                "b": b[name],
                "equal": a[name] == b[name]
            })
    return render_template("compare.html", comparison=comparison)

@app.route("/render_jinja", methods=["POST"])
def render_jinja():
    data = request.get_json()
    template_str = data.get("template", "")
    auto_vars = data.get("variables", {})
    manual_vars = data.get("manual_variables", {})
    merged_vars = {**auto_vars, **manual_vars}
    if not template_str.strip():
        return jsonify({"result": "", "status": "success", "missing_vars": []})
    try:
        from jinja2 import Environment, BaseLoader, meta, Undefined
        class KeepUndefined(Undefined):
            def __str__(self):
                return f"{{{{ {self._undefined_name} }}}}"

        env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=KeepUndefined
        )
        ast = env.parse(template_str)
        all_vars = meta.find_undeclared_variables(ast)
        missing = sorted([v for v in all_vars if v not in auto_vars and v.lower() not in auto_vars and v.upper() not in auto_vars])

        template = env.from_string(template_str)
        rendered = template.render(merged_vars)
        rendered = re.sub(r'\n\s*\n+', '\n\n', rendered.strip())
        return jsonify({"result": rendered, "status": "success", "missing_vars": missing})
    except Exception as e:
        return jsonify({"result": f"[Error en la plantilla Jinja: {e}]", "status": "error", "missing_vars": []}), 400