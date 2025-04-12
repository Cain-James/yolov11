import os
import sys
import urllib.request
import shutil
from pathlib import Path

def install_simhei_font():
    """下载并安装SimHei字体供OpenCV使用"""
    
    print("开始安装SimHei字体...")
    
    # 确定字体保存位置
    font_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "fonts"
    font_path = font_dir / "SimHei.ttf"
    
    # 创建字体目录
    os.makedirs(font_dir, exist_ok=True)
    
    # 如果字体已存在，则跳过下载
    if font_path.exists():
        print(f"字体已存在: {font_path}")
        return str(font_path)
    
    # 下载字体
    try:
        # SimHei字体下载地址
        font_url = "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf"
        print(f"正在从 {font_url} 下载字体...")
        
        # 下载字体文件
        urllib.request.urlretrieve(font_url, font_path)
        print(f"字体下载成功: {font_path}")
        
        return str(font_path)
    except Exception as e:
        print(f"下载字体失败: {str(e)}")
        
        # 如果下载失败，尝试在系统中查找字体
        system_fonts = []
        
        # Linux系统字体路径
        if sys.platform.startswith('linux'):
            system_fonts.extend([
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Debian/Ubuntu
                "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",  # CentOS/Fedora
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc"
            ])
        # MacOS系统字体路径
        elif sys.platform == 'darwin':
            system_fonts.extend([
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial Unicode.ttf"
            ])
        # Windows系统字体路径
        elif sys.platform == 'win32':
            system_fonts.extend([
                "C:\\Windows\\Fonts\\simhei.ttf",
                "C:\\Windows\\Fonts\\msyh.ttf"
            ])
        
        # 尝试查找可用的系统字体
        for system_font in system_fonts:
            if os.path.exists(system_font):
                print(f"找到系统字体: {system_font}")
                # 复制系统字体到项目目录
                shutil.copy2(system_font, font_path)
                print(f"已复制字体到: {font_path}")
                return str(font_path)
        
        print("警告: 无法找到合适的中文字体，将使用默认字体。这可能导致中文显示不正确。")
        return None

if __name__ == "__main__":
    font_path = install_simhei_font()
    if font_path:
        print(f"字体安装成功: {font_path}")
    else:
        print("字体安装失败，请手动安装SimHei.ttf字体") 