import os
import sys
import logging

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from backend.app import create_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("正在创建应用实例...")
        app = create_app()
        
        # 获取端口，默认为5000
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"应用将在端口 {port} 上启动")
        
        # 启动应用
        logger.info("正在启动应用...")
        app.run(
            host='0.0.0.0',  # 允许外部访问
            port=port,
            debug=False
        )
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 