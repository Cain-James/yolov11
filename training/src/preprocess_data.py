import os
import glob
import shutil
import cv2
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime

def setup_logger():
    """设置日志记录器"""
    # 创建logs目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名，包含时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"preprocess_{timestamp}.log")
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()

def normalize_label_file(img_path, label_path, logger):
    """归一化标签文件中的坐标值，超出图片边界的部分将被裁剪到边界"""
    # 读取图片尺寸
    img = cv2.imread(img_path)
    if img is None:
        logger.error(f"无法读取图片: {img_path}")
        return False
    
    height, width = img.shape[:2]
    
    try:
        # 读取标签
        with open(label_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        normalized_lines = []
        has_valid_boxes = False
        for line in lines:
            values = line.strip().split()
            if len(values) == 5:
                try:
                    class_id = int(float(values[0]))
                    x_center = float(values[1])
                    y_center = float(values[2])
                    w = float(values[3])
                    h = float(values[4])
                    
                    # 如果是绝对坐标，转换为相对坐标
                    if x_center > 1 or y_center > 1 or w > 1 or h > 1:
                        # 转换为绝对坐标进行边界处理
                        x_min = (x_center - w/2) * width if w <= 1 else x_center - w/2
                        y_min = (y_center - h/2) * height if h <= 1 else y_center - h/2
                        x_max = (x_center + w/2) * width if w <= 1 else x_center + w/2
                        y_max = (y_center + h/2) * height if h <= 1 else y_center + h/2
                        
                        # 裁剪到图片边界
                        x_min = max(0, min(width, x_min))
                        y_min = max(0, min(height, y_min))
                        x_max = max(0, min(width, x_max))
                        y_max = max(0, min(height, y_max))
                        
                        # 检查边界框是否仍然有效
                        if x_max > x_min and y_max > y_min:
                            # 转换回中心点坐标
                            x_center = (x_min + x_max) / 2 / width
                            y_center = (y_min + y_max) / 2 / height
                            w = (x_max - x_min) / width
                            h = (y_max - y_min) / height
                            
                            # 确保类别ID在正确范围内 (0-11)
                            class_id = np.clip(class_id, 0, 11)
                            
                            normalized_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
                            has_valid_boxes = True
                        else:
                            logger.warning(f"标签框 {line.strip()} 在裁剪后无效，已忽略 (文件: {label_path})")
                    else:
                        # 已经是归一化坐标的情况
                        x_min = (x_center - w/2)
                        y_min = (y_center - h/2)
                        x_max = (x_center + w/2)
                        y_max = (y_center + h/2)
                        
                        # 裁剪到[0,1]范围
                        x_min = max(0, min(1, x_min))
                        y_min = max(0, min(1, y_min))
                        x_max = max(0, min(1, x_max))
                        y_max = max(0, min(1, y_max))
                        
                        # 检查边界框是否仍然有效
                        if x_max > x_min and y_max > y_min:
                            x_center = (x_min + x_max) / 2
                            y_center = (y_min + y_max) / 2
                            w = x_max - x_min
                            h = y_max - y_min
                            
                            # 确保类别ID在正确范围内 (0-11)
                            class_id = np.clip(class_id, 0, 11)
                            
                            normalized_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
                            has_valid_boxes = True
                        else:
                            logger.warning(f"标签框 {line.strip()} 在裁剪后无效，已忽略 (文件: {label_path})")
                            
                except ValueError as e:
                    logger.error(f"处理标签行时出错 {line.strip()} in {label_path}: {e}")
                    continue
        
        if not has_valid_boxes:
            logger.error(f"文件 {label_path} 中没有有效的标签框")
            return False
            
        # 创建临时文件来保存标签
        temp_label_path = label_path + '.tmp'
        try:
            with open(temp_label_path, 'w', encoding='utf-8') as f:
                f.writelines(normalized_lines)
            # 如果写入成功，替换原文件
            os.replace(temp_label_path, label_path)
            return True
        except Exception as e:
            logger.error(f"保存标签文件时出错 {label_path}: {e}")
            if os.path.exists(temp_label_path):
                os.remove(temp_label_path)
            return False
            
    except Exception as e:
        logger.error(f"处理文件时出错 {label_path}: {e}")
        return False

def standardize_filename(filename):
    """标准化文件名（移除空格和特殊字符）"""
    # 保留扩展名
    name, ext = os.path.splitext(filename)
    # 替换空格和特殊字符
    name = name.replace(' ', '_').replace('.', '_')
    # 只保留字母、数字和下划线
    name = ''.join(c for c in name if c.isalnum() or c == '_')
    return f"{name}{ext}"

def process_dataset(img_dir, label_dir):
    """处理整个数据集"""
    logger = setup_logger()
    logger.info("开始处理数据集...")
    logger.info(f"图片目录: {img_dir}")
    logger.info(f"标签目录: {label_dir}")
    
    # 确保目录存在
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)
    
    # 获取所有图片文件
    img_files = glob.glob(os.path.join(img_dir, "*.[jp][pn][g]"))
    logger.info(f"找到 {len(img_files)} 个图片文件")
    
    # 创建图片-标签对的映射
    img_label_pairs = []
    unmatched_images = []
    for img_path in img_files:
        img_name = os.path.basename(img_path)
        img_base = os.path.splitext(img_name)[0]
        
        # 查找对应的标签文件
        label_path = None
        possible_label_names = [
            f"{img_base}.txt",
            f"{img_base.replace(' ', '_')}.txt",
            f"{img_base.replace('.', '_')}.txt"
        ]
        
        for label_name in possible_label_names:
            temp_path = os.path.join(label_dir, label_name)
            if os.path.exists(temp_path):
                label_path = temp_path
                break
        
        if label_path:
            img_label_pairs.append((img_path, label_path))
        else:
            unmatched_images.append(img_path)
            logger.warning(f"找不到图片对应的标签文件: {img_name}")
    
    logger.info(f"成功匹配 {len(img_label_pairs)} 对图片和标签")
    if unmatched_images:
        logger.warning(f"有 {len(unmatched_images)} 个图片没有找到对应的标签文件")
    
    # 处理每对图片和标签
    success_count = 0
    failed_pairs = []
    for img_path, label_path in tqdm(img_label_pairs, desc="处理文件"):
        try:
            # 生成新的标准化文件名
            new_img_name = standardize_filename(os.path.basename(img_path))
            new_label_name = os.path.splitext(new_img_name)[0] + '.txt'
            
            new_img_path = os.path.join(img_dir, new_img_name)
            new_label_path = os.path.join(label_dir, new_label_name)
            
            # 首先处理标签文件
            if normalize_label_file(img_path, label_path, logger):
                # 如果标签处理成功，同步重命名图片和标签
                try:
                    if img_path != new_img_path:
                        shutil.move(img_path, new_img_path)
                    if label_path != new_label_path:
                        shutil.move(label_path, new_label_path)
                    success_count += 1
                    logger.info(f"成功处理: {os.path.basename(img_path)}")
                except Exception as e:
                    logger.error(f"重命名文件时出错 {img_path} -> {new_img_path}: {e}")
                    failed_pairs.append((img_path, label_path))
            else:
                logger.error(f"标签处理失败: {os.path.basename(label_path)}")
                failed_pairs.append((img_path, label_path))
                
        except Exception as e:
            logger.error(f"处理文件对时出错 {img_path} - {label_path}: {e}")
            failed_pairs.append((img_path, label_path))
    
    # 处理未匹配的图片（仅重命名）
    unmatched_success = 0
    unmatched_failed = []
    if unmatched_images:
        logger.info("开始处理未匹配的图片...")
        for img_path in tqdm(unmatched_images, desc="处理未匹配图片"):
            try:
                # 生成新的标准化文件名
                new_img_name = standardize_filename(os.path.basename(img_path))
                new_img_path = os.path.join(img_dir, new_img_name)
                
                # 重命名图片
                if img_path != new_img_path:
                    shutil.move(img_path, new_img_path)
                    unmatched_success += 1
                    logger.info(f"成功重命名未匹配图片: {os.path.basename(img_path)} -> {new_img_name}")
                else:
                    unmatched_success += 1
                    logger.info(f"未匹配图片已经是标准化名称: {new_img_name}")
            except Exception as e:
                logger.error(f"重命名未匹配图片时出错 {img_path}: {e}")
                unmatched_failed.append(img_path)
    
    # 输出处理总结
    logger.info("\n处理总结:")
    logger.info(f"总共找到的图片: {len(img_files)}")
    logger.info(f"成功匹配的图片-标签对: {len(img_label_pairs)}")
    logger.info(f"成功处理的图片-标签对: {success_count}")
    logger.info(f"处理失败的图片-标签对: {len(failed_pairs)}")
    logger.info(f"未匹配图片总数: {len(unmatched_images)}")
    logger.info(f"成功重命名的未匹配图片: {unmatched_success}")
    logger.info(f"重命名失败的未匹配图片: {len(unmatched_failed)}")
    
    if failed_pairs:
        logger.info("\n处理失败的文件列表:")
        for img_path, label_path in failed_pairs:
            logger.info(f"图片: {os.path.basename(img_path)}, 标签: {os.path.basename(label_path)}")
    
    if unmatched_failed:
        logger.info("\n重命名失败的未匹配图片列表:")
        for img_path in unmatched_failed:
            logger.info(f"图片: {os.path.basename(img_path)}")
    
    if unmatched_images:
        logger.info("\n未找到标签的图片列表（重命名后）:")
        for img_path in unmatched_images:
            new_name = standardize_filename(os.path.basename(img_path))
            logger.info(f"图片: {new_name}")

if __name__ == "__main__":
    # 设置数据目录
    img_dir = "training/data/imgs"
    label_dir = "training/data/labels"
    
    # 处理数据集
    process_dataset(img_dir, label_dir)
    print("数据预处理完成！") 