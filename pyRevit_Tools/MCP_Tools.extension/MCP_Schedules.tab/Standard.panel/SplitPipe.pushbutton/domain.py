# -*- coding: utf-8 -*-
"""
數學模型領域核心 (Domain Math)
負責計算將指定長度的管線，依照標準出廠原材長度 (如 5000 mm)
以及一對背對背法蘭的總厚度 (Gap) 進行陣列座標計算。
"""

class PipeSplitMathDomain:

    def __init__(self, raw_pipe_length=5000.0, flange_pair_thickness=156.0):
        """
        :param raw_pipe_length: 完整出廠直管長度，例如 5000 mm。
        :param flange_pair_thickness: 兩片背對背法蘭產生的總間隙寬度 (Gap)，例如 78*2 = 156 mm。
        """
        self.raw_pipe_length = raw_pipe_length
        self.gap = flange_pair_thickness

    def calculate_split_spans(self, total_span):
        """
        給定原管線的總物理長度(total_span)，
        回傳所有切分模組的座標清單。
        """
        segments = []
        current_head = 0.0
        idx = 0
        
        while current_head < total_span - 0.1:
            remaining = total_span - current_head
            
            p_start = current_head
            
            # 如果剩下的長度比一根滿管還要長
            if remaining > self.raw_pipe_length:
                p_end = p_start + self.raw_pipe_length
                has_end_flange = True
                next_head = p_end + self.gap
            else:
                # 這是最後一根管子，直接補滿到終點
                p_end = total_span
                has_end_flange = False
                next_head = total_span
                
            segments.append({
                "segment_index": idx,
                "pipe_start": p_start,
                "pipe_end": p_end,
                "pipe_length": p_end - p_start,
                "has_end_flange": has_end_flange,   # 代表這根管子的尾端是否需要上法蘭
                "has_start_flange": (idx > 0)       # 代表這根管子的起點是否需要上法蘭 (第一根永遠不用)
            })
            
            current_head = next_head
            idx += 1
            
        return segments
