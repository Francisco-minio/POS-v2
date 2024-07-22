import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import create_app, db
from models import Usuario, Producto, Venta, DetalleVenta
from fpdf import FPDF
import io
import barcode
from barcode.writer import ImageWriter

app = create_app()
def generate_invoice_pdf(venta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    logo_path = 'static/img/logo.png'
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=33)
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Boleta de Venta', 0, 1, 'C')
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Número de Boleta: {venta.id}', 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font('Arial', '', 12)
    
    pdf.cell(60, 10, 'Producto', 1, 0, 'C')
    pdf.cell(30, 10, 'Cantidad', 1, 0, 'C')
    pdf.cell(40, 10, 'Precio Unitario', 1, 0, 'C')
    pdf.cell(40, 10, 'Subtotal', 1, 1, 'C')

    total = 0
    detalles = DetalleVenta.query.filter_by(id_venta=venta.id).all()
    if detalles:
        for detalle in detalles:
            producto = db.session.get(Producto, detalle.id_producto)
            if producto:
                subtotal = detalle.cantidad * detalle.precio_unitario
                total += subtotal
                pdf.cell(60, 10, f'{producto.nombre}', 1)
                pdf.cell(30, 10, f'{detalle.cantidad}', 1, 0, 'C')
                pdf.cell(40, 10, f'${detalle.precio_unitario:.2f}', 1, 0, 'R')
                pdf.cell(40, 10, f'${subtotal:.2f}', 1, 1, 'R')
    else:
        pdf.cell(0, 10, 'No hay detalles para esta venta.', 1, 1, 'C')
    
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Total:', 0, 0, 'L')
    pdf.cell(0, 10, f'${total:.2f}', 0, 1, 'R')

    return pdf.output(dest='S').encode('latin1')

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/productos', methods=['GET', 'POST'])
def productos():
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        cantidad = int(request.form['cantidad'])
        codigo_barra = request.form['codigo_barra']

        nuevo_producto = Producto(codigo_barra=codigo_barra, nombre=nombre, precio=precio, cantidad=cantidad)

        ean = barcode.get('ean13', codigo_barra, writer=ImageWriter())
        filename = f'static/barcodes/{codigo_barra}.png'
        ean.save(filename)

        db.session.add(nuevo_producto)
        db.session.commit()
        flash('Producto agregado con éxito!')
        return redirect(url_for('productos'))

    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

@app.route('/caja', methods=['GET', 'POST'])
def caja():
    if 'user_id' not in session or session['user_role'] not in ['cajero', 'administrador']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        productos_ids = request.form.getlist('producto_id')
        cantidades = request.form.getlist('cantidad')
        total = float(request.form['total'])

        venta = Venta(total=total, id_cajero=session['user_id'])
        db.session.add(venta)
        db.session.commit()

        for producto_id, cantidad in zip(productos_ids, cantidades):
            producto = db.session.get(Producto, producto_id)
            if producto and producto.cantidad >= int(cantidad):
                subtotal = producto.precio * int(cantidad)
                producto.cantidad -= int(cantidad)
                detalle = DetalleVenta(id_venta=venta.id, id_producto=producto.id, cantidad=cantidad, precio_unitario=producto.precio)
                db.session.add(detalle)
            else:
                flash(f'Cantidad insuficiente para el producto {producto.nombre}')
        
        db.session.commit()

        boleta_pdf = generate_invoice_pdf(venta)
        response = send_file(io.BytesIO(boleta_pdf), as_attachment=True, download_name=f'boleta_{venta.id}.pdf', mimetype='application/pdf')

        flash('Venta realizada exitosamente. Se está generando la boleta.')
        return response

    productos = Producto.query.all()
    return render_template('caja.html', productos=productos)

@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    if 'user_id' not in session or session['user_role'] not in ['cajero', 'administrador']:
        return redirect(url_for('login'))

    codigo_barra = request.form['codigo_barra']
    producto = Producto.query.filter_by(codigo_barra=codigo_barra).first()

    if producto:
        venta_items = session.get('venta_items', [])
        found = False
        for item in venta_items:
            if item['codigo_barra'] == codigo_barra:
                item['cantidad'] += 1
                found = True
                break

        if not found:
            venta_items.append({
                'codigo_barra': producto.codigo_barra,
                'nombre': producto.nombre,
                'precio': producto.precio,
                'cantidad': 1
            })

        session['venta_items'] = venta_items
        return jsonify({'success': True, 'venta_items': venta_items})
    else:
        return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404

@app.route('/finalizar_venta', methods=['POST'])
def finalizar_venta():
    if 'user_id' not in session or session['user_role'] not in ['cajero', 'administrador']:
        return redirect(url_for('login'))

    venta_items = session.get('venta_items', [])
    if not venta_items:
        flash('No hay productos en la venta.')
        return redirect(url_for('caja'))

    total = sum(item['precio'] * item['cantidad'] for item in venta_items)
    venta = Venta(total=total, id_cajero=session['user_id'])
    db.session.add(venta)
    db.session.commit()

    for item in venta_items:
        producto = Producto.query.filter_by(codigo_barra=item['codigo_barra']).first()
        if producto and producto.cantidad >= item['cantidad']:
            producto.cantidad -= item['cantidad']
            detalle = DetalleVenta(id_venta=venta.id, id_producto=producto.codigo_barra, cantidad=item['cantidad'], precio_unitario=item['precio'])
            db.session.add(detalle)
        else:
            flash(f'Cantidad insuficiente para el producto {producto.nombre}')
            db.session.rollback()
            return redirect(url_for('caja'))

    db.session.commit()
    session.pop('venta_items', None)

    boleta_pdf = generate_invoice_pdf(venta)
    response = send_file(io.BytesIO(boleta_pdf), as_attachment=True, download_name=f'boleta_{venta.id}.pdf', mimetype='application/pdf')

    flash('Venta realizada exitosamente. Se está generando la boleta.')
    return response

@app.route('/reportes', methods=['GET'])
def reportes():
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))

    ventas = Venta.query.all()
    return render_template('reportes.html', ventas=ventas)

@app.route('/configuracion')
def configuracion():
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))
    return render_template('configuracion.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_nombre = request.form['usuario']
        contrasena = request.form['contrasena']
        user = Usuario.query.filter_by(usuario=usuario_nombre).first()

        if user and check_password_hash(user.contrasena, contrasena):
            session['user_id'] = user.id
            session['user_role'] = user.rol
            return redirect(url_for('index'))
        flash('Credenciales incorrectas. Intente nuevamente.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)