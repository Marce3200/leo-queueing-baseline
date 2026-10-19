import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle

fig, ax = plt.subplots(figsize=(11, 4.0))
ax.set_xlim(0, 22); ax.set_ylim(0, 7.6); ax.axis("off")

AZUL="#1F3864"; GRIS="#5A5A5A"; ROJO="#B03A2E"; CLARO="#EDF1F7"; ROJOCLARO="#FBEAE7"

def delay(x, y, titulo, sub, demanda):
    # servidor infinito: tres circulos apilados
    for i,dy in enumerate((0.85,0,-0.85)):
        ax.add_patch(Circle((x+1.6, y+dy), 0.32, facecolor="white", edgecolor=GRIS, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((x, y-1.55), 2.9, 3.1, facecolor=CLARO, edgecolor=GRIS, lw=1.3, zorder=1))
    ax.text(x+1.45, y+1.85, titulo, ha="center", va="bottom", fontsize=10, fontweight="bold", color=AZUL)
    ax.text(x+1.45, y-1.95, sub, ha="center", va="top", fontsize=8, color=GRIS, style="italic")
    ax.text(x+1.45, y-2.55, demanda, ha="center", va="top", fontsize=9, color="black")

def cola(x, y, titulo, sub, demanda, critico=False):
    fondo = ROJOCLARO if critico else CLARO
    borde = ROJO if critico else GRIS
    ax.add_patch(Rectangle((x, y-1.55), 2.9, 3.1, facecolor=fondo, edgecolor=borde, lw=1.6 if critico else 1.3, zorder=1))
    # buffer: cuatro casillas
    for i in range(4):
        ax.add_patch(Rectangle((x+0.35+i*0.32, y-0.34), 0.30, 0.68, facecolor="white", edgecolor=borde, lw=1.0, zorder=3))
    ax.add_patch(Circle((x+2.2, y), 0.42, facecolor="white", edgecolor=borde, lw=1.4, zorder=3))
    ax.text(x+1.45, y+1.85, titulo, ha="center", va="bottom", fontsize=10, fontweight="bold", color=ROJO if critico else AZUL)
    ax.text(x+1.45, y-1.95, sub, ha="center", va="top", fontsize=8, color=GRIS, style="italic")
    ax.text(x+1.45, y-2.55, demanda, ha="center", va="top", fontsize=9, color="black")

Y=4.6
delay(1.2, Y, "Nodo emisor", "retardo puro", "D = 0,3287 s")
cola(5.4, Y, "Canal mesh", "cola, un servidor", "D = 0,59 s")
cola(9.6, Y, "Enlace de subida", "cola, un servidor", "D = 162,11 s / N", critico=True)
delay(13.8, Y, "Descarga a tierra", "retardo puro", "D = 0,0208 s")

def flecha(x1, x2, y=Y, txt=None):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=14,
                                 lw=1.4, color=GRIS, zorder=2))
    if txt: ax.text((x1+x2)/2, y+0.28, txt, ha="center", fontsize=8, color=GRIS)

# fuente y sumidero
ax.add_patch(Circle((0.55, Y), 0.42, facecolor="white", edgecolor=AZUL, lw=1.4, zorder=3))
ax.text(0.55, Y, "λ", ha="center", va="center", fontsize=11, color=AZUL)
ax.text(0.55, Y-2.0, "llegadas", ha="center", va="top", fontsize=8, color=GRIS, style="italic")
flecha(1.02, 1.2)
flecha(4.1, 5.4)
flecha(8.3, 9.6)
flecha(12.5, 13.8)
ax.add_patch(FancyArrowPatch((16.7, Y), (17.9, Y), arrowstyle="-|>", mutation_scale=14, lw=1.4, color=GRIS, zorder=2))
ax.text(18.6, Y, "salida", ha="left", va="center", fontsize=9, color=AZUL)

ax.text(0.2, 1.05, "El recuadro destacado señala el recurso crítico previsto.", fontsize=8, color=ROJO, style="italic")
ax.text(0.2, 0.45, "N: número de satélites de la constelación. La demanda del enlace de subida incorpora la disponibilidad del 1,42 % con un satélite.",
        fontsize=8, color=GRIS, style="italic")
fig.tight_layout()
fig.savefig("fig04_modelo_colas.png", dpi=220, bbox_inches="tight")
print("ok")
