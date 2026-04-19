# -*- coding: utf-8 -*-
"""
測試腳本：往南 20cm 複製選取的管線與法蘭，並自動修改為 5m 直管加兩側法蘭。
"""
from pyrevit import revit, DB, forms, script

doc = revit.doc
uidoc = revit.uidoc

refs = uidoc.Selection.GetElementIds()

# 南移 20cm (Y軸負向)
vec_south = DB.XYZ(0, -200.0 / 304.8, 0)
target_len_ft = 5000.0 / 304.8

with revit.Transaction("測試：複製出 法蘭+5m直管+法蘭"):
    # 1. 先複製原本選到的物件往南20cm
    new_ids = DB.ElementTransformUtils.CopyElements(doc, refs, vec_south)
    doc.Regenerate()

    new_pipe = None
    new_flange1 = None

    for eid in new_ids:
        elem = doc.GetElement(eid)
        if isinstance(elem, DB.Plumbing.Pipe):
            new_pipe = elem
        elif isinstance(elem, DB.FamilyInstance):
            new_flange1 = elem

    if not new_pipe or not new_flange1:
        forms.alert("請確保您在畫面上選取了『一根直管』及『一個法蘭』再執行此功能！", exitscript=True)

    # 2. 判斷法蘭在哪一端，以此端為基準點把管子縮成 5m
    curve = new_pipe.Location.Curve
    pt0 = curve.GetEndPoint(0)
    pt1 = curve.GetEndPoint(1)
    
    flange_pt = new_flange1.Location.Point
    
    dist_to_0 = flange_pt.DistanceTo(pt0)
    dist_to_1 = flange_pt.DistanceTo(pt1)
    
    pipe_dir = (pt1 - pt0).Normalize()
    
    if dist_to_0 < dist_to_1:
        # 法蘭靠近 pt0，保留 pt0
        fixed_pt = pt0
        free_pt = pt0 + pipe_dir * target_len_ft
    else:
        # 法蘭靠近 pt1，保留 pt1
        fixed_pt = pt1
        free_pt = pt1 - pipe_dir * target_len_ft

    # 3. 套用新的管長度 (5m)
    new_line = DB.Line.CreateBound(fixed_pt, free_pt)
    new_pipe.Location.Curve = new_line
    doc.Regenerate()

    # 4. 把法蘭複製到另一端 (距離 = 5m)，並旋轉 180 度翻面
    # 移動向量就是 (free_pt - fixed_pt)
    move_vec = free_pt - fixed_pt
    new_flange2_ids = DB.ElementTransformUtils.CopyElement(doc, new_flange1.Id, move_vec)
    new_flange2_id = new_flange2_ids[0]
    
    # 旋轉 180 度。旋轉軸為法向量 (管線的 Z軸或任意垂直管線的向量)
    # 取 BasisZ 若為無效向量則用 BasisX 叉積
    up_vec = DB.XYZ.BasisZ
    if abs(pipe_dir.DotProduct(up_vec)) > 0.99:
        up_vec = DB.XYZ.BasisX
        
    rot_axis_dir = pipe_dir.CrossProduct(up_vec).Normalize()
    rot_axis = DB.Line.CreateUnbound(free_pt, rot_axis_dir)
    
    import math
    DB.ElementTransformUtils.RotateElement(doc, new_flange2_id, rot_axis, math.pi)
    
    # 自動讓選取移到新生成的物件上
    uidoc.Selection.SetElementIds(new_ids)

forms.alert("✅ 複製測試環境成功！\n已往南偏移 20cm，並產生了一組 [法蘭 + 5m直管 + 對向法蘭]！")
