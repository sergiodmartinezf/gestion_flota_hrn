from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import Proveedor
from ..forms import ProveedorForm
from .utilidades import es_administrador

# Listar proveedores
@login_required
@user_passes_test(es_administrador)
def listar_proveedores(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        proveedores = Proveedor.objects.all().order_by('nombre_fantasia')
    else:
        proveedores = Proveedor.objects.filter(activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/listar_proveedores.html', {
        'proveedores': proveedores,
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })


# Registrar proveedores
@login_required
@user_passes_test(es_administrador)
def registrar_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'Proveedor {proveedor.nombre_fantasia} registrado exitosamente.')
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm()
    
    return render(request, 'flota/registrar_proveedor.html', {'form': form, 'titulo': 'Registrar Proveedor'})


# Modificar proveedores
@login_required
@user_passes_test(es_administrador)
def modificar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'Proveedor {proveedor.nombre_fantasia} modificado exitosamente.')
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)

    return render(request, 'flota/registrar_proveedor.html', {'form': form, 'titulo': 'Modificar Proveedor'})


# Habilitar proveedor
@login_required
@user_passes_test(es_administrador)
def habilitar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    
    if request.method == 'POST':
        proveedor.activo = True
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_fantasia} habilitado exitosamente.')
        return redirect('listar_proveedores')
    
    return render(request, 'flota/habilitar_proveedor.html', {'proveedor': proveedor})


# Deshabilitar proveedores
@login_required
@user_passes_test(es_administrador)
def deshabilitar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == 'POST':
        proveedor.activo = False
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_fantasia} deshabilitado exitosamente.')
        return redirect('listar_proveedores')
    
    return render(request, 'flota/deshabilitar_proveedor.html', {'proveedor': proveedor})


