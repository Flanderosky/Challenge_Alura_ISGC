"""
Genera un PDF de ejemplo con políticas internas de empresa.
"""

import os
from fpdf import FPDF


class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Manual de Políticas Internas - AluraTech", ln=True, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 8, body)
        self.ln()


def main():
    os.makedirs("data", exist_ok=True)
    pdf = PDF()
    pdf.add_page()

    pdf.chapter_title("1. Política de Vacaciones")
    pdf.chapter_body(
        "Todos los colaboradores tienen derecho a 15 días hábiles de vacaciones "
        "después de cada año de trabajo continuo. Las vacaciones deben solicitarse "
        "con al menos 15 días de anticipación y aprobarse por el líder directo. "
        "Los días no tomados pueden acumularse hasta un máximo de 30 días."
    )

    pdf.chapter_title("2. Horario de Trabajo")
    pdf.chapter_body(
        "El horario estándar es de lunes a viernes de 9:00 a 18:00. El equipo de "
        "tecnología puede optar por horario flexible, siempre que asista a las "
        "reuniones obligatorias y cumpla con sus entregas."
    )

    pdf.chapter_title("3. Tecnologías Utilizadas")
    pdf.chapter_body(
        "La plataforma principal de la empresa utiliza Python en el back-end, "
        "Streamlit para prototipos internos y React para las aplicaciones de cliente. "
        "La base de datos principal es PostgreSQL y usamos Docker para el despliegue "
        "de servicios. El equipo de datos trabaja con Pandas, LangChain y modelos de "
        "lenguaje de Cohere y OpenAI."
    )

    pdf.chapter_title("4. Código de Conducta")
    pdf.chapter_body(
        "Se espera que todos los colaboradores traten a sus compañeros con respeto, "
        "mantengan la confidencialidad de la información interna y reporten cualquier "
        "incidente de seguridad al área correspondiente."
    )

    pdf.output("data/politicas_ejemplo.pdf")
    print("PDF generado en data/politicas_ejemplo.pdf")


if __name__ == "__main__":
    main()
