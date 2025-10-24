#!/usr/bin/env python3
"""
测试完整的CRM Pipeline流程：从抓取数据到生成内容
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.controllers.scraping_controller import get_scraping_controller
from app.services.data_aggregator import get_data_aggregator
from app.services.generator_service import get_generator_service
from app.services.data_store import get_data_store
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_full_pipeline():
    """测试完整的CRM Pipeline流程"""
    
    print("🚀 开始测试完整的CRM Pipeline流程")
    print("=" * 60)
    
    # Test company
    company_name = "Tesla"
    
    try:
        # Step 1: 抓取数据
        print(f"\n📡 Step 1: 抓取 {company_name} 的数据...")
        controller = get_scraping_controller()
        
        scrape_result = await controller.scrape_company(
            company_name=company_name,
            include_news=True,
            include_case_studies=True,
            max_urls=5,  # 限制URL数量以加快测试
            save_to_file=True  # 保存到文件
        )
        
        print(f"✅ 抓取完成!")
        print(f"   - 找到URL数量: {scrape_result['total_urls_found']}")
        print(f"   - 成功抓取: {scrape_result['successful_scrapes']}")
        print(f"   - 保存文件: {scrape_result.get('saved_filepath', 'N/A')}")
        
        # 显示内容处理统计
        content_processing = scrape_result.get('content_processing', {})
        print(f"   - 处理的内容项: {content_processing.get('processed_items', 0)}/{content_processing.get('total_items', 0)}")
        
        # Step 2: 验证保存的数据
        print(f"\n💾 Step 2: 验证保存的数据...")
        data_store = get_data_store()
        saved_data = data_store.load_latest_scraped_data(company_name)
        
        if saved_data:
            print(f"✅ 成功加载保存的数据")
            print(f"   - 公司名称: {saved_data['company_name']}")
            print(f"   - 官方网站: {saved_data.get('official_website', 'N/A')}")
            print(f"   - 内容项数量: {len(saved_data.get('scraped_content', []))}")
            
            # 检查是否有处理后的数据
            processed_items = [item for item in saved_data.get('scraped_content', []) 
                             if 'processed_markdown' in item]
            print(f"   - 已处理的内容项: {len(processed_items)}")
            
            # 显示第一个内容项的统计
            if processed_items:
                first_item = processed_items[0]
                print(f"   - 第一个内容项:")
                print(f"     URL: {first_item.get('url', 'N/A')}")
                print(f"     类型: {first_item.get('content_type', 'N/A')}")
                print(f"     原始长度: {first_item.get('original_markdown_length', 0)}")
                print(f"     处理后长度: {first_item.get('processed_markdown_length', 0)}")
                print(f"     压缩比例: {first_item.get('compression_ratio', 0):.2f}")
        else:
            print("❌ 无法加载保存的数据")
            return
        
        # Step 3: 准备上下文
        print(f"\n🔧 Step 3: 准备生成上下文...")
        data_aggregator = get_data_aggregator()
        
        context = await data_aggregator.prepare_context(
            company_name=company_name,
            max_chars=8000,  # 限制上下文长度
            include_news=True,
            include_case_studies=True,
            max_urls=5
        )
        
        print(f"✅ 上下文准备完成!")
        print(f"   - 上下文长度: {len(context)} 字符")
        print(f"   - 上下文预览: {context[:200]}...")
        
        # Step 4: 生成内容
        print(f"\n🎯 Step 4: 生成Persona内容...")
        generator_service = get_generator_service()
        
        generation_result = await generator_service.generate(
            generator_type="personas",
            company_name=company_name,
            generate_count=2,  # 生成2个persona
            max_context_chars=8000,
            include_news=True,
            include_case_studies=True,
            max_urls=5
        )
        
        print(f"✅ 内容生成完成!")
        print(f"   - 生成结果: {generation_result.get('success', False)}")
        
        if generation_result.get('success'):
            result_data = generation_result.get('result', {})
            personas = result_data.get('personas', [])
            print(f"   - 生成的Persona数量: {len(personas)}")
            print(f"   - 保存文件: {generation_result.get('saved_filepath', 'N/A')}")
            
            # 显示第一个persona的概要
            if personas:
                first_persona = personas[0]
                print(f"   - 第一个Persona:")
                print(f"     名称: {first_persona.get('name', 'N/A')}")
                print(f"     职位: {first_persona.get('title', 'N/A')}")
                print(f"     层级: {first_persona.get('tier', 'N/A')}")
                print(f"     痛点: {first_persona.get('pain_points', [])[:2]}...")  # 只显示前2个
        
        # Step 5: 显示完整流程总结
        print(f"\n📊 Step 5: 流程总结")
        print("=" * 60)
        print(f"✅ 完整流程测试成功!")
        print(f"   - 公司: {company_name}")
        print(f"   - 抓取URL: {scrape_result['total_urls_found']}")
        print(f"   - 成功抓取: {scrape_result['successful_scrapes']}")
        print(f"   - 内容处理: {content_processing.get('processed_items', 0)} 项")
        print(f"   - 上下文长度: {len(context)} 字符")
        print(f"   - 生成Persona: {len(personas) if generation_result.get('success') else 0} 个")
        print(f"   - 保存文件: {scrape_result.get('saved_filepath', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.exception("Full pipeline test failed")
        return False


async def test_data_flow():
    """测试数据流"""
    print(f"\n🔍 测试数据流...")
    
    company_name = "Tesla"
    data_store = get_data_store()
    
    # 检查是否有保存的数据
    saved_data = data_store.load_latest_scraped_data(company_name)
    if not saved_data:
        print("❌ 没有找到保存的数据，请先运行抓取测试")
        return False
    
    print(f"✅ 找到保存的数据")
    
    # 检查数据结构
    scraped_content = saved_data.get('scraped_content', [])
    processed_items = [item for item in scraped_content if 'processed_markdown' in item]
    
    print(f"   - 总内容项: {len(scraped_content)}")
    print(f"   - 已处理项: {len(processed_items)}")
    
    # 显示处理统计
    if processed_items:
        total_original = sum(item.get('original_markdown_length', 0) for item in processed_items)
        total_processed = sum(item.get('processed_markdown_length', 0) for item in processed_items)
        avg_compression = total_processed / total_original if total_original > 0 else 0
        
        print(f"   - 原始总长度: {total_original}")
        print(f"   - 处理后总长度: {total_processed}")
        print(f"   - 平均压缩比例: {avg_compression:.2f}")
    
    return True


if __name__ == "__main__":
    print("🧪 CRM Pipeline 完整流程测试")
    print("=" * 60)
    
    async def main():
        # 测试完整流程
        success = await test_full_pipeline()
        
        if success:
            # 测试数据流
            await test_data_flow()
        
        print(f"\n🎉 测试完成!")
    
    # 运行测试
    asyncio.run(main())


