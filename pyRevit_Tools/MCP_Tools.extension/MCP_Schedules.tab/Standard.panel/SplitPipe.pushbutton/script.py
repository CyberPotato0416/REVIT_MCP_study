# -*- coding: utf-8 -*-
"""
UPW 管線 Delete & Redraw (砍掉重練) 工具
作者: Antigravity / Jerry
說明: 不改變原管線頭尾邊界！在總長度內每隔滿管(5m)打斷一次，並安插背對背法蘭間隙。
"""
from pyrevit import revit, DB, forms, script
import math
import System
from domain import PipeSplitMathDomain

logger = script.get_logger()
doc = revit.doc
uidoc = revit.uidoc

# ─────────────────────────────────────────
# 步驟 1: 設定與獲取法蘭族群
# ─────────────────────────────────────────
all_symbols = (DB.FilteredElementCollector(doc)
               .OfClass(DB.FamilySymbol)
               .OfCategory(DB.BuiltInCategory.OST_PipeFitting)
               .ToElements())

target_flange_name = "PIF_PROGEF Plus bf - flange adaptor comb joint face flat and serr_GF".lower()
selected_flange_symbol = None

for sym in all_symbols:
    name = "{} - {}".format(sym.FamilyName, sym.Name)
    if target_flange_name in name.lower() or target_flange_name in sym.Name.lower() or target_flange_name in sym.FamilyName.lower():
        selected_flange_symbol = sym
        break

if not selected_flange_symbol:
    forms.alert("找不到法蘭型號，請確認族群已載入！", exitscript=True)

if not selected_flange_symbol.IsActive:
    with revit.Transaction("啟用法蘭"):
        selected_flange_symbol.Activate()
        doc.Regenerate()

# ─────────────────────────────────────────
# 步驟 2: 向使用者詢問幾何參數
# ─────────────────────────────────────────
res_pipe = forms.ask_for_string(default="5000", prompt="請輸入直管標準出廠長度 (mm):", title="Delete & Redraw 切管設定")
res_gap = forms.ask_for_string(default="156", prompt="請輸入 兩片背對背法蘭 的總間隔厚距 Gap (mm):", title="Delete & Redraw 切管設定")

if not res_pipe or not res_gap:
    script.exit()

try:
    raw_pipe_length_mm = float(res_pipe)
    flange_pair_gap_mm = float(res_gap)
except Exception:
    forms.alert("請輸入有效的數字！", exitscript=True)

# ─────────────────────────────────────────
# 步驟 3: 執行生成
# ─────────────────────────────────────────
selected_ids = uidoc.Selection.GetElementIds()
pipes = [doc.GetElement(eid) for eid in selected_ids if isinstance(doc.GetElement(eid), DB.Plumbing.Pipe)]

if not pipes:
    forms.alert("請至少選取一根直管！", exitscript=True)

new_created_elements = []

with revit.Transaction("砍掉重練式 - 精準管線切分生成"):
    for pipe in pipes:
        sys_type_id = pipe.MEPSystem.GetTypeId() if pipe.MEPSystem else DB.ElementId.InvalidElementId
        pipe_type_id = pipe.PipeType.Id
        level_id = pipe.ReferenceLevel.Id if pipe.ReferenceLevel else doc.ActiveView.GenLevel.Id
        diam_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
        diam_val = diam_param.AsDouble() if diam_param else 0.0
        
        curve = pipe.Location.Curve
        pt0 = curve.GetEndPoint(0)
        pt1 = curve.GetEndPoint(1)
        total_len_ft = pt0.DistanceTo(pt1)
        pipe_dir = (pt1 - pt0).Normalize()
        
        # 記憶兩端外部接頭
        conns = [c for c in pipe.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
        conn0 = min(conns, key=lambda c: c.Origin.DistanceTo(pt0)) if conns else None
        conn1 = min(conns, key=lambda c: c.Origin.DistanceTo(pt1)) if conns else None
        
        orig_refs_0 = [r for r in conn0.AllRefs if r.Owner.Id != pipe.Id and r.ConnectorType != DB.ConnectorType.Logical] if conn0 else []
        orig_refs_1 = [r for r in conn1.AllRefs if r.Owner.Id != pipe.Id and r.ConnectorType != DB.ConnectorType.Logical] if conn1 else []
        
        # 計算 1D 空間切分陣列
        domain_core = PipeSplitMathDomain(raw_pipe_length=raw_pipe_length_mm, flange_pair_thickness=flange_pair_gap_mm)
        segments = domain_core.calculate_split_spans(total_len_ft * 304.8)
        
        # 砍！
        doc.Delete(pipe.Id)
        
        def attach_flange(pt, target_out_dir, target_pipe_conn):
            f = doc.Create.NewFamilyInstance(pt, selected_flange_symbol, DB.Structure.StructuralType.NonStructural)
            doc.Regenerate()
            for nm in ["DN1", "DN2", "DN", "Size"]:
                pm = f.LookupParameter(nm)
                if pm and not pm.IsReadOnly:
                    try: pm.Set(diam_val)
                    except:
                        try: pm.Set(float(round(diam_val * 304.8)))
                        except: pass
            doc.Regenerate()
            new_created_elements.append(f.Id)
            
            f_conns = [c for c in f.MEPModel.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
            f_conns.sort(key=lambda c: c.Origin.DistanceTo(pt))
            pipe_sc = f_conns[0]
            
            c_dir = pipe_sc.CoordinateSystem.BasisZ
            ang = c_dir.AngleTo(target_out_dir)
            if ang > 0.001:
                ax = c_dir.CrossProduct(target_out_dir)
                if ax.GetLength() < 0.001:
                    ax = pipe_sc.CoordinateSystem.BasisX
                    if ax.GetLength() < 0.001: ax = pipe_sc.CoordinateSystem.BasisY
                DB.ElementTransformUtils.RotateElement(doc, f.Id, DB.Line.CreateUnbound(pt, ax.Normalize()), ang)
                doc.Regenerate()
                
            f_conns2 = [c for c in f.MEPModel.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
            f_conns2.sort(key=lambda c: c.Origin.DistanceTo(pt))
            
            # 將法蘭接到管子上！
            if target_pipe_conn:
                target_pipe_conn.ConnectTo(f_conns2[0])
            
            return f, f_conns2[-1]
            
        prev_flange_B_outer = None
        first_pipe_start_conn = None
        last_pipe_end_conn = None
        
        for seg in segments:
            # 轉換為 Revit 世界坐標系 3D (feet)
            p_start_pt = pt0 + pipe_dir * (seg["pipe_start"] / 304.8)
            p_end_pt = pt0 + pipe_dir * (seg["pipe_end"] / 304.8)
            
            # 生成該斷面管線
            new_pipe = DB.Plumbing.Pipe.Create(doc, sys_type_id, pipe_type_id, level_id, p_start_pt, p_end_pt)
            new_pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(diam_val)
            doc.Regenerate()
            new_created_elements.append(new_pipe.Id)
            
            p_conns = [c for c in new_pipe.ConnectorManager.Connectors if c.ConnectorType != DB.ConnectorType.Logical]
            p_conn_A = min(p_conns, key=lambda c: c.Origin.DistanceTo(p_start_pt))
            p_conn_B = min(p_conns, key=lambda c: c.Origin.DistanceTo(p_end_pt))
            
            # 第一段管的頭，需要留著後續接外部母體
            if seg["segment_index"] == 0:
                first_pipe_start_conn = p_conn_A
            # 每一段管的尾，隨時更新留著給最後接母體
            last_pipe_end_conn = p_conn_B
            
            # 前置法蘭 (有法蘭代表要跟上一個模組互扣)
            if seg["has_start_flange"]:
                fA, fA_out = attach_flange(p_start_pt, pipe_dir, p_conn_A)
                # 與上一個模組的尾巴互扣
                if prev_flange_B_outer:
                    try: prev_flange_B_outer.ConnectTo(fA_out)
                    except: pass
                    
            # 後置法蘭
            if seg["has_end_flange"]:
                fB, fB_out = attach_flange(p_end_pt, -pipe_dir, p_conn_B)
                prev_flange_B_outer = fB_out
                
        # 整個大陣列生成完畢，首尾管線嘗試接回母體
        if first_pipe_start_conn and orig_refs_0:
            for r in orig_refs_0:
                try: first_pipe_start_conn.ConnectTo(r)
                except: pass
        if last_pipe_end_conn and orig_refs_1:
            for r in orig_refs_1:
                try: last_pipe_end_conn.ConnectTo(r)
                except: pass

ListType = System.Collections.Generic.List[DB.ElementId]
ids_list = ListType()
for eid in new_created_elements: ids_list.Add(eid)
uidoc.Selection.SetElementIds(ids_list)

forms.alert("✅ Delete & Redraw 完美管線替換完成！\n所有直管均被保證從錨點出發，並精準插入背對背法蘭間隙。")
