import os
from io import BytesIO
from datetime import datetime
from pathlib import Path
import boto3
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


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
