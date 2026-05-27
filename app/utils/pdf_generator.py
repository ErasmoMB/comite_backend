"""Módulo para generar PDFs de dictamenes y subirlos a AWS S3"""
from datetime import datetime, timedelta
from io import BytesIO
import os
import boto3
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def get_s3_client():
    """Inicializa cliente S3 con variables de entorno"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_S3_REGION', 'us-east-1')
    )


def generar_pdf_dictamen(numero_dictamen: str, tipo_dictamen: str, contenido: str, 
                         titulo_protocolo: str, investigadores: str, fecha_firma: datetime) -> str:
    """
    Genera un PDF de dictamen aprobado y lo sube a S3.
    
    Args:
        numero_dictamen: Número único del dictamen (ej: DICT-2026-A1B2C3)
        tipo_dictamen: "aprobado" o "observado"
        contenido: Contenido/texto del dictamen
        titulo_protocolo: Título del protocolo/proyecto
        investigadores: Nombres de investigadores
        fecha_firma: Fecha de firma
    
    Returns:
        URL presignada de S3 (válida por 7 días) o ruta local si S3 no está configurado
    """
    # Generar PDF en memoria
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    
    story = []
    
    # Estilos
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
    
    # Encabezado
    story.append(Paragraph("COMITÉ DE ÉTICA EN INVESTIGACIÓN", title_style))
    story.append(Paragraph("DICTAMEN", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Información del dictamen
    info_data = [
        ["Número de Dictamen:", numero_dictamen],
        ["Fecha de Emisión:", datetime.now().strftime("%d/%m/%Y")],
        ["Fecha de Firma:", fecha_firma.strftime("%d/%m/%Y")],
        ["Resultado:", tipo_dictamen.upper()],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Detalles del protocolo
    story.append(Paragraph("PROTOCOLO", heading_style))
    protocolo_data = [
        ["Título:", titulo_protocolo],
        ["Investigador(es):", investigadores],
    ]
    
    protocolo_table = Table(protocolo_data, colWidths=[1.5*inch, 4.5*inch])
    protocolo_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(protocolo_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Contenido del dictamen
    story.append(Paragraph("RESOLUCIÓN DEL COMITÉ", heading_style))
    story.append(Paragraph(contenido, body_style))
    
    story.append(Spacer(1, 0.5*inch))
    
    # Firma
    story.append(Paragraph("_" * 60, body_style))
    story.append(Paragraph("Mg. JUDITH GABY MORALES MARTINEZ", body_style))
    story.append(Paragraph("Presidenta del Comité de Ética en Investigación", body_style))
    story.append(Paragraph(f"Resolución N° 018-2026-R-UCH", body_style))
    
    # Generar PDF en buffer
    doc.build(story)
    pdf_buffer.seek(0)
    
    # Intentar subir a S3
    try:
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        if s3_bucket:
            s3_client = get_s3_client()
            
            # Nombre del archivo en S3
            s3_key = f"dictamenes/{numero_dictamen}_{datetime.now().timestamp()}.pdf"
            
            # Subir a S3
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=pdf_buffer.getvalue(),
                ContentType='application/pdf',
                Metadata={
                    'tipo_dictamen': tipo_dictamen,
                    'numero': numero_dictamen,
                    'fecha': fecha_firma.isoformat()
                }
            )
            
            # Generar presigned URL (válida por 7 días)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3_bucket, 'Key': s3_key},
                ExpiresIn=7*24*3600  # 7 días en segundos
            )
            
            return presigned_url
    except Exception as e:
        print(f"Error subiendo a S3: {str(e)}")
    
    # Fallback: guardar localmente si S3 no está disponible
    from pathlib import Path
    uploads_dir = Path("uploads/dictamenes")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    pdf_filename = f"{numero_dictamen}_{tipo_dictamen}_{datetime.now().timestamp()}.pdf"
    pdf_path = uploads_dir / pdf_filename
    with open(pdf_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    return str(pdf_path)
