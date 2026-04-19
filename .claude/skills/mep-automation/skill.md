---
name: mep-automation
description: "對 MEP 元素進行自動標註與資訊查詢。提供設備流水號編號與管路接頭座標檢查。觸發字：MEP, 標註設備, 管件, 接頭, mep marking, mep equipment, connector info."
---

# MEP 設備標註與管路資訊查詢

本 Skill 提供 MEP（機械、電機、管路）相關的自動化工具編排，協助完成設備標註與管路系統狀態檢查。

## Sub-Workflows

### 1. 管路接頭狀態檢查
查詢指定管線的接頭座標與連接狀態，用於空間協調或路徑分析。
1. 取得目標管件的所有接頭資訊。
2. 回傳接頭座標、方向與目前是否已連接。

### 2. 批量設備標註
為一群組的 MEP 設備設定帶有前綴的自動流水號（Mark）。
1. 確認目標設備 ID 列表。
2. 執行前綴（prefix）與起始流水號（startNumber）的設定。

## 工具
| 工具名稱 | 用途 | 模組 |
|---------|------|------|
| `get_connector_info` | 取得 MEP 元素的接頭座標與連接狀態。 | `mep-tools` |
| `batch_set_marks` | 為元素列表進行流水號批量編號。 | `marking-tools` |
| `set_element_mark` | 為單一元素設定標記（Mark）內容。 | `marking-tools` |

## Reference
詳見 `domain/mep-automation-workflow.md`。
