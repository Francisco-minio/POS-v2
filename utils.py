from fpdf import FPDF

def generate_invoice_pdf(venta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    
    # Agregar logo
    pdf.image('static/img/logo.png', x=10, y=8, w=33)
    
    pdf.cell(0, 10, 'Boleta de Venta', ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Número de Boleta: {venta.id}', ln=True)
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 12)
    detalles = DetalleVenta.query.filter_by(id_venta=venta.id).all()
    for detalle in detalles:
        producto = Producto.query.get(detalle.id_producto)
        subtotal = detalle.cantidad * detalle.precio_unitario
        pdf.cell(0, 10, f'{producto.nombre} - {detalle.cantidad} x ${detalle.precio_unitario:.2f} = ${subtotal:.2f}', ln=True)
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Total: ${venta.total:.2f}', ln=True)
    
    return pdf.output(dest='S').encode('latin1')
