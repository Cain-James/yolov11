import os
import random
from pathlib import Path
import shutil

def split_dataset(
    source_dir="../data",
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1,
    img_ext=('.jpg', '.jpeg', '.png', '.bmp')
):
    """
    将数据集分割为训练集、验证集和测试集
    :param source_dir: 源数据目录
    :param train_ratio: 训练集比例
    :param val_ratio: 验证集比例
    :param test_ratio: 测试集比例
    :param img_ext: 支持的图片扩展名
    """
    # 验证比例之和是否为1
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-5:
        raise ValueError("数据集比例之和必须为1")

    source_path = Path(source_dir)
    img_dir = source_path / "images"
    label_dir = source_path / "labels"

    if not img_dir.exists() or not label_dir.exists():
        raise ValueError(f"数据集目录结构不正确: {source_dir}")

    # 创建分割后的目录
    splits = ['train', 'val', 'test']
    for split in splits:
        (source_path / split / 'images').mkdir(parents=True, exist_ok=True)
        (source_path / split / 'labels').mkdir(parents=True, exist_ok=True)

    # 获取所有图片文件
    image_files = []
    for ext in img_ext:
        image_files.extend(list(img_dir.glob(f"*{ext}")))

    # 随机打乱文件列表
    random.shuffle(image_files)

    # 计算每个集合的大小
    total = len(image_files)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    # 分割数据集
    train_files = image_files[:train_size]
    val_files = image_files[train_size:train_size + val_size]
    test_files = image_files[train_size + val_size:]

    # 复制文件到对应目录
    def copy_files(files, split_name):
        count = 0
        for img_file in files:
            # 复制图片
            dest_img = source_path / split_name / 'images' / img_file.name
            shutil.copy2(img_file, dest_img)

            # 复制对应的标签文件
            label_file = label_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                dest_label = source_path / split_name / 'labels' / label_file.name
                shutil.copy2(label_file, dest_label)
                count += 1

        return count

    # 执行复制
    train_count = copy_files(train_files, 'train')
    val_count = copy_files(val_files, 'val')
    test_count = copy_files(test_files, 'test')

    # 输出统计信息
    print("数据集分割完成！")
    print(f"训练集: {train_count} 对文件")
    print(f"验证集: {val_count} 对文件")
    print(f"测试集: {test_count} 对文件")

if __name__ == "__main__":
    split_dataset() 