from flask import Flask, Blueprint, render_template, request, redirect, url_for

app = Blueprint("qos", __name__, template_folder="templates")


def get_granularity(total_kbps, card_type):
    if card_type == "1g":
        table = [
            (4096, 16),
            (8192, 32),
            (16384, 64),
            (32768, 128),
            (65535, 256),
            (131072, 512),
            (262144, 1024),
            (1000000, 4096),
        ]
    elif card_type == "10g":
        table = [
            (10240, 40),
            (20480, 80),
            (40960, 160),
            (81920, 320),
            (163840, 640),
            (327680, 1280),
            (655360, 2560),
            (2611200, 10240),
            (5222400, 20480),
            (10000000, 40960),
        ]
    else:  # 100g
        table = [(ub * 10, gran * 10) for (ub, gran) in [
            (10240, 40),
            (20480, 80),
            (40960, 160),
            (81920, 320),
            (163840, 640),
            (327680, 1280),
            (655360, 2560),
            (2611200, 10240),
            (5222400, 20480),
            (10000000, 40960),
        ]]
    for ub, gran in table:
        if total_kbps <= ub:
            return gran
    return table[-1][1]


def adjust_value_for_granularity(name, value_kbps, gran_enabled=None, gran_kbps=None):
    """
    Ajusta una clase individual a la granularidad de policer (8 Kbps).
    - Conserva la firma para compatibilidad con llamadas existentes.
    - NO aplica la granularidad del shaper (gran_kbps); eso se aplica solamente al total (shaper).
    - Voice -> round UP al múltiplo de 8
    - Resto -> round DOWN al múltiplo de 8
    """
    v = int(round(value_kbps or 0))
    if name.lower().startswith("voice"):
        # Voice: redondear hacia arriba al múltiplo de 8
        v = ((v + 7) // 8) * 8
    else:
        # Resto: redondear hacia abajo al múltiplo de 8
        v = (v // 8) * 8
    return int(v)

def restar_en_cascada(adjusted_values, diff, order, bronze_min):
    """
    Resta 'diff' kbps siguiendo el orden de prioridad en 'order'.
    - Bronze nunca baja de bronze_min (según reglas de negocio).
    - Si Bronze no alcanza, el resto se descuenta de las demás en cascada.
    """
    values = dict(adjusted_values)

    for cname in order:
        if diff <= 0:
            break
        if cname in values and values[cname] > 0:
            if cname == "Data-Bronze":
                # Bronze no baja del mínimo exigido
                max_reducible = max(values[cname] - bronze_min, 0)
                take = min(max_reducible, diff)
            else:
                take = min(values[cname], diff)

            values[cname] -= take
            diff -= take

    return list(values.items())

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    status = None
    form = request.form
    defaults = {k: form.get(k, "") for k in [
        "total_download", "voice_download", "video_download", "data_platinum_download",
        "data_gold_download", "data_silver_download", "data_bronze_download",
        "granularity_enabled", "card_type", "gestion", "tipo_acceso"
    ]}
    if request.method == "POST":
        if "clear" in form:
            return redirect(url_for("qos.index"))
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

            gran_enabled = "granularity_enabled" in form
            card_type = form.get("card_type")
            gestion = form.get("gestion")  # gestionado / no_gestionado
            tipo_acceso = form.get("tipo_acceso")  # directo / indirecto

            gran_kbps = get_granularity(total, card_type) if gran_enabled else None
            total_adjusted = (int(total) // gran_kbps) * gran_kbps if gran_enabled else int(total)

            raw = [
                ("Voice", voice),
                ("Video", video),
                ("Data-Platinum", platinum),
                ("Data-Gold", gold),
                ("Data-Silver", silver),
                ("Data-Bronze", bronze)
            ]
            CLASSES_ORDER = ["Data-Bronze", "Data-Silver", "Data-Gold", "Data-Platinum", "Video", "Voice"]
            adjusted_values = []
            for name, kbps in raw:
                adj = adjust_value_for_granularity(name, kbps, gran_enabled, gran_kbps)
                adjusted_values.append((name, adj))
                
            # reglas de management
            management_kbps = 0

            if gestion == "gestionado":
                if tipo_acceso == "indirecto":
                    management_kbps = 16
                    bronze_min = 80
                    adjusted_values = restar_en_cascada(adjusted_values, management_kbps, CLASSES_ORDER, bronze_min)
                    bronze = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
                    if bronze < bronze_min:
                        status = f"error: Bronze en indirecto gestionado debe ser >= {bronze_min} Kbps"
                else:  # gestionado directo
                    management_kbps = 64
                    bronze_min = 128
                    adjusted_values = restar_en_cascada(adjusted_values, management_kbps, CLASSES_ORDER, bronze_min)
                    bronze = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
                    if bronze < bronze_min:
                        status = f"error: Bronze en directo gestionado debe ser >= {bronze_min} Kbps"

            elif gestion == "no_gestionado":
                management_kbps = 64
                bronze_min = 128
                adjusted_values = restar_en_cascada(adjusted_values, management_kbps, CLASSES_ORDER, bronze_min)
                bronze = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
                if bronze < bronze_min:
                    status = f"error: Bronze en no gestionado debe ser >= {bronze_min} Kbps"

            else:  # estándar
                management_kbps = 64
                bronze_min = 64
                adjusted_values = restar_en_cascada(adjusted_values, management_kbps, CLASSES_ORDER, bronze_min)
                bronze = next((v for n, v in adjusted_values if n == "Data-Bronze"), 0)
                if bronze < bronze_min:
                    status = f"error: Bronze estándar debe ser >= {bronze_min} Kbps"


            gran_diff = int(total) - int(total_adjusted)

            if gran_diff > 0:
                adjusted_values = restar_en_cascada(adjusted_values, gran_diff, CLASSES_ORDER, bronze_min)         

            suma_clases = sum(val for _, val in adjusted_values) + management_kbps

            # Construir lista clases
            classes = []
            for name, adj in adjusted_values:
                percent = (adj / total_adjusted * 100) if total_adjusted else 0
                classes.append({
                    "name": name,
                    "kbps": adj,
                    "percent": percent,
                    "burst_size": round(adj * 0.1875 * 1000),
                    "peak_burst": round(adj * 0.375 * 1000)
                })

            classes.append({
                "name": "Management",
                "kbps": management_kbps,
                "percent": (management_kbps / total_adjusted * 100) if total_adjusted else 0,
                "burst_size": round(management_kbps * 0.1875 * 1000),
                "peak_burst": round(management_kbps * 0.375 * 1000)
            })

            total_burst = round(total_adjusted * 0.1875 * 1000)
            total_peak = round(total_adjusted * 0.375 * 1000)

            if not status:  # solo marcar correcto/incorrecto si no hay error de reglas
                status = "correcto" if abs(suma_clases - total_adjusted) < 1e-6 else "incorrecto"

            total_final = int(total_adjusted if gran_enabled else total)
            result = {
                "total": total_final,
                "classes": classes,
                "burst_size": total_burst,
                "peak_burst": total_peak,
                "suma": int(suma_clases),
                "gran_enabled": gran_enabled,
                "gran_kbps": gran_kbps if gran_enabled else None,
                "card_type": card_type
            }

            for k in defaults:
                defaults[k] = form.get(k, defaults[k])
            defaults["granularity_enabled"] = "on" if gran_enabled else ""
            #defaults["total_download"] = str(total_final)

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
