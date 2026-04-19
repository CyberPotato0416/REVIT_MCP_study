# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms
import json
import os

doc = revit.doc
uidoc = revit.uidoc

def dump_info():
    output_data = []
    
    # 優先從全模型搜尋目標名稱或 IFCGUID
    target_names = [
        "PIF_PROGEF Plus bf - flange adaptor comb joint face flat and serr_GF",
        "PIF_PROGEF Plus bf - outlet flange adaptor_GF"
    ]
    target_ids = ["2kCCeOSFr3b9qlvn7aQjx$", "2kCCeOSFr3b9qlvn7aQjtY"]
    
    # 收集選取的元件 (防呆)
    selection = [doc.GetElement(eid) for eid in uidoc.Selection.GetElementIds()]
    
    # 或者如果選取範圍內沒有，就全模型搜尋
    if not selection:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).ToElements()
        for inst in collector:
            uid = inst.UniqueId
            if inst.Name in target_names or any(t in uid for t in target_ids):
                selection.append(inst)
                
    if not selection:
        forms.alert("畫面上沒有選取元件，我也找不到指定名稱的法蘭！")
        return

    for inst in selection:
        if not isinstance(inst, DB.FamilyInstance):
            continue
            
        uid = inst.UniqueId
        
        elem_info = {
            "Name": inst.Name,
            "FamilyName": inst.Symbol.FamilyName if inst.Symbol else "Unknown",
            "Category": inst.Category.Name if inst.Category else "None",
            "Id": inst.Id.IntegerValue,
            "UniqueId": uid
        }
        
        param_part_type = inst.Symbol.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE)
        if not param_part_type:
            param_part_type = inst.Symbol.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE)
            
        if param_part_type:
            elem_info["PartType"] = param_part_type.AsInteger()
        
        # Connectors
        connectors_info = []
        mep_model = inst.MEPModel
        if mep_model and getattr(mep_model, "ConnectorManager", None):
            for conn in mep_model.ConnectorManager.Connectors:
                # 只記錄真實存在的實體接頭
                if conn.ConnectorType == DB.ConnectorType.Logical:
                    continue
                    
                connectors_info.append({
                    "Id": conn.Id,
                    "Shape": str(conn.Shape),
                    "Domain": str(conn.Domain),
                    "ConnectorType": str(conn.ConnectorType),
                    "Origin": "{}, {}, {}".format(conn.Origin.X, conn.Origin.Y, conn.Origin.Z),
                    "DirectionZ": "{}, {}, {}".format(conn.CoordinateSystem.BasisZ.X, conn.CoordinateSystem.BasisZ.Y, conn.CoordinateSystem.BasisZ.Z)
                })
        elem_info["Connectors"] = connectors_info
        
        output_data.append(elem_info)

    out_path = r"h:\0_REVIT MCP\REVIT_MCP_study-main\flange_info.json"
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    forms.alert("屬性已導出！請告訴 AI 已經點擊完畢。")

dump_info()
