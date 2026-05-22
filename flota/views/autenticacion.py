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

            try:
                usuario = Usuario.objects.get(rut=rut)
            except Usuario.DoesNotExist:
                usuario = None

            if usuario is None:
                messages.error(request, 'RUT o contraseña incorrectos.')
                return render(request, 'flota/login.html', {'form': form})

            if not usuario.activo:
                messages.error(request, 'Usuario deshabilitado. Contacte al administrador.')
                return render(request, 'flota/login.html', {'form': form})

            user = authenticate(request, username=rut, password=password)
            if user is not None:
                login(request, user)
                if user.rol == 'Conductor':
                    return redirect('historial_conductor')
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
    