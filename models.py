from config import db
from sqlalchemy import Column, Integer, String, Float

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    contrasena = db.Column(db.String(120), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

class Producto(db.Model):
    __tablename__ = 'producto'
    codigo_barra = db.Column(db.String(12), primary_key=True, unique=True, nullable=False)
    nombre = db.Column(db.String(80), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    def __init__(self, nombre, precio, cantidad, codigo_barra):
        self.nombre = nombre
        self.precio = precio
        self.cantidad = cantidad
        self.codigo_barra = codigo_barra

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float, nullable=False)
    id_cajero = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)

class DetalleVenta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    codigo_barra_producto = db.Column(db.String(12), db.ForeignKey('producto.codigo_barra'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(200), nullable=True)
