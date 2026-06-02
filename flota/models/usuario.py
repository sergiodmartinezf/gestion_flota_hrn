from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

# --- GESTIÓN DE USUARIOS ---

class UsuarioManager(BaseUserManager):
    def create_user(self, rut, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un email')
        if not rut:
            raise ValueError('El usuario debe tener un RUT')
        
        email = self.normalize_email(email)
        user = self.model(rut=rut, email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # Contraseña por defecto: rut
            user.set_password(rut)
        
        user.save(using=self._db)
        return user

    def create_superuser(self, rut, email, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'Administrador')
        extra_fields.setdefault('activo', True)
        
        if password is None:
            password = rut  # Contraseña por defecto para superusuarios
        
        return self.create_user(rut, email, password, **extra_fields)

class Usuario(AbstractBaseUser):
    ROLES = [
        ('Administrador', 'Administrador'),
        ('Conductor', 'Conductor'),
        ('Visualizador', 'Visualizador'),
    ]
    
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='Visualizador')
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'rut'
    REQUIRED_FIELDS = ['email', 'nombre', 'apellido']
    
    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.rut})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def has_perm(self, perm, obj=None):
        return self.rol == 'Administrador'
    
    def has_module_perms(self, app_label):
        return True
    
    @property
    def is_staff(self):
        return self.rol == 'Administrador'
    
    @property
    def is_active(self):
        return self.activo


