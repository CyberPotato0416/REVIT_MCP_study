---
name: mep-automation-workflow
description: MEP 設備半自動標註流程 (Pick Mark)
tags: [MEP, 標註, SOP]
version: 1.2
---

# MEP 自動化處理流程

本文件定義 MEP 設備的標註標準與管路資訊查詢邏輯。

## 1. MEP 設備標註流程

MEP 設備（如泵浦、空調機組、控制盤）的標註應遵循專案命名編號規範。

### 標註標準
- **參數位置**：優先寫入 `Mark`參數；若為系統編號，則寫入自定義參數。
- **命名規則**：[系統代碼]-[樓層]-[序號] (例如：`WP-1F-01`)。

### 執行步驟
1. **針對單一或具體設備**：
   - 使用 `query_elements` 篩選。
   - 呼叫 `get_element_info` 確認當前參數內容。
   - 呼叫 `set_element_mark` 寫入新標號。

2. **針對批量點選編號 (Pick Mark 工作流)**：
   > [!WARNING]
   > **執行模式：Human-in-the-loop (手動互動)**
   > 批量標記 (Pick Mark) 核心邏輯實作於 pyRevit 腳本中，本機目前**沒有**完全對應的無人值守 MCP 工具！
   > 當使用者要求執行此流程時，**絕對禁止** AI 嘗試呼叫 `batch_set_marks` 等不存在或未實作之 MCP 工具以免導致迴圈報錯。
   > **AI 的唯一工作是引導使用者**：請輸出說明，明確引導使用者至 Revit 上方 Ribbon 點選 `MCP_Schedules -> PickMark (點選編號)` 按鈕，讓工程師親手在畫面中完成點擊操作。

