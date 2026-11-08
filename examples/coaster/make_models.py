"""Two-colour test models for the positive sparse-layer case (binary STL, stdlib only).
Variant top: 40x40x6 base (filament 1) with a 20x20 pocket on top, logo (filament 2) only at z 5-6.
Variant two: same, plus a 20x20 band of filament 2 at z 0-1 (bottom pocket), so both STLs touch the bed.
Boxes only: a pocketed slab is a full slab plus four frame boxes, touching faces are fine for the slicer."""
import struct, sys, os

def box(x0, y0, z0, x1, y1, z1):
    v = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    f = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [(v[a],v[b],v[c]) for a,b,c in f]

def write(path, tris):
    with open(path, 'wb') as fh:
        fh.write(b'\0'*80); fh.write(struct.pack('<I', len(tris)))
        for a,b,c in tris:
            fh.write(struct.pack('<3f', 0,0,0))
            for p in (a,b,c): fh.write(struct.pack('<3f', *p))
            fh.write(b'\0\0')

def frame(x0,y0,x1,y1,px0,py0,px1,py1,z0,z1):  # slab minus a rectangular pocket
    return (box(x0,y0,z0,px0,y1,z1) + box(px1,y0,z0,x1,y1,z1)
            + box(px0,y0,z0,px1,py0,z1) + box(px0,py1,z0,px1,y1,z1))

if __name__ == '__main__':
    O = 115.0  # plate offset, model spans 115..155 on a 270 mm bed
    X0,Y0,X1,Y1 = O,O,O+40,O+40
    P0,P1 = O+10,O+30
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    # top: logo only on the last 1 mm
    write(f'{out}/base_top.stl', box(X0,Y0,0,X1,Y1,5) + frame(X0,Y0,X1,Y1,P0,P0,P1,P1,5,6))
    write(f'{out}/logo_top.stl', box(P0,P0,5,P1,P1,6))
    # two: a band of the second colour on the first 1 mm too (both STLs touch the bed)
    write(f'{out}/base_two.stl', frame(X0,Y0,X1,Y1,P0,P0,P1,P1,0,1) + box(X0,Y0,1,X1,Y1,5) + frame(X0,Y0,X1,Y1,P0,P0,P1,P1,5,6))
    write(f'{out}/logo_two.stl', box(P0,P0,0,P1,P1,1) + box(P0,P0,5,P1,P1,6))
    # self-check: volumes by counting boxes (mm3)
    assert len(box(0,0,0,1,1,1)) == 12
    print('ok', sorted(os.listdir(out)))
