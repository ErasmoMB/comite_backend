import os
from io import BytesIO
from datetime import datetime
from pathlib import Path
import boto3
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def get_s3_client():
    """Initialize S3 client with credentials from environment variables"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION', 'us-east-1')
        )
        return s3_client
    except Exception as e:
        print(f"Error al conectar con S3: {e}")
        return None


def generar_pdf_dictamen(numero_dictamen, titulo, contenido, investigador_nombre, dictamen_fecha):
    """
    Generate PDF dictamen and upload to S3 with presigned URL
    Falls back to local storage if S3 fails
    
    Args:
        numero_dictamen: Dictamen number (e.g., "DIC-2026-001")
        titulo: Dictamen title
        contenido: Dictamen content/body
        investigador_nombre: Researcher name
        dictamen_fecha: Date of dictamen
    
    Returns:
        str: Presigned URL (S3) or local file path, or None on error
    """
    try:
        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#003366'),
            spaceAfter=12,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=colors.HexColor('#003366'),
            spaceAfter=6,
            spaceBefore=6
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            alignment=4,  # Justify
            spaceAfter=10
        )
        
        # Header
        story.append(Paragraph("COMITÉ DE ÉTICA EN INVESTIGACIÓN", title_style))
        story.append(Paragraph("DICTAMEN", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Dictamen information
        info_data = [
            ["Número de Dictamen:", numero_dictamen],
            ["Fecha:", dictamen_fecha],
            ["Investigador:", investigador_nombre],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0F5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Title
        story.append(Paragraph(titulo, heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Content
        story.append(Paragraph(contenido, body_style))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        
        # Try to upload to S3
        s3_client = get_s3_client()
        if s3_client:
            try:
                # Generate S3 key
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"dictamenes/{numero_dictamen}_{timestamp}.pdf"
                
                # Upload to S3
                s3_client.put_object(
                    Bucket=os.getenv('AWS_S3_BUCKET', 'comite-etica-pdfs'),
                    Key=s3_key,
                    Body=pdf_buffer.getvalue(),
                    ContentType='application/pdf'
                )
                
                # Generate presigned URL (7 days)
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': os.getenv('AWS_S3_BUCKET', 'comite-etica-pdfs'), 'Key': s3_key},
                    ExpiresIn=604800  # 7 days
                )
                
                print(f"PDF uploaded to S3: {s3_key}")
                return presigned_url
            except Exception as e:
                print(f"Error subiendo a S3: {e}. Usando almacenamiento local...")
        
        # Fallback to local storage
        uploads_dir = Path("uploads/dictamenes")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{numero_dictamen}_{timestamp}.pdf"
        
        pdf_path = uploads_dir / pdf_filename
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return str(pdf_path)
    
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None


def generar_pdf_evaluacion_completa(
    evaluacion,
    expediente,
    evaluador,
    autores,
    criterios_con_puntajes,
    fecha_str,
):
    """
    Genera el PDF de evaluación siguiendo el formato del documento de referencia.
    Incluye: datos generales, tabla de rúbrica, puntaje total, observaciones y dictamen final.

    Returns:
        tuple: (pdf_buffer: BytesIO, filename: str)
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('Title', parent=styles['Heading1'],
                                  fontSize=14, alignment=TA_CENTER,
                                  spaceAfter=6, textColor=colors.HexColor('#003366'),
                                  fontName='Helvetica-Bold')
    style_subtitle = ParagraphStyle('Subtitle', parent=styles['Heading2'],
                                     fontSize=11, alignment=TA_CENTER,
                                     spaceAfter=12, textColor=colors.HexColor('#003366'))
    style_section = ParagraphStyle('Section', parent=styles['Heading2'],
                                    fontSize=11, spaceBefore=10, spaceAfter=6,
                                    textColor=colors.HexColor('#003366'),
                                    fontName='Helvetica-Bold')
    style_body = ParagraphStyle('Body', parent=styles['Normal'],
                                 fontSize=9, leading=13, alignment=TA_JUSTIFY,
                                 spaceAfter=4)
    style_body_small = ParagraphStyle('BodySmall', parent=styles['Normal'],
                                       fontSize=8, leading=11, alignment=TA_JUSTIFY,
                                       spaceAfter=2)
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'],
                                 fontSize=8, leading=10, spaceAfter=0)
    style_cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'],
                                      fontSize=8, leading=10, spaceAfter=0,
                                      fontName='Helvetica-Bold')
    style_result = ParagraphStyle('Result', parent=styles['Normal'],
                                   fontSize=11, spaceBefore=4, spaceAfter=4,
                                   leftIndent=20, leading=16)

    story = []

    # --- HEADER ---
    story.append(Paragraph("COMITÉ DE ÉTICA EN INVESTIGACIÓN", style_title))
    story.append(Paragraph("FORMATO DE EVALUACIÓN Y DICTAMEN ÉTICO DE PROYECTOS DE INVESTIGACIÓN", style_subtitle))
    story.append(Spacer(1, 0.3*cm))

    # --- DATOS GENERALES ---
    story.append(Paragraph("DATOS GENERALES", style_section))

    autor_str = ", ".join([a.apellidos_nombres for a in autores]) if autores else (expediente.investigador_nombre or "")
    info_data = [
        ["Código de expediente:", expediente.codigo_unico or ""],
        ["Fecha de revisión:", fecha_str],
        ["Título del proyecto:", expediente.titulo_protocolo or ""],
        ["Investigador(a) / Estudiante(s):", autor_str],
        ["Revisor:", f"{evaluador.nombre} {evaluador.apellido}".strip()],
    ]
    info_table = Table(info_data, colWidths=[4.5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0F5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    # --- EVALUACIÓN ÉTICA (tabla de rúbrica) ---
    story.append(Paragraph("EVALUACIÓN ÉTICA", style_section))

    criterios_con_puntajes.sort(key=lambda x: x.get("orden", 0))
    header = [Paragraph("<b>Criterio</b>", style_cell_bold),
              Paragraph("<b>Descripción</b>", style_cell_bold),
              Paragraph("<b>Puntaje<br/>Máximo</b>", style_cell_bold),
              Paragraph("<b>Puntaje<br/>Obtenido</b>", style_cell_bold),
              Paragraph("<b>Observaciones</b>", style_cell_bold)]

    table_data = [header]
    for item in criterios_con_puntajes:
        table_data.append([
            Paragraph(item.get("nombre", ""), style_cell),
            Paragraph(item.get("descripcion", ""), style_body_small),
            Paragraph(str(item.get("puntaje_max", 0)), style_cell),
            Paragraph(str(item.get("puntaje", 0)), style_cell),
            Paragraph(item.get("observacion", "") or "", style_cell),
        ])

    rubrica_table = Table(table_data, colWidths=[3.2*cm, 5.5*cm, 1.5*cm, 1.5*cm, 3.8*cm],
                          repeatRows=1)
    rubrica_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
    ]))
    story.append(rubrica_table)
    story.append(Spacer(1, 0.3*cm))

    # --- PUNTAJE TOTAL ---
    total = evaluacion.puntaje_total or sum(item.get("puntaje", 0) for item in criterios_con_puntajes)
    story.append(Paragraph(f"<b>Puntaje Total: {total} / 20</b>", style_section))
    story.append(Spacer(1, 0.3*cm))

    # --- OBSERVACIONES DEL COMITÉ ---
    story.append(Paragraph("OBSERVACIONES DEL COMITÉ", style_section))
    obs_text = evaluacion.observaciones or "Ninguna"
    story.append(Paragraph(obs_text, style_body))
    story.append(Spacer(1, 0.3*cm))

    # --- DICTAMEN FINAL ---
    story.append(Paragraph("DICTAMEN FINAL", style_section))

    resultados = [
        ("aprobado", "Aprobado"),
        ("aprobado_observaciones", "Aprobado con observaciones"),
        ("no_aprobado", "No aprobado"),
    ]
    for key, label in resultados:
        checked = "X" if evaluacion.resultado == key else " "
        story.append(Paragraph(f"[{checked}]  {label}", style_result))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Fecha de emisión: {fecha_str}", style_body))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    filename = f"evaluacion_{evaluacion.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return buffer, filename


def guardar_pdf_evaluacion(evaluacion, expediente, evaluador, autores, criterios_con_puntajes):
    """Generate and save the evaluation PDF locally, returns the file path."""
    from datetime import datetime
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    buffer, filename = generar_pdf_evaluacion_completa(
        evaluacion, expediente, evaluador, autores,
        criterios_con_puntajes, fecha_str,
    )

    uploads_dir = Path("uploads/evaluaciones")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    filepath = uploads_dir / filename
    with open(filepath, "wb") as f:
        f.write(buffer.getvalue())

    return str(filepath)
