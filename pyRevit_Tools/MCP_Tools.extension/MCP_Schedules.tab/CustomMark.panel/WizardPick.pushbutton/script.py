# -*- coding: utf-8 -*-
"""Wizard Pick and Mark tool."""

__title__ = "Wizard Pick"
__author__ = "MCP"

import clr
import ctypes
import os

clr.AddReference("PresentationCore")
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")

from System.Windows import Point
from Autodesk.Revit import DB
from pyrevit import forms, revit, script


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_mouse_screen_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def get_target_param(element, param_name):
    try:
        param = element.LookupParameter(param_name)
        if param and not param.IsReadOnly:
            return param
    except Exception:
        pass
    return None


class MCPWizardSuccessWindow(forms.WPFWindow):
    def __init__(self, xaml_file, mark_text, spawn_x, spawn_y):
        forms.WPFWindow.__init__(self, xaml_file)
        self.msg_text.Text = str(mark_text)
        self.Left = spawn_x + 50
        self.Top = spawn_y + 50
        self.ContentRendered += self.on_rendered

    def on_rendered(self, sender, args):
        try:
            screen_pos = self.ok_btn.PointToScreen(Point(50, 17))
            ctypes.windll.user32.SetCursorPos(int(screen_pos.X), int(screen_pos.Y))
        except Exception:
            pass

    def on_ok(self, sender, args):
        self.Close()


def format_wizard_tag(config):
    # 1. System + 2. Flow + 3. ;
    tag = config.get_option("system", "")
    tag += config.get_option("flow", "")
    tag += ";"
    
    # 4. Building + .
    tag += config.get_option("building", "F2")
    tag += "."
    
    # 5. Floor + .
    tag += config.get_option("floor", "L05")
    tag += "."
    
    # 6. Column + 7. Ceiling + .
    tag += config.get_option("column", "")
    tag += config.get_option("ceiling", "")
    tag += "."
    
    # 8. Direction + -
    tag += config.get_option("direction", "")
    tag += "-"
    
    # 9. Sequence
    idx = config.get_option("index", 1)
    padding = config.get_option("padding", 2)
    
    fmt = "{:0" + str(padding) + "d}"
    seq_str = fmt.format(int(idx))
    tag += seq_str
    
    return tag


def run_wizard_pick():
    config = script.get_config("MCP_Wizard")
    target_param_name = config.get_option("target_param", "MCP_Marking")
    
    if not target_param_name:
        forms.alert("請先在『精靈設定』中設定目標參數名稱。", title="精靈未設定")
        return

    xaml_file = os.path.join(os.path.dirname(__file__), "confirm.xaml")
    count = 0

    while True:
        try:
            element = revit.pick_element("精靈標註模式：請點選元件。按下 ESC 結束。")
        except Exception:
            break

        if not element:
            break

        # Generate tag
        mark_value = format_wizard_tag(config)
        mouse_x, mouse_y = get_mouse_screen_pos()

        try:
            with revit.Transaction("MCP Wizard: Mark {}".format(mark_value)):
                param = get_target_param(element, target_param_name)
                if not param:
                    elem_cat = element.Category.Name if element.Category else "Unknown"
                    msg = "元件 [ID: {}] (類別: {}) 找不到可寫入的參數『{}』。\n請檢查參數名稱是否 100% 正確。".format(
                        element.Id, elem_cat, target_param_name)
                    forms.alert(msg, title="精靈標註錯誤")
                    continue
                
                param.Set(mark_value)
        except Exception as ex:
            forms.alert("標註失敗: {}".format(ex), title="精靈標註錯誤")
            continue

        # Show success dialog
        window = MCPWizardSuccessWindow(xaml_file, mark_value, mouse_x, mouse_y)
        window.show_dialog()

        # Update index
        count += 1
        curr_idx = config.get_option("index", 1)
        step = config.get_option("step", 1)
        config.set_option("index", curr_idx + step)
        script.save_config()

    forms.alert("精靈標註結束。共更新了 {} 個元件。".format(count), title="MCP 標註精靈")


if __name__ == "__main__":
    run_wizard_pick()
