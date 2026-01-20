from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import Usuario
from ..forms import UsuarioForm
from .utilidades import es_administrador

# RF_02: Registrar usuario
@login_required
@user_passes_test(es_administrador)
def registrar_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            try:
                usuario = form.save()
                messages.success(request, f'Usuario {usuario.nombre_completo} registrado exitosamente. Contraseña establecida.')
                return redirect('listar_usuarios')
            except Exception as e:
                messages.error(request, f'Error al registrar usuario: {str(e)}')
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm()
    
    return render(request, 'flota/registrar_usuario.html', {'form': form})


# RF_03: Listar usuarios
@login_required
@user_passes_test(es_administrador)
def listar_usuarios(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        usuarios = Usuario.objects.all().order_by('apellido', 'nombre')
    else:
        usuarios = Usuario.objects.filter(activo=True).order_by('apellido', 'nombre')
    
    return render(request, 'flota/listar_usuarios.html', {
        'usuarios': usuarios,
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })


# RF_04: Modificar usuario
@login_required
@user_passes_test(es_administrador)
def modificar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            try:
                usuario = form.save()
                messages.success(request, f'Usuario {usuario.nombre_completo} modificado exitosamente.')
                return redirect('listar_usuarios')
            except Exception as e:
                messages.error(request, f'Error al modificar usuario: {str(e)}')
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'flota/modificar_usuario.html', {'form': form, 'usuario': usuario})


# RF_05: Deshabilitar usuario
@login_required
@user_passes_test(es_administrador)
def deshabilitar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
    
    # Prevenir que un administrador se deshabilite a sí mismo
    if request.user.rut == usuario.rut:
        messages.error(request, 'No puedes deshabilitarte a ti mismo. Otro administrador debe hacerlo.')
        return redirect('listar_usuarios')
    
    if request.method == 'POST':
        usuario.activo = False
        usuario.save()
        messages.success(request, f'Usuario {usuario.nombre_completo} deshabilitado exitosamente.')
        return redirect('listar_usuarios')
    
    return render(request, 'flota/deshabilitar_usuario.html', {'usuario': usuario})


