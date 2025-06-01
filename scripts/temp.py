from xml.etree.ElementTree import Element, SubElement, ElementTree
import xml.dom.minidom

# List of Ramsay Round summits
summits = [
    "Mullach nan Coirean", "Stob Bàn (Mamores)", "Sgùrr a' Mhàim", "Sgùrr an Iubhair",
    "Am Bodach", "Stob Coire a' Chàirn", "An Gearanach", "Na Gruagaichean", "Binnein Mòr",
    "Binnein Beag", "Sgùrr Eilde Mòr", "Beinn na Lap", "Chno Dearg", "Stob Coire Sgrìodain",
    "Stob a' Choire Mheadhoin", "Stob Coire Easain", "Stob Bàn (Grey Corries)",
    "Stob Choire Claurigh", "Stob Coire an Laoigh", "Sgùrr Choinnich Mòr", "Aonach Beag",
    "Aonach Mòr", "Carn Mòr Dearg", "Ben Nevis"
]

# Create root GPX element
gpx = Element('gpx', version="1.1", creator="ramsay_round_gpx_generator", xmlns="http://www.topografix.com/GPX/1/1")

# Add waypoints for each summit with dummy lat/lon/elevation
for summit in summits:
    wpt = SubElement(gpx, 'wpt', lat="0.0", lon="0.0")
    ele = SubElement(wpt, 'ele')
    ele.text = "0"
    name = SubElement(wpt, 'name')
    name.text = summit

# Pretty print the XML
rough_string = ElementTree(gpx).write("ramsay_round_summits.gpx", encoding="utf-8", xml_declaration=True)

print("GPX file 'ramsay_round_summits.gpx' created with placeholder coordinates.")
