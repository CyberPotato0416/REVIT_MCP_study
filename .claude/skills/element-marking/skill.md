---
name: element-marking
description: "對 Revit 元素進行單一或批量標記（Mark）與編號。提供自動流水號、前綴設定與參數改值。觸發字：標號, 編號, Mark, 標記, 批量編號, 自動流水號, marking, sequential tagging, project marks."
---

# 元素標記與自動編號

本 Skill 協助管理 Revit 專案中門、窗、設備或週邊元件的識別標號（Mark）。支援單一編輯與大規模批量編號。

## Sub-Workflows

### 1. 單一標記設定
為特定的 Revit 元素設定識別編碼。
1. 取得目標元素 ID。
2. 呼叫 `set_element_mark` 設定其 `Mark` 參數內容。

### 2. 批量自動編號
針對一組選取的元素，按照指定的規則（前綴、起始序號、位數）產生連續的標號。
1. 搜集目標元素 ID 列表。
2. 指定前綴（如 `D-` 代表門）。
3. 指定起始數字與位數。
4. 呼叫 `batch_set_marks` 進行處理。

## 工具
| 工具名稱 | 用途 | 模組 |
|---------|------|------|
| `set_element_mark` | 設定單一元素的 Mark 參數。 | `marking-tools` |
| `batch_set_marks` | 批量元素依規則自動產生標號。 | `marking-tools` |

## Reference
詳見 `domain/marking-system-sop.md`。
