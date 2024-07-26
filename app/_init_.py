from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)

    with app.app_context():
        from .models import Usuario, Producto, Venta, DetalleVenta
        db.create_all()
        # Crear usuario administrador si no existe
        admin = Usuario.query.filter_by(usuario='admin').first()
        if not admin:
            hashed_password = generate_password_hash('admin_pass', method='pbkdf2:sha256')
            admin = Usuario(usuario='admin', contrasena=hashed_password, rol='administrador')
            db.session.add(admin)
            db.session.commit()

    from .routes import init_routes
    init_routes(app)

    return app
