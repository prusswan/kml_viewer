import kml_repair

from arcpy import GetParameterAsText, AddMessage
from kml_repair import check_kml

inputPath = GetParameterAsText(0)
targetPath = GetParameterAsText(1)

def execute(source, target):
    # force ArcGIS to reload the module on every execution of the script
    reload(kml_repair)
    check_kml(source, target)

execute(inputPath, targetPath) 
    
AddMessage("Process completed")