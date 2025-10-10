from flask import Blueprint, render_template, request, redirect, url_for

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

            # Construcción datos para template
            suma_clases = sum(v for _, v in adjusted_values) + management_kbps
            classes = []
            for name, adj in adjusted_values:
                percent = (adj / total * 100) if total else 0
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
                "percent": (management_kbps / total * 100) if total else 0,
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

            if not status:
                status = "correcto" if abs(suma_clases - total) < 1e-6 else "incorrecto"

            total_final = int(total)
            result = {
                "total_ingresado": int(total),
                "total": total_final,
                "classes": classes,
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