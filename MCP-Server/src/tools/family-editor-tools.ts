/**
 * 族群編輯器專用工具 (Family Editor Tools)
 * 允許 AI Agent 在 Revit 族群環境 (.rfa) 中查詢環境、變更品類、增修參數與公式、建立參照平面及實體/空心拉伸。
 */

import { Tool } from "@modelcontextprotocol/sdk/types.js";

export const familyEditorTools: Tool[] = [
    {
        name: "get_family_editor_info",
        description: "取得當前族群編輯器環境資訊（作用中族群檔名、族群品類、族群類型列表、所有參數名稱與公式、既有參照平面）。僅能在族群環境 (.rfa) 中執行。",
        inputSchema: {
            type: "object",
            properties: {}
        }
    },
    {
        name: "set_family_category",
        description: "變更目前族群檔案的品類（如 Specialty Equipment、Generic Models、Doors、Windows 等），並可設定是否啟用載入時空心剪切 (cutWithVoids)。",
        inputSchema: {
            type: "object",
            properties: {
                categoryName: {
                    type: "string",
                    description: "品類名稱（英文或繁中，如 'Specialty Equipment' 或 '特殊設備'、'Generic Models' 或 '一般模型'）"
                },
                cutWithVoids: {
                    type: "boolean",
                    description: "是否啟用載入時空心剪切（預設 true）",
                    default: true
                }
            },
            required: ["categoryName"]
        }
    },
    {
        name: "add_family_parameter",
        description: "在目前族群中新增或更新參數，支援長度、整數、數值、是/否開關或文字，並可直接指定預設值與公式 (Formula)。",
        inputSchema: {
            type: "object",
            properties: {
                name: {
                    type: "string",
                    description: "參數名稱，如 '梯總高 H'、'踏桿間距'、'啟用防護籠'"
                },
                type: {
                    type: "string",
                    enum: ["Length", "Integer", "Number", "YesNo", "Text"],
                    description: "參數類型（預設 Length）",
                    default: "Length"
                },
                isInstance: {
                    type: "boolean",
                    description: "是否為實體參數 (Instance Parameter，可拉伸 Shape Handle)，預設 false (類型參數)",
                    default: false
                },
                value: {
                    type: "number",
                    description: "預設數值（長度單位為 mm，整數為數值，YesNo 傳 1 或 0）"
                },
                formula: {
                    type: "string",
                    description: "參數公式，如 '梯總高 H / 踏桿間距' 或 '梯總高 H > 3000 mm'"
                }
            },
            required: ["name"]
        }
    },
    {
        name: "create_reference_plane",
        description: "在目前族群視圖中建立一條命名的參照平面 (Reference Plane)，可用於尺寸定位與幾何約束對齊。",
        inputSchema: {
            type: "object",
            properties: {
                name: {
                    type: "string",
                    description: "參照平面名稱，如 '梯寬_左'、'離牆面'、'頂部扶手高'"
                },
                p1: {
                    type: "object",
                    properties: {
                        x: { type: "number", description: "起點 X 座標 (mm)" },
                        y: { type: "number", description: "起點 Y 座標 (mm)" },
                        z: { type: "number", description: "起點 Z 座標 (mm，預設 0)" }
                    },
                    required: ["x", "y"]
                },
                p2: {
                    type: "object",
                    properties: {
                        x: { type: "number", description: "終點 X 座標 (mm)" },
                        y: { type: "number", description: "終點 Y 座標 (mm)" },
                        z: { type: "number", description: "終點 Z 座標 (mm，預設 0)" }
                    },
                    required: ["x", "y"]
                }
            },
            required: ["name", "p1", "p2"]
        }
    },
    {
        name: "create_family_extrusion",
        description: "在目前族群環境中建立實體或空心拉伸幾何 (NewExtrusion)。支援圓形管狀 (circle)、矩形 (rectangle) 或任意多邊形封閉點序列 (points)，並可直接關聯端點至族群長度參數。",
        inputSchema: {
            type: "object",
            properties: {
                isSolid: {
                    type: "boolean",
                    description: "是否為實體 (true 實體拉伸，false 空心剪切)",
                    default: true
                },
                depth: {
                    type: "number",
                    description: "拉伸深度/高度 (mm)",
                    default: 1000.0
                },
                startOffset: {
                    type: "number",
                    description: "拉伸起點偏移 (mm)",
                    default: 0.0
                },
                planeName: {
                    type: "string",
                    description: "工作平面/參照平面名稱（若未填則預設使用水平基準 XY 平面）"
                },
                associateParamName: {
                    type: "string",
                    description: "要自動關聯拉伸端點 (EXTRUSION_END) 的族群參數名稱（如 '梯總高 H'）"
                },
                circle: {
                    type: "object",
                    description: "圓形輪廓（適用於圓管柱、踏桿、圓棒）",
                    properties: {
                        radius: { type: "number", description: "半徑 (mm)" },
                        center: {
                            type: "object",
                            properties: {
                                x: { type: "number" },
                                y: { type: "number" },
                                z: { type: "number" }
                            },
                            required: ["x", "y"]
                        }
                    },
                    required: ["radius"]
                },
                rectangle: {
                    type: "object",
                    description: "矩形輪廓",
                    properties: {
                        width: { type: "number", description: "寬度 (mm)" },
                        depth: { type: "number", description: "長度/深度 (mm)" },
                        center: {
                            type: "object",
                            properties: {
                                x: { type: "number" },
                                y: { type: "number" }
                            }
                        }
                    },
                    required: ["width", "depth"]
                },
                points: {
                    type: "array",
                    description: "任意多邊形封閉點序列（依序連接封閉）",
                    items: {
                        type: "object",
                        properties: {
                            x: { type: "number" },
                            y: { type: "number" },
                            z: { type: "number" }
                        },
                        required: ["x", "y"]
                    }
                }
            }
        }
    }
];
