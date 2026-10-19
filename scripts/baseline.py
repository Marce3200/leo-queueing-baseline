"""
Modelo de colas baseline del recorrido del mensaje de emergencia.

Red abierta con forma producto, resuelta analiticamente. Replica el modelo
construido en JMVA y genera la planilla de validacion, las figuras y los
umbrales operativos.

Uso:
    python scripts/baseline.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------
# Parametros del escenario (apartado 4.1 de la tesis)
# --------------------------------------------------------------------------

AIRTIME_MESH = 0.3287       # s, SF9 con 50 B
SALTOS_MEDIOS = 1.8         # razon de visitas del canal mesh, gateway al centro
AIRTIME_UPLINK = 2.302      # s, SF12 con 50 B
DISPONIBILIDAD_N1 = 0.0142  # fraccion de tiempo con enlace disponible, 1 satelite
TRAMA_BAJADA_BITS = 25 * 8  # bits por mensaje en el enlace de bajada
TASA_BAJADA_BPS = 9600      # cota conservadora del rango declarado

PLAZO_UTILIDAD = 1800.0     # s, plazo de utilidad operativa

REGIMENES = {               # mensajes por segundo
    "normal": 200 / 86400,
    "emergencia": 600 / 86400,
    "desastre": 1600 / 86400,
}

CONSTELACIONES = [1, 4, 12]

# Puntos de control obtenidos en JMVA (validacion cruzada)
JMVA_REFERENCIA = [
    # satelites, lambda, utilizacion, tiempo de residencia (s), numero de mensajes
    (1, 0.0005, 0.081, 176.0, None),
    (1, 0.0060, 0.973, 5929.407, 35.576),
    (4, 0.0240, 0.973, 1485.704, 35.657),
]

TOLERANCIA = 0.05  # 5 % de error relativo admitido

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_FIGURAS = os.path.join(RAIZ, "figuras")
DIR_RESULTADOS = os.path.join(RAIZ, "resultados")


# --------------------------------------------------------------------------
# Demandas de servicio
# --------------------------------------------------------------------------

def demandas(n_satelites):
    """Demanda de servicio por estacion, en segundos."""
    return {
        "Nodo emisor": AIRTIME_MESH,
        "CanalMesh": AIRTIME_MESH * SALTOS_MEDIOS,
        "EnlaceSubida": AIRTIME_UPLINK / (DISPONIBILIDAD_N1 * n_satelites),
        "DescargaTierra": TRAMA_BAJADA_BITS / TASA_BAJADA_BPS,
    }


TIPO_ESTACION = {
    "Nodo emisor": "delay",
    "CanalMesh": "cola",
    "EnlaceSubida": "cola",
    "DescargaTierra": "delay",
}


# --------------------------------------------------------------------------
# Solucion analitica de la red abierta con forma producto
# --------------------------------------------------------------------------

def resolver(lmbda, n_satelites):
    """Indices de rendimiento por estacion para una tasa de llegada dada."""
    d = demandas(n_satelites)
    out = {}
    for est, demanda in d.items():
        if TIPO_ESTACION[est] == "delay":
            util = lmbda * demanda          # numero medio de clientes en servicio
            residencia = demanda            # sin espera
            clientes = lmbda * demanda
        else:
            util = lmbda * demanda
            if util >= 1.0:
                residencia = float("inf")
                clientes = float("inf")
            else:
                residencia = demanda / (1.0 - util)
                clientes = util / (1.0 - util)
        out[est] = {
            "utilizacion": util,
            "residencia": residencia,
            "clientes": clientes,
        }
    out["Sistema"] = {
        "utilizacion": float("nan"),
        "residencia": sum(v["residencia"] for k, v in out.items()),
        "clientes": sum(v["clientes"] for k, v in out.items()),
    }
    return out


def saturacion(n_satelites):
    """Tasa de llegada que satura el recurso critico."""
    d = demandas(n_satelites)
    colas = {k: v for k, v in d.items() if TIPO_ESTACION[k] == "cola"}
    critico = max(colas, key=colas.get)
    return critico, 1.0 / colas[critico]


def cruce_plazo(n_satelites):
    """Tasa de llegada a la que el tiempo de residencia del enlace iguala el plazo."""
    d_up = demandas(n_satelites)["EnlaceSubida"]
    if d_up >= PLAZO_UTILIDAD:
        return None
    # D / (1 - lambda*D) = PLAZO  ->  lambda = (1 - D/PLAZO) / D
    return (1.0 - d_up / PLAZO_UTILIDAD) / d_up


# --------------------------------------------------------------------------
# Validacion cruzada contra JMVA
# --------------------------------------------------------------------------

def validar():
    filas = []
    for n_sat, lmbda, u_ref, r_ref, n_ref in JMVA_REFERENCIA:
        calc = resolver(lmbda, n_sat)["EnlaceSubida"]
        for metrica, ref, val in (
            ("Utilizacion", u_ref, calc["utilizacion"]),
            ("Tiempo de residencia (s)", r_ref, calc["residencia"]),
            ("Numero de mensajes", n_ref, calc["clientes"]),
        ):
            if ref is None:
                continue
            err = abs(val - ref) / ref
            filas.append({
                "satelites": n_sat,
                "lambda": f"{lmbda:.5f}",
                "metrica": metrica,
                "jmva": f"{ref:.4f}",
                "python": f"{val:.4f}",
                "error_relativo": f"{err:.5f}",
                "dentro_tolerancia": "si" if err <= TOLERANCIA else "NO",
            })
    return filas


# --------------------------------------------------------------------------
# Barridos y salidas
# --------------------------------------------------------------------------

def barrido(n_satelites, puntos=200):
    _, lmax = saturacion(n_satelites)
    lambdas = np.linspace(0.05 * lmax, 0.97 * lmax, puntos)
    return lambdas, [resolver(l, n_satelites) for l in lambdas]


def escribir_csv(ruta, filas, campos):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def figura_por_indice(indice, etiqueta, nombre, escala_log=False):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for n in CONSTELACIONES:
        lambdas, res = barrido(n)
        ax.plot(lambdas * 1000, [r["EnlaceSubida"][indice] for r in res],
                label=f"Enlace de subida, N = {n}")
    lambdas, res = barrido(1)
    ax.plot(lambdas * 1000, [r["CanalMesh"][indice] for r in res],
            linestyle="--", label="Canal mesh")
    ax.set_xlabel("Tasa de llegada (mensajes/s, escala 1e-3)")
    ax.set_ylabel(etiqueta)
    if escala_log:
        ax.set_yscale("log")
    ax.grid(True, linewidth=0.4, alpha=0.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_FIGURAS, nombre), dpi=200)
    plt.close(fig)


def main():
    os.makedirs(DIR_FIGURAS, exist_ok=True)
    os.makedirs(DIR_RESULTADOS, exist_ok=True)

    # 1. Planilla de validacion
    filas = validar()
    escribir_csv(os.path.join(DIR_RESULTADOS, "validacion_jmva.csv"), filas,
                 ["satelites", "lambda", "metrica", "jmva", "python",
                  "error_relativo", "dentro_tolerancia"])
    print("Validacion contra JMVA")
    for f in filas:
        print(f"  N={f['satelites']:>2}  lambda={f['lambda']}  {f['metrica']:<26} "
              f"JMVA={f['jmva']:>10}  Python={f['python']:>10}  "
              f"err={f['error_relativo']}  {f['dentro_tolerancia']}")

    # 2. Umbrales por constelacion
    filas_u = []
    print("\nUmbrales por tamano de constelacion")
    for n in CONSTELACIONES:
        critico, lsat = saturacion(n)
        lplazo = cruce_plazo(n)
        d = demandas(n)
        fila = {
            "satelites": n,
            "recurso_critico": critico,
            "demanda_enlace_s": f"{d['EnlaceSubida']:.2f}",
            "lambda_saturacion": f"{lsat:.6f}",
            "mensajes_dia_saturacion": f"{lsat * 86400:.0f}",
            "lambda_cruce_plazo": f"{lplazo:.6f}" if lplazo else "n/a",
            "mensajes_dia_cruce_plazo": f"{lplazo * 86400:.0f}" if lplazo else "n/a",
        }
        filas_u.append(fila)
        print(f"  N={n:>2}  D_enlace={fila['demanda_enlace_s']:>8} s  "
              f"saturacion={fila['mensajes_dia_saturacion']:>6} msg/dia  "
              f"cruce plazo={fila['mensajes_dia_cruce_plazo']:>6} msg/dia")
    escribir_csv(os.path.join(DIR_RESULTADOS, "umbrales_constelacion.csv"), filas_u,
                 list(filas_u[0].keys()))

    # 3. Estabilidad por regimen
    filas_r = []
    print("\nEstabilidad por regimen de trafico")
    for n in CONSTELACIONES:
        for nombre, lmbda in REGIMENES.items():
            r = resolver(lmbda, n)["EnlaceSubida"]
            estable = r["utilizacion"] < 1.0
            filas_r.append({
                "satelites": n,
                "regimen": nombre,
                "lambda": f"{lmbda:.6f}",
                "utilizacion_enlace": f"{r['utilizacion']:.4f}",
                "residencia_enlace_s": f"{r['residencia']:.1f}" if estable else "inf",
                "dentro_de_plazo": ("si" if estable and r["residencia"] <= PLAZO_UTILIDAD
                                    else "no"),
                "estable": "si" if estable else "no",
            })
            print(f"  N={n:>2}  {nombre:<11} U={r['utilizacion']:.3f}  "
                  f"{'estable' if estable else 'INESTABLE'}")
    escribir_csv(os.path.join(DIR_RESULTADOS, "estabilidad_regimenes.csv"), filas_r,
                 list(filas_r[0].keys()))

    # 4. Curvas completas del barrido, para N = 1
    lambdas, res = barrido(1, puntos=20)
    filas_b = [{
        "lambda": f"{l:.6f}",
        "utilizacion_enlace": f"{r['EnlaceSubida']['utilizacion']:.4f}",
        "residencia_enlace_s": f"{r['EnlaceSubida']['residencia']:.2f}",
        "clientes_enlace": f"{r['EnlaceSubida']['clientes']:.3f}",
        "utilizacion_mesh": f"{r['CanalMesh']['utilizacion']:.6f}",
        "residencia_mesh_s": f"{r['CanalMesh']['residencia']:.4f}",
        "residencia_sistema_s": f"{r['Sistema']['residencia']:.2f}",
    } for l, r in zip(lambdas, res)]
    escribir_csv(os.path.join(DIR_RESULTADOS, "barrido_N1.csv"), filas_b,
                 list(filas_b[0].keys()))

    # 5. Figuras
    figura_por_indice("utilizacion", "Utilizacion",
                      "fig10_utilizacion_constelaciones.png")
    figura_por_indice("residencia", "Tiempo de residencia (s)",
                      "fig11_residencia_constelaciones.png", escala_log=True)
    figura_por_indice("clientes", "Numero medio de mensajes",
                      "fig12_clientes_constelaciones.png", escala_log=True)

    print(f"\nResultados en {DIR_RESULTADOS}")
    print(f"Figuras en {DIR_FIGURAS}")


if __name__ == "__main__":
    main()
