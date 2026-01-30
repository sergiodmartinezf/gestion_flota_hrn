function habilitarProveedor(proveedorId, nombreProveedor) {
    // Configurar el modal
    document.getElementById('nombreProveedor').textContent = nombreProveedor;
    document.getElementById('habilitarProveedorForm').action = `/proveedores/${proveedorId}/habilitar/`;
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('habilitarProveedorModal'));
    modal.show();
}