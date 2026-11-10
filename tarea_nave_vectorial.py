import pygame   # Librería para crear la ventana, leer el teclado y dibujar
import sys      # Se usa al final para cerrar el programa limpiamente
import math     # Seno, coseno y conversión de grados a radianes
import random   # Números al azar, solo para crear el fondo de estrellas
 
# ---------------------------------------------------------------------
# 1. INICIALIZACIÓN
# ---------------------------------------------------------------------
 
# Arranca todos los módulos internos de pygame (video, eventos, etc.)
pygame.init()
 
# Tamaño de la ventana en píxeles: ANCHO (eje X) y ALTO (eje Y)
ANCHO, ALTO = 800, 600
 
# Crea la ventana. pygame.DOUBLEBUF activa el "doble buffer": se dibuja cada
# cuadro en una imagen oculta y flip() la intercambia con la que se ve.
# Así no hay parpadeos mientras se dibuja.
pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.DOUBLEBUF)
 
# Título de la barra superior de la ventana
pygame.display.set_caption("Graficación 2D - Nave Vectorial")
 
# Reloj para limitar el bucle a 60 FPS (sin él correría a máxima velocidad)
reloj = pygame.time.Clock()
 
# ---------------------------------------------------------------------
# CONSTANTES DE JUEGO (ajusta aquí los valores sin tocar el resto)
# ---------------------------------------------------------------------
FPS = 60                    # Cuadros por segundo
VEL_ROTACION = 3.5          # Grados que gira la nave por cuadro
VEL_NAVE = 4                # Píxeles por cuadro al avanzar
VEL_REVERSA = 2.5           # Píxeles por cuadro al retroceder (más lento)
VEL_PROYECTIL = 10          # Píxeles por cuadro del proyectil (más rápido que la nave)
VIDA_PROYECTIL = 90         # Cuadros de vida del proyectil (1.5 s a 60 FPS)
COOLDOWN_DISPARO = 250      # Milisegundos mínimos entre un disparo y otro
 
# Colores de la nave en formato (R, G, B), cada canal de 0 a 255
COLOR_NAVE = (225, 232, 245)     # Relleno: blanco plateado
COLOR_BORDE = (120, 170, 255)    # Borde: azul claro
 
 
# ---------------------------------------------------------------------
# FONDO DE ESPACIO (fijo)
# ---------------------------------------------------------------------
def crear_fondo():
    """Genera UNA imagen estática con degradado, nebulosas y estrellas.
    Se llama una sola vez; después solo se pega en pantalla cada cuadro,
    lo cual es mucho más rápido que redibujar todo 60 veces por segundo."""
 
    # Superficie vacía del tamaño de la ventana donde pintaremos el fondo
    fondo = pygame.Surface((ANCHO, ALTO))
 
    # --- Degradado vertical azul-negro ---
    # Recorremos cada fila de píxeles (y) y la pintamos con un color un
    # poco más azul que la anterior. t va de 0.0 (arriba) a 1.0 (abajo).
    for y in range(ALTO):
        t = y / ALTO
        color = (int(8 + 14 * t), int(8 + 6 * t), int(22 + 30 * t))
        pygame.draw.line(fondo, color, (0, y), (ANCHO, y))
 
    # --- Nebulosas suaves (círculos translúcidos) ---
    # SRCALPHA da a la superficie un canal de transparencia (alfa)
    nebulosa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
 
    # random.seed(7) fija la semilla: las nebulosas y estrellas salen
    # SIEMPRE en los mismos lugares cada vez que ejecutas el programa
    random.seed(7)
 
    for _ in range(6):  # 6 nebulosas
        # Centro de la nebulosa al azar dentro de la ventana
        cx, cy = random.randint(0, ANCHO), random.randint(0, ALTO)
        # Color base elegido al azar: morado, azul o magenta oscuro
        base = random.choice([(90, 40, 140), (40, 70, 160), (130, 40, 90)])
        # Círculos concéntricos de radio 160 a 40 (de 20 en 20), cada uno
        # con alfa 5 (casi transparente). Al apilarse forman un brillo suave.
        for r in range(160, 20, -20):
            pygame.draw.circle(nebulosa, (*base, 5), (cx, cy), r)
 
    # Pegamos las nebulosas encima del degradado
    fondo.blit(nebulosa, (0, 0))
 
    # --- Estrellas fijas ---
    for _ in range(220):  # 220 estrellas
        # Posición al azar (ANCHO - 1 y ALTO - 1 para no salirnos del borde)
        x, y = random.randint(0, ANCHO - 1), random.randint(0, ALTO - 1)
        # Brillo al azar: 110 (tenue) a 255 (muy brillante)
        brillo = random.randint(110, 255)
        # El 85% de las estrellas miden 1 px de radio y el 15% miden 2 px
        radio = 1 if random.random() < 0.85 else 2
        # Color blanco con un toque azulado (el canal azul es +20, máx. 255)
        pygame.draw.circle(fondo, (brillo, brillo, min(255, brillo + 20)), (x, y), radio)
 
    return fondo
 
 
# Creamos el fondo una sola vez, antes del bucle principal
fondo_espacio = crear_fondo()
 
 
# ---------------------------------------------------------------------
# 2. TRANSFORMACIÓN GEOMÉTRICA 2D
# ---------------------------------------------------------------------
# Convierte un punto del modelo local (coordenadas alrededor de (0,0)) en
# un punto de la pantalla, aplicando en orden: escala -> rotación -> traslación.
def transformar_vertice(vertice, pos_x, pos_y, escala, angulo):
    # Separamos el vértice en sus coordenadas x e y
    x, y = vertice
 
    # ESCALAMIENTO: multiplicamos por el factor de escala (1.2 = 20% más grande)
    x_esc, y_esc = x * escala, y * escala
 
    # ROTACIÓN: sin y cos trabajan en radianes, así que convertimos los grados
    rad = math.radians(angulo)
    # Fórmulas de rotación 2D alrededor del origen (0,0). Como el centroide
    # de la nave está en (0,0), la nave gira sobre sí misma.
    x_rot = x_esc * math.cos(rad) - y_esc * math.sin(rad)
    y_rot = x_esc * math.sin(rad) + y_esc * math.cos(rad)
 
    # TRASLACIÓN: sumamos la posición de la nave para llevar el punto desde
    # el origen hasta el lugar donde está la nave en la pantalla
    return (x_rot + pos_x, y_rot + pos_y)
 
 
# ---------------------------------------------------------------------
# MODELO LOCAL DE LA NAVE
# ---------------------------------------------------------------------
# En pantalla el eje Y crece hacia ABAJO, por eso la proa está en y = -25.
#   (0, -25)    -> proa (la punta)
#   (-18, 12.5) -> esquina trasera izquierda
#   (18, 12.5)  -> esquina trasera derecha
# El centroide queda en (0,0) porque (-25 + 12.5 + 12.5) / 3 = 0
modelo_nave = [(0, -25), (-18, 12.5), (18, 12.5)]
 
# ---------------------------------------------------------------------
# ESTADO DE LA NAVE (variables que cambian mientras corre el programa)
# ---------------------------------------------------------------------
pos_x, pos_y = 400, 300   # Posición inicial: centro de la pantalla
angulo = 0                # Ángulo en grados. 0 = la proa apunta hacia arriba
escala = 1.2              # Factor de tamaño de la nave
 
# Lista dinámica de proyectiles. Cada uno es un diccionario:
#   "x", "y"   -> posición actual
#   "vx", "vy" -> velocidad en cada eje (píxeles por cuadro)
#   "vida"     -> cuadros que le quedan antes de desaparecer
proyectiles = []
 
# Momento (en ms) del último disparo. Empieza en -COOLDOWN_DISPARO para que
# se pueda disparar desde el primer instante sin esperar.
ultimo_disparo = -COOLDOWN_DISPARO
 
 
# ---------------------------------------------------------------------
# FUNCIÓN AUXILIAR
# ---------------------------------------------------------------------
def direccion_proa(angulo_grados):
    """Devuelve el vector unitario (de longitud 1) hacia donde apunta la proa,
    usando cos(theta) y sin(theta).
    Se resta 90° porque con angulo = 0 la proa apunta hacia ARRIBA (-Y),
    pero cos/sin con theta = 0 apuntarían hacia la DERECHA (+X)."""
    theta = math.radians(angulo_grados - 90)
    return math.cos(theta), math.sin(theta)
 
 
# ---------------------------------------------------------------------
# 3. BUCLE PRINCIPAL (se repite 60 veces por segundo hasta cerrar)
# ---------------------------------------------------------------------
ejecutando = True
while ejecutando:
 
    # --- EVENTOS ---
    # Revisa lo que pasó en la ventana desde el cuadro anterior
    for evento in pygame.event.get():
        # Clic en la X de la ventana: terminamos el bucle
        if evento.type == pygame.QUIT:
            ejecutando = False
        # Tecla ESC presionada: también terminamos
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            ejecutando = False
 
    # --- TECLADO ---
    # Estado de TODAS las teclas ahora mismo (True = presionada).
    # Sirve para acciones continuas: mantener presionado = seguir girando.
    teclas = pygame.key.get_pressed()
 
    # --- ROTACIÓN ---
    # Restar grados gira a la izquierda; sumar gira a la derecha
    if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
        angulo -= VEL_ROTACION
    if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
        angulo += VEL_ROTACION
 
    # --- AVANCE Y REVERSA ---
    # Vector unitario hacia donde apunta la proa en este momento
    dir_x, dir_y = direccion_proa(angulo)
    # Avanzar: posición nueva = posición actual + dirección * velocidad
    if teclas[pygame.K_w] or teclas[pygame.K_UP]:
        pos_x += dir_x * VEL_NAVE
        pos_y += dir_y * VEL_NAVE
    # Retroceder: igual pero restando, y con velocidad menor
    if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
        pos_x -= dir_x * VEL_REVERSA
        pos_y -= dir_y * VEL_REVERSA
 
    # --- PANTALLA ENVOLVENTE (reto opcional) ---
    # El operador % (módulo) hace que la posición "dé la vuelta": si x pasa
    # de 800 vuelve a 0, y si baja de 0 reaparece en 800. Igual para Y con 600.
    pos_x %= ANCHO
    pos_y %= ALTO
 
    # --- VÉRTICES DE LA NAVE EN PANTALLA ---
    # Aplicamos escala + rotación + traslación a cada vértice del modelo local.
    # El resultado son las 3 esquinas reales del triángulo en la ventana.
    vertices_pantalla = [
        transformar_vertice(v, pos_x, pos_y, escala, angulo)
        for v in modelo_nave
    ]
 
    # --- DISPARO ---
    # Tiempo transcurrido desde que inició pygame, en milisegundos
    ahora = pygame.time.get_ticks()
 
    # Dispara solo si se presiona ESPACIO y ya pasaron 250 ms desde el
    # último disparo (cooldown). Así no salen cientos de balas por segundo.
    if teclas[pygame.K_SPACE] and ahora - ultimo_disparo >= COOLDOWN_DISPARO:
        ultimo_disparo = ahora   # Guardamos cuándo disparamos
 
        # La punta de la nave es el vértice 0 (la proa), que ya está
        # transformado, así que la bala nace exactamente ahí
        punta_x, punta_y = vertices_pantalla[0]
 
        # Creamos el proyectil y lo agregamos a la lista
        proyectiles.append({
            "x": punta_x,                    # Nace en la punta de la nave
            "y": punta_y,
            "vx": dir_x * VEL_PROYECTIL,     # Velocidad en la dirección de la proa
            "vy": dir_y * VEL_PROYECTIL,
            "vida": VIDA_PROYECTIL,          # Cuadros antes de desaparecer
        })
 
    # --- ACTUALIZAR PROYECTILES ---
    # Lista nueva donde guardaremos solo los proyectiles que siguen vivos
    vivos = []
    for p in proyectiles:
        # Movemos el proyectil según su velocidad y le restamos un cuadro de vida
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vida"] -= 1
        # ¿Sigue dentro de la ventana (0 a 800 en X, 0 a 600 en Y)?
        dentro = 0 <= p["x"] <= ANCHO and 0 <= p["y"] <= ALTO
        # Solo se conserva si está dentro de la pantalla Y le queda vida.
        # Los demás se descartan (gestión de memoria).
        if dentro and p["vida"] > 0:
            vivos.append(p)
    proyectiles = vivos
 
    # =================================================================
    # RENDERIZADO (el orden importa: lo que se dibuja después queda encima)
    # =================================================================
 
    # 1) Fondo: pegamos la imagen del espacio, que también borra el cuadro anterior
    pantalla.blit(fondo_espacio, (0, 0))
 
    # 2) Proyectiles: círculos amarillos de radio 3.
    # int() porque los píxeles no admiten decimales.
    for p in proyectiles:
        pygame.draw.circle(pantalla, (255, 220, 80), (int(p["x"]), int(p["y"])), 3)
 
    # 3) Nave: primero el relleno y luego el borde encima (el 2 es el grosor)
    pygame.draw.polygon(pantalla, COLOR_NAVE, vertices_pantalla)
    pygame.draw.polygon(pantalla, COLOR_BORDE, vertices_pantalla, 2)
 
    # Intercambia el buffer oculto con el visible: aquí aparece todo lo que
    # se dibujó en este cuadro (doble buffer)
    pygame.display.flip()
 
    # Espera lo necesario para mantener 60 cuadros por segundo
    reloj.tick(FPS)
 
# ---------------------------------------------------------------------
# 4. CIERRE
# ---------------------------------------------------------------------
pygame.quit()   # Libera los recursos de pygame
sys.exit()      # Termina el programa
 