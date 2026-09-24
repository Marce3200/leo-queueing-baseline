"""
Analisis de sensibilidad sobre los factores declarados en el apartado 4.1.7.

Determina si las conclusiones del modelo conservan su signo dentro del rango
de validez comprometido. Una conclusion que se mantiene en todo el rango se
atribuye a la arquitectura; una que se invierte dentro del rango se reporta
como dependiente del escenario.

Factores:
    numero medio de saltos          1,5 a 6
    numero de nodos                 30 a 80
    tamano de constelacion          1 a 12 satelites
    plazo de utilidad operativa     15, 30, 60 y 360 minutos
    posicion del gateway            centro y esquina

Uso:
    python sensibilidad.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from baseline import (AIRTIME_MESH, AIRTIME_UPLINK, DIR_FIGURAS,
                      DIR_RESULTADOS, DISPONIBILIDAD_N1, REGIMENES,
                      escribir_csv)

N_NODOS_BASE = 30
SALTOS_BASE = 1.8
SALTOS_ESQUINA = 3.5

SALTOS = [1.5, 1.8, 2.5, 3.5, 4.5, 6.0]
NODOS = [30, 40, 50, 60, 80]
SATELITES = [1, 2, 4, 8, 12]
PLAZOS_MIN = [15, 30, 60, 360]


def d_mesh(saltos):
    return AIRTIME_MESH * saltos


def d_uplink(n_satelites):
    return AIRTIME_UPLINK / (DISPONIBILIDAD_N1 * n_satelites)


# --------------------------------------------------------------------------
# Factor: numero medio de saltos (incluye la posicion del gateway)
# --------------------------------------------------------------------------

def sens_saltos():
    filas = []
    lmbda = REGIMENES["desastre"]
    for s in SALTOS:
        dm = d_mesh(s)
        for n in (1, 12):
            du = d_uplink(n)
            filas.append({
                "saltos_medios": s,
                "satelites": n,
                "demanda_mesh_s": f"{dm:.3f}",
                "demanda_enlace_s": f"{du:.2f}",
                "razon_enlace_mesh": f"{du / dm:.1f}",
                "recurso_critico": "EnlaceSubida" if du > dm else "CanalMesh",
                "utilizacion_mesh_desastre": f"{lmbda * dm:.4f}",
            })
    return filas


# --------------------------------------------------------------------------
# Factor: numero de nodos
# --------------------------------------------------------------------------

def sens_nodos(escala_carga=True):
    """Si escala_carga es cierto, la tasa por nodo se mantiene y la carga
    total crece con el numero de nodos. En caso contrario, la carga total
    permanece fija y se reparte entre mas nodos."""
    filas = []
    for nodos in NODOS:
        factor = nodos / N_NODOS_BASE if escala_carga else 1.0
        for regimen, lmbda_base in REGIMENES.items():
            lmbda = lmbda_base * factor
            for n in (1, 4, 12):
                du = d_uplink(n)
                u = lmbda * du
                filas.append({
                    "nodos": nodos,
                    "carga_escala_con_nodos": "si" if escala_carga else "no",
                    "regimen": regimen,
                    "satelites": n,
                    "lambda": f"{lmbda:.6f}",
                    "utilizacion_enlace": f"{u:.4f}" if u < 1 else ">1",
                    "estable": "si" if u < 1 else "no",
                    "utilizacion_mesh": f"{lmbda * d_mesh(SALTOS_BASE):.5f}",
                    "periodo_sondeo_critico_s": f"{nodos * d_mesh(SALTOS_BASE) / (1 - lmbda * d_mesh(SALTOS_BASE)):.1f}",
                })
    return filas


# --------------------------------------------------------------------------
# Factor: plazo de utilidad operativa
# --------------------------------------------------------------------------

def sens_plazo():
    filas = []
    for pm in PLAZOS_MIN:
        P = pm * 60.0
        for n in SATELITES:
            du = d_uplink(n)
            lsat = 1.0 / du
            lplazo = (1.0 - du / P) / du if du < P else None
            filas.append({
                "plazo_min": pm,
                "satelites": n,
                "capacidad_saturacion_dia": f"{lsat * 86400:.0f}",
                "capacidad_dentro_de_plazo_dia": (f"{lplazo * 86400:.0f}"
                                                  if lplazo else "0"),
                "fraccion_de_la_capacidad": (f"{lplazo / lsat:.3f}"
                                             if lplazo else "0"),
            })
    return filas


# --------------------------------------------------------------------------
# Factor: posicion del gateway
# --------------------------------------------------------------------------

def sens_gateway():
    filas = []
    lmbda = REGIMENES["desastre"]
    for nombre, s in (("centro", SALTOS_BASE), ("esquina", SALTOS_ESQUINA)):
        dm = d_mesh(s)
        filas.append({
            "posicion": nombre,
            "saltos_medios": s,
            "demanda_mesh_s": f"{dm:.3f}",
            "utilizacion_mesh_desastre": f"{lmbda * dm:.4f}",
            "limite_saltos_por_defecto_suficiente": "si" if s <= 3 else "no",
            "periodo_sondeo_critico_s": f"{N_NODOS_BASE * dm / (1 - lmbda * dm):.1f}",
        })
    return filas


# --------------------------------------------------------------------------

def main():
    os.makedirs(DIR_FIGURAS, exist_ok=True)
    os.makedirs(DIR_RESULTADOS, exist_ok=True)

    f_saltos = sens_saltos()
    escribir_csv(os.path.join(DIR_RESULTADOS, "sens_saltos.csv"), f_saltos,
                 list(f_saltos[0].keys()))
    print("Saltos medios (regimen de desastre)")
    for f in f_saltos:
        print(f"  saltos={f['saltos_medios']:<4} N={f['satelites']:>2}  "
              f"D_mesh={f['demanda_mesh_s']:>6} s  razon={f['razon_enlace_mesh']:>6}  "
              f"critico={f['recurso_critico']}")

    f_nodos = sens_nodos(True) + sens_nodos(False)
    escribir_csv(os.path.join(DIR_RESULTADOS, "sens_nodos.csv"), f_nodos,
                 list(f_nodos[0].keys()))
    print("\nNumero de nodos, carga por nodo constante (desastre)")
    for f in f_nodos:
        if f["regimen"] == "desastre" and f["carga_escala_con_nodos"] == "si":
            print(f"  nodos={f['nodos']:>2} N={f['satelites']:>2}  "
                  f"U_enlace={f['utilizacion_enlace']:>7}  estable={f['estable']:>2}  "
                  f"T_sondeo_critico={f['periodo_sondeo_critico_s']:>6} s")

    f_plazo = sens_plazo()
    escribir_csv(os.path.join(DIR_RESULTADOS, "sens_plazo.csv"), f_plazo,
                 list(f_plazo[0].keys()))
    print("\nPlazo de utilidad operativa (capacidad dentro de plazo, mensajes/dia)")
    encabezado = "  plazo  " + "".join(f"N={n:<8}" for n in SATELITES)
    print(encabezado)
    for pm in PLAZOS_MIN:
        fila = [f for f in f_plazo if f["plazo_min"] == pm]
        print(f"  {pm:>3} min " + "".join(
            f"{f['capacidad_dentro_de_plazo_dia']:<10}" for f in fila))

    f_gw = sens_gateway()
    escribir_csv(os.path.join(DIR_RESULTADOS, "sens_gateway.csv"), f_gw,
                 list(f_gw[0].keys()))
    print("\nPosicion del gateway")
    for f in f_gw:
        print(f"  {f['posicion']:<8} saltos={f['saltos_medios']:<4} "
              f"U_mesh={f['utilizacion_mesh_desastre']}  "
              f"limite 3 suficiente: {f['limite_saltos_por_defecto_suficiente']}  "
              f"T_sondeo_critico={f['periodo_sondeo_critico_s']} s")

    # Figura: razon entre demandas en funcion de saltos y satelites
    fig, ax = plt.subplots(figsize=(7, 4.2))
    s = np.linspace(1.0, 8.0, 200)
    for n in (1, 4, 12, 17):
        ax.plot(s, d_uplink(n) / d_mesh(s), label=f"N = {n} satelites")
    ax.axhline(1.0, linestyle=":", label="Conmutacion del recurso critico")
    ax.set_xlabel("Numero medio de saltos")
    ax.set_ylabel("Demanda del enlace / demanda del canal mesh")
    ax.set_yscale("log")
    ax.grid(True, linewidth=0.4, alpha=0.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_FIGURAS, "fig15_sensibilidad_saltos.png"), dpi=200)
    plt.close(fig)

    print(f"\nResultados en {DIR_RESULTADOS}")
    print(f"Figuras en {DIR_FIGURAS}")


if __name__ == "__main__":
    main()
