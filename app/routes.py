from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Usuario, Producto, Venta, DetalleVenta
from . import db

main = Blueprint('main', __name__)

def init_routes(app):
    app.register_blueprint(main)

@main.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    return render_template('index.html')

# Rutas adicionales como productos, caja, reportes, etc.

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_nombre = request.form['usuario']
        contrasena = request.form['contrasena']
        user = Usuario.query.filter_by(usuario=usuario_nombre).first()

        if user and check_password_hash(user.contrasena, contrasena):
            session['user_id'] = user.id
            session['user_role'] = user.rol
            return redirect(url_for('main.index'))
        flash('Credenciales inválidas.')

    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('main.login'))
