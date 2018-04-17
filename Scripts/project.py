import arcpy
import kml_repair
from kml_repair import check_kml

inputPath = arcpy.GetParameterAsText(0)
targetPath = arcpy.GetParameterAsText(1)

def execute(source, target):
    reload(kml_repair)
    check_kml(source, target)

execute(inputPath, targetPath) 
    
arcpy.AddMessage("Process completed")