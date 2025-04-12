import os
from pathlib import Path

def process_empty_labels(labels_dir="../data/labels"):
    """
    处理空的标签文件
    :param labels_dir: 标签文件目录
    """
    labels_path = Path(labels_dir)
    if not labels_path.exists():
        print(f"目录不存在: {labels_dir}")
        return

    empty_files = []
    processed = 0

    # 遍历所有txt文件
    for txt_file in labels_path.glob("*.txt"):
        if txt_file.stat().st_size == 0:
            empty_files.append(txt_file.name)
            txt_file.unlink()  # 删除空文件
            processed += 1

    # 输出处理结果
    print(f"处理完成！共删除 {processed} 个空标签文件")
    if empty_files:
        print("\n已删除的文件：")
        for f in empty_files:
            print(f"- {f}")

if __name__ == "__main__":
    process_empty_labels() 