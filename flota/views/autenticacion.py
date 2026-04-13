# flota/views/autenticacion.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ..forms import LoginForm
from ..models import Usuario

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']
            
            # 1. Buscar el usuario por RUT
            try:
                usuario = Usuario.objects.get(rut=rut)
            except Usuario.DoesNotExist:
                usuario = None
            
            # 2. Si el usuario no existe -> credenciales incorrectas
            if usuario is None:
                messages.error(request, 'RUT o contraseña incorrectos.')
                return render(request, 'flota/login.html', {'form': form})
            
            # 3. Si el usuario existe pero está deshabilitado
            if not usuario.activo:
                messages.error(request, 'Usuario deshabilitado. Contacte al administrador.')
                return render(request, 'flota/login.html', {'form': form})
            
            # 4. Usuario activo: intentar autenticar
            user = authenticate(request, username=rut, password=password)
            if user is not None:
                login(request, user)
                if user.rol == 'Conductor':
                    return redirect('listar_bitacoras')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, 'RUT o contraseña incorrectos.')
    else:
        form = LoginForm()
    
    return render(request, 'flota/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')
    