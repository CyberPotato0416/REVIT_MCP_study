# -*- coding: utf-8 -*-
"""Settings for MCP Marking Wizard."""

__title__ = "Wizard Settings"
__author__ = "MCP"

import os
from pyrevit import forms, script


class MCPWizardSettingsWindow(forms.WPFWindow):
    def __init__(self, xaml_file, **kwargs):
        forms.WPFWindow.__init__(self, xaml_file)
        self.target_param_box.Text = str(kwargs.get("target_param", "MCP_Marking"))
        self.system_box.Text = str(kwargs.get("system", ""))
        self.flow_box.Text = str(kwargs.get("flow", ""))
        self.building_box.Text = str(kwargs.get("building", "F2"))
        self.floor_box.Text = str(kwargs.get("floor", "L05"))
        self.column_box.Text = str(kwargs.get("column", ""))
        self.ceiling_box.Text = str(kwargs.get("ceiling", ""))
        self.direction_box.Text = str(kwargs.get("direction", ""))
        
        self.index_box.Text = str(kwargs.get("index", 1))
        self.padding_box.Text = str(kwargs.get("padding", 2))
        self.step_box.Text = str(kwargs.get("step", 1))
        
        self.response = None
        self.start_picking = False

    def on_save(self, sender, args):
        self._process_response()

    def on_start(self, sender, args):
        self._process_response()
        if self.response:
            self.start_picking = True

    def _process_response(self):
        # Validation
        if not self.target_param_box.Text:
            forms.alert("請輸入目標專案參數名稱。", title="精靈設定錯誤")
            return
        if not self.system_box.Text:
            forms.alert("『系統別』為必填欄位。", title="精靈設定錯誤")
            return
        if not self.column_box.Text:
            forms.alert("『柱位』為必填欄位。", title="精靈設定錯誤")
            return
        if not self.direction_box.Text:
            forms.alert("『方位』為必填欄位。", title="精靈設定錯誤")
            return

        try:
            padding_value = int(self.padding_box.Text)
            index_value = int(self.index_box.Text)
            step_value = int(self.step_box.Text or 1)
        except ValueError:
            forms.alert("流水號相關欄位必須為整數。", title="精靈設定錯誤")
            return

        self.response = {
            "target_param": self.target_param_box.Text,
            "system": self.system_box.Text,
            "flow": self.flow_box.Text,
            "building": self.building_box.Text,
            "floor": self.floor_box.Text,
            "column": self.column_box.Text,
            "ceiling": self.ceiling_box.Text,
            "direction": self.direction_box.Text,
            "index": index_value,
            "padding": padding_value,
            "step": step_value
        }
        self.Close()


def main():
    config = script.get_config("MCP_Wizard")
    
    defaults = {
        "target_param": config.get_option("target_param", "MCP_Marking"),
        "system": config.get_option("system", ""),
        "flow": config.get_option("flow", ""),
        "building": config.get_option("building", "F2"),
        "floor": config.get_option("floor", "L05"),
        "column": config.get_option("column", ""),
        "ceiling": config.get_option("ceiling", ""),
        "direction": config.get_option("direction", ""),
        "index": config.get_option("index", 1),
        "padding": config.get_option("padding", 2),
        "step": config.get_option("step", 1)
    }

    xaml_file = os.path.join(os.path.dirname(__file__), "ui.xaml")
    window = MCPWizardSettingsWindow(xaml_file, **defaults)
    window.show_dialog()

    if window.response:
        try:
            for key, value in window.response.items():
                config.set_option(key, value)
            script.save_config()
            
            if window.start_picking:
                forms.toast("設定已儲存。請點選『精靈標記』按鈕開始動作。", title="MCP 標註精靈")
            else:
                forms.toast("設定已儲存。", title="MCP 精靈設定")
                
        except Exception as ex:
            forms.alert("無法儲存設定: {}".format(ex), title="Wizard Settings")


if __name__ == "__main__":
    main()
