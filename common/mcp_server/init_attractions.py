"""景点数据初始化脚本。

读取 mock_data/attractions/*.json 中的景点数据，向量化后存入 ChromaDB。
导入后，search_attractions 工具可通过 ChromaDB 向量检索获得更精确的匹配结果。

用法：
  uv run python -m common.mcp_server.init_attractions

注意：需要 Ollama 运行中且已加载 qwen3-embedding:8b 或配置的 Embedding 模型。
如果 Embedding 服务不可用，search_attractions 会回退到 JSON 文件直接读取。
"""

import json
import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common.vector_store import add_attractions


def _check_embedding() -> bool:
    """检查 Embedding 服务是否可用。"""
    try:
        from common.embedding_client import embedding

        embedding.embed_texts(["测试"])
        return True
    except Exception as e:
        print(f"⚠️  Embedding 服务不可用：{e}")
        print("   工具将使用 JSON 文件直接读取，结果不受影响。")
        print("   如需启用向量检索，请启动 Ollama：ollama serve")
        return False


def init():
    """读取景点 JSON 文件，向量化并存入 ChromaDB。"""
    if not _check_embedding():
        print("\n💡 跳过 ChromaDB 导入，search_attractions 会回退到 JSON 读取。")
        return

    attractions_dir = Path(__file__).parent / "mock_data" / "attractions"
    json_files = sorted(attractions_dir.glob("*.json"))

    if not json_files:
        print(f"❌ 未找到景点数据文件：{attractions_dir}")
        return

    total = 0
    for file_path in json_files:
        city_name = file_path.stem  # 拼音文件名
        print(f"📄 处理 {city_name}...", end=" ")

        with open(file_path, encoding="utf-8") as f:
            attractions = json.load(f)

        # 构造向量化文本：名称 + 类别 + 描述 + 偏好的组合
        texts = [
            f"{a['name']} {a['category']} {a['description']} 适合：{'、'.join(a.get('preferences', []))}"
            for a in attractions
        ]

        # 写入 ChromaDB（collection 名称为 "attractions"）
        try:
            add_attractions(city_name, attractions, texts)
            print(f"✅ {len(attractions)} 个景点")
            total += len(attractions)
        except Exception as e:
            print(f"❌ 失败：{e}")

    print(f"\n🎉 完成！共导入 {total} 个景点到 ChromaDB（collection: attractions）")


if __name__ == "__main__":
    init()
