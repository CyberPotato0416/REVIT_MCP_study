---
name: connector-query-workflow
description: 管路接頭資訊查詢流程 (尚未實測完畢 WIP)
tags: [MEP, 接頭, SOP, WIP]
version: 0.1
---

# 管路接頭資訊查詢

在進行空間協調或自動配管前，需先取得管線末端的座標與狀態。

## 執行步驟
1. 取得目標管件（Pipe/Duct） ID。
2. 呼叫 `get_connector_info` 檢查所有接頭（Connector）。
3. AI 應彙整回傳的座標與連接狀態，供後續路徑規劃參考。

## 注意事項
- **單位格式**：API 內部座標使用公釐 (mm)。
- **重複检查**：在標註前，建議先檢查是否有重複的 Mark 值，避免 Revit 發出重複警告。
