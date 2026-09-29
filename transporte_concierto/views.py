from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from . import consultas

# =======================
# VISTA PRINCIPAL (HOME)
# =======================
def home(request):
    html_content = """
    <html>
    <head>
        <title>API - Transporte a Conciertos</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; background-color: #f4f6f9; color: #333; }
            .container { max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            h1 { color: #007BFF; border-bottom: 2px solid #eee; padding-bottom: 10px; }
            h3 { color: #444; margin-top: 25px; }
            .endpoint { background-color: #f9f9f9; border-left: 4px solid #007BFF; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
            .post-endpoint { border-left-color: #28a745; }
            .delete-endpoint { border-left-color: #dc3545; }
            a { text-decoration: none; color: #007BFF; font-weight: bold; font-size: 1.1em; }
            a:hover { text-decoration: underline; }
            code { background-color: #e9ecef; padding: 8px; border-radius: 4px; color: #d63384; display: block; margin-top: 8px; font-family: monospace; white-space: pre-wrap; }
            p { margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API - Transporte a Conciertos (Consultas SQL & Funciones)</h1>
            <p>Bienvenido. A continuación se presentan los enlaces a las consultas habilitadas en el sistema:</p>
            
            <h3>Consultas de Lectura (GET)</h3>
            
            <div class="endpoint">
                <a href="/api/pagos/" target="_blank">1. Listar Pagos Realizados</a>
                <code>SELECT "id_pago", "monto" FROM "Pago";</code>
            </div>

            <div class="endpoint">
                <a href="/api/viajes/pendientes/" target="_blank">2. Listar Viajes a Conciertos Pendientes (con Vehículo)</a>
                <code>SELECT v."modelo", v."patente", vc."id_viaje", vc."direccion_origen", vc."direccion_destino" 
FROM "Viaje_a_concierto" vc 
INNER JOIN "Viaje_a_concierto_usa_Vehiculo" vv ON vc."id_viaje" = vv."id_viaje" 
INNER JOIN "Vehiculo" v ON vv."patente" = v."patente" 
WHERE vc."estado" = 'pendiente';</code>
            </div>

            <div class="endpoint">
                <a href="/api/pasajeros/reservas/" target="_blank">3. Listar Pasajeros con Reserva y Asientos</a>
                <code>SELECT DISTINCT pas."nombre_completo", pas."telefono", pas."correo_electronico", ar."asientos_reserva" 
FROM "Pasajero" pas 
INNER JOIN "Reserva" r ON pas."id_pasajero" = r."id_pasajero" 
INNER JOIN "asientos_reserva" ar ON r."id_reserva" = ar."id_reserva";</code>
            </div>

            <h3>Operaciones de Escritura y Gestión (POST / DELETE)</h3>
            
            <div class="endpoint post-endpoint">
                <p><strong>Registrar Nuevo Viaje Pendiente (POST):</strong> <code>/api/viajes/nuevo/</code></p>
                <code>INSERT INTO "Viaje_a_concierto" (...) VALUES (...) RETURNING "id_viaje";</code>
            </div>

            <div class="endpoint post-endpoint">
                <p><strong>Asignar Vehículo a Viaje (POST):</strong> <code>/api/viajes/asignar-vehiculo/</code></p>
                <code>INSERT INTO "Viaje_a_concierto_usa_Vehiculo" ("id_viaje", "patente") VALUES (%s, %s);</code>
            </div>

            <div class="endpoint delete-endpoint">
                <p><strong>Eliminar Viaje por ID (DELETE):</strong> <code>/api/viajes/&lt;id_viaje&gt;/eliminar/</code></p>
                <code>DELETE FROM "Viaje_a_concierto" WHERE "id_viaje" = %s;</code>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)

# =======================
# VISTAS DE LA API (GET)
# =======================
def listar_viajes_pendientes(request):
    if request.method == 'GET':
        try:
            viajes = consultas.get_viajes_pendientes()
            return JsonResponse({'status': 'success', 'data': viajes})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def listar_pagos(request):
    if request.method == 'GET':
        try:
            pagos = consultas.get_pagos_realizados()
            return JsonResponse({'status': 'success', 'data': pagos})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def listar_pasajeros_reserva(request):
    if request.method == 'GET':
        try:
            pasajeros = consultas.get_pasajeros_con_reserva()
            return JsonResponse({'status': 'success', 'data': pasajeros})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# =======================
# VISTAS DE ESCRITURA (POST / DELETE)
# =======================
@csrf_exempt
def registrar_viaje_pendiente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nuevo_id = consultas.crear_viaje_pendiente(
                id_admin=data['id_admin'],
                fecha_viaje=data['fecha_viaje'],
                descripcion=data.get('descripcion', ''),
                recinto=data['recinto'],
                titulo=data['titulo'],
                origen=data['direccion_origen'],
                destino=data['direccion_destino']
            )
            return JsonResponse({'status': 'success', 'id_viaje_generado': nuevo_id}, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@csrf_exempt
def eliminar_viaje(request, id_viaje):
    if request.method == 'DELETE':
        try:
            consultas.borrar_viaje(id_viaje)
            return JsonResponse({'status': 'success', 'message': f'Viaje {id_viaje} eliminado exitosamente'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
        
@csrf_exempt
def asignar_vehiculo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            consultas.asignar_vehiculo_a_viaje(
                id_viaje=data['id_viaje'], 
                patente=data['patente']
            )
            return JsonResponse({'status': 'success', 'message': 'Vehículo asignado correctamente'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
