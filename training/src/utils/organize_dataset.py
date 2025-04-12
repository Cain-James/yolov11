import os
import shutil
from pathlib import Path

def check_disk_space(path, min_space_gb=1):
    """检查目标路径所在磁盘的剩余空间"""
    usage = shutil.disk_usage(path)
    if usage.free < min_space_gb * 1024**3:
        raise RuntimeError(f"磁盘空间不足，需要至少 {min_space_gb}GB 剩余空间")

def organize_dataset(source_dir="../data/raw", img_ext=('.jpg', '.jpeg', '.png', '.bmp'), label_ext=('.txt')):
    """
    整理数据集文件到标准目录结构
    :param source_dir: 原始数据集目录
    :param img_ext: 支持的图片扩展名
    :param label_ext: 支持的标签扩展名
    """
    # 定义目标目录
    dest_dir = Path("../data")
    img_dir = dest_dir / "images"
    label_dir = dest_dir / "labels"
    
    # 创建目标目录
    img_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    # 在遍历文件前调用
    check_disk_space(str(dest_dir), min_space_gb=5)

    # 统计计数器
    file_count = 0
    error_files = []

    # 遍历源目录
    for root, _, files in os.walk(source_dir):
        # 跳过已创建的目标目录
        if str(root).startswith(str(img_dir)) or str(root).startswith(str(label_dir)):
            continue

        for file in files:
            file_path = Path(root) / file
            stem = file_path.stem
            ext = file_path.suffix.lower()

            try:
                # 处理图片文件
                if ext in img_ext:
                    dest = img_dir / file
                    if dest.exists():
                        new_name = f"{stem}_{hash(file_path)}{ext}"
                        dest = img_dir / new_name
                    shutil.copy2(file_path, dest)
                    file_count += 1

                # 处理标签文件
                elif ext in label_ext:
                    dest = label_dir / file
                    if dest.exists():
                        new_name = f"{stem}_{hash(file_path)}{ext}"
                        dest = label_dir / new_name
                    shutil.copy2(file_path, dest)
                    file_count += 1

            except Exception as e:
                error_files.append((file_path, str(e)))

    # 输出统计信息
    print(f"处理完成！共整理 {file_count} 个文件")
    if error_files:
        print("\n以下文件处理失败：")
        for f, e in error_files:
            print(f"- {f}: {e}")

if __name__ == "__main__":
    organize_dataset() 