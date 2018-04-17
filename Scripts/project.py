import arcpy
from arcpy import env
import fastkml

import lxml

# system modules, no need to install
import os
import shutil
import httplib
import urllib
import csv
import json
from math import radians, cos, sin, asin, sqrt

from fastkml.kml import KML
from shapely.geometry import LineString, MultiLineString, mapping, shape




#read KML


def read_kml(path='ss.kml'):
    kml = KML()
    kml.from_string(open(path).read())
    points = dict()
    h = {}
    result = []
    fname = os.path.basename(path)
    print path, fname
    for feature in kml.features():
        # print list(feature.features())
        for placemark in feature.features():
            geo = placemark.geometry
            #print type(geo)
            if isinstance(geo, MultiLineString):
                result += geo
                print 'MultiLine: {0}'.format(len(geo))
                # print type(lines)
                #for line in geo:
                #    print line.coords[:3] # first 3 points
            elif isinstance(geo, LineString):
                result.append(geo)
                print 'SingleLine: {0}'.format(len(geo.coords))
                # print geo.coords[:2]
            #if placemark.styleUrl.startswith('#hf'):
            #    points.update({placemark.name:
            #                (placemark.geometry.y, placemark.geometry.x, )})
    h[fname] = result
    return kml, h


#line_25 = read_kml('25-1.kml')
#line_25
def is_sublist(a,b):
    dir1 = any(a[i:i + len(b)] == b for i in range(len(a) - len(b) + 1))
    dir2 = any(a[i:i + len(b)] == reversed(b) for i in range(len(a) - len(b) + 1))
    return dir1 or dir2

def join_with_overlap(a, b, offset=None):
    if offset:
        max_offset = offset
    else:
        max_offset = len(b)  # can't overlap with greater size than len(b)
        
    c = list(reversed(b))
    type = 0
    for i in reversed(range(2, max_offset+1)):
        # checks for equivalence of decreasing sized slices
        # print i, a[-i:], b[:i]
        if a[-i:] == b[:i]:
            type = 1
            break
        elif b[-i:] == a[:i]:
            type = 2
            break
        elif a[-i:] == c[:i]:
            type = 3
            break
        elif c[-i:] == a[:i]:
            type = 4
            break
    if type == 1:
        return a + b[i:]
    elif type == 2:
        return b + a[i:]
    elif type == 3:
        return a + c[i:]
    elif type == 4:
        return c + a[i:]
    
    return False
    
def join_lines(line1, line2):
    # print len(line1.coords), len(line2.coords)
    if len(line1.coords) == 0:
        return line2, 0
    
    line2Rcoords = list(reversed(line2.coords[:]))
    
    # repeated lines
    if line1.coords[:] == line2.coords[:] or line1.coords[:] == line2Rcoords:
        return line1, 1
        
    if line1.coords[-1] == line2.coords[0]:
        #print line1.coords, line2.coords
        line1.coords = line1.coords[:] + line2.coords[1:]
        return line1, 0
    elif line1.coords[-1] == line2.coords[-1]: # reverse case
        line1.coords = line1.coords[:] + line2Rcoords
        return line1, 2
    elif line1.coords[0] == line2.coords[-1]: # out of order
        line2.coords = line2.coords[:] + line1.coords[1:]
        return line2, 3
    elif line1.coords[0] == line2.coords[0]: # out of order (and reversed)
        line1.coords = line2Rcoords[:] + line1.coords[1:]
        return line1, 3
    
    common_points = set(line1.coords[:]) & set(line2Rcoords)
    if len(common_points) > 0:
        longer = line1.coords[:] if len(line1.coords) > len(line2.coords) else line2Rcoords
        shorter = line1.coords[:] if len(line1.coords) < len(line2.coords) else line2Rcoords
        if is_sublist(longer, shorter):
            line1.coords = longer
            return line1, 4
        else:
            r = join_with_overlap(longer, shorter, len(common_points))
            if r:
                line1.coords = r
                return line1, 5
    
        print common_points #, longer, shorter
    return False, len(common_points)



def check_kml(pathname, targetPath, knownData=None):
    kml, lines_hash = read_kml(pathname)
    filename = os.path.basename(pathname)
    lines = lines_hash[filename]
    srv_no = filename[:-4]

    
    #    print "Service:", srv_no
    #    print "First point:", lines[0].coords[0]
    #    print "Last point:", lines[-1].coords[-1]

    arcpy.AddMessage('Processing KML file: '+ pathname)
    
    if knownData:
        srv = knownData[srv_no]
        print "From:", srv['StartDesc']
        print "To:", srv['EndDesc']
        known_start_lat, known_start_lon = float(srv['StartLat']), float(srv['StartLon'])
   
    current_line = LineString()
    
    state = 0
    repeat = 0
    reverse = 0
    badorder = 0
    overlap = 0
    last_step = 0

    for step, line in enumerate(lines, start=1): 
        result, join_state = join_lines(current_line, line)
        if join_state > 0:
            if join_state == 1:
                repeat = 1
            elif join_state == 2:
                reverse = 1
            elif join_state == 3:
                badorder = 1                
            else:
                overlap = join_state
            
        if result:
            current_line = result
        else:
            print "cannot extend.. giving up", join_state
            arcpy.AddMessage("Failing to extend at Segment {0} of {1}, giving up".format(step, len(lines)))
            last_step = step
            state = -1
            break
        #result = join_lines(current_line, line)
        #lon, lat = line.coords[0]
        #dist = haversine(lon, lat, known_start_lon, known_start_lat)
        #print "dist from first coord: {0} km".format(dist)
        #if (dist >= 0.05):
        #    print "WARNING: starting point is far from expected location"
        
        #
        #lon, lat = line.coords[-1]
        #dist = haversine(lon, lat, known_start_lon, known_start_lat)
        #print "dist from last coord: {0} km".format(dist)

            
        
    if state == 0:
        print srv_no, "fixed!"
        arcpy.AddMessage(srv_no + " is fixed!");
        #fixed_path = 'fixed/'
        #if not os.path.exists(fixed_path):
        #    os.mkdir(fixed_path)
        # write to new kml file
        kml._features[0]._features[0].geometry = current_line
        # with open(fixed_path + srv_no + "-fixed.kml", "w") as f:
     
        with open(targetPath, "w") as f:
            xml_header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            result = kml.to_string(prettyprint=True)
            f.write(xml_header + result)

        
        processed_path = 'processed/'
        if not os.path.exists(processed_path):
            os.mkdir(processed_path)
        #os.rename('kml/bad/' + filename, processed_path + filename)
        shutil.copyfile(pathname, processed_path + filename)
    
    return srv_no, state, repeat, reverse, badorder, overlap, last_step, len(lines), current_line, kml

inputfc = arcpy.GetParameterAsText(0)
targetPath = arcpy.GetParameterAsText(1)
arcpy.AddMessage("input file: " + inputfc)
arcpy.AddMessage("output file: " + targetPath)

check_kml(inputfc, targetPath)

arcpy.AddMessage("Process completed")