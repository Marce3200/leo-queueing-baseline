"""
Inyeccion de antipatrones de rendimiento sobre el modelo baseline.

Reutiliza la especificacion del modelo definida en baseline.py y cuantifica
el efecto de cada antipatron sobre los indices de rendimiento.

Antipatrones cubiertos analiticamente:
    Traffic Jam        acumulacion durante la indisponibilidad del enlace
    One-Lane Bridge    ubicacion del recurso critico y condicion de cruce
    Are We There Yet?  costo del sondeo periodico sobre el canal compartido
    Where Was I?       sobrecosto de recuperacion tras corte de enlace

El antipatron de politica de gestion del buffer requiere capacidad finita con
bloqueo y queda fuera del alcance analitico.

Uso:
    python scripts/antipatrones.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from baseline import (AIRTIME_MESH, AIRTIME_UPLINK, CONSTELACIONES,
                      DIR_FIGURAS, DIR_RESULTADOS, DISPONIBILIDAD_N1,
                      PLAZO_UTILIDAD, REGIMENES, SALTOS_MEDIOS, demandas,
                      escribir_csv, resolver, saturacion)

N_NODOS = 30

# Geometria de contacto con un satelite (apartado 5.1)
HUECO_MEDIO_H = 6.7
HUECO_MAXIMO_H = 11.6
DURACION_MEDIA_S = 360.0
DURACION_MAXIMA_S = 474.0

# Where Was I?: niveles del factor experimental de falla de nodo
PROB_CORTE = [0.0, 0.1, 0.2, 0.3, 0.4]
COSTO_RECUPERACION = 1.0   # visitas adicionales al enlace por mensaje afectado


# --------------------------------------------------------------------------
# Traffic Jam
# --------------------------------------------------------------------------

def traffic_jam():
    """Respaldo acumulado al abrirse una ventana frente a su capacidad."""
    cap_media = DURACION_MEDIA_S / AIRTIME_UPLINK
    cap_maxima = DURACION_MAXIMA_S / AIRTIME_UPLINK
    filas = []
    for nombre, lmbda in REGIMENES.items():
        respaldo_medio = lmbda * HUECO_MEDIO_H * 3600
        respaldo_maximo = lmbda * HUECO_MAXIMO_H * 3600
        hueco_critico_h = cap_media / (lmbda * 3600)
        filas.append({
            "regimen": nombre,
            "tasa_mensajes_hora": f"{lmbda * 3600:.1f}",
            "respaldo_hueco_medio": f"{respaldo_medio:.0f}",
            "respaldo_hueco_maximo": f"{respaldo_maximo:.0f}",
            "capacidad_ventana_media": f"{cap_media:.0f}",
            "razon_respaldo_capacidad": f"{respaldo_maximo / cap_media:.2f}",
            "hueco_critico_h": f"{hueco_critico_h:.1f}",
            "excede_con_un_satelite": "si" if HUECO_MAXIMO_H > hueco_critico_h else "no",
        })
    return filas, cap_media, cap_maxima


# --------------------------------------------------------------------------
# One-Lane Bridge
# --------------------------------------------------------------------------

def one_lane_bridge():
    """Transmisiones por mensaje necesarias para que el canal mesh sea critico."""
    filas = []
    for n in CONSTELACIONES + [17]:
        d_up = AIRTIME_UPLINK / (DISPONIBILIDAD_N1 * n)
        k_cruce = d_up / AIRTIME_MESH
        filas.append({
            "satelites": n,
            "demanda_enlace_s": f"{d_up:.2f}",
            "transmisiones_para_cruce": f"{k_cruce:.0f}",
            "maximo_fisico_nodos": N_NODOS,
            "factor_sobre_maximo": f"{k_cruce / N_NODOS:.2f}",
            "alcanzable": "si" if k_cruce <= N_NODOS else "no",
        })
    return filas


# --------------------------------------------------------------------------
# Are We There Yet?
# --------------------------------------------------------------------------

def are_we_there_yet(periodos, n_satelites=1, regimen="normal"):
    """Efecto del sondeo periodico sobre el canal mesh y el recorrido completo."""
    d = demandas(n_satelites)
    lmbda_datos = REGIMENES[regimen]
    filas = []
    for T in periodos:
        lmbda_sondeo = N_NODOS / T          # mensajes de sondeo por segundo
        u_mesh = (lmbda_datos + lmbda_sondeo) * d["CanalMesh"]
        if u_mesh >= 1.0:
            r_mesh = float("inf")
        else:
            r_mesh = d["CanalMesh"] / (1.0 - u_mesh)
        base = resolver(lmbda_datos, n_satelites)
        r_total = (base["Sistema"]["residencia"]
                   - base["CanalMesh"]["residencia"]
                   + (r_mesh if r_mesh != float("inf") else float("inf")))
        filas.append({
            "periodo_sondeo_s": T,
            "lambda_sondeo": f"{lmbda_sondeo:.4f}",
            "utilizacion_mesh": f"{u_mesh:.4f}" if u_mesh < 1 else ">1",
            "residencia_mesh_s": f"{r_mesh:.3f}" if r_mesh != float("inf") else "inf",
            "residencia_sistema_s": f"{r_total:.1f}" if r_total != float("inf") else "inf",
            "canal_saturado": "si" if u_mesh >= 1.0 else "no",
        })
    # periodo critico: utilizacion del canal mesh igual a 1
    lmbda_max = 1.0 / d["CanalMesh"] - lmbda_datos
    T_critico = N_NODOS / lmbda_max
    return filas, T_critico


# --------------------------------------------------------------------------
# Where Was I?
# --------------------------------------------------------------------------

def where_was_i(n_satelites=4, regimen="desastre"):
    """Sobrecosto de recuperacion tras corte: visitas adicionales al enlace."""
    lmbda = REGIMENES[regimen]
    d = demandas(n_satelites)
    filas = []
    for p in PROB_CORTE:
        factor = 1.0 + p * COSTO_RECUPERACION
        d_up = d["EnlaceSubida"] * factor
        u = lmbda * d_up
        r = d_up / (1.0 - u) if u < 1.0 else float("inf")
        lmbda_sat = 1.0 / d_up
        filas.append({
            "prob_corte": f"{p:.1f}",
            "factor_demanda": f"{factor:.2f}",
            "demanda_enlace_s": f"{d_up:.2f}",
            "utilizacion": f"{u:.4f}" if u < 1 else ">1",
            "residencia_enlace_s": f"{r:.1f}" if r != float("inf") else "inf",
            "capacidad_mensajes_dia": f"{lmbda_sat * 86400:.0f}",
            "perdida_capacidad_pct": f"{100 * (1 - 1 / factor):.1f}",
            "dentro_de_plazo": "si" if r <= PLAZO_UTILIDAD else "no",
        })
    return filas


# --------------------------------------------------------------------------

def main():
    os.makedirs(DIR_FIGURAS, exist_ok=True)
    os.makedirs(DIR_RESULTADOS, exist_ok=True)

    # Traffic Jam
    filas_tj, cap_media, cap_maxima = traffic_jam()
    escribir_csv(os.path.join(DIR_RESULTADOS, "ap_traffic_jam.csv"), filas_tj,
                 list(filas_tj[0].keys()))
    print(f"Traffic Jam  (capacidad de ventana: media {cap_media:.0f}, "
          f"maxima {cap_maxima:.0f} mensajes)")
    for f in filas_tj:
        print(f"  {f['regimen']:<11} respaldo max={f['respaldo_hueco_maximo']:>4} "
              f"razon={f['razon_respaldo_capacidad']:>5}  "
              f"hueco critico={f['hueco_critico_h']:>5} h  "
              f"excede: {f['excede_con_un_satelite']}")

    # One-Lane Bridge
    filas_olb = one_lane_bridge()
    escribir_csv(os.path.join(DIR_RESULTADOS, "ap_one_lane_bridge.csv"), filas_olb,
                 list(filas_olb[0].keys()))
    print("\nOne-Lane Bridge  (transmisiones por mensaje para desplazar al enlace)")
    for f in filas_olb:
        print(f"  N={f['satelites']:>2}  k_cruce={f['transmisiones_para_cruce']:>4}  "
              f"x{f['factor_sobre_maximo']:>5} del maximo fisico  "
              f"alcanzable: {f['alcanzable']}")

    # Are We There Yet?
    periodos = [5, 10, 15, 18, 20, 30, 60, 120, 300, 600, 900]
    filas_awty, T_critico = are_we_there_yet(periodos)
    escribir_csv(os.path.join(DIR_RESULTADOS, "ap_are_we_there_yet.csv"), filas_awty,
                 list(filas_awty[0].keys()))
    print(f"\nAre We There Yet?  (periodo critico: {T_critico:.1f} s por nodo)")
    for f in filas_awty:
        print(f"  T={f['periodo_sondeo_s']:>4} s  U_mesh={f['utilizacion_mesh']:>7}  "
              f"R_mesh={f['residencia_mesh_s']:>8} s  saturado: {f['canal_saturado']}")

    # Where Was I?
    filas_wwi = where_was_i()
    escribir_csv(os.path.join(DIR_RESULTADOS, "ap_where_was_i.csv"), filas_wwi,
                 list(filas_wwi[0].keys()))
    print("\nWhere Was I?  (cuatro satelites, regimen de desastre)")
    for f in filas_wwi:
        print(f"  p={f['prob_corte']}  U={f['utilizacion']:>7}  "
              f"R={f['residencia_enlace_s']:>8} s  "
              f"capacidad={f['capacidad_mensajes_dia']:>5} msg/dia  "
              f"perdida={f['perdida_capacidad_pct']:>5} %")

    # Figuras
    Ts = np.linspace(5, 900, 400)
    filas, _ = are_we_there_yet(Ts)
    u = [float(f["utilizacion_mesh"]) if f["utilizacion_mesh"] != ">1" else np.nan
         for f in filas]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(Ts, u, label="Utilizacion del canal mesh")
    ax.axhline(1.0, linestyle=":", label="Saturacion")
    ax.axvline(T_critico, linestyle="--",
               label=f"Periodo critico ({T_critico:.0f} s)")
    ax.set_xlabel("Periodo de sondeo por nodo (s)")
    ax.set_ylabel("Utilizacion del canal mesh")
    ax.set_ylim(0, 1.6)
    ax.grid(True, linewidth=0.4, alpha=0.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_FIGURAS, "fig13_sondeo_canal_mesh.png"), dpi=200)
    plt.close(fig)

    ps = np.linspace(0, 0.6, 200)
    d_up = demandas(4)["EnlaceSubida"]
    lmbda = REGIMENES["desastre"]
    r = []
    for p in ps:
        dd = d_up * (1 + p * COSTO_RECUPERACION)
        uu = lmbda * dd
        r.append(dd / (1 - uu) if uu < 1 else np.nan)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ps, r, label="Tiempo de residencia en el enlace")
    ax.axhline(PLAZO_UTILIDAD, linestyle=":", label="Plazo de utilidad operativa")
    ax.set_xlabel("Probabilidad de corte con perdida de estado")
    ax.set_ylabel("Tiempo de residencia (s)")
    ax.set_yscale("log")
    ax.grid(True, linewidth=0.4, alpha=0.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_FIGURAS, "fig14_recuperacion_enlace.png"), dpi=200)
    plt.close(fig)

    print(f"\nResultados en {DIR_RESULTADOS}")
    print(f"Figuras en {DIR_FIGURAS}")


if __name__ == "__main__":
    main()
