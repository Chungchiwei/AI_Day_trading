"""
Perplexity API 連線測試程式 - 更新版
"""

import os
import requests
from dotenv import load_dotenv

def get_available_models():
    """獲取當前可用的模型列表"""
    
    # 根據 Perplexity 最新文檔的模型名稱
    return {
        "online_models": [
            "sonar",                    # 最新的線上搜尋模型
            "sonar-pro",                # 專業版線上搜尋
        ],
        "chat_models": [
            "sonar-reasoning",          # 推理模型
            "sonar-reasoning-pro",      # 專業推理模型
        ],
        "research_models": [
            "sonar-deep-research",      # 深度研究模型
        ]
    }

def test_perplexity_api():
    """測試 Perplexity API 連線"""
    
    print("=" * 60)
    print("🔍 Perplexity API 連線測試")
    print("=" * 60)
    
    # 載入環境變數
    load_dotenv()
    api_key = os.getenv('PERPLEXITY_API_KEY')
    
    # 1. 檢查 API Key 是否存在
    print("\n1️⃣ 檢查 API Key...")
    if not api_key:
        print("❌ 錯誤: 找不到 PERPLEXITY_API_KEY")
        print("   請在 .env 文件中設定:")
        print("   PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        return False
    
    print(f"✅ API Key 已設定")
    print(f"   前綴: {api_key[:10]}...")
    print(f"   長度: {len(api_key)} 字元")
    
    # 2. 測試可用的模型
    print("\n2️⃣ 測試可用模型...")
    
    models_to_test = [
        "sonar",                # 最基本的線上模型
        "sonar-pro",            # 專業版
        "sonar-reasoning",      # 推理模型
    ]
    
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    success_models = []
    failed_models = []
    
    for model in models_to_test:
        print(f"\n   測試模型: {model}")
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": "Say 'Hello' in one word."
                }
            ],
            "max_tokens": 10,
            "temperature": 0.0,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print(f"   ✅ {model} - 可用")
                
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0].get('message', {}).get('content', '')
                    print(f"      回應: {content}")
                
                if 'usage' in data:
                    usage = data['usage']
                    print(f"      Token: {usage.get('total_tokens', 0)}")
                
                success_models.append(model)
                
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', '')
                
                if 'Invalid model' in error_msg:
                    print(f"   ❌ {model} - 模型不存在")
                else:
                    print(f"   ❌ {model} - 錯誤: {error_msg}")
                
                failed_models.append(model)
                
            elif response.status_code == 401:
                print(f"   ❌ 認證失敗 (401)")
                print(f"      您的 API Key 可能無效")
                return False
                
            else:
                print(f"   ❌ {model} - HTTP {response.status_code}")
                failed_models.append(model)
                
        except requests.exceptions.Timeout:
            print(f"   ⚠️ {model} - 請求超時")
            failed_models.append(model)
            
        except Exception as e:
            print(f"   ❌ {model} - 錯誤: {str(e)}")
            failed_models.append(model)
    
    # 3. 顯示測試結果
    print("\n" + "=" * 60)
    print("📊 測試結果")
    print("=" * 60)
    
    if success_models:
        print(f"\n✅ 可用模型 ({len(success_models)}):")
        for model in success_models:
            print(f"   - {model}")
    
    if failed_models:
        print(f"\n❌ 不可用模型 ({len(failed_models)}):")
        for model in failed_models:
            print(f"   - {model}")
    
    return len(success_models) > 0


def show_latest_models():
    """顯示最新的模型資訊"""
    
    print("\n" + "=" * 60)
    print("📋 Perplexity 最新模型列表 (2024)")
    print("=" * 60)
    
    models = get_available_models()
    
    print("\n🌐 線上搜尋模型 (Online Models):")
    for model in models['online_models']:
        print(f"   • {model}")
        if model == "sonar":
            print("     └─ 基礎線上搜尋模型，支援即時網路資訊")
        elif model == "sonar-pro":
            print("     └─ 專業版，更強大的搜尋和分析能力")
    
    print("\n💭 對話/推理模型 (Chat/Reasoning Models):")
    for model in models['chat_models']:
        print(f"   • {model}")
        if model == "sonar-reasoning":
            print("     └─ 推理模型，適合複雜分析")
        elif model == "sonar-reasoning-pro":
            print("     └─ 專業推理模型，最強分析能力")
    
    print("\n🔬 研究模型 (Research Models):")
    for model in models['research_models']:
        print(f"   • {model}")
        if model == "sonar-deep-research":
            print("     └─ 深度研究模型，適合專題研究")
    
    print("\n" + "=" * 60)
    print("💡 建議使用策略")
    print("=" * 60)
    
    print("""
1. **新聞搜尋**: 使用 sonar (最省 Token)
2. **技術分析**: 使用 sonar-reasoning (不需聯網)
3. **綜合分析**: 使用 sonar-pro (含新聞)
4. **深度研究**: 使用 sonar-deep-research (重大事件)

⚠️ 注意: 模型名稱可能隨時更新，請參考官方文檔
    """)


def show_api_info():
    """顯示 API 相關資訊"""
    
    print("\n" + "=" * 60)
    print("ℹ️  API 資訊")
    print("=" * 60)
    
    print("\n🔗 相關連結:")
    print("   - API 設定: https://www.perplexity.ai/settings/api")
    print("   - 官方文檔: https://docs.perplexity.ai/")
    print("   - 模型列表: https://docs.perplexity.ai/guides/model-cards")
    print("   - 定價資訊: https://www.perplexity.ai/pricing")
    
    print("\n💡 使用提示:")
    print("   1. 免費帳戶有請求次數限制")
    print("   2. 建議從最小的模型開始測試")
    print("   3. 查看官方文檔確認最新模型名稱")
    print("   4. 使用 search_domain_filter 可以過濾搜尋來源")


def main():
    """主函數"""
    
    # 測試 API 連線
    success = test_perplexity_api()
    
    # 顯示最新模型
    show_latest_models()
    
    # 顯示 API 資訊
    show_api_info()
    
    # 總結
    print("\n" + "=" * 60)
    if success:
        print("✅ 測試完成: 至少有一個模型可用")
        print("\n建議: 使用測試成功的模型更新您的程式碼")
    else:
        print("❌ 測試完成: 所有模型都無法使用")
        print("\n建議:")
        print("1. 檢查 API Key 是否正確")
        print("2. 前往官方文檔查看最新模型名稱")
        print("3. 確認帳戶是否有足夠的配額")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    main()
