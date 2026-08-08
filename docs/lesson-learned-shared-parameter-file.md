# Revit 共享參數 (Shared Parameters) 腳本建立失敗之經驗總結 (Lesson Learned)

> **適合對象**：使用 pyRevit、Python 或 Revit API 進行專案參數批次自動化建立的開發者與 BIM 工程師。  
> **難易度**：白話口語、觀念避坑指南。

---

## 遇到的核心問題與現象

### 現象：執行 pyRevit 按鈕時拋出例外
執行 Python / IronPython 腳本寫入共享參數檔並開檔時，Revit API 拋出底層死棋級別的內部例外：
```text
Autodesk.Revit.Exceptions.InternalException: Error in readParamDatabase
於 Autodesk.Revit.ApplicationServices.Application.OpenSharedParameterFile()
```

### 白話解釋：
Revit API 的 `OpenSharedParameterFile()` 對外部 `.txt` 檔案的判定非常嚴苛！  
除了編碼必須是帶有 BOM 的 `UTF-16 LE` (Unicode) 規範之外，不同 Revit 版本/地區語系以及作業系統預設的跳格鍵 (Tab `\t`) 與換行符號 (`\r\n`)，只要有一點點格式微差，Revit 的 C++ Parser 就會直接崩潰拒絕讀取（誤以為檔案損壞），完全無法透過純 Python `open()` 或簡單的檔頭生成。

---

## 黃金標準最佳實踐 (Best Practice SOP)

當腳本自動建立全新的 Shared Parameter txt 檔案失敗或不可預期時，最穩健、100% 成功的避坑黃金組合為：

### 🛠️ 「手動建立乾淨 TXT 標頭 + 腳本自動批次建欄位與綁定」

```mermaid
flowchart TD
    A[使用者在 Revit UI 手動點擊「建立」共享參數檔 .txt] -->|產出 100% 合法格式與 GUID 標頭| B(Revit UI 環境已識別並綁定此 txt 檔)
    B --> C[點擊 pyRevit 自動化按鈕]
    C --> D[腳本自動開啟現有合法 txt]
    D --> E[API 自動在記憶體與 txt 批次建立所有Definitions]
    E --> F[一鍵綁定 Binding 至目標品類 (如 Rooms)]
```

#### 步驟 1：使用者先手動建立乾淨的 TXT 標頭
1. 打開 Revit，前往 **管理 (Manage)** 頁籤 → 點擊 **共用參數 (Shared Parameters)**。
2. 點擊 **「建立 (Create)」**，選擇路徑並存成一個全新的 `.txt` 檔案（或隨手建立一個測試參數）。
3. **原理**：由 Revit 官方介面產生的檔案，100% 帶有目前 Revit 版本與語系最相容的隱藏 BOM、GUID 與格式標頭。

#### 步驟 2：後續由 pyRevit 腳本接手全自動化
1. 腳本呼叫 `app.OpenSharedParameterFile()` 讀取這個合法的 `.txt` 檔。
2. 腳本透過 API `group.Definitions.Create(...)` 自動在記憶體與檔案中**批次新增大量參數定義**（如：`樓層粉刷代號`、`牆面粉刷代號`、`天花板粉刷代號`）。
3. 自動建立 `NewInstanceBinding` 並寫入 `doc.ParameterBindings`，**一鍵綁定至專案品類（如 Rooms）**。

---

## 程式碼例外處理建議 (Code Defensive Pattern)

在 pyRevit 腳本中，建議加入以下**黃金防衛邏輯 (Defensive Handling)**：若檢測到 `OpenSharedParameterFile()` 失敗，自動彈窗指引使用者進行「步驟 1」手動建立，避免程式直接崩潰：

```python
# 防衛型共享參數檔載入範例
definition_file = None
try:
    definition_file = app.OpenSharedParameterFile()
except Exception:
    definition_file = None

# 若無法讀取，指引使用者手動挑選或建置標頭
if definition_file is None:
    forms.alert(
        "【溫馨提示】\n\nRevit 目前無法解析共享參數檔。\n"
        "請在 Revit「管理 -> 共用參數」中手動【建立】一個空白 txt 檔後再試！",
        title="共享參數檔載入提示",
        warn_icon=True
    )
    selected_file = forms.pick_file(file_ext='txt', title='選擇您建立的共享參數檔 (.txt)')
    if selected_file:
        app.SharedParametersFilename = selected_file
        definition_file = app.OpenSharedParameterFile()
```

---

> **最後更新日期**：2026-07-28  
> **紀錄與貢獻者**：Jerry / Antigravity Assistant  
