#!/usr/bin/env python3
"""Genera las imágenes del README del perfil, con el estilo del portfolio.

  python generador/generar.py            # cartel + estadísticas
  python generador/generar.py cartel     # solo el cartel (no necesita red)

Las estadísticas se piden a la API de GitHub con GITHUB_TOKEN (o GH_TOKEN).
Cada imagen sale en dos versiones, clara y oscura; el README elige con <picture>.
Las fuentes van dentro del SVG porque una imagen no puede cargar fuentes de fuera.
"""
import base64
import datetime as dt
import html
import json
import os
import sys
import urllib.request

from fontTools.ttLib import TTFont

USUARIO = "Pikeras72"
WEB = "pikeras72.github.io"
# Repos que no cuentan: el del propio perfil (se actualiza solo) y uno que no es mío al 95 %.
OCULTOS = {"Pikeras72", "G8_el_caso_SELECTA"}
# Lenguajes que GitHub cuenta pero que no dicen mucho de lo que programo.
SIN_CONTAR = {"HTML", "CSS", "CMake", "Makefile", "Dockerfile", "Shell"}
# Por debajo de esto es código de plantilla (lo que genera Flutter, por ejemplo), no algo que yo haya escrito.
MINIMO_BYTES = 5000

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "imagenes")

TEMAS = {
    "claro": dict(papel="#f4efe4", punto="rgba(29,27,46,.13)", tinta="#1d1b2e", suave="#575366",
                  tarjeta="#fffaf0", rojo="#c63c22", amarillo="#ffd447", sombra="#1d1b2e",
                  lenguajes=["#c63c22", "#3346d3", "#e0a800", "#1f7a6c", "#8e44ad", "#575366"]),
    "oscuro": dict(papel="#15141c", punto="rgba(241,235,221,.07)", tinta="#f1ebdd", suave="#a8a2b5",
                   tarjeta="#1e1d28", rojo="#ff6b4b", amarillo="#e9c46a", sombra="#000000",
                   lenguajes=["#ff6b4b", "#8f9cff", "#e9c46a", "#4fc1ab", "#c792ea", "#a8a2b5"]),
}


class Fuente:
    """Una fuente incrustable que además sabe medir texto (para colocar los subrayados)."""

    def __init__(self, archivo):
        ruta = os.path.join(AQUI, "fuentes", archivo)
        t = TTFont(ruta)
        self.upm = t["head"].unitsPerEm
        self.cmap = t.getBestCmap()
        self.hmtx = t["hmtx"]
        self.nombre = archivo.split(".")[0]
        with open(ruta, "rb") as f:
            self.b64 = base64.b64encode(f.read()).decode()

    def ancho(self, texto, tam, espaciado=0.0):
        unidades = sum(self.hmtx[self.cmap.get(ord(c), "space")][0] for c in texto)
        return unidades * tam / self.upm + espaciado * tam * len(texto)

    def css(self):
        return f"@font-face{{font-family:{self.nombre};src:url(data:font/woff2;base64,{self.b64}) format('woff2')}}"


TITULO = Fuente("fraunces-titulo.woff2")
NUMERO = Fuente("fraunces-numero.woff2")
CURSIVA = Fuente("fraunces-cursiva.woff2")
NEGRITA = Fuente("bricolage.woff2")
NORMAL = Fuente("bricolage-normal.woff2")
MANO = Fuente("caveat.woff2")
MONO = Fuente("mono.woff2")

e = html.escape


def lienzo(ancho, alto, tema, fuentes, estilo, cuerpo):
    c = TEMAS[tema]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}">
<style>{''.join(f.css() for f in fuentes)}
{estilo}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}</style>
<defs><pattern id="puntos" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r="1.3" fill="{c['punto']}"/></pattern></defs>
<rect x="14" y="14" width="{ancho - 22}" height="{alto - 22}" rx="26" fill="{c['sombra']}"/>
<rect x="6" y="6" width="{ancho - 22}" height="{alto - 22}" rx="26" fill="{c['papel']}" stroke="{c['tinta']}" stroke-width="2.5"/>
<rect x="6" y="6" width="{ancho - 22}" height="{alto - 22}" rx="26" fill="url(#puntos)"/>
{cuerpo}
</svg>
"""


def partir(palabras, fuente, tam, maximo):
    """Reparte las palabras en líneas que quepan en `maximo` píxeles."""
    lineas, actual = [], []
    for p in palabras:
        prueba = " ".join(t for t, _ in actual + [p])
        if actual and fuente.ancho(prueba, tam) > maximo:
            lineas.append(actual)
            actual = []
        actual.append(p)
    return lineas + [actual]


def imagen(nombre):
    with open(os.path.join(AQUI, nombre), "rb") as f:
        tipo = "image/png" if nombre.endswith(".png") else "image/jpeg"
        return f"data:{tipo};base64,{base64.b64encode(f.read()).decode()}"


# --------------------------------------------------------------- el cartel
def cartel(tema):
    c = TEMAS[tema]
    W, H, x0 = 960, 330, 52
    partes = []

    partes.append(f'<text x="{x0 + 4}" y="74" transform="rotate(-3 {x0} 74)" font-family="caveat" font-size="31" fill="{c["rojo"]}">hi, I’m</text>')

    nombre = "Diego Ruiz Piqueras"
    tam = min(64, 560 / TITULO.ancho(nombre, 1, -0.035))
    partes.append(f'<text x="{x0}" y="138" font-family="fraunces-titulo" font-size="{tam:.1f}" letter-spacing="-0.035em" fill="{c["tinta"]}">{nombre}</text>')

    # La frase, con los dos trozos subrayados como en la web.
    frase = [("Every", 0), ("project", 0), ("starts", 0), ("with", 0), ("a", 1), ("question,", 1),
             ("and", 0), ("almost", 0), ("all", 0), ("of", 0), ("them", 0), ("end", 0), ("with", 0),
             ("a", 2), ("more", 2), ("interesting", 2), ("one.", 2)]
    tf, y = 23, 184
    for linea in partir(frase, CURSIVA, tf, 560):
        x = x0
        marcas = {}
        for i, (palabra, marca) in enumerate(linea):
            visible = palabra.rstrip(",.") if marca else palabra
            if marca:
                ini, fin = marcas.get(marca, (x, x))
                marcas[marca] = (ini, x + CURSIVA.ancho(visible, tf))
            x += CURSIVA.ancho(palabra + " ", tf)
        for n, (ini, fin) in enumerate(marcas.values()):
            if tema == "claro":
                partes.append(f'<rect class="marca" style="animation-delay:{.5 + n * .5}s" x="{ini - 2:.1f}" y="{y - tf * .34:.1f}" width="{fin - ini + 4:.1f}" height="{tf * .44:.1f}" fill="{c["amarillo"]}"/>')
            else:
                partes.append(f'<rect class="marca" style="animation-delay:{.5 + n * .5}s" x="{ini - 2:.1f}" y="{y + tf * .08:.1f}" width="{fin - ini + 4:.1f}" height="{tf * .16:.1f}" fill="{c["amarillo"]}"/>')
        texto = " ".join(p for p, _ in linea)
        partes.append(f'<text x="{x0}" y="{y}" font-family="fraunces-cursiva" font-size="{tf}" fill="{c["tinta"]}">{e(texto)}</text>')
        y += 31

    # El botón (todo el cartel es un enlace en el README; esto es lo que lo dice).
    boton = "Explore my portfolio ↗"
    tb, by, bh = 19, y + 2, 50
    bw = NEGRITA.ancho(boton, tb) + 44
    partes.append(f'<g class="boton"><rect x="{x0 + 5}" y="{by + 5}" width="{bw:.1f}" height="{bh}" rx="25" fill="{c["sombra"]}"/>'
                  f'<rect x="{x0}" y="{by}" width="{bw:.1f}" height="{bh}" rx="25" fill="#ffd447" stroke="{c["tinta"]}" stroke-width="2.5"/>'
                  f'<text x="{x0 + 22}" y="{by + 32}" font-family="bricolage" font-size="{tb}" fill="#1d1b2e">{e(boton)}</text></g>')
    partes.append(f'<text x="{x0 + bw + 20:.1f}" y="{by + 31}" font-family="mono" font-size="15" fill="{c["suave"]}">{WEB}</text>')

    # La foto, que cada pocos segundos se convierte en la figura de LegofyNet.
    cx, cy, r = 786, 146, 98
    partes.append(f'<clipPath id="circulo"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                  f'<circle cx="{cx + 7}" cy="{cy + 7}" r="{r}" fill="{c["sombra"]}"/>'
                  f'<g clip-path="url(#circulo)">'
                  f'<image x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" xlink:href="{imagen("foto.jpg")}"/>'
                  f'<g class="lego"><rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="#ffffff"/>'
                  f'<image x="{cx - r * .48:.1f}" y="{cy - r * .96:.1f}" width="{r * .96:.1f}" height="{r * 1.92:.1f}" style="image-rendering:pixelated" xlink:href="{imagen("lego.png")}"/></g>'
                  f'</g><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c["tinta"]}" stroke-width="3"/>')
    nota = "↑ me, and how my neural net sees me"
    tn = min(22, 236 / MANO.ancho(nota, 1))
    partes.append(f'<text x="{cx}" y="{cy + r + 40}" text-anchor="middle" transform="rotate(-2 {cx} {cy + r + 40})" font-family="caveat" font-size="{tn:.1f}" fill="{c["rojo"]}">{e(nota)}</text>')

    estilo = """
.marca { transform-box: fill-box; transform-origin: 0 50%; animation: pinta 1.1s cubic-bezier(.6,0,.2,1) both; }
@keyframes pinta { from { transform: scaleX(0); } }
.lego { opacity: 0; animation: alterna 10s ease-in-out 2s infinite; }
@keyframes alterna { 0%, 40% { opacity: 0; } 50%, 90% { opacity: 1; } 100% { opacity: 0; } }"""
    return lienzo(W, H, tema, [TITULO, CURSIVA, NEGRITA, MANO, MONO], estilo, "\n".join(partes))


# --------------------------------------------------------- las estadísticas
CONSULTA = """query($login: String!) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { name pushedAt languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection { contributionCalendar { totalContributions } }
  }
}"""


def pedir_datos():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Falta GITHUB_TOKEN para pedir las estadísticas.")
    peticion = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USUARIO},
    )
    with urllib.request.urlopen(peticion, timeout=30) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        sys.exit(f"La API de GitHub ha fallado: {respuesta['errors']}")
    return respuesta["data"]["user"]


def hace(fecha, hoy):
    dias = (hoy - fecha.date()).days
    if dias <= 0: return "today"
    if dias == 1: return "yesterday"
    if dias < 30: return f"{dias} days ago"
    meses = dias // 30
    if meses < 12: return f"{meses} month{'s' if meses > 1 else ''} ago"
    anios = dias // 365
    return f"{anios} year{'s' if anios > 1 else ''} ago"


def resumir(datos, hoy):
    repos = [r for r in datos["repositories"]["nodes"] if r["name"] not in OCULTOS]
    bytes_por_lenguaje = {}
    for r in repos:
        for borde in r["languages"]["edges"]:
            nombre = borde["node"]["name"]
            if nombre not in SIN_CONTAR:
                bytes_por_lenguaje[nombre] = bytes_por_lenguaje.get(nombre, 0) + borde["size"]
    bytes_por_lenguaje = {n: b for n, b in bytes_por_lenguaje.items() if b >= MINIMO_BYTES}
    total = sum(bytes_por_lenguaje.values()) or 1
    lenguajes = sorted(bytes_por_lenguaje.items(), key=lambda x: -x[1])
    cabeza = [(n, b / total) for n, b in lenguajes[:5]]
    resto = sum(b for _, b in lenguajes[5:]) / total
    if resto > 0.005:
        cabeza.append(("Other", resto))
    creado = dt.datetime.fromisoformat(datos["createdAt"].replace("Z", "+00:00")).date()
    return {
        "contribuciones": datos["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "proyectos": len(repos),
        "lenguajes": len(lenguajes),
        "anios": int((hoy - creado).days // 365.25),
        "reparto": cabeza,
        "ultimos": [(r["name"], hace(dt.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")), hoy)) for r in repos[:3]],
    }


def estadisticas(tema, d, hoy):
    c = TEMAS[tema]
    W, H, x0 = 960, 346, 52
    partes = [
        f'<text x="{x0 + 2}" y="60" transform="rotate(-2 {x0} 60)" font-family="caveat" font-size="29" fill="{c["rojo"]}">my GitHub, in numbers</text>',
        f'<text x="{W - x0 - 8}" y="57" text-anchor="end" font-family="mono" font-size="12.5" fill="{c["suave"]}">updated {hoy.day} {hoy:%b %Y} · refreshes by itself</text>',
    ]

    fichas = [(d["contribuciones"], "contributions in the last year"), (d["proyectos"], "public projects"),
              (d["lenguajes"], "programming languages"), (d["anios"], "years building on GitHub")]
    hueco, fy, fh = 18, 82, 108
    fw = (W - 16 - 2 * x0 - 3 * hueco) / 4
    for i, (numero, etiqueta) in enumerate(fichas):
        fx = x0 + i * (fw + hueco)
        lineas = [" ".join(p for p, _ in l) for l in partir([(p, 0) for p in etiqueta.split()], NORMAL, 14.5, fw - 36)]
        texto = "".join(f'<tspan x="{fx + 20:.1f}" dy="{0 if k == 0 else 18}">{e(l)}</tspan>' for k, l in enumerate(lineas))
        partes.append(f'<g class="ficha" style="animation-delay:{.1 + i * .12:.2f}s">'
                      f'<rect x="{fx + 4:.1f}" y="{fy + 4}" width="{fw:.1f}" height="{fh}" rx="16" fill="{c["sombra"]}"/>'
                      f'<rect x="{fx:.1f}" y="{fy}" width="{fw:.1f}" height="{fh}" rx="16" fill="{c["tarjeta"]}" stroke="{c["tinta"]}" stroke-width="2"/>'
                      f'<text x="{fx + 20:.1f}" y="{fy + 50}" font-family="fraunces-numero" font-size="40" fill="{c["tinta"]}">{numero}</text>'
                      f'<text x="{fx + 20:.1f}" y="{fy + 76}" font-family="bricolage-normal" font-size="14.5" fill="{c["suave"]}">{texto}</text></g>')

    # Lenguajes: una barra partida y su leyenda.
    by, bw = 240, 400
    partes.append(f'<text x="{x0}" y="{by - 12}" font-family="mono" font-size="12" letter-spacing="1.5" fill="{c["suave"]}">WHAT I WRITE IN</text>')
    partes.append(f'<clipPath id="barra"><rect x="{x0}" y="{by}" width="{bw}" height="16" rx="8"/></clipPath><g clip-path="url(#barra)">')
    x = x0
    for i, (nombre, parte) in enumerate(d["reparto"]):
        partes.append(f'<rect class="tramo" style="animation-delay:{.5 + i * .1:.1f}s" x="{x:.1f}" y="{by}" width="{bw * parte + .5:.1f}" height="16" fill="{c["lenguajes"][i]}"/>')
        x += bw * parte
    partes.append(f'</g><rect x="{x0}" y="{by}" width="{bw}" height="16" rx="8" fill="none" stroke="{c["tinta"]}" stroke-width="2"/>')
    for i, (nombre, parte) in enumerate(d["reparto"]):
        lx, ly = x0 + (i % 3) * 136, by + 44 + (i // 3) * 24
        partes.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{c["lenguajes"][i]}"/>'
                      f'<text x="{lx + 16}" y="{ly}" font-family="mono" font-size="12.5" fill="{c["tinta"]}">{e(nombre)} <tspan fill="{c["suave"]}">{round(parte * 100)}%</tspan></text>')

    # Lo último en lo que he estado.
    lx = 520
    partes.append(f'<text x="{lx}" y="{by - 12}" font-family="mono" font-size="12" letter-spacing="1.5" fill="{c["suave"]}">LATELY</text>')
    for i, (nombre, cuando) in enumerate(d["ultimos"]):
        ly = by + 14 + i * 28
        partes.append(f'<text x="{lx}" y="{ly}" font-family="bricolage" font-size="15" fill="{c["tinta"]}"><tspan fill="{c["rojo"]}">✦ </tspan>{e(nombre)}</text>'
                      f'<text x="{W - x0 - 8}" y="{ly}" text-anchor="end" font-family="mono" font-size="12.5" fill="{c["suave"]}">{cuando}</text>')

    estilo = """
.ficha { animation: sube .6s cubic-bezier(.3,1.4,.5,1) both; }
@keyframes sube { from { opacity: 0; transform: translateY(10px); } }
.tramo { transform-box: fill-box; transform-origin: 0 50%; animation: crece .8s cubic-bezier(.6,0,.2,1) both; }
@keyframes crece { from { transform: scaleX(0); } }"""
    return lienzo(W, H, tema, [NUMERO, NEGRITA, NORMAL, MANO, MONO], estilo, "\n".join(partes))


def guardar(nombre, svg):
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    for tema in TEMAS:
        guardar(f"cartel-{tema}.svg", cartel(tema))
    if que != "cartel":
        hoy = dt.datetime.now(dt.timezone.utc).date()
        datos = resumir(pedir_datos(), hoy)
        for tema in TEMAS:
            guardar(f"estadisticas-{tema}.svg", estadisticas(tema, datos, hoy))
    print("hecho")
