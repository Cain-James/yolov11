import torch
import torch.nn as nn
import torch.nn.functional as F

class YOLOLoss(nn.Module):
    def __init__(self, num_classes=12, anchors=None):
        super(YOLOLoss, self).__init__()
        self.num_classes = num_classes
        self.anchors = anchors if anchors is not None else [
            [10, 13], [16, 30], [33, 23],
            [30, 61], [62, 45], [59, 119],
            [116, 90], [156, 198], [373, 326]
        ]
        self.anchors = torch.tensor(self.anchors).float()
        self.num_anchors = len(self.anchors)
        
        # 损失权重
        self.lambda_coord = 5.0  # 坐标损失权重
        self.lambda_noobj = 0.5  # 无目标损失权重
        
        # 使用BCEWithLogitsLoss，添加pos_weight参数
        self.bce = nn.BCEWithLogitsLoss(reduction='sum', pos_weight=torch.tensor([2.0]))  # 正样本权重更大

    def forward(self, predictions, targets):
        """
        计算YOLO损失
        :param predictions: (batch_size, num_anchors, grid_h, grid_w, num_classes + 5)
        :param targets: (batch_size, max_objects, 5) [class, x, y, w, h]
        """
        device = predictions.device
        batch_size = predictions.size(0)
        
        # 提取预测值
        pred_xy = predictions[..., :2].sigmoid()  # 中心点坐标
        pred_wh = predictions[..., 2:4].exp()     # 宽高
        pred_conf = predictions[..., 4]           # 置信度（不应用sigmoid）
        pred_cls = predictions[..., 5:]           # 类别预测（不应用sigmoid）

        # 初始化损失列表
        xy_losses = []
        wh_losses = []
        conf_losses = []
        cls_losses = []

        # 对每个batch处理
        for b in range(batch_size):
            # 获取有效目标
            valid_targets = targets[b]
            if valid_targets.sum() == 0:  # 如果所有值都是0，跳过这个样本
                continue

            # 确保valid_targets的维度正确
            if len(valid_targets.shape) == 1:
                valid_targets = valid_targets.unsqueeze(0)

            # 验证标签值范围
            if valid_targets.size(0) > 0:
                # 确保类别ID在有效范围内
                valid_targets[:, 0] = torch.clamp(valid_targets[:, 0], 0, self.num_classes - 1)
                # 确保坐标值在[0,1]范围内
                valid_targets[:, 1:5] = torch.clamp(valid_targets[:, 1:5], 0, 1)

            # 展平预测值
            pred_xy_flat = pred_xy[b].reshape(-1, 2)  # (N, 2)
            pred_wh_flat = pred_wh[b].reshape(-1, 2)  # (N, 2)
            pred_conf_flat = pred_conf[b].reshape(-1)  # (N,)
            pred_cls_flat = pred_cls[b].reshape(-1, self.num_classes)  # (N, num_classes)

            # 计算IoU
            ious = self.compute_iou(pred_xy_flat, pred_wh_flat, valid_targets[:, 1:])  # (num_targets, N)
            best_ious, best_idx = ious.max(0)  # 对每个预测框找最匹配的目标

            # 正样本掩码
            obj_mask = (best_ious > 0.5)  # (N,)

            # 坐标损失
            if obj_mask.any():
                # 获取正样本的预测值
                pred_xy_selected = pred_xy_flat[obj_mask]
                pred_wh_selected = pred_wh_flat[obj_mask]
                
                # 获取正样本的目标值
                matched_targets = valid_targets[best_idx[obj_mask]]
                target_xy = matched_targets[:, 1:3].float()
                target_wh = matched_targets[:, 3:5].float()

                # 计算坐标损失
                xy_loss = F.mse_loss(
                    pred_xy_selected,
                    target_xy,
                    reduction='sum'
                ) * self.lambda_coord
                xy_losses.append(xy_loss)

                wh_loss = F.mse_loss(
                    pred_wh_selected,
                    target_wh,
                    reduction='sum'
                ) * self.lambda_coord
                wh_losses.append(wh_loss)

            # 置信度损失（使用BCEWithLogitsLoss）
            # 添加数值稳定性检查
            pred_conf_flat = torch.clamp(pred_conf_flat, -100, 100)
            conf_loss = self.bce(
                pred_conf_flat,
                obj_mask.float()
            )
            conf_losses.append(conf_loss)

            # 类别损失（使用BCEWithLogitsLoss）
            if obj_mask.any():
                pred_cls_selected = pred_cls_flat[obj_mask]
                # 添加数值稳定性检查
                pred_cls_selected = torch.clamp(pred_cls_selected, -100, 100)
                target_cls = F.one_hot(matched_targets[:, 0].long(), self.num_classes).float()
                
                cls_loss = self.bce(
                    pred_cls_selected,
                    target_cls
                )
                cls_losses.append(cls_loss)

        # 计算总损失
        loss = {
            'xy': torch.stack(xy_losses).sum() if xy_losses else torch.zeros(1, device=device, requires_grad=True),
            'wh': torch.stack(wh_losses).sum() if wh_losses else torch.zeros(1, device=device, requires_grad=True),
            'conf': torch.stack(conf_losses).sum() if conf_losses else torch.zeros(1, device=device, requires_grad=True),
            'cls': torch.stack(cls_losses).sum() if cls_losses else torch.zeros(1, device=device, requires_grad=True)
        }

        # 计算总损失
        total_loss = sum(loss.values()) / batch_size
        
        # 检查损失值是否为NaN
        if torch.isnan(total_loss):
            print("警告: 总损失为NaN，使用零损失")
            total_loss = torch.zeros(1, device=device, requires_grad=True)
            loss = {k: torch.zeros(1, device=device, requires_grad=True) for k in loss.keys()}
        
        return total_loss, loss

    def compute_iou(self, pred_xy, pred_wh, targets):
        """
        计算预测框和目标框的IoU
        :param pred_xy: (num_anchors, grid_h, grid_w, 2) 预测的中心点坐标
        :param pred_wh: (num_anchors, grid_h, grid_w, 2) 预测的宽高
        :param targets: (num_targets, 4) 目标框的中心点坐标和宽高
        """
        # 确保输入张量在正确的设备上
        device = pred_xy.device
        targets = targets.to(device)

        # 展平预测框
        pred_xy = pred_xy.reshape(-1, 2)  # (N, 2)
        pred_wh = pred_wh.reshape(-1, 2)  # (N, 2)

        # 预测框
        pred_x1y1 = pred_xy - pred_wh / 2
        pred_x2y2 = pred_xy + pred_wh / 2

        # 目标框
        target_xy = targets[:, :2]
        target_wh = targets[:, 2:]
        target_x1y1 = target_xy - target_wh / 2
        target_x2y2 = target_xy + target_wh / 2

        # 计算交集
        inter_x1y1 = torch.max(pred_x1y1.unsqueeze(0), target_x1y1.unsqueeze(1))
        inter_x2y2 = torch.min(pred_x2y2.unsqueeze(0), target_x2y2.unsqueeze(1))
        inter_wh = torch.clamp(inter_x2y2 - inter_x1y1, min=0)
        inter_area = inter_wh[..., 0] * inter_wh[..., 1]

        # 计算并集
        pred_area = pred_wh[..., 0] * pred_wh[..., 1]
        target_area = target_wh[..., 0] * target_wh[..., 1]
        union_area = pred_area.unsqueeze(0) + target_area.unsqueeze(1) - inter_area

        # 计算IoU
        iou = inter_area / (union_area + 1e-16)

        # 重新整形为原始形状
        iou = iou.reshape(targets.size(0), *pred_xy.shape[:-1])

        return iou 