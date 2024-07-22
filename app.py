import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
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

    # Agregar logo
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
    
    # Encabezado de la tabla
    pdf.cell(60, 10, 'Producto', 1, 0, 'C')
    pdf.cell(30, 10, 'Cantidad', 1, 0, 'C')
    pdf.cell(40, 10, 'Precio Unitario', 1, 0, 'C')
    pdf.cell(40, 10, 'Subtotal', 1, 1, 'C')

    total = 0
    detalles = DetalleVenta.query.filter_by(id_venta=venta.id).all()
    if detalles:
        for detalle in detalles:
            producto = db.session.get(Producto, detalle.id_producto)  # Usar Session.get() en lugar de query.get()
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
    
    # Total
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Total:', 0, 0, 'L')
    pdf.cell(0, 10, f'${total:.2f}', 0, 1, 'R')

    return pdf.output(dest='S').encode('latin1')

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/caja', methods=['GET', 'POST'])
def caja():
    if 'user_id' not in session or session['user_role'] not in ['cajero', 'administrador']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        productos_barras = request.form.getlist('producto_barra')  # Cambiado de producto_id a producto_barra
        cantidades = request.form.getlist('cantidad')
        total = float(request.form['total'])

        venta = Venta(total=total, id_cajero=session['user_id'])
        db.session.add(venta)
        db.session.commit()

        for codigo_barra, cantidad in zip(productos_barras, cantidades):
            producto = db.session.get(Producto, codigo_barra)  # Cambiado a codigo_barra
            if producto and producto.cantidad >= int(cantidad):
                subtotal = producto.precio * int(cantidad)
                producto.cantidad -= int(cantidad)
                detalle = DetalleVenta(id_venta=venta.id, id_producto=producto.codigo_barra, cantidad=cantidad, precio_unitario=producto.precio)  # Cambiado a codigo_barra
                db.session.add(detalle)
            else:
                flash(f'Cantidad insuficiente para el producto {producto.nombre}')
        
        db.session.commit()

        # Generar boleta en PDF
        boleta_pdf = generate_invoice_pdf(venta)
        response = send_file(io.BytesIO(boleta_pdf), as_attachment=True, download_name=f'boleta_{venta.id}.pdf', mimetype='application/pdf')

        # Redirigir a la página de caja después de completar la venta
        flash('Venta realizada exitosamente. Se está generando la boleta.')
        return response

    productos = Producto.query.all()
    return render_template('caja.html', productos=productos)


@app.route('/productos', methods=['GET', 'POST'])
def productos():
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        cantidad = int(request.form['cantidad'])
        codigo_barra = request.form['codigo_barra']

        nuevo_producto = Producto(nombre=nombre, precio=precio, cantidad=cantidad, codigo_barra=codigo_barra)

        # Generar el código de barras
        ean = barcode.get('ean13', codigo_barra, writer=ImageWriter())
        filename = f'static/barcodes/{codigo_barra}.png'
        ean.save(filename)

        db.session.add(nuevo_producto)
        db.session.commit()
        flash('Producto agregado con éxito!')
        return redirect(url_for('productos'))

    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

@app.route('/editar_producto/<codigo_barra>', methods=['GET', 'POST'])
def editar_producto(codigo_barra):
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))

    producto = Producto.query.get(codigo_barra)
    if not producto:
        flash('Producto no encontrado.')
        return redirect(url_for('productos'))

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.precio = float(request.form['precio'])
        producto.cantidad = int(request.form['cantidad'])
        # `codigo_barra` no se actualiza ya que es la clave primaria
        
        db.session.commit()
        flash('Producto actualizado con éxito!')
        return redirect(url_for('productos'))

    return render_template('editar_producto.html', producto=producto)

@app.route('/eliminar_producto/<codigo_barra>', methods=['POST'])
def eliminar_producto(codigo_barra):
    if 'user_id' not in session or session['user_role'] != 'administrador':
        return redirect(url_for('login'))

    producto = Producto.query.filter_by(codigo_barra=codigo_barra).first()
    if producto:
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado con éxito!')
    else:
        flash('Producto no encontrado.')

    return redirect(url_for('productos'))

@app.route('/buscar_producto', methods=['GET'])
def buscar_producto():
    if 'user_id' not in session or session['user_role'] not in ['cajero', 'administrador']:
        return redirect(url_for('login'))
    
    codigo_barra = request.args.get('codigo_barra')
    producto = Producto.query.filter_by(codigo_barra=codigo_barra).first()
    
    if producto:
        return {
            'nombre': producto.nombre,
            'precio': producto.precio,
            'cantidad': producto.cantidad
        }
    else:
        return {'error': 'Producto no encontrado'}, 404


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
        flash('Credenciales inválidas.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)

