import vtk
import numpy as np

class ColorTable(vtk.vtkLookupTable):
    def __init__(self, project, valueVector):
        super().__init__()
        self.project = project
        self.valueVector = valueVector
        # self.matriz = matriz
        # self.normal = {}
        self.min_value = min(self.valueVector)
        self.max_value = max(self.valueVector)
                
        self.SetTableRange(self.min_value,self.max_value)
        self.SetHueRange( 2/3, 0 )
        #self.SetHueRange(self.min_value, self.max_value/1.5)
        self.ForceBuild()

    def is_empty(self):
        return len(self.valueVector) == 0

    def distance_to(self, cord1, cord2):
        return np.linalg.norm(cord1 - cord2)

    def get_color_by_id(self, key):
        if self.is_empty():
            return [255,255,255]
        
        color_temp = [0,0,0]
        self.GetColor(self.valueVector[key], color_temp)
        
        for i in range(3):
            color_temp[i] = int(color_temp[i]*255)
        
        #color_temp[0], color_temp[2] = color_temp[2], color_temp[0]
        return color_temp
