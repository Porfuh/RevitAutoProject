# -*- coding: utf-8 -*-
import sys
import os

# Adicionar pasta lib ao path
lib_path = os.path.join(os.path.dirname(__file__), '..', '..', 'lib')
sys.path.append(lib_path)

from image_analyzer import BlueprintAnalyzer
from Autodesk.Revit.DB import (
    FilteredElementCollector, Wall, Level, WallType, WallKind,
    Line, XYZ, Transaction
)
from Autodesk.Revit.UI import TaskDialog
from System.Windows.Forms import OpenFileDialog, DialogResult

# Get the active Revit document
doc = __revit__.ActiveUIDocument.Document

def meters_to_feet(meters):
    """Converte metros para pés"""
    return meters * 3.28084

def select_image_file():
    """Abre diálogo para selecionar arquivo de imagem"""
    dialog = OpenFileDialog()
    dialog.Title = "Selecionar Imagem da Planta Baixa"
    dialog.Filter = "Arquivos de Imagem|*.jpg;*.jpeg;*.png;*.bmp;*.tiff"
    
    if dialog.ShowDialog() == DialogResult.OK:
        return dialog.FileName
    return None

def get_revit_elements():
    """Busca elementos necessários do Revit"""
    # Encontrar tipo de parede básica
    basic_wall_type = None
    all_wall_types = FilteredElementCollector(doc).OfClass(WallType).ToElements()
    
    for w_type in all_wall_types:
        if w_type.Kind == WallKind.Basic:
            basic_wall_type = w_type
            break
    
    # Encontrar nível
    level = FilteredElementCollector(doc).OfClass(Level).FirstElement()
    
    return basic_wall_type, level

def create_walls_from_points(points, wall_type, level, height=2.7):
    """Cria paredes no Revit a partir de lista de pontos"""
    if len(points) < 3:
        TaskDialog.Show("Erro", "Necessário pelo menos 3 pontos para criar paredes")
        return False
    
    # Converter pontos para pés e criar XYZ
    points_feet = []
    for point in points:
        x_feet = meters_to_feet(point[0])
        y_feet = meters_to_feet(point[1])
        z_feet = meters_to_feet(point[2])
        points_feet.append(XYZ(x_feet, y_feet, z_feet))
    
    height_feet = meters_to_feet(height)
    
    # Criar transação
    t = Transaction(doc, "Create Walls from Image Blueprint")
    t.Start()
    
    try:
        # Criar paredes conectando os pontos
        for i in range(len(points_feet)):
            start_point = points_feet[i]
            end_point = points_feet[(i + 1) % len(points_feet)]
            
            # Verificar se os pontos são diferentes
            if start_point.DistanceTo(end_point) > 0.1:  # Mínimo 0.1 pés
                wall_line = Line.CreateBound(start_point, end_point)
                Wall.Create(doc, wall_line, wall_type.Id, level.Id, height_feet, 0, False, False)
        
        t.Commit()
        return True
        
    except Exception as e:
        t.RollBack()
        TaskDialog.Show("Erro", "Erro ao criar paredes: {}".format(str(e)))
        return False

# EXECUÇÃO PRINCIPAL
try:
    # Selecionar arquivo de imagem
    image_path = select_image_file()
    if not image_path:
        TaskDialog.Show("Cancelado", "Nenhuma imagem foi selecionada")
    else:
        # Analisar imagem
        analyzer = BlueprintAnalyzer()
        result = analyzer.analyze_image(image_path)
        
        points = result['points']
        dimensions = result['dimensions']
        
        if not points:
            TaskDialog.Show("Erro", "Não foi possível detectar geometria na imagem")
        else:
            # Buscar elementos do Revit
            wall_type, level = get_revit_elements()
            
            if not wall_type or not level:
                TaskDialog.Show("Erro", "Tipo de parede ou nível não encontrado")
            else:
                # Criar paredes
                success = create_walls_from_points(points, wall_type, level)
                
                if success:
                    msg = "Ambiente criado com sucesso!\n"
                    msg += "Pontos detectados: {}\n".format(len(points))
                    if dimensions:
                        msg += "Dimensões encontradas: {}".format(", ".join(map(str, dimensions)))
                    TaskDialog.Show("Sucesso", msg)

except ImportError:
    TaskDialog.Show("Erro", "Bibliotecas necessárias não encontradas. Instale: opencv-python, pillow, pytesseract")
except Exception as e:
    TaskDialog.Show("Erro", "Erro inesperado: {}".format(str(e)))