#!/usr/bin/env python3
"""测试language参数为必填"""

import asyncio
from paddleocr_cli.mcp_server import handle_call_tool, handle_list_tools

async def test():
    # 1. 测试工具定义中language是否为required
    tools = await handle_list_tools()
    tool = tools[0]
    print("1. 工具定义测试:")
    print(f"   required字段: {tool.inputSchema['required']}")
    print(f"   language在required中: {'language' in tool.inputSchema['required']}")
    
    # 2. 测试不提供language参数是否报错
    print("\n2. 测试不提供language参数:")
    try:
        result = await handle_call_tool('ocr_image', {'image_path': 'c9c2184db3e2483fbd406a8ae3bf8f11.png'})
        print("   ✗ 应该报错但没有报错")
    except ValueError as e:
        print(f"   ✓ 正确报错: {e}")
    
    # 3. 测试提供language参数
    print("\n3. 测试提供language='ch':")
    try:
        result = await handle_call_tool('ocr_image', {'image_path': 'c9c2184db3e2483fbd406a8ae3bf8f11.png', 'language': 'ch'})
        print(f"   ✓ 成功，输出文件: {result[0].text}")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

asyncio.run(test())
