from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ..forms import LoginForm

# RF_01: Iniciar sesión
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']
            user = authenticate(request, username=rut, password=password)
            if user is not None and user.activo:
                login(request, user)
                # --- NUEVA LÓGICA DE REDIRECCIÓN POR ROL ---
                if user.rol == 'Conductor':
                    return redirect('registrar_bitacora')
                else:
                    return redirect('dashboard')
                # -------------------------------------------
            else:
                messages.error(request, 'RUT o contraseña incorrectos, o usuario deshabilitado.')
    else:
        form = LoginForm()
    
    return render(request, 'flota/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


