import vtk
import numpy as np 
from time import time
from scipy.spatial.transform import Rotation

from pulse.interface.vtkActorBase import vtkActorBase
# from pulse.utils import directional_vectors_xyz_rotation

class TubeActor(vtkActorBase):
    def __init__(self, elements, project):
        super().__init__()

        self.elements = elements
        self.project = project
        self._key_index = {j:i for i,j in enumerate(self.elements.keys())}

        self.transparent = True

        self._data = vtk.vtkPolyData()
        self._mapper = vtk.vtkGlyph3DMapper()
        self.colorTable = None
        self._colors = vtk.vtkUnsignedCharArray()
        self._colors.SetNumberOfComponents(3)
        self._colors.SetNumberOfTuples(len(self.elements))
        

    @property
    def transparent(self):
        return self.__transparent

    @transparent.setter
    def transparent(self, value):
        if value:
            self._actor.GetProperty().SetOpacity(0.1)
            self._actor.GetProperty().SetLighting(False)
        else:
            self._actor.GetProperty().SetOpacity(1)
            self._actor.GetProperty().SetLighting(True)
        self.__transparent = value

    def source(self):
        points = vtk.vtkPoints()
        sources = vtk.vtkIntArray()
        sources.SetName('sources')
        rotations = vtk.vtkDoubleArray()
        rotations.SetNumberOfComponents(3)
        rotations.SetName('rotations')

        cache = dict()
        counter = 0

        for element in self.elements.values():
            x,y,z = element.first_node.coordinates
            points.InsertNextPoint(x,y,z)
            rotations.InsertNextTuple(element.undeformed_rotation_xyz)
            self._colors.InsertNextTuple((255,255,255))
            
            if element.cross_section not in cache:
                cache[element.cross_section] = counter
                source = self.createTubeSection(element)
                self._mapper.SetSourceData(counter, source)
                counter += 1
            sources.InsertNextTuple1(cache[element.cross_section])

        self._data.SetPoints(points)
        self._data.GetPointData().AddArray(sources)
        self._data.GetPointData().AddArray(rotations)
        self._data.GetPointData().SetScalars(self._colors)

    def map(self):
        self._mapper.SetInputData(self._data)
        self._mapper.SourceIndexingOn()
        self._mapper.SetSourceIndexArray('sources')
        self._mapper.SetOrientationArray('rotations')
        self._mapper.SetOrientationModeToRotation()
        self._mapper.Update()

    def filter(self):
        pass
    
    def actor(self):
        self._actor.SetMapper(self._mapper)
        self._actor.GetProperty().BackfaceCullingOff()

    def setColor(self, color, keys=None):
        c = vtk.vtkUnsignedCharArray()
        c.DeepCopy(self._colors)
        keys = keys if keys else self.elements.keys()
        for key in keys:
            index = self._key_index[key]
            c.SetTuple(index, color)
        self._data.GetPointData().SetScalars(c)
        self._colors = c
        self._mapper.Update()
    
    def setColorTable(self, colorTable):
        self.colorTable = colorTable

        c = vtk.vtkUnsignedCharArray()
        c.DeepCopy(self._colors)
        for key, element in self.elements.items():
            index = self._key_index[key]
            color = self.colorTable.get_color_by_id(element.first_node.global_index)
            c.SetTuple(index, color)

        self._data.GetPointData().SetScalars(c)
        self._colors = c

    def createTubeSection(self, element):
        extruderFilter = vtk.vtkLinearExtrusionFilter()
        polygon = self.createSectionPolygon(element)
        size = self.project.get_element_size()
        extruderFilter.SetInputConnection(polygon.GetOutputPort())
        extruderFilter.SetExtrusionTypeToVectorExtrusion()
        extruderFilter.SetVector(1,0,0)
        extruderFilter.SetScaleFactor(size)
        extruderFilter.Update()
        return extruderFilter.GetOutput()

    # def createSectionPolygon(self, element):
    #     points = vtk.vtkPoints()
    #     edges = vtk.vtkCellArray()
    #     polygon = vtk.vtkPolygon()
    #     polyData = vtk.vtkPolyData()
    #     triangleFilter = vtk.vtkTriangleFilter() # this prevents bugs on extruder

    #     # Ys, Zs = self.project.get_mesh().get_cross_section_points(element.index)
    #     # polygon.GetPointIds().SetNumberOfIds(len(Ys))

    #     outer_points, inner_points, number_points = self.project.get_mesh().get_cross_section_points(element.index)
    #     polygon.GetPointIds().SetNumberOfIds(int(number_points/2))
        
    #     # for i, (y, z) in enumerate(zip(Ys, Zs)):
    #     for i, (y, z) in enumerate(outer_points):
    #         points.InsertNextPoint(0, y, z)
    #         polygon.GetPointIds().SetId(i,i)
    #     edges.InsertNextCell(polygon)

    #     polyData.SetPoints(points)
    #     polyData.SetPolys(edges)
    #     triangleFilter.AddInputData(polyData)
    #     return triangleFilter

    def createSectionPolygon(self, element):

        # inner and outer are a list of sequential coordinates
        # they need to be clockwise ordered

        # inner_points = [(0.015, 0.015), (0.015, -0.015), (-0.015, -0.015), (-0.015, 0.015)]
        # outer_points = [(0.025, 0.025), (0.025, -0.025), (-0.025, -0.025), (-0.025, 0.025)]
        # number_inner_points = 4

        # we should get this info like this
        outer_points, inner_points = self.project.get_mesh().get_cross_section_points(element.index)
        number_inner_points = len(inner_points)
        number_outer_points = len(outer_points)
        # print(number_inner_points)

        # TODO:
        # to be honest like this should be much better
        # outer, inner = element.get_cross_section_points()

        # definitions
        points = vtk.vtkPoints()
        outerData = vtk.vtkPolyData()    
        innerPolygon = vtk.vtkPolygon()
        innerCell = vtk.vtkCellArray()
        innerData = vtk.vtkPolyData()
        delaunay = vtk.vtkDelaunay2D()
        
        outerPolygon = vtk.vtkPolygon()
        edges = vtk.vtkCellArray()
        source = vtk.vtkTriangleFilter()

        # create points - check the axis alignments - older version (0, y, z)
        for y, z in inner_points:
            points.InsertNextPoint(y, z, 0)

        for y, z in outer_points:
            points.InsertNextPoint(y, z, 0)

        # create external polygon
        outerData.SetPoints(points)
        delaunay.SetInputData(outerData)

        if number_inner_points >= 3:
            # remove inner area for holed sections
            for i in range(number_inner_points):
                innerPolygon.GetPointIds().InsertNextId(i)

            innerCell.InsertNextCell(innerPolygon)
            innerData.SetPoints(points)
            innerData.SetPolys(innerCell) 
            delaunay.SetSourceData(innerData)
            delaunay.Update()

            return delaunay

        else:
            
            outerPolygon.GetPointIds().SetNumberOfIds(number_outer_points)
            for i in range(number_outer_points):
                outerPolygon.GetPointIds().SetId(i,i)
            edges.InsertNextCell(outerPolygon)
            
            outerData.SetPolys(edges)
            source.AddInputData(outerData)

            return source