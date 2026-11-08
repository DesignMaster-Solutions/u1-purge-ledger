"""coaster.3mf: one object, two parts (base = extruder 1, logo on top = extruder 2), Orca/Bambu layout."""
import struct, zipfile, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from make_pos_models import box, frame

def mesh_xml(tris):
    verts, idx, out = {}, [], []
    for t in tris:
        tri = []
        for p in t:
            if p not in verts: verts[p] = len(verts)
            tri.append(verts[p])
        idx.append(tri)
    vs = ''.join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for (x,y,z) in verts)
    ts = ''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in idx)
    return f'<mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh>'

X0,Y0,X1,Y1 = 0.0,0.0,40.0,40.0; P0,P1 = 10.0,30.0
base = box(X0,Y0,0,X1,Y1,5) + frame(X0,Y0,X1,Y1,P0,P0,P1,P1,5,6)
logo = box(P0,P0,5,P1,P1,6)
I = "1 0 0 0 1 0 0 0 1 0 0 0"
model = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<metadata name="Application">make_pos_3mf.py</metadata>
<resources>
<object id="1" type="model">{mesh_xml(base)}</object>
<object id="2" type="model">{mesh_xml(logo)}</object>
<object id="3" type="model"><components><component objectid="1" transform="{I}"/><component objectid="2" transform="{I}"/></components></object>
</resources>
<build><item objectid="3" transform="1 0 0 0 1 0 0 0 1 115 115 0" printable="1"/></build>
</model>'''
settings = '''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="3">
    <metadata key="name" value="coaster"/>
    <metadata key="extruder" value="1"/>
    <part id="1" subtype="normal_part"><metadata key="name" value="base"/><metadata key="extruder" value="1"/></part>
    <part id="2" subtype="normal_part"><metadata key="name" value="logo"/><metadata key="extruder" value="2"/></part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <model_instance><metadata key="object_id" value="3"/><metadata key="instance_id" value="0"/></model_instance>
  </plate>
</config>
'''
out = sys.argv[1]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="text/xml"/></Types>')
    z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr('3D/3dmodel.model', model)
    z.writestr('Metadata/model_settings.config', settings)
print('ok', out, os.path.getsize(out))
