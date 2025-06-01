#!/usr/bin/env python3
import inkex
try:
    from lxml import etree
except ImportError:
    inkex.errormsg("Error crítico: No se pudo encontrar la librería lxml.")
    exit(1)

try:
    import numpy as np
    import noise
    from skimage import measure
except ImportError as e:
    inkex.errormsg(f"Error: Falta una librería necesaria ({e}). Ejecuta: pip install numpy noise scikit-image")
    exit(1)

class RorschachGenerator(inkex.Effect):
    def __init__(self):
        super().__init__()
        # --- Parámetros que definiremos en el .inx ---
        self.arg_parser.add_argument("--tab") # Necesario para pestañas en UI (si se usa)
        self.arg_parser.add_argument("--noise_scale", type=float, default=0.04, help="Escala/detalle del ruido")
        self.arg_parser.add_argument("--threshold", type=float, default=0.0, help="Umbral para contorno (ruido Perlin va de -1 a 1 aprox.)")
        self.arg_parser.add_argument("--steps", type=int, default=100, help="Resolución de la cuadrícula de ruido (más = más detalle/lento)")
        self.arg_parser.add_argument("--width", type=float, default=200.0, help="Ancho de la mancha generada")
        self.arg_parser.add_argument("--height", type=float, default=300.0, help="Alto de la mancha generada")
        self.arg_parser.add_argument("--fill_color", type=str, default="#000000", help="Color de relleno (ej: #000000)")
        self.arg_parser.add_argument("--stroke_color", type=str, default="none", help="Color de borde (ej: none o #FF0000)")
        self.arg_parser.add_argument("--stroke_width", type=float, default=1.0, help="Ancho del borde")
        # Podríamos añadir más: octaves, persistence para el ruido, etc.

    def effect(self):
        # Obtener el centro del documento o vista actual para posicionar
        center_x, center_y = self.svg.view_center # Asigna directamente x, y desde la tupla
        
        # O usar el centro de la página si se prefiere
        # page_bbox = self.svg.get_page_bounding_box()
        # center_x = page_bbox.center.x
        # center_y = page_bbox.center.y

        # --- 1. Generar Campo de Ruido (Mitad Izquierda) ---
        scale = self.options.noise_scale
        octaves = 6 # Parámetro del ruido Perlin
        persistence = 0.5 # Parámetro del ruido Perlin
        lacunarity = 2.0 # Parámetro del ruido Perlin
        width_steps = self.options.steps // 2 # Solo calculamos la mitad
        height_steps = self.options.steps

        # Crear cuadrícula de coordenadas (solo mitad izquierda, centrada en 0,0 por ahora)
        lin_x = np.linspace(-self.options.width / 2, 0, width_steps)
        lin_y = np.linspace(-self.options.height / 2, self.options.height / 2, height_steps)

        # Generar el campo de ruido 2D
        noise_field = np.zeros((height_steps, width_steps))
        for i in range(height_steps):
            for j in range(width_steps):
                # Usamos pnoise2 de la librería 'noise'
                noise_field[i][j] = noise.pnoise2(lin_x[j] * scale,
                                                  lin_y[i] * scale,
                                                  octaves=octaves,
                                                  persistence=persistence,
                                                  lacunarity=lacunarity,
                                                  base=np.random.randint(0, 100)) # Base aleatoria para variedad

        # --- 2. Encontrar Contornos ---
        # Usamos scikit-image para encontrar los contornos en el nivel del umbral
        # find_contours devuelve una lista de arrays [ (fila, col), (fila, col), ... ]
        contours = measure.find_contours(noise_field, self.options.threshold)

        # --- 3. Convertir Contornos a Rutas SVG ---
        # Grupo principal para toda la mancha
        main_group = etree.Element("g", id="rorschach_group")

        # Grupo para la mitad izquierda
        left_group = etree.SubElement(main_group, "g", id="rorschach_left")

        for contour in contours:
            # Mapear coordenadas del array (fila, col) a coordenadas SVG (x, y)
            # Origen (0,0) del array es esquina superior izquierda
            # Necesitamos escalar y trasladar a nuestras dimensiones deseadas
            path_data = "M " # Start path
            for i, point in enumerate(contour):
                # point[0] es fila (y), point[1] es columna (x)
                # Mapeo: col -> x, fila -> y
                svg_x = np.interp(point[1], [0, width_steps - 1], [-self.options.width / 2, 0])
                svg_y = np.interp(point[0], [0, height_steps - 1], [-self.options.height / 2, self.options.height / 2])
                
                if i == 0:
                    path_data += f"{svg_x:.2f},{svg_y:.2f}"
                else:
                    path_data += f" L {svg_x:.2f},{svg_y:.2f}"
            path_data += " Z" # Close the path

            # Crear el elemento path SVG
            path_el = etree.SubElement(left_group, "path", d=path_data)

        # --- 4. Aplicar Simetría (Reflejar el Grupo Izquierdo) ---
        # Crear una copia del grupo izquierdo para el lado derecho
        # Usamos inkex.nodes.utils.transform_node para aplicar la transformación
        # Reflejar horizontalmente respecto al eje Y (x=0)
        
        # Forma más simple: Crear un elemento <use> que referencie el grupo izquierdo y lo transforme
        right_use = etree.SubElement(main_group, inkex.addNS('use', 'svg'))
        right_use.set(inkex.addNS('href', 'xlink'), '#rorschach_left') # Referencia al ID del grupo izquierdo
        # Transformación: escalar -1 en X (reflejar)
        right_use.set('transform', 'scale(-1, 1)')

        # --- 5. Aplicar Estilo y Posicionar ---
        # Estilo aplicado al grupo principal afectará a ambos lados
        style_str = f"fill:{self.options.fill_color};stroke:{self.options.stroke_color};stroke-width:{self.options.stroke_width};"
        main_group.set('style', style_str)

        # Mover el grupo completo al centro de la vista/página
        main_group.set('transform', f'translate({center_x}, {center_y})')

        # --- 6. Añadir al Documento ---
        # Obtener la capa actual
        parent = self.svg.get_current_layer()
        parent.append(main_group)

# Punto de entrada
if __name__ == '__main__':
    RorschachGenerator().run()
