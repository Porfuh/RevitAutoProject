# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import (
    FilteredElementCollector, Wall, Level, WallType,
    Line, XYZ, Transaction
)
from Autodesk.Revit.UI import TaskDialog

# Get the active Revit document
doc = __revit__.ActiveUIDocument.Document

# -- 1. THE BLUEPRINT DATA (in Meters) -- SESCSO
room_width_m = 4.0
room_depth_m = 5.0
wall_height_m = 2.7

# -- 2. HELPER FUNCTION for unit conversion --
def meters_to_feet(meters):
    """Converts a value from meters to decimal feet."""
    return meters * 3.28084

# -- 3. GATHER REQUIRED REVIT ELEMENTS --
from Autodesk.Revit.DB import WallKind # We need this to check the wall kind

# Find the first available "Basic" WallType
basic_wall_type = None
all_wall_types = FilteredElementCollector(doc).OfClass(WallType).ToElements()

for w_type in all_wall_types:
    # Check if the wall's kind is 'Basic'
    if w_type.Kind == WallKind.Basic:
        basic_wall_type = w_type
        break # Stop looking once we've found one

# Find the first available Level
level = FilteredElementCollector(doc).OfClass(Level).FirstElement()

# Check if we found what we need before continuing
if not basic_wall_type or not level:
    TaskDialog.Show("Error", "A valid Wall Type or Level could not be found.")
else:
    # -- 4. DEFINE CORNER POINTS (in Meters) - CENTERED AT ORIGIN --
    half_width = room_width_m / 2.0
    half_depth = room_depth_m / 2.0
    
    p1 = XYZ(-half_width, -half_depth, 0)  # Bottom-left
    p2 = XYZ(half_width, -half_depth, 0)   # Bottom-right
    p3 = XYZ(half_width, half_depth, 0)    # Top-right
    p4 = XYZ(-half_width, half_depth, 0)   # Top-left
    
    points_in_meters = [p1, p2, p3, p4]
    
    # -- 5. CONVERT to the API's required units (Feet) --
    points_in_feet = [XYZ(meters_to_feet(p.X), meters_to_feet(p.Y), meters_to_feet(p.Z)) for p in points_in_meters]
    wall_height_feet = meters_to_feet(wall_height_m)
    
    # -- 6. CREATE THE WALLS (within a Transaction) --
    t = Transaction(doc, "Create Room from Blueprint")
    t.Start()
    
    # Loop to create the four walls
    for i in range(4):
        start_point = points_in_feet[i]
        # The end point is the next one in the list, wrapping around for the last wall
        end_point = points_in_feet[(i + 1) % 4]
        
        # Create a line as the wall's path
        wall_line = Line.CreateBound(start_point, end_point)
        
        # This is the corrected line
        Wall.Create(doc, wall_line, basic_wall_type.Id, level.Id, wall_height_feet, 0, False, False)
        
    t.Commit()
    
    TaskDialog.Show("Success", "A {}m x {}m room was created.".format(room_width_m, room_depth_m))