import json
import os
import numpy as np
import logging
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)

class RulesChecker:
    """施工规范检查器，负责检查施工图纸是否符合规范要求"""
    
    def __init__(self):
        """初始化规则检查器"""
        self.rules = self._initialize_rules()
        
    def _initialize_rules(self):
        """初始化规则列表"""
        return [
            # 基础设施规则
            {
                "id": "1.5.4-1",
                "category": "加工场",
                "description": "4、钢筋加工场",
                "severity": "重要",
                "check_method": self._check_steel_processing_exists
            },
            {
                "id": "1.5.4-2",
                "category": "加工场",
                "description": "钢筋加工场应临近施工道路",
                "severity": "重要",
                "check_method": self._check_steel_processing_near_road
            },
            # 塔吊相关规则
            {
                "id": "1.5.1-1",
                "category": "塔吊",
                "description": "3）塔吊应覆盖钢筋加工场、装配式堆场",
                "severity": "重要",
                "check_method": self._check_tower_crane_covers_steel_processing
            },
            {
                "id": "1.5.1-2",
                "category": "塔吊",
                "description": "2）塔吊应至少覆盖95%面积的地下车库，完全覆盖主楼",
                "severity": "严重",
                "check_method": self._check_tower_crane_covers_main_building
            },
            # 道路和通行规则
            {
                "id": "1.5.8-1",
                "category": "大门",
                "description": "2）大门应直通主施工道路",
                "severity": "重要",
                "check_method": self._check_gate_connects_to_road
            },
            {
                "id": "1.5.8-2",
                "category": "大门",
                "description": "1）应至少设置一个大门",
                "severity": "重要",
                "check_method": self._check_gate_exists
            },
            {
                "id": "1.5.7-1",
                "category": "施工道路",
                "description": "2）施工道路应连接上下人通道与大门",
                "severity": "重要",
                "check_method": self._check_road_connects_gate
            },
            # 安全和消防规则
            {
                "id": "1.10.8-6",
                "category": "消防设施",
                "description": "3）施工现场内应设置临时消防车道",
                "severity": "严重",
                "check_method": self._check_fire_truck_road_exists
            },
            {
                "id": "1.10.8-7",
                "category": "消防设施",
                "description": "仅设置一个大门的，洗车设备安排在大门内（含三级沉淀池）。设置多个大门或临时通道的，尽量在每个出土通道设置洗车设备和三级沉淀池等。",
                "severity": "重要",
                "check_method": self._check_car_wash_exists
            },
            {
                "id": "1.10.1-1",
                "category": "场地布局",
                "description": "1、用地红线。应标明用地红线范围。",
                "severity": "严重",
                "check_method": self._check_within_red_line
            },
            # 材料堆场规则
            {
                "id": "1.7.3-1",
                "category": "材料堆场",
                "description": "2）材料堆场设置应临近施工道路",
                "severity": "一般",
                "check_method": self._check_material_storage_near_road
            },
            {
                "id": "1.7.3-2",
                "category": "材料堆场",
                "description": "3）危废堆放区、危险化学品堆放区、可（易）燃材料堆放区、原材料堆放区、半成品堆放区等应单独设置。",
                "severity": "严重",
                "check_method": self._check_hazardous_material_storage_isolation
            }
        ]

    
    def _check_tower_crane_covers_steel_processing(self, detections):
        """检查塔吊是否覆盖钢筋加工厂"""
        tower_cranes = [d for d in detections if d['class'] == '塔吊']
        steel_processing = [d for d in detections if d['class'] == '钢筋加工厂']
        
        if not tower_cranes or not steel_processing:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未同时识别到塔吊和钢筋加工厂"
            }
        
        for tc in tower_cranes:
            tc_x = (tc['bbox'][0] + tc['bbox'][2]) / 2
            tc_y = (tc['bbox'][1] + tc['bbox'][3]) / 2
            
            # 简化模型：假设塔吊覆盖半径为图像宽度的30%
            tc_radius = (tc['bbox'][2] - tc['bbox'][0]) * 5
            
            for sp in steel_processing:
                sp_x = (sp['bbox'][0] + sp['bbox'][2]) / 2
                sp_y = (sp['bbox'][1] + sp['bbox'][3]) / 2
                
                distance = np.sqrt((tc_x - sp_x) ** 2 + (tc_y - sp_y) ** 2)
                if distance <= tc_radius:
                    return {
                        "status": "合规",
                        "message": "塔吊覆盖了钢筋加工厂"
                    }
        
        return {
            "status": "不合规",
            "message": "塔吊未覆盖钢筋加工厂"
        }
    
    def _check_tower_crane_distance(self, detections):
        """检查多塔吊之间的距离"""
        tower_cranes = [d for d in detections if d['class'] == '塔吊']
        
        if len(tower_cranes) < 2:
            return {
                "status": "无法检测",
                "message": "无法检测，图中塔吊数量少于2台"
            }
        
        # 计算塔吊之间的距离
        for i in range(len(tower_cranes)):
            for j in range(i+1, len(tower_cranes)):
                tc1_x = (tower_cranes[i]['bbox'][0] + tower_cranes[i]['bbox'][2]) / 2
                tc1_y = (tower_cranes[i]['bbox'][1] + tower_cranes[i]['bbox'][3]) / 2
                
                tc2_x = (tower_cranes[j]['bbox'][0] + tower_cranes[j]['bbox'][2]) / 2
                tc2_y = (tower_cranes[j]['bbox'][1] + tower_cranes[j]['bbox'][3]) / 2
                
                distance = np.sqrt((tc1_x - tc2_x) ** 2 + (tc1_y - tc2_y) ** 2)
                
                # 这里需要将像素距离转换为实际距离，简化处理：假设图像宽度100px对应10m
                pixel_to_meter_ratio = 0.1  # 每像素代表的米数
                real_distance = distance * pixel_to_meter_ratio
                
                if real_distance < 2:
                    return {
                        "status": "不合规",
                        "message": f"塔吊间距为{real_distance:.2f}m，小于规定的2m最小距离"
                    }
        
        return {
            "status": "合规",
            "message": "多塔吊之间的距离符合规范要求"
        }
    
    def _check_office_outside_tower_crane_radius(self, detections):
        """检查办公室是否在塔吊作业半径之外"""
        tower_cranes = [d for d in detections if d['class'] == '塔吊']
        offices = [d for d in detections if d['class'] == '办公室']
        
        if not tower_cranes or not offices:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未同时识别到塔吊和办公室"
            }
        
        for tc in tower_cranes:
            tc_x = (tc['bbox'][0] + tc['bbox'][2]) / 2
            tc_y = (tc['bbox'][1] + tc['bbox'][3]) / 2
            
            # 简化模型：假设塔吊作业半径为图像宽度的30%
            tc_radius = (tc['bbox'][2] - tc['bbox'][0]) * 5
            
            for office in offices:
                office_x = (office['bbox'][0] + office['bbox'][2]) / 2
                office_y = (office['bbox'][1] + office['bbox'][3]) / 2
                
                distance = np.sqrt((tc_x - office_x) ** 2 + (tc_y - office_y) ** 2)
                if distance <= tc_radius:
                    return {
                        "status": "不合规",
                        "message": "办公室位于塔吊作业半径内，存在安全隐患"
                    }
        
        return {
            "status": "合规",
            "message": "办公室位于塔吊作业半径外"
        }
    
    def _check_gate_connects_to_road(self, detections):
        """检查大门是否直通主施工道路"""
        gates = [d for d in detections if d['class'] == '大门']
        roads = [d for d in detections if d['class'] == '道路']
        
        if not gates or not roads:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未同时识别到大门和道路"
            }
        
        for gate in gates:
            gate_x = (gate['bbox'][0] + gate['bbox'][2]) / 2
            gate_y = (gate['bbox'][1] + gate['bbox'][3]) / 2
            
            gate_width = gate['bbox'][2] - gate['bbox'][0]
            gate_height = gate['bbox'][3] - gate['bbox'][1]
            
            # 检查门附近是否有道路
            for road in roads:
                # 简化处理：检查大门的中心点是否在道路的扩展包围框内
                road_x1, road_y1, road_x2, road_y2 = road['bbox']
                
                # 扩展道路包围框
                extended_road_x1 = road_x1 - gate_width
                extended_road_y1 = road_y1 - gate_height
                extended_road_x2 = road_x2 + gate_width
                extended_road_y2 = road_y2 + gate_height
                
                if (extended_road_x1 <= gate_x <= extended_road_x2 and 
                    extended_road_y1 <= gate_y <= extended_road_y2):
                    return {
                        "status": "合规",
                        "message": "大门直通主施工道路"
                    }
        
        return {
            "status": "不合规",
            "message": "大门未直通主施工道路"
        }
    
    def _check_gate_exists(self, detections):
        """检查是否至少设置一个大门"""
        gates = [d for d in detections if d['class'] == '大门']
        
        if not gates:
            return {
                "status": "不合规",
                "message": "未设置大门"
            }
        
        return {
            "status": "合规",
            "message": f"设置了{len(gates)}个大门"
        }
    
    def _check_main_road_width(self, detections):
        """检查主干道路宽度是否不小于6m"""
        roads = [d for d in detections if d['class'] == '道路']
        
        if not roads:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未识别到道路"
            }
        
        # 简化处理：假设所有道路都是主干道，计算道路宽度
        for road in roads:
            road_width = min(road['bbox'][2] - road['bbox'][0], road['bbox'][3] - road['bbox'][1])
            
            # 假设100像素宽度对应10米
            pixel_to_meter_ratio = 0.1
            road_width_meters = road_width * pixel_to_meter_ratio
            
            if road_width_meters < 6:
                return {
                    "status": "不合规",
                    "message": f"主干道路宽度为{road_width_meters:.2f}m，小于规定的6m"
                }
        
        return {
            "status": "合规",
            "message": "主干道路宽度符合规范要求"
        }
    
    def _check_secondary_road_width(self, detections):
        """检查次干道路宽度是否不低于3m"""
        # 由于无法区分主次干道，此处简化处理
        return {
            "status": "无法检测",
            "message": "无法区分主次干道，请人工检查"
        }
    
    def _check_within_red_line(self, detections):
        """检查建筑物和设施是否在红线范围内"""
        red_lines = [d for d in detections if d['class'] == '红线']
        
        if not red_lines:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未识别到红线"
            }
        
        # 简化处理：假设红线是一个封闭的多边形
        # 实际应用中需要更复杂的处理来构建红线多边形
        red_line = red_lines[0]
        red_line_polygon = Polygon([
            (red_line['bbox'][0], red_line['bbox'][1]),
            (red_line['bbox'][2], red_line['bbox'][1]),
            (red_line['bbox'][2], red_line['bbox'][3]),
            (red_line['bbox'][0], red_line['bbox'][3])
        ])
        
        # 检查所有建筑物和设施是否在红线内
        for detection in detections:
            if detection['class'] == '红线':
                continue
                
            # 检查每个建筑物/设施的中心点
            center_x = (detection['bbox'][0] + detection['bbox'][2]) / 2
            center_y = (detection['bbox'][1] + detection['bbox'][3]) / 2
            
            point = Point(center_x, center_y)
            
            if not red_line_polygon.contains(point):
                return {
                    "status": "不合规",
                    "message": f"{detection['class']}位于红线范围外"
                }
        
        return {
            "status": "合规",
            "message": "所有建筑物和设施均在红线范围内"
        }
    
    def _check_dormitory_safety_distance(self, detections):
        """检查宿舍安全距离"""
        # 简化处理：当前无法检测易燃易爆危险品仓库
        return {
            "status": "无法检测",
            "message": "无法检测，需要人工查看是否有易燃易爆危险品仓库靠近宿舍"
        }
    
    def _check_fire_truck_road_exists(self, detections):
        """检查是否设置临时消防车道"""
        roads = [d for d in detections if d['class'] == '道路']
        
        if not roads:
            return {
                "status": "不合规",
                "message": "未设置临时消防车道"
            }
        
        # 简化处理：假设检测到的道路中至少有一条可以作为消防车道
        # 实际应用中可能需要特殊标注消防车道
        return {
            "status": "合规",
            "message": "已设置临时消防车道"
        }
    
    def _check_fire_truck_road_width(self, detections):
        """检查临时消防车道的净宽度是否不小于4m"""
        roads = [d for d in detections if d['class'] == '道路']
        
        if not roads:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未识别到道路"
            }
        
        # 简化处理：估计道路宽度
        pixel_to_meter_ratio = 0.1  # 每像素代表的米数，实际应用中需要根据图像比例尺确定
        
        for road in roads:
            road_width = road['bbox'][2] - road['bbox'][0]
            estimated_width = road_width * pixel_to_meter_ratio
            
            if estimated_width >= 4:
                return {
                    "status": "合规",
                    "message": f"临时消防车道宽度约为{estimated_width:.1f}m，符合不小于4m的要求"
                }
        
        return {
            "status": "不合规",
            "message": "所有道路宽度均小于4m，不符合临时消防车道要求"
        }
    
    def _check_road_connects_gate(self, detections):
        """检查施工道路是否连接上下人通道与大门"""
        roads = [d for d in detections if d['class'] == '道路']
        gates = [d for d in detections if d['class'] == '大门']
        stairs = [d for d in detections if d['class'] == '楼梯']  # 假设楼梯可以作为上下人通道
        
        if not roads or not gates:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未同时识别到道路和大门"
            }
        
        if not stairs:
            return {
                "status": "无法检测",
                "message": "无法检测，图中未识别到上下人通道(楼梯)"
            }
        
        # 简化处理：检查是否存在一条道路同时连接大门和楼梯
        for road in roads:
            road_bbox = road['bbox']
            road_polygon = Polygon([
                (road_bbox[0], road_bbox[1]),
                (road_bbox[2], road_bbox[1]),
                (road_bbox[2], road_bbox[3]),
                (road_bbox[0], road_bbox[3])
            ])
            
            connects_gate = False
            connects_stairs = False
            
            # 检查是否连接大门
            for gate in gates:
                gate_center = Point((gate['bbox'][0] + gate['bbox'][2]) / 2, 
                                   (gate['bbox'][1] + gate['bbox'][3]) / 2)
                if road_polygon.distance(gate_center) < 50:  # 像素距离阈值
                    connects_gate = True
                    break
            
            # 检查是否连接楼梯
            for stair in stairs:
                stair_center = Point((stair['bbox'][0] + stair['bbox'][2]) / 2, 
                                    (stair['bbox'][1] + stair['bbox'][3]) / 2)
                if road_polygon.distance(stair_center) < 50:  # 像素距离阈值
                    connects_stairs = True
                    break
            
            if connects_gate and connects_stairs:
                return {
                    "status": "合规",
                    "message": "施工道路连接了上下人通道与大门"
                }
        
        return {
            "status": "不合规",
            "message": "施工道路未同时连接上下人通道与大门"
        }
    
    def _check_fence_height(self, detections):
        """检查施工场界围挡高度是否不低于2.0m"""
        # 注意：实际应用中可能需要专门检测围挡
        # 这里简化处理，可能需要特殊标注或其他方式来获取围挡信息
        
        # 由于围挡可能不容易通过目标检测直接识别，暂返回无法检测
        return {
            "status": "无法检测",
            "message": "无法自动检测围挡高度，需要人工检查"
        }
    
    def _check_steel_processing_exists(self, detections):
        """检查是否设置钢筋加工场"""
        steel_processing = [d for d in detections if d['class'] == '钢筋加工厂']
        
        if not steel_processing:
            return {
                "status": "不合规",
                "message": "未设置钢筋加工场"
            }
        
        return {
            "status": "合规",
            "message": f"已设置{len(steel_processing)}个钢筋加工场"
        }
        
    def _check_steel_processing_near_road(self, detections):
        """检查钢筋加工场是否临近施工道路"""
        steel_processing = [d for d in detections if d['class'] == '钢筋加工厂']
        roads = [d for d in detections if d['class'] == '施工道路']
        
        if not steel_processing:
            return {
                "status": "不合规",
                "message": "未设置钢筋加工场"
            }
            
        if not roads:
            return {
                "status": "不合规",
                "message": "未检测到施工道路"
            }
            
        for sp in steel_processing:
            sp_center = Point((sp['bbox'][0] + sp['bbox'][2]) / 2, 
                            (sp['bbox'][1] + sp['bbox'][3]) / 2)
            
            for road in roads:
                road_polygon = Polygon([
                    (road['bbox'][0], road['bbox'][1]),
                    (road['bbox'][2], road['bbox'][1]),
                    (road['bbox'][2], road['bbox'][3]),
                    (road['bbox'][0], road['bbox'][3])
                ])
                
                if road_polygon.distance(sp_center) < 50:  # 50像素阈值
                    return {
                        "status": "合规",
                        "message": "钢筋加工场临近施工道路"
                    }
        
        return {
            "status": "不合规",
            "message": "钢筋加工场未临近施工道路"
        }
        
    def _check_tower_crane_covers_main_building(self, detections):
        """检查塔吊是否完全覆盖主楼"""
        tower_cranes = [d for d in detections if d['class'] == '塔吊']
        buildings = [d for d in detections if d['class'] == '主楼']
        
        if not tower_cranes:
            return {
                "status": "不合规",
                "message": "未检测到塔吊"
            }
            
        if not buildings:
            return {
                "status": "不合规",
                "message": "未检测到主楼"
            }
            
        for building in buildings:
            building_polygon = Polygon([
                (building['bbox'][0], building['bbox'][1]),
                (building['bbox'][2], building['bbox'][1]),
                (building['bbox'][2], building['bbox'][3]),
                (building['bbox'][0], building['bbox'][3])
            ])
            
            covered = False
            for crane in tower_cranes:
                crane_center = Point((crane['bbox'][0] + crane['bbox'][2]) / 2, 
                                   (crane['bbox'][1] + crane['bbox'][3]) / 2)
                crane_radius = max(crane['bbox'][2] - crane['bbox'][0], 
                                 crane['bbox'][3] - crane['bbox'][1]) / 2
                
                # 检查主楼的四个角点是否都在塔吊覆盖范围内
                corners = [
                    Point(building['bbox'][0], building['bbox'][1]),
                    Point(building['bbox'][2], building['bbox'][1]),
                    Point(building['bbox'][2], building['bbox'][3]),
                    Point(building['bbox'][0], building['bbox'][3])
                ]
                
                if all(crane_center.distance(corner) <= crane_radius for corner in corners):
                    covered = True
                    break
            
            if not covered:
                return {
                    "status": "不合规",
                    "message": "塔吊未完全覆盖主楼"
                }
        
        return {
            "status": "合规",
            "message": "塔吊完全覆盖主楼"
        }
        
    def _check_car_wash_exists(self, detections):
        """检查是否设置洗车池和三级沉淀池"""
        car_wash = [d for d in detections if d['class'] == '洗车池']
        sedimentation = [d for d in detections if d['class'] == '三级沉淀池']
        
        if not car_wash:
            return {
                "status": "不合规",
                "message": "未设置洗车池"
            }
            
        if not sedimentation:
            return {
                "status": "不合规",
                "message": "未设置三级沉淀池"
            }
            
        return {
            "status": "合规",
            "message": f"已设置{len(car_wash)}个洗车池和{len(sedimentation)}个三级沉淀池"
        }
        
    def _check_material_storage_near_road(self, detections):
        """检查材料堆场是否临近施工道路"""
        storages = [d for d in detections if d['class'] == '材料堆场']
        roads = [d for d in detections if d['class'] == '施工道路']
        
        if not storages:
            return {
                "status": "不合规",
                "message": "未检测到材料堆场"
            }
            
        if not roads:
            return {
                "status": "不合规",
                "message": "未检测到施工道路"
            }
            
        for storage in storages:
            storage_center = Point((storage['bbox'][0] + storage['bbox'][2]) / 2, 
                                 (storage['bbox'][1] + storage['bbox'][3]) / 2)
            
            near_road = False
            for road in roads:
                road_polygon = Polygon([
                    (road['bbox'][0], road['bbox'][1]),
                    (road['bbox'][2], road['bbox'][1]),
                    (road['bbox'][2], road['bbox'][3]),
                    (road['bbox'][0], road['bbox'][3])
                ])
                
                if road_polygon.distance(storage_center) < 50:  # 50像素阈值
                    near_road = True
                    break
            
            if not near_road:
                return {
                    "status": "不合规",
                    "message": "存在材料堆场未临近施工道路"
                }
        
        return {
            "status": "合规",
            "message": "所有材料堆场均临近施工道路"
        }
        
    def _check_hazardous_material_storage_isolation(self, detections):
        """检查危险品堆场是否与其他区域分开设置"""
        hazardous = [d for d in detections if d['class'] == '危险品堆场']
        other_areas = [d for d in detections if d['class'] in ['材料堆场', '钢筋加工厂', '办公区', '生活区']]
        
        if not hazardous:
            return {
                "status": "合规",
                "message": "未设置危险品堆场"
            }
            
        for haz in hazardous:
            haz_polygon = Polygon([
                (haz['bbox'][0], haz['bbox'][1]),
                (haz['bbox'][2], haz['bbox'][1]),
                (haz['bbox'][2], haz['bbox'][3]),
                (haz['bbox'][0], haz['bbox'][3])
            ])
            
            for area in other_areas:
                area_polygon = Polygon([
                    (area['bbox'][0], area['bbox'][1]),
                    (area['bbox'][2], area['bbox'][1]),
                    (area['bbox'][2], area['bbox'][3]),
                    (area['bbox'][0], area['bbox'][3])
                ])
                
                if haz_polygon.distance(area_polygon) < 100:  # 100像素安全距离
                    return {
                        "status": "不合规",
                        "message": f"危险品堆场与{area['class']}距离过近"
                    }
        
        return {
            "status": "合规",
            "message": "危险品堆场与其他区域保持安全距离"
        }
    
    def check_rules(self, detections):
        """检查所有规则并返回结果"""
        results = []
        
        for rule in self.rules:
            try:
                check_result = rule["check_method"](detections)
                results.append({
                    "rule_id": rule["id"],
                    "category": rule["category"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "status": check_result["status"],
                    "message": check_result["message"]
                })
            except Exception as e:
                logger.error(f"检查规则 {rule['id']} 时出错: {str(e)}")
                results.append({
                    "rule_id": rule["id"],
                    "category": rule["category"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "status": "检查失败",
                    "message": f"检查过程出错: {str(e)}"
                })
        
        return results

    def save_results_to_json(self, results, output_path):
        """将结果保存为JSON文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存结果到JSON文件时出错: {str(e)}")
            return False 