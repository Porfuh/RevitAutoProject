# -*- coding: utf-8 -*-
import cv2
import numpy as np
import re
from PIL import Image
import pytesseract

class BlueprintAnalyzer:
    def __init__(self):
        self.scale_factor = 1.0  # metros por pixel
        
    def analyze_image(self, image_path):
        """Analisa uma imagem de planta baixa e retorna pontos e dimensões"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Não foi possível carregar a imagem")
            
        # Converter para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detectar linhas (paredes)
        lines = self._detect_lines(gray)
        
        # Extrair medidas do texto
        dimensions = self._extract_dimensions(gray)
        
        # Processar linhas em pontos conectados
        points = self._lines_to_points(lines, dimensions)
        
        return {
            'points': points,
            'dimensions': dimensions,
            'scale': self.scale_factor
        }
    
    def _detect_lines(self, gray_img):
        """Detecta linhas principais na imagem"""
        # Aplicar filtro para reduzir ruído
        blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
        
        # Detectar bordas
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
        
        # Detectar linhas usando Hough Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                               minLineLength=50, maxLineGap=10)
        
        return lines if lines is not None else []
    
    def _extract_dimensions(self, gray_img):
        """Extrai dimensões numéricas da imagem usando OCR"""
        try:
            # Configurar OCR para números
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,'
            text = pytesseract.image_to_string(gray_img, config=config)
            
            # Buscar padrões de medidas (ex: 4.5, 3.2, etc.)
            dimensions = re.findall(r'\d+\.?\d*', text)
            return [float(d) for d in dimensions if float(d) > 0.5]  # Filtrar valores muito pequenos
            
        except:
            return []
    
    def _lines_to_points(self, lines, dimensions):
        """Converte linhas detectadas em pontos conectados"""
        if not lines.any():
            return []
            
        points = []
        tolerance = 10  # Tolerância para conectar pontos próximos
        
        # Extrair todos os pontos das linhas
        all_points = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            all_points.extend([(x1, y1), (x2, y2)])
        
        # Agrupar pontos próximos
        unique_points = self._cluster_points(all_points, tolerance)
        
        # Ordenar pontos para formar um polígono
        if len(unique_points) >= 3:
            points = self._order_points_clockwise(unique_points)
        
        # Converter pixels para metros (assumindo escala)
        if dimensions:
            self.scale_factor = self._calculate_scale(points, dimensions)
        
        # Aplicar escala
        scaled_points = [(x * self.scale_factor, y * self.scale_factor, 0) 
                        for x, y in points]
        
        return scaled_points
    
    def _cluster_points(self, points, tolerance):
        """Agrupa pontos próximos em um único ponto"""
        if not points:
            return []
            
        clustered = []
        used = set()
        
        for i, point in enumerate(points):
            if i in used:
                continue
                
            cluster = [point]
            used.add(i)
            
            for j, other_point in enumerate(points[i+1:], i+1):
                if j in used:
                    continue
                    
                distance = np.sqrt((point[0] - other_point[0])**2 + 
                                 (point[1] - other_point[1])**2)
                
                if distance <= tolerance:
                    cluster.append(other_point)
                    used.add(j)
            
            # Calcular centroide do cluster
            avg_x = sum(p[0] for p in cluster) / len(cluster)
            avg_y = sum(p[1] for p in cluster) / len(cluster)
            clustered.append((avg_x, avg_y))
        
        return clustered
    
    def _order_points_clockwise(self, points):
        """Ordena pontos em sentido horário para formar polígono"""
        # Encontrar centroide
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        
        # Ordenar por ângulo em relação ao centroide
        def angle_from_center(point):
            return np.arctan2(point[1] - cy, point[0] - cx)
        
        return sorted(points, key=angle_from_center)
    
    def _calculate_scale(self, points, dimensions):
        """Calcula fator de escala baseado nas dimensões encontradas"""
        if not points or not dimensions:
            return 0.01  # Escala padrão: 1cm por pixel
            
        # Calcular maior distância entre pontos
        max_distance_pixels = 0
        for i in range(len(points)):
            for j in range(i+1, len(points)):
                dist = np.sqrt((points[i][0] - points[j][0])**2 + 
                              (points[i][1] - points[j][1])**2)
                max_distance_pixels = max(max_distance_pixels, dist)
        
        # Assumir que a maior dimensão corresponde à maior distância
        max_dimension_meters = max(dimensions) if dimensions else 5.0
        
        return max_dimension_meters / max_distance_pixels if max_distance_pixels > 0 else 0.01