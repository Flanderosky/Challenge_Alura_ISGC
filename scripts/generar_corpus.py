"""
Genera el corpus documental de Meridia, la tienda ficticia del proyecto.

Cinco documentos de atención al cliente en PDF y dos conjuntos de datos en CSV.
Todo es determinista: la misma ejecución produce los mismos archivos, así que
el corpus se puede regenerar y auditar en vez de aparecer de la nada.

Uso:
    python scripts/generar_corpus.py
"""

import csv
import os
import random
from datetime import date, timedelta
from typing import List, Tuple

from fpdf import FPDF
from fpdf.enums import XPos, YPos

DATA = "data"
MARCA = "Meridia"
SEMILLA = 20260724

# Las fuentes base del PDF cubren latin-1: los acentos y la eñe entran sin
# problema, pero no las rayas largas ni las comillas tipográficas.
Seccion = Tuple[str, List[str]]


# --------------------------------------------------------------------- PDFs


class Documento(FPDF):
    def __init__(self, titulo: str, subtitulo: str):
        super().__init__()
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 6, MARCA.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(180, 180, 180)
        self.line(10, 20, 200, 20)
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"{self.titulo} · página {self.page_no()}", align="C")

    def portada(self):
        self.add_page()
        self.set_font("Helvetica", "B", 20)
        self.multi_cell(0, 10, self.titulo)
        self.ln(2)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(90, 90, 90)
        self.multi_cell(0, 6, self.subtitulo)
        self.set_text_color(0, 0, 0)
        self.ln(6)

    def seccion(self, encabezado: str, parrafos: List[str]):
        self.set_font("Helvetica", "B", 13)
        self.ln(3)
        self.multi_cell(0, 7, encabezado)
        self.ln(1)
        self.set_font("Helvetica", "", 11)
        for parrafo in parrafos:
            self.multi_cell(0, 6, parrafo)
            self.ln(2)


def escribir_pdf(nombre: str, titulo: str, subtitulo: str, secciones: List[Seccion]) -> None:
    pdf = Documento(titulo, subtitulo)
    pdf.portada()
    for encabezado, parrafos in secciones:
        pdf.seccion(encabezado, parrafos)
    ruta = os.path.join(DATA, nombre)
    pdf.output(ruta)
    print(f"  {ruta}  ({pdf.page_no()} paginas)")


DEVOLUCIONES: List[Seccion] = [
    ("1. Plazo para solicitar una devolución", [
        "El cliente cuenta con 30 días naturales contados desde la fecha de entrega para "
        "solicitar la devolución de un producto. El plazo se cuenta desde que la paquetería "
        "registra la entrega, no desde la fecha de compra.",
        "Los productos de la categoría Electrónica tienen un plazo reducido de 14 días "
        "naturales, por las condiciones de garantía del fabricante.",
        "Pasado el plazo, la solicitud solo procede si el producto presenta un defecto de "
        "fabricación cubierto por la garantía legal de 90 días descrita en los términos y "
        "condiciones.",
    ]),
    ("2. Cómo iniciar la solicitud", [
        "La devolución se inicia desde la sección Mis pedidos de la cuenta, seleccionando el "
        "pedido y el producto correspondiente. El sistema genera una guía de retorno "
        "prepagada en un plazo máximo de 24 horas hábiles.",
        "Si la compra se realizó como invitado, la solicitud se envía al correo "
        "devoluciones@meridia.mx indicando el número de pedido y el motivo.",
        "Cada solicitud recibe un folio con el formato DEV seguido de seis dígitos. Ese folio "
        "es el que se debe citar en cualquier comunicación posterior.",
    ]),
    ("3. Costo del envío de retorno", [
        "Cuando la devolución se debe a un producto defectuoso, incompleto, dañado en "
        "tránsito o distinto al solicitado, Meridia cubre el costo total del envío de retorno.",
        "Cuando la devolución se debe a arrepentimiento del cliente, el costo del envío de "
        "retorno es de 120 pesos mexicanos y se descuenta del monto reembolsado.",
        "El primer cambio de talla de cualquier producto de la categoría Ropa no tiene costo "
        "de envío. A partir del segundo cambio sobre el mismo pedido aplica la tarifa de 120 "
        "pesos.",
    ]),
    ("4. Estado en que debe devolverse el producto", [
        "El producto debe devolverse completo, con todos sus accesorios, manuales y empaques "
        "originales, y sin señales de uso más allá de la revisión razonable.",
        "Los productos de la categoría Electrónica deben conservar los sellos de garantía "
        "intactos. Un sello roto invalida la devolución por arrepentimiento, aunque no la "
        "garantía por defecto de fabricación.",
    ]),
    ("5. Productos que no admiten devolución", [
        "No se aceptan devoluciones de licencias de software una vez activadas, productos de "
        "higiene personal cuyo empaque haya sido abierto, artículos personalizados o grabados "
        "por encargo, ni tarjetas de regalo.",
        "Tampoco se aceptan devoluciones de productos adquiridos en liquidación final, "
        "identificados en la ficha del producto con la leyenda venta final.",
    ]),
    ("6. Plazos y forma del reembolso", [
        "Una vez que el centro de devoluciones recibe y valida el producto, el reembolso se "
        "procesa en un plazo de 5 a 10 días hábiles.",
        "El reembolso se emite siempre al método de pago original. En pagos con tarjeta de "
        "crédito, el abono puede tardar hasta dos periodos de corte en reflejarse, según el "
        "banco emisor. En pagos en efectivo se solicitan datos bancarios para transferencia.",
        "El monto reembolsado incluye el precio del producto y los impuestos. El costo del "
        "envío original solo se reembolsa cuando la devolución se origina por causa "
        "atribuible a Meridia.",
    ]),
    ("7. Cancelaciones antes del envío", [
        "Un pedido puede cancelarse sin costo mientras su estado sea En preparación. Una vez "
        "que pasa a estado Enviado, la cancelación se tramita como devolución ordinaria.",
        "La cancelación se solicita desde Mis pedidos y el reembolso se procesa en un plazo "
        "de 3 a 5 días hábiles, menor al de una devolución porque no requiere validación "
        "física del producto.",
    ]),
]

ENVIOS: List[Seccion] = [
    ("1. Modalidades de envío disponibles", [
        "Meridia ofrece tres modalidades de envío. El plazo se cuenta en días hábiles a "
        "partir de la confirmación del pago, sin contar sábados, domingos ni días festivos.",
        "Envío estándar: entrega en 3 a 5 días hábiles, con un costo de 99 pesos mexicanos. "
        "Es gratuito en pedidos cuyo importe iguale o supere los 999 pesos.",
        "Envío exprés: entrega en 1 a 2 días hábiles, con un costo de 199 pesos. No tiene "
        "umbral de gratuidad.",
        "Envío el mismo día: disponible únicamente en Ciudad de México y Monterrey, para "
        "pedidos confirmados antes de las 12:00 horas, con un costo de 299 pesos.",
    ]),
    ("2. Cobertura geográfica", [
        "Se realizan envíos a los 32 estados de la república mexicana. Las localidades "
        "clasificadas como zona extendida por la paquetería suman 2 días hábiles adicionales "
        "al plazo de la modalidad contratada.",
        "El envío el mismo día está limitado a las alcaldías de Ciudad de México y a los "
        "municipios del área metropolitana de Monterrey. Fuera de esas zonas, la opción no "
        "aparece durante el pago.",
        "No se realizan envíos internacionales.",
    ]),
    ("3. Empresas de paquetería", [
        "Meridia trabaja con tres transportistas: Estafeta para envío estándar, DHL para "
        "envío exprés y Paquetexpress para zonas extendidas y envío el mismo día.",
        "La asignación del transportista depende del destino y la modalidad, y no puede "
        "elegirse durante la compra.",
    ]),
    ("4. Rastreo del pedido", [
        "El número de rastreo se envía por correo electrónico dentro de las 24 horas "
        "siguientes a que el pedido cambia a estado Enviado.",
        "El rastreo también está disponible en la sección Mis pedidos. Los estados posibles "
        "son En preparación, Enviado, En reparto, Entregado e Incidencia.",
        "Un pedido puede permanecer hasta 48 horas sin actualizaciones de rastreo sin que "
        "ello implique un problema: las paqueterías registran los movimientos al llegar a "
        "cada centro de distribución.",
    ]),
    ("5. Entregas fallidas e incidencias", [
        "La paquetería realiza hasta tres intentos de entrega en días hábiles consecutivos. "
        "Tras el tercer intento fallido, el paquete se resguarda 5 días hábiles en la sucursal "
        "más cercana antes de retornar al centro de distribución de Meridia.",
        "Si el pedido retorna por no haber sido recogido, se reembolsa el importe del producto "
        "descontando el costo del envío original.",
        "Un pedido se considera extraviado cuando permanece 10 días hábiles sin movimiento de "
        "rastreo. En ese caso se abre una reclamación ante la paquetería y Meridia repone el "
        "producto o reembolsa el importe completo, a elección del cliente.",
    ]),
    ("6. Paquetes dañados en tránsito", [
        "Si el paquete llega visiblemente dañado, se recomienda no rechazarlo y documentar el "
        "estado con fotografías del empaque antes de abrirlo.",
        "La reclamación por daño en tránsito debe presentarse dentro de las 48 horas "
        "siguientes a la entrega, adjuntando las fotografías al correo incidencias@meridia.mx. "
        "La reposición se envía sin costo en modalidad exprés.",
    ]),
]

PRIVACIDAD: List[Seccion] = [
    ("1. Responsable del tratamiento", [
        "Meridia Comercio Digital, S.A. de C.V., con domicilio en Avenida Reforma 222, "
        "colonia Juárez, Ciudad de México, es responsable del tratamiento de los datos "
        "personales recabados a través de su tienda en línea.",
        "Cualquier consulta relacionada con esta política puede dirigirse a "
        "privacidad@meridia.mx.",
    ]),
    ("2. Datos que se recaban", [
        "Datos de identificación y contacto: nombre completo, correo electrónico, teléfono y "
        "domicilio de entrega y facturación.",
        "Datos de la transacción: historial de pedidos, importes, método de pago y dirección "
        "de envío. Meridia no almacena el número completo de tarjeta: el procesador de pagos "
        "entrega únicamente los cuatro últimos dígitos y la marca.",
        "Datos de navegación: dirección IP, tipo de dispositivo, páginas visitadas y "
        "productos consultados, obtenidos mediante cookies.",
    ]),
    ("3. Finalidades del tratamiento", [
        "Finalidades primarias, necesarias para la relación comercial: procesar y entregar "
        "pedidos, emitir comprobantes fiscales, gestionar devoluciones y atender solicitudes "
        "de soporte.",
        "Finalidades secundarias, que requieren consentimiento y pueden revocarse en "
        "cualquier momento: envío de promociones, encuestas de satisfacción y recomendaciones "
        "personalizadas de productos.",
    ]),
    ("4. Transferencia de datos", [
        "Meridia no vende ni renta datos personales a terceros.",
        "Los datos se comparten únicamente con las empresas de paquetería, para la entrega "
        "del pedido, y con el procesador de pagos, para la autorización del cobro. Ambos "
        "están obligados contractualmente a tratar los datos solo para esa finalidad.",
        "Los datos podrán entregarse a autoridades competentes cuando exista un requerimiento "
        "fundado y motivado.",
    ]),
    ("5. Plazo de conservación", [
        "Los datos asociados a una transacción se conservan 5 años, plazo que corresponde a "
        "las obligaciones fiscales aplicables.",
        "Los datos de navegación se conservan 12 meses. Los datos tratados con fines "
        "promocionales se eliminan al revocarse el consentimiento.",
    ]),
    ("6. Derechos ARCO", [
        "El titular puede ejercer sus derechos de acceso, rectificación, cancelación y "
        "oposición enviando una solicitud a privacidad@meridia.mx desde el correo registrado "
        "en su cuenta.",
        "La solicitud debe incluir el nombre del titular, la descripción clara del derecho "
        "que se ejerce y un documento que acredite la identidad.",
        "Meridia responde en un plazo máximo de 20 días hábiles. Si la solicitud procede, se "
        "hace efectiva dentro de los 15 días hábiles siguientes a la respuesta.",
    ]),
    ("7. Uso de cookies", [
        "Se utilizan cookies necesarias, que permiten el funcionamiento del carrito y la "
        "sesión, y cookies analíticas y de personalización, que pueden rechazarse desde el "
        "aviso que aparece en la primera visita.",
        "El rechazo de las cookies opcionales no limita la posibilidad de comprar.",
    ]),
]

FAQ: List[Seccion] = [
    ("Pedidos y pagos", [
        "¿Qué métodos de pago se aceptan? Tarjetas de crédito y débito Visa, Mastercard y "
        "American Express, transferencia SPEI, y pago en efectivo en tiendas de conveniencia "
        "mediante referencia con vigencia de 48 horas.",
        "¿Puedo pagar a meses sin intereses? Sí, a 3, 6 y 12 meses con tarjetas de crédito "
        "participantes, en compras iguales o superiores a 3,000 pesos.",
        "¿Cuándo se cobra el pedido? El cargo se realiza al confirmar la compra. En pagos con "
        "referencia en efectivo, el pedido se prepara al acreditarse el pago.",
        "¿Puedo modificar mi pedido después de comprarlo? Solo puede modificarse la dirección "
        "de entrega, y únicamente mientras el pedido esté En preparación.",
    ]),
    ("Envíos y entregas", [
        "¿Cuánto tarda mi pedido? El envío estándar tarda de 3 a 5 días hábiles, el exprés de "
        "1 a 2, y el del mismo día se entrega la misma jornada si se confirma antes de las "
        "12:00 horas.",
        "¿Cuándo es gratis el envío? El envío estándar es gratuito en pedidos de 999 pesos o "
        "más.",
        "¿Cómo rastreo mi pedido? Con el número de rastreo que se envía por correo dentro de "
        "las 24 horas posteriores al cambio a estado Enviado, o desde Mis pedidos.",
        "¿Qué pasa si no estoy cuando llega el paquete? La paquetería hace hasta tres intentos "
        "de entrega en días hábiles consecutivos.",
    ]),
    ("Devoluciones y reembolsos", [
        "¿Cuánto tiempo tengo para devolver? 30 días naturales desde la entrega, o 14 días en "
        "la categoría Electrónica.",
        "¿Cuánto tarda el reembolso? De 5 a 10 días hábiles desde que se valida el producto "
        "devuelto, al mismo método de pago con el que se compró.",
        "¿Tengo que pagar el envío de la devolución? No, si el producto llegó defectuoso o "
        "equivocado. Si es por arrepentimiento, se descuentan 120 pesos del reembolso.",
        "¿Puedo cambiar la talla? Sí, el primer cambio de talla en la categoría Ropa no tiene "
        "costo de envío.",
    ]),
    ("Cuenta y facturación", [
        "¿Necesito una cuenta para comprar? No, se puede comprar como invitado, aunque la "
        "cuenta permite rastrear pedidos e iniciar devoluciones sin escribir a soporte.",
        "¿Cómo solicito factura? Desde Mis pedidos, dentro del mismo mes calendario de la "
        "compra, cargando la constancia de situación fiscal.",
        "¿Puedo facturar un pedido de un mes anterior? No. Las facturas solo pueden emitirse "
        "dentro del mes calendario en que se realizó la compra.",
    ]),
    ("Garantía y soporte", [
        "¿Qué garantía tienen los productos? La garantía legal es de 90 días por defectos de "
        "fabricación. Algunos fabricantes ofrecen plazos mayores, indicados en la ficha del "
        "producto.",
        "¿Cómo contacto a soporte? Por chat en el sitio de lunes a viernes de 9:00 a 19:00 y "
        "sábados de 10:00 a 14:00, o por correo a soporte@meridia.mx, con respuesta en un "
        "plazo máximo de 24 horas hábiles.",
    ]),
]

TERMINOS: List[Seccion] = [
    ("1. Aceptación de los términos", [
        "El uso de la tienda en línea de Meridia implica la aceptación de estos términos y "
        "condiciones. Si el usuario no está de acuerdo con alguno de ellos, debe abstenerse "
        "de utilizar el sitio.",
        "Meridia puede modificar estos términos en cualquier momento. Los cambios aplican a "
        "los pedidos realizados a partir de su publicación.",
    ]),
    ("2. Capacidad para contratar", [
        "Para realizar una compra es necesario ser mayor de 18 años y contar con capacidad "
        "legal para contratar.",
        "El usuario es responsable de la veracidad de los datos que proporciona. Un domicilio "
        "incorrecto que impida la entrega no da derecho a reembolso del costo de envío.",
    ]),
    ("3. Precios, impuestos y disponibilidad", [
        "Todos los precios se expresan en pesos mexicanos e incluyen el impuesto al valor "
        "agregado.",
        "Los precios pueden cambiar sin previo aviso, pero el precio aplicable es siempre el "
        "vigente al momento de confirmar el pedido.",
        "La disponibilidad se actualiza de forma continua. Si un producto se agota después de "
        "confirmado el pedido, Meridia lo notifica en un plazo de 48 horas y reembolsa el "
        "importe completo o propone un producto equivalente.",
    ]),
    ("4. Garantía legal", [
        "Todos los productos cuentan con una garantía de 90 días naturales por defectos de "
        "fabricación, contados desde la fecha de entrega.",
        "La garantía no cubre daños por uso indebido, caídas, contacto con líquidos ni "
        "desgaste normal. Tampoco cubre consumibles.",
        "Para hacer válida la garantía se requiere el número de pedido y una descripción del "
        "defecto. Meridia repara, repone o reembolsa, en ese orden de preferencia.",
    ]),
    ("5. Promociones y cupones", [
        "Los cupones de descuento no son acumulables entre sí ni aplicables sobre productos "
        "en liquidación final, salvo que la promoción lo indique expresamente.",
        "Cada cupón tiene una vigencia y un importe mínimo de compra especificados en sus "
        "condiciones. Un cupón aplicado a un pedido que después se devuelve no se restituye.",
    ]),
    ("6. Propiedad intelectual", [
        "Los contenidos del sitio, incluidos textos, fotografías de producto, logotipos y "
        "código, son propiedad de Meridia o se utilizan bajo licencia.",
        "Queda prohibida su reproducción con fines comerciales sin autorización previa por "
        "escrito.",
    ]),
    ("7. Limitación de responsabilidad", [
        "Meridia responde por el cumplimiento del pedido en los términos descritos en estos "
        "documentos. No responde por daños indirectos derivados del uso de los productos "
        "fuera de las indicaciones del fabricante.",
        "Las interrupciones del sitio por mantenimiento o causas de fuerza mayor no generan "
        "derecho a indemnización.",
    ]),
    ("8. Ley aplicable y jurisdicción", [
        "Estos términos se rigen por la legislación mexicana. Para la interpretación y "
        "cumplimiento, las partes se someten a los tribunales de la Ciudad de México, "
        "renunciando a cualquier otro fuero.",
        "El usuario puede acudir a la Procuraduría Federal del Consumidor para presentar "
        "cualquier queja relacionada con su compra.",
    ]),
]

PDFS = [
    ("politica_devoluciones.pdf", "Política de devoluciones y reembolsos",
     f"{MARCA} · atención al cliente · vigente desde enero de 2026", DEVOLUCIONES),
    ("guia_envios.pdf", "Guía de envíos y entregas",
     f"{MARCA} · atención al cliente · vigente desde enero de 2026", ENVIOS),
    ("politica_privacidad.pdf", "Política de privacidad",
     f"{MARCA} · aviso de privacidad integral · vigente desde enero de 2026", PRIVACIDAD),
    ("preguntas_frecuentes.pdf", "Preguntas frecuentes",
     f"{MARCA} · centro de ayuda · actualizado en enero de 2026", FAQ),
    ("terminos_condiciones.pdf", "Términos y condiciones de uso",
     f"{MARCA} · documento legal · vigente desde enero de 2026", TERMINOS),
]


# --------------------------------------------------------------------- CSVs

CATALOGO = [
    # (producto, categoría, precio)
    ("Laptop Meridia Pro 14", "Electrónica", 24990),
    ("Monitor curvo 27 pulgadas", "Electrónica", 6490),
    ("Teclado mecánico retroiluminado", "Electrónica", 1890),
    ("Audífonos con cancelación de ruido", "Electrónica", 3990),
    ("Silla ergonómica de oficina", "Hogar", 5490),
    ("Escritorio elevable", "Hogar", 8990),
    ("Lámpara de escritorio LED", "Hogar", 890),
    ("Cafetera de goteo programable", "Hogar", 1490),
    ("Mochila para laptop impermeable", "Accesorios", 1290),
    ("Cargador USB-C de 65 W", "Accesorios", 790),
    ("Funda protectora para laptop", "Accesorios", 490),
    ("Sudadera con capucha", "Ropa", 899),
    ("Camiseta de algodón orgánico", "Ropa", 399),
    ("Chamarra ligera impermeable", "Ropa", 1690),
]

REGIONES = ["Ciudad de México", "Nuevo León", "Jalisco", "Puebla", "Yucatán", "Baja California"]
CANALES = ["Web", "App móvil", "Marketplace"]
ENVIO_TIPOS = ["Estándar", "Exprés", "Mismo día"]
MOTIVOS = [
    "Producto defectuoso",
    "Talla incorrecta",
    "Arrepentimiento",
    "Producto equivocado",
    "Dañado en tránsito",
]


def generar_pedidos(n: int) -> List[dict]:
    rng = random.Random(SEMILLA)
    inicio = date(2026, 1, 1)
    filas = []
    for i in range(n):
        producto, categoria, precio = rng.choice(CATALOGO)
        unidades = rng.choices([1, 1, 1, 2, 2, 3], k=1)[0]
        region = rng.choice(REGIONES)
        envio = rng.choices(ENVIO_TIPOS, weights=[70, 25, 5], k=1)[0]
        dias = {"Estándar": rng.randint(3, 6), "Exprés": rng.randint(1, 2), "Mismo día": 0}[envio]
        filas.append({
            "fecha": (inicio + timedelta(days=rng.randint(0, 364))).isoformat(),
            "pedido": f"MER-{100000 + i}",
            "categoria": categoria,
            "producto": producto,
            "region": region,
            "canal": rng.choice(CANALES),
            "envio": envio,
            "unidades": unidades,
            "importe": round(precio * unidades, 2),
            "dias_entrega": dias,
        })
    filas.sort(key=lambda f: f["fecha"])
    return filas


def generar_devoluciones(pedidos: List[dict], tasa: float) -> List[dict]:
    rng = random.Random(SEMILLA + 1)
    filas = []
    for pedido in pedidos:
        if rng.random() > tasa:
            continue
        motivo = rng.choices(MOTIVOS, weights=[30, 25, 20, 15, 10], k=1)[0]
        entrega = date.fromisoformat(pedido["fecha"]) + timedelta(days=pedido["dias_entrega"])
        filas.append({
            "fecha_solicitud": (entrega + timedelta(days=rng.randint(1, 25))).isoformat(),
            "pedido": pedido["pedido"],
            "categoria": pedido["categoria"],
            "producto": pedido["producto"],
            "motivo": motivo,
            "importe_reembolsado": pedido["importe"],
            "dias_resolucion": rng.randint(3, 12),
        })
    filas.sort(key=lambda f: f["fecha_solicitud"])
    return filas


def escribir_csv(nombre: str, filas: List[dict]) -> None:
    ruta = os.path.join(DATA, nombre)
    with open(ruta, "w", encoding="utf-8", newline="") as handle:
        escritor = csv.DictWriter(handle, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"  {ruta}  ({len(filas)} filas)")


def main() -> None:
    os.makedirs(DATA, exist_ok=True)

    print("Documentos PDF:")
    for nombre, titulo, subtitulo, secciones in PDFS:
        escribir_pdf(nombre, titulo, subtitulo, secciones)

    print("Conjuntos de datos:")
    pedidos = generar_pedidos(420)
    escribir_csv("pedidos_2026.csv", pedidos)
    escribir_csv("devoluciones_2026.csv", generar_devoluciones(pedidos, tasa=0.18))


if __name__ == "__main__":
    main()
