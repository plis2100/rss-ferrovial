import re
import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

WEB_URL = "https://newsroom.ferrovial.com/es/"
OUTPUT_FILE = Path("ferrovial.xml")


def descargar_noticias():
    solicitud = urllib.request.Request(
        WEB_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9",
            "Cache-Control": "no-cache",
        },
    )

    with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
        contenido = respuesta.read()

    soup = BeautifulSoup(contenido, "html.parser")

    noticias = []
    enlaces_encontrados = set()

    for tarjeta in soup.select(
        "section.last-notes article.last-notes__item"
    ):
        enlace_elemento = tarjeta.select_one("a[href]")

        if not enlace_elemento:
            continue

        enlace = enlace_elemento.get("href", "").strip()

        titulo = enlace_elemento.get(
            "title",
            "",
        ).strip()

        if not titulo:
            titulo_elemento = tarjeta.select_one(
                "[class*='caption-title']"
            )

            if titulo_elemento:
                titulo = titulo_elemento.get_text(
                    " ",
                    strip=True,
                )

        fecha = ""

        fecha_elemento = tarjeta.select_one("time")

        if fecha_elemento:
            fecha = (
                fecha_elemento.get("datetime")
                or fecha_elemento.get_text(" ", strip=True)
            )

        imagen = ""

        fondo_elemento = tarjeta.select_one(
            "[style*='background-image']"
        )

        if fondo_elemento:
            estilo = fondo_elemento.get("style", "")
            coincidencia = re.search(
                r"url\(\s*['\"]?([^'\")]+)",
                estilo,
            )

            if coincidencia:
                imagen = coincidencia.group(1).strip()

        if (
            not titulo
            or not enlace
            or enlace in enlaces_encontrados
        ):
            continue

        enlaces_encontrados.add(enlace)

        noticias.append(
            {
                "titulo": titulo,
                "enlace": enlace,
                "fecha": fecha,
                "imagen": imagen,
            }
        )

    return noticias


def convertir_fecha(fecha):
    formatos = [
        "%d %b %Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]

    meses = {
        "Ene": "Jan",
        "Abr": "Apr",
        "Ago": "Aug",
        "Dic": "Dec",
    }

    for espanol, ingles in meses.items():
        fecha = fecha.replace(espanol, ingles)

    for formato in formatos:
        try:
            return datetime.strptime(
                fecha,
                formato,
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def crear_rss(noticias):
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
            "xmlns:media": "http://search.yahoo.com/mrss/",
        },
    )

    canal = ET.SubElement(rss, "channel")

    ET.SubElement(canal, "title").text = (
        "Notas de prensa de Ferrovial"
    )
    ET.SubElement(canal, "link").text = WEB_URL
    ET.SubElement(canal, "description").text = (
        "Últimas notas de prensa y comunicaciones "
        "corporativas de Ferrovial"
    )
    ET.SubElement(canal, "language").text = "es"
    ET.SubElement(canal, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    enlace_atom = ET.SubElement(
        canal,
        "{http://www.w3.org/2005/Atom}link",
    )
    enlace_atom.set("href", WEB_URL)
    enlace_atom.set("rel", "self")
    enlace_atom.set("type", "application/rss+xml")

    for noticia in noticias:
        elemento = ET.SubElement(canal, "item")

        ET.SubElement(
            elemento,
            "title",
        ).text = noticia["titulo"]

        ET.SubElement(
            elemento,
            "link",
        ).text = noticia["enlace"]

        ET.SubElement(
            elemento,
            "description",
        ).text = noticia["titulo"]

        ET.SubElement(
            elemento,
            "category",
        ).text = "Notas de prensa"

        identificador = ET.SubElement(elemento, "guid")
        identificador.set("isPermaLink", "true")
        identificador.text = noticia["enlace"]

        if noticia["fecha"]:
            fecha_publicacion = convertir_fecha(
                noticia["fecha"]
            )

            if fecha_publicacion:
                ET.SubElement(
                    elemento,
                    "pubDate",
                ).text = format_datetime(fecha_publicacion)

        if noticia["imagen"]:
            imagen = ET.SubElement(
                elemento,
                "{http://search.yahoo.com/mrss/}content",
            )
            imagen.set("url", noticia["imagen"])
            imagen.set("medium", "image")

    ET.indent(rss, space="  ")

    ET.ElementTree(rss).write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    noticias = descargar_noticias()

    if not noticias:
        raise RuntimeError(
            "No se encontraron notas de prensa de Ferrovial"
        )

    crear_rss(noticias)

    print(
        f"RSS creada correctamente con "
        f"{len(noticias)} noticias"
    )


if __name__ == "__main__":
    main()
