using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;

#if REVIT2025_OR_GREATER
using IdType = System.Int64;
#else
using IdType = System.Int32;
#endif

namespace RevitMCP.Core
{
    public partial class CommandExecutor
    {
        /// <summary>
        /// 輔助函式：取得目前作用中的族群文件 (Family Document)
        /// 若當前非族群文件，拋出明確例外
        /// </summary>
        private Document GetActiveFamilyDocument()
        {
            Document doc = _uiApp.ActiveUIDocument?.Document;
            if (doc == null)
            {
                throw new InvalidOperationException("未找到作用中的 Revit 文件。");
            }
            if (!doc.IsFamilyDocument)
            {
                throw new InvalidOperationException($"目前作用中文件 '{doc.Title}' 不是族群文件 (.rfa)。此工具僅能在族群編輯器環境中執行。");
            }
            return doc;
        }

        /// <summary>
        /// 輔助函式：取得草圖平面 (SketchPlane)
        /// 若未指定 planeName，預設使用族群內部 Z=0 的基準水平面
        /// </summary>
        private SketchPlane GetOrCreateSketchPlane(Document famDoc, string planeName = null)
        {
            if (!string.IsNullOrWhiteSpace(planeName))
            {
                var refPlane = new FilteredElementCollector(famDoc)
                    .OfClass(typeof(ReferencePlane))
                    .Cast<ReferencePlane>()
                    .FirstOrDefault(rp => string.Equals(rp.Name, planeName, StringComparison.OrdinalIgnoreCase));

                if (refPlane != null)
                {
                    Plane pl = Plane.CreateByNormalAndOrigin(refPlane.Normal, refPlane.BubbleEnd);
                    return SketchPlane.Create(famDoc, pl);
                }

                var datumPlane = new FilteredElementCollector(famDoc)
                    .OfClass(typeof(SketchPlane))
                    .Cast<SketchPlane>()
                    .FirstOrDefault(sp => string.Equals(sp.Name, planeName, StringComparison.OrdinalIgnoreCase));

                if (datumPlane != null)
                {
                    return datumPlane;
                }
            }

            // 預設建立基準水平 XY 平面 (Normal: BasisZ, Origin: Zero)
            Plane xyPlane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero);
            return SketchPlane.Create(famDoc, xyPlane);
        }

        /// <summary>
        /// 工具 1: 取得當前族群編輯器之環境資訊 (族群品類、族群類型、參數清單、參照平面)
        /// </summary>
        private object GetFamilyEditorInfo()
        {
            Document famDoc = GetActiveFamilyDocument();
            FamilyManager mgr = famDoc.FamilyManager;

            var types = mgr.Types
                .Cast<FamilyType>()
                .Select(t => t.Name)
                .ToList();

            var parameters = mgr.Parameters
                .Cast<FamilyParameter>()
                .Select(p => new
                {
                    Name = p.Definition.Name,
                    IsInstance = p.IsInstance,
                    IsShared = p.IsShared,
                    Formula = p.Formula ?? string.Empty,
                    StorageType = p.StorageType.ToString()
                })
                .ToList();

            var refPlanes = new FilteredElementCollector(famDoc)
                .OfClass(typeof(ReferencePlane))
                .Cast<ReferencePlane>()
                .Select(rp => new
                {
                    Id = (IdType)rp.Id.Value,
                    Name = rp.Name ?? string.Empty
                })
                .ToList();

            return new
            {
                Title = famDoc.Title,
                Category = famDoc.OwnerFamily?.FamilyCategory?.Name ?? "未知",
                CategoryId = famDoc.OwnerFamily?.FamilyCategory != null ? (IdType)famDoc.OwnerFamily.FamilyCategory.Id.Value : -1,
                CurrentType = mgr.CurrentType?.Name ?? string.Empty,
                Types = types,
                Parameters = parameters,
                ReferencePlanes = refPlanes
            };
        }

        /// <summary>
        /// 工具 2: 設定族群品類 (例如: Specialty Equipment, Generic Models)
        /// </summary>
        private object SetFamilyCategory(JObject parameters)
        {
            Document famDoc = GetActiveFamilyDocument();
            string categoryName = parameters["categoryName"]?.Value<string>();
            bool cutWithVoids = parameters["cutWithVoids"]?.Value<bool>() ?? true;

            if (string.IsNullOrWhiteSpace(categoryName))
            {
                throw new ArgumentException("必須提供 categoryName 參數。");
            }

            Family ownerFamily = famDoc.OwnerFamily;
            if (ownerFamily == null)
            {
                throw new InvalidOperationException("無法取得族群的 OwnerFamily 物件。");
            }

            Category targetCategory = null;
            Categories categories = famDoc.Settings.Categories;
            foreach (Category cat in categories)
            {
                if (string.Equals(cat.Name, categoryName, StringComparison.OrdinalIgnoreCase) ||
                    cat.Name.IndexOf(categoryName, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    targetCategory = cat;
                    break;
                }
            }

            using (Transaction tx = new Transaction(famDoc, "MCP: 設定族群品類"))
            {
                tx.Start();

                if (targetCategory != null && ownerFamily.IsAppropriateCategoryId(targetCategory.Id))
                {
                    ownerFamily.FamilyCategoryId = targetCategory.Id;
                }

                if (cutWithVoids)
                {
                    Parameter cutParam = ownerFamily.get_Parameter(BuiltInParameter.FAMILY_ALLOW_CUT_WITH_VOIDS);
                    if (cutParam != null && !cutParam.IsReadOnly)
                    {
                        cutParam.Set(1);
                    }
                }

                tx.Commit();
            }

            return new
            {
                Success = true,
                CurrentCategory = ownerFamily.FamilyCategory?.Name ?? categoryName,
                CutWithVoids = cutWithVoids
            };
        }

        /// <summary>
        /// 工具 3: 新增/更新族群參數與公式
        /// </summary>
        private object AddFamilyParameter(JObject parameters)
        {
            Document famDoc = GetActiveFamilyDocument();
            string paramName = parameters["name"]?.Value<string>();
            string paramType = parameters["type"]?.Value<string>() ?? "Length"; // Length, Integer, Number, YesNo, Text
            bool isInstance = parameters["isInstance"]?.Value<bool>() ?? false;
            string formula = parameters["formula"]?.Value<string>();
            double? doubleValue = parameters["value"]?.Value<double>();

            if (string.IsNullOrWhiteSpace(paramName))
            {
                throw new ArgumentException("必須提供參數名稱 name。");
            }

            FamilyManager mgr = famDoc.FamilyManager;
            FamilyParameter famParam = null;

            using (Transaction tx = new Transaction(famDoc, $"MCP: 新增/更新族群參數 {paramName}"))
            {
                tx.Start();

                famParam = mgr.get_Parameter(paramName);
                if (famParam == null)
                {
                    ForgeTypeId specTypeId = SpecTypeId.Length;
                    if (string.Equals(paramType, "Integer", StringComparison.OrdinalIgnoreCase)) specTypeId = SpecTypeId.Int.Integer;
                    else if (string.Equals(paramType, "Number", StringComparison.OrdinalIgnoreCase)) specTypeId = SpecTypeId.Number;
                    else if (string.Equals(paramType, "YesNo", StringComparison.OrdinalIgnoreCase) || string.Equals(paramType, "Boolean", StringComparison.OrdinalIgnoreCase)) specTypeId = SpecTypeId.Boolean.YesNo;
                    else if (string.Equals(paramType, "Text", StringComparison.OrdinalIgnoreCase) || string.Equals(paramType, "String", StringComparison.OrdinalIgnoreCase)) specTypeId = SpecTypeId.String.Text;

                    famParam = mgr.AddParameter(paramName, GroupTypeId.Geometry, specTypeId, isInstance);
                }

                if (doubleValue.HasValue)
                {
                    if (string.Equals(paramType, "Length", StringComparison.OrdinalIgnoreCase))
                    {
                        mgr.Set(famParam, doubleValue.Value * (1.0 / 304.8));
                    }
                    else if (string.Equals(paramType, "Integer", StringComparison.OrdinalIgnoreCase))
                    {
                        mgr.Set(famParam, (int)doubleValue.Value);
                    }
                    else
                    {
                        mgr.Set(famParam, doubleValue.Value);
                    }
                }

                if (!string.IsNullOrWhiteSpace(formula))
                {
                    mgr.SetFormula(famParam, formula);
                }

                tx.Commit();
            }

            return new
            {
                Success = true,
                ParameterName = famParam.Definition.Name,
                IsInstance = famParam.IsInstance,
                Formula = famParam.Formula ?? formula
            };
        }

        /// <summary>
        /// 工具 4: 建立參照平面 (Reference Plane)
        /// </summary>
        private object CreateReferencePlane(JObject parameters)
        {
            Document famDoc = GetActiveFamilyDocument();
            string name = parameters["name"]?.Value<string>();
            var p1Obj = parameters["p1"] as JObject;
            var p2Obj = parameters["p2"] as JObject;

            if (p1Obj == null || p2Obj == null)
            {
                throw new ArgumentException("必須提供起點 p1 與終點 p2 {x, y, z} (單位: mm)。");
            }

            double scale = 1.0 / 304.8;
            XYZ p1 = new XYZ(p1Obj["x"].Value<double>() * scale, p1Obj["y"].Value<double>() * scale, (p1Obj["z"]?.Value<double>() ?? 0.0) * scale);
            XYZ p2 = new XYZ(p2Obj["x"].Value<double>() * scale, p2Obj["y"].Value<double>() * scale, (p2Obj["z"]?.Value<double>() ?? 0.0) * scale);

            ReferencePlane refPlane = null;
            using (Transaction tx = new Transaction(famDoc, $"MCP: 建立參照平面 {name}"))
            {
                tx.Start();
                XYZ cutVec = XYZ.BasisZ;
                if (Math.Abs(p1.Z - p2.Z) > 1e-4)
                {
                    cutVec = XYZ.BasisY;
                }

                refPlane = famDoc.FamilyCreate.NewReferencePlane(p1, p2, cutVec, famDoc.ActiveView);
                if (!string.IsNullOrWhiteSpace(name))
                {
                    refPlane.Name = name;
                }
                tx.Commit();
            }

            return new
            {
                Success = true,
                Id = (IdType)refPlane.Id.Value,
                Name = refPlane.Name
            };
        }

        /// <summary>
        /// 工具 5: 建立實體/空心拉伸幾何 (NewExtrusion)
        /// 支援多邊形輪廓 (封閉點陣列) 或圓形輪廓 (center + radius)
        /// 座標與尺寸單位: mm
        /// </summary>
        private object CreateFamilyExtrusion(JObject parameters)
        {
            Document famDoc = GetActiveFamilyDocument();
            bool isSolid = parameters["isSolid"]?.Value<bool>() ?? true;
            double depthMm = parameters["depth"]?.Value<double>() ?? 1000.0;
            double startOffsetMm = parameters["startOffset"]?.Value<double>() ?? 0.0;
            string planeName = parameters["planeName"]?.Value<string>();
            string associateParamName = parameters["associateParamName"]?.Value<string>();

            double scale = 1.0 / 304.8;
            double depthFeet = depthMm * scale;
            double startOffsetFeet = startOffsetMm * scale;

            SketchPlane sketchPlane = GetOrCreateSketchPlane(famDoc, planeName);
            CurveArrArray curveArrArray = new CurveArrArray();
            CurveArray loop = new CurveArray();

            if (parameters["circle"] is JObject circleObj)
            {
                double radiusMm = circleObj["radius"]?.Value<double>() ?? 25.0;
                double rFeet = radiusMm * scale;
                var c = circleObj["center"] as JObject;
                XYZ center = c != null 
                    ? new XYZ(c["x"].Value<double>() * scale, c["y"].Value<double>() * scale, (c["z"]?.Value<double>() ?? 0.0) * scale)
                    : XYZ.Zero;

                XYZ p1 = center + new XYZ(rFeet, 0, 0);
                XYZ p2 = center - new XYZ(rFeet, 0, 0);
                XYZ mid1 = center + new XYZ(0, rFeet, 0);
                XYZ mid2 = center - new XYZ(0, -rFeet, 0);

                Arc arc1 = Arc.Create(p1, p2, mid1);
                Arc arc2 = Arc.Create(p2, p1, mid2);
                loop.Append(arc1);
                loop.Append(arc2);
            }
            else if (parameters["points"] is JArray pointsArr && pointsArr.Count >= 3)
            {
                List<XYZ> pts = new List<XYZ>();
                foreach (JObject ptObj in pointsArr)
                {
                    pts.Add(new XYZ(
                        ptObj["x"].Value<double>() * scale,
                        ptObj["y"].Value<double>() * scale,
                        (ptObj["z"]?.Value<double>() ?? 0.0) * scale
                    ));
                }

                for (int i = 0; i < pts.Count; i++)
                {
                    XYZ start = pts[i];
                    XYZ end = pts[(i + 1) % pts.Count];
                    loop.Append(Line.CreateBound(start, end));
                }
            }
            else if (parameters["rectangle"] is JObject rectObj)
            {
                double wFeet = (rectObj["width"]?.Value<double>() ?? 400.0) * scale;
                double dFeet = (rectObj["depth"]?.Value<double>() ?? 400.0) * scale;
                var c = rectObj["center"] as JObject;
                double cx = (c?["x"]?.Value<double>() ?? 0.0) * scale;
                double cy = (c?["y"]?.Value<double>() ?? 0.0) * scale;

                XYZ p0 = new XYZ(cx - wFeet / 2.0, cy - dFeet / 2.0, 0);
                XYZ p1 = new XYZ(cx + wFeet / 2.0, cy - dFeet / 2.0, 0);
                XYZ p2 = new XYZ(cx + wFeet / 2.0, cy + dFeet / 2.0, 0);
                XYZ p3 = new XYZ(cx - wFeet / 2.0, cy + dFeet / 2.0, 0);

                loop.Append(Line.CreateBound(p0, p1));
                loop.Append(Line.CreateBound(p1, p2));
                loop.Append(Line.CreateBound(p2, p3));
                loop.Append(Line.CreateBound(p3, p0));
            }
            else
            {
                throw new ArgumentException("必須提供 circle (圓形)、points (點陣列) 或 rectangle (矩形) 幾何定義。");
            }

            curveArrArray.Append(loop);

            Extrusion extrusion = null;
            using (Transaction tx = new Transaction(famDoc, isSolid ? "MCP: 建立實體拉伸" : "MCP: 建立空心拉伸"))
            {
                tx.Start();
                extrusion = famDoc.FamilyCreate.NewExtrusion(isSolid, curveArrArray, sketchPlane, depthFeet);

                if (Math.Abs(startOffsetFeet) > 1e-4)
                {
                    Parameter startParam = extrusion.get_Parameter(BuiltInParameter.EXTRUSION_START_PARAM);
                    if (startParam != null && !startParam.IsReadOnly)
                    {
                        startParam.Set(startOffsetFeet);
                    }
                }

                if (!string.IsNullOrWhiteSpace(associateParamName))
                {
                    FamilyManager mgr = famDoc.FamilyManager;
                    FamilyParameter famParam = mgr.get_Parameter(associateParamName);
                    if (famParam != null)
                    {
                        Parameter endParam = extrusion.get_Parameter(BuiltInParameter.EXTRUSION_END_PARAM);
                        if (endParam != null && mgr.CanElementParameterBeAssociated(endParam))
                        {
                            mgr.AssociateElementParameterToFamilyParameter(endParam, famParam);
                        }
                    }
                }

                tx.Commit();
            }

            return new
            {
                Success = true,
                Id = (IdType)extrusion.Id.Value,
                IsSolid = isSolid,
                DepthMm = depthMm
            };
        }
    }
}
