import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Opcional, pero recomendado para desactivar el seguimiento de modificaciones

    db.init_app(app)

    with app.app_context():
        from models import Usuario, Producto, Venta, DetalleVenta  # Importar modelos aquí para crear tablas
        db.create_all()  # Crear tablas en la base de datos

        # Crear usuario administrador si no existe
        admin = Usuario.query.filter_by(usuario='admin').first()
        if not admin:
            hashed_password = generate_password_hash('admin_pass', method='pbkdf2:sha256')  # Cambia a tu método de hash
            admin = Usuario(usuario='admin', contrasena=hashed_password, rol='administrador')
            db.session.add(admin)
            db.session.commit()

    return app
