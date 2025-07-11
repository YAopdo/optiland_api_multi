# app.py  (Opdo simulation backend)

from flask import Flask, request, jsonify
from flask_cors import CORS
import matplotlib
matplotlib.use("Agg")               # headless backend
import matplotlib.pyplot as plt
import numpy as np
import base64, io, traceback, os

from optiland import optic, analysis

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def fig_to_data_url(fig) -> str:
    """Return figure as a data-URL PNG (data:image/png;base64,...)"""
    buf = io.BytesIO()
    fig.savefig(buf, dpi=300, bbox_inches="tight")
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def build_lens(surfaces_json):
    lens = optic.Optic()
    lens.add_surface(index=0, thickness=np.inf)        # object plane

    for i, s in enumerate(surfaces_json, start=1):
        kwargs = {
            "index":       i,
            "radius":      s["radius"],
            "thickness":   s["thickness"],
            "material":    s.get("material", "Air"),
            "surface_type": s.get("surface_type"),
            "conic":       s.get("conic"),
            "coefficients": s.get("coefficients"),
        }
        # drop None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        lens.add_surface(**kwargs)

    lens.add_surface(index=len(surfaces_json) + 1, is_stop=True)
    lens.set_aperture(aperture_type="EPD", value=10)
    lens.set_field_type(field_type="angle")
    lens.add_field(y=0)
    lens.add_field(y=5)
    
    lens.add_wavelength(value=0.55)
    return lens


# ---------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------

@app.route("/simulate", methods=["POST"])
def simulate():
    try:
        payload   = request.get_json(force=True)
        surfaces  = payload["surfaces"]
        lens = build_lens(surfaces)

        plots = {}

        # 1️⃣ Ray-trace figure
        lens.draw(num_rays=10)
        fig_rt = plt.gcf()
        plots["raytrace"] = fig_to_data_url(fig_rt)

        # 2️⃣ Distortion
        analysis.Distortion(lens).view()
        fig_dist = plt.gcf()
        plots["distortion"] = fig_to_data_url(fig_dist)

        # 3️⃣ Ray fan
        analysis.RayFan(lens).view()
        fig_fan = plt.gcf()
        plots["rayfan"] = fig_to_data_url(fig_fan)

        return jsonify({"plots": plots})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# ---------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run("0.0.0.0", port)
