# -*- coding: utf-8 -*-
"""
自動法蘭對接診斷工具 (Flange Diagnosis)
目標：於選取之一根直管，先往南複製20cm，然後在複製管兩側自動接上背對背法蘭，並輸出除錯表。
"""
from pyrevit import revit, DB, forms, script
import math

logger = script.get_logger()
output = script.get_output()
doc = revit.doc
uidoc = revit.uidoc

# User 指定之法蘭目標型號
TARGET_FLANGE_NAME = "PIF_PROGEF Plus bf - flange adaptor comb joint face flat and serr_GF"

def get_flange_symbol():
    all_symbols = (DB.FilteredElementCollector(doc)
                   .OfClass(DB.FamilySymbol)
                   .OfCategory(DB.BuiltInCategory.OST_PipeFitting)
                   .ToElements())
    for sym in all_symbols:
        name = "{} - {}".format(sym.FamilyName, sym.Name)
        if TARGET_FLANGE_NAME.lower() in name.lower():
            return sym
    return None

def fmt_xyz(pt):
    return "({:8.2f}, {:8.2f}, {:8.2f})".format(pt.X*304.8, pt.Y*304.8, pt.Z*304.8)

refs = uidoc.Selection.GetElementIds()
original_pipe = None
for eid in refs:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.Plumbing.Pipe):
        original_pipe = elem
        break

if not original_pipe:
    forms.alert("請精準選取『一根短直管』作為測試基準！", exitscript=True)

flange_symbol = get_flange_symbol()
if not flange_symbol:
    forms.alert("找不到指定的法蘭型號，請確認族群已載入模型中！\n目標名稱: " + TARGET_FLANGE_NAME, exitscript=True)

with revit.Transaction("產生單一管線極限測試包 (南移版)"):
    if flange_symbol and not flange_symbol.IsActive:
        flange_symbol.Activate()
        doc.Regenerate()

    # 1. 往南複製 20cm
    vec_south = DB.XYZ(0, -200.0 / 304.8, 0)
    new_ids = DB.ElementTransformUtils.CopyElement(doc, original_pipe.Id, vec_south)
    doc.Regenerate()
    pipe = doc.GetElement(new_ids[0])

    curve = pipe.Location.Curve
    pt0 = curve.GetEndPoint(0)
    pt1 = curve.GetEndPoint(1)
    pipe_dir = (pt1 - pt0).Normalize()

    # 初始化報告
    output.print_html("<h1 style='color: #2b579a;'>🛠 法蘭自動對接與方向診斷報告</h1>")
    output.print_md("---")
    output.print_md("## 📌 1. 直管基礎數據 (Pipe Base Info)")
    output.print_md("- **來源管線 ID**: `{}`".format(original_pipe.Id.IntegerValue))
    output.print_md("- **複製測資管線 ID**: `{}`".format(pipe.Id.IntegerValue))
    output.print_md("- **左端錨點 (pt0)**: `{}`".format(fmt_xyz(pt0)))
    output.print_md("- **右端錨點 (pt1)**: `{}`".format(fmt_xyz(pt1)))
    output.print_md("- **管體方向向量 (pt0 -> pt1)**: `{}`".format(fmt_xyz(pipe_dir)))

    # 獲取給接合用的管端口 (Connectors)
    pipe_conns = []
    try:
        for c in pipe.ConnectorManager.Connectors:
            if c.ConnectorType != DB.ConnectorType.Logical:
                pipe_conns.append(c)
    except: pass

    pipe_conn0 = min(pipe_conns, key=lambda c: c.Origin.DistanceTo(pt0)) if pipe_conns else None
    pipe_conn1 = min(pipe_conns, key=lambda c: c.Origin.DistanceTo(pt1)) if pipe_conns else None

    def place_and_diagnose(pt, target_out_dir, is_pt0, p_conn):
        pt_name = "起點錨點 (pt0)" if is_pt0 else "終點錨點 (pt1)"
        output.print_md("---")
        output.print_md("## 📌 放置法蘭於: **{}**".format(pt_name))
        
        output.print_md("- 🎯 **預期法蘭朝外法向量 (Target Outward Vector)**: `{}`".format(fmt_xyz(target_out_dir)))
        
        inst = doc.Create.NewFamilyInstance(pt, flange_symbol, DB.Structure.StructuralType.NonStructural)
        doc.Regenerate()
        
        try:
            pipe_dn_ft = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).AsDouble()
            for p_name in ["DN1", "DN2", "DN", "公稱直徑", "Nominal Diameter", "Size"]:
                p = inst.LookupParameter(p_name)
                if p and not p.IsReadOnly:
                    if "DN" in p_name: p.Set(float(round(pipe_dn_ft * 304.8)))
                    else: 
                        try: p.Set(pipe_dn_ft)
                        except: p.Set(float(round(pipe_dn_ft * 304.8)))
        except: pass
        doc.Regenerate()
        
        conns = [c for c in inst.MEPModel.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
        
        if len(conns) < 2:
            output.print_md("- ⚠️ **警告**: 法蘭擁有的 Connector 數量小於 2 (目前只有 {} 個)，無法執行雙向判定。".format(len(conns)))
            return inst
            
        conns.sort(key=lambda c: c.Origin.DistanceTo(pt))
        pipe_side_conn = conns[0]
        face_side_conn = conns[-1]
        
        output.print_md("- **捕捉到的法蘭內建接點 (Connectors)**:")
        output.print_md("   1. 👉 **接管專用端** (Connector 索引不固定) - 原點座標: `{}`".format(fmt_xyz(pipe_side_conn.Origin)))
        output.print_md("   2. 🛡 **對接外露面** (Connector 索引不固定) - 原點座標: `{}`".format(fmt_xyz(face_side_conn.Origin)))
        
        current_dir = pipe_side_conn.CoordinateSystem.BasisZ
        angle = current_dir.AngleTo(target_out_dir)
        
        output.print_md("- **對接前方位差**: 當前接管端 Z 軸指向 `{}`，與目標朝向夾角為: **{:.2f} 度**".format(fmt_xyz(current_dir), math.degrees(angle)))
        
        if angle > 0.001:
            rot_axis = current_dir.CrossProduct(target_out_dir)
            if rot_axis.GetLength() < 0.001:
                rot_axis = pipe_side_conn.CoordinateSystem.BasisX
                if rot_axis.GetLength() < 0.001:
                    rot_axis = pipe_side_conn.CoordinateSystem.BasisY
            
            rot_axis = rot_axis.Normalize()
            axis_line = DB.Line.CreateUnbound(pt, rot_axis)
            DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis_line, angle)
            doc.Regenerate()
            output.print_md("- 🔄 **旋轉引擎啟動**: 已自動對齊角度")
        else:
            output.print_md("- 🔄 **旋轉引擎**: 無須旋轉，方向已自然平行")
        
        if p_conn:
            try:
                conns2 = [c for c in inst.MEPModel.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
                conns2.sort(key=lambda c: c.Origin.DistanceTo(pt))
                updated_pipe_side_conn = conns2[0]
                
                p_conn.ConnectTo(updated_pipe_side_conn)
                output.print_md("- ✅ **連接驗證**: `ConnectTo()` API 呼叫**成功**！拓樸已接合。")
            except Exception as e:
                output.print_md("- ❌ **連接驗證**: 呼叫失敗，錯誤訊息 ({})".format(str(e)))
                
        t = inst.GetTransform()
        output.print_md("- 🏁 **定位結果結算**:")
        output.print_md("  * 實體 Transform.BasisZ = `{}`".format(fmt_xyz(t.BasisZ)))
        output.print_md("  * 實體 FacingOrientation = `{}`".format(fmt_xyz(inst.FacingOrientation)))
        
        return inst

    dir_pt0_out = -pipe_dir
    f0 = place_and_diagnose(pt0, dir_pt0_out, True, pipe_conn0)
    
    dir_pt1_out = pipe_dir
    f1 = place_and_diagnose(pt1, dir_pt1_out, False, pipe_conn1)

forms.alert("診斷測試完成！\n已經往南複製並精準計算、打出完整的空間分析報告。\n👉 請查閱即將開啟的 Output 視窗報告！", title="Flange Diagnosis")
